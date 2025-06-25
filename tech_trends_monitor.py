import requests
import smtplib
import os
import json
import time
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from xml.etree import ElementTree as ET

# === Setup Logging ===
logging.basicConfig(
    filename='tech_trends.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

class TechTrendsMonitor:
    def __init__(self):
        self.email_user = os.environ.get('EMAIL_USER')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.recipient_email = os.environ.get('RECIPIENT_EMAIL')
        self.newsapi_key = os.environ.get('NEWSAPI_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        self.sent_log_file = 'sent_trends_log.json'

    def load_sent_urls(self):
        if not os.path.exists(self.sent_log_file):
            return set()
        try:
            with open(self.sent_log_file, 'r') as f:
                return set(json.load(f))
        except Exception as e:
            logging.error(f"Failed to load sent URLs: {e}")
            return set()

    def save_sent_urls(self, urls):
        try:
            with open(self.sent_log_file, 'w') as f:
                json.dump(list(urls), f)
        except Exception as e:
            logging.error(f"Failed to save sent URLs: {e}")

    def get_hacker_news_ai_posts(self):
        try:
            url = "https://hn.algolia.com/api/v1/search?query=AI%20OR%20machine%20learning&tags=story&hitsPerPage=10"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            return [
                {'title': hit['title'], 'url': hit['url'], 'points': hit.get('points', 0), 'source': 'Hacker News'}
                for hit in data.get('hits', []) if hit.get('title') and hit.get('url')
            ]
        except Exception as e:
            logging.error(f"Hacker News error: {e}")
            return []

    def get_reddit_ml_posts(self):
        try:
            posts = []
            for subreddit in ['MachineLearning', 'artificial', 'datascience']:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
                response = requests.get(url, headers=self.headers, timeout=10)
                data = response.json()
                for post in data.get('data', {}).get('children', []):
                    d = post['data']
                    if not d.get('is_self'):
                        posts.append({
                            'title': d['title'],
                            'url': f"https://reddit.com{d['permalink']}",
                            'points': d.get('score', 0),
                            'source': f'r/{subreddit}'
                        })
                time.sleep(1)
            return posts
        except Exception as e:
            logging.error(f"Reddit error: {e}")
            return []

    def get_arxiv_papers(self):
        try:
            url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            return [
                {'title': entry.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                 'url': entry.find('{http://www.w3.org/2005/Atom}id').text,
                 'points': 0,
                 'source': 'arXiv'}
                for entry in root.findall('{http://www.w3.org/2005/Atom}entry')
            ]
        except Exception as e:
            logging.error(f"arXiv error: {e}")
            return []

    def get_newsapi_articles(self):
        if not self.newsapi_key:
            logging.warning("NewsAPI key not provided.")
            return []
        try:
            keywords = "artificial intelligence OR machine learning OR data science"
            url = f"https://newsapi.org/v2/everything?q={keywords}&sortBy=popularity&language=en&pageSize=10&apiKey={self.newsapi_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get('status') != 'ok':
                logging.error(f"NewsAPI error: {data.get('message')}")
                return []
            return [
                {'title': a['title'], 'url': a['url'], 'points': 0, 'source': f"News: {a['source']['name']}"}
                for a in data.get('articles', [])
                if a.get('title') and a.get('url') and '[Removed]' not in a['title']
            ]
        except Exception as e:
            logging.error(f"NewsAPI exception: {e}")
            return []

    def get_github_trending(self):
        try:
            url = "https://api.github.com/search/repositories?q=machine+learning&sort=stars&order=desc&per_page=5"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            return [
                {'title': f"{r['name']} - {r['description'][:80]}..." if r['description'] else r['name'],
                 'url': r['html_url'],
                 'points': r.get('stargazers_count', 0),
                 'source': 'GitHub'}
                for r in data.get('items', [])
            ]
        except Exception as e:
            logging.error(f"GitHub error: {e}")
            return []

    def compile_trends(self):
        logging.info("Fetching trends...")
        all_items = (
            self.get_hacker_news_ai_posts() +
            self.get_reddit_ml_posts() +
            self.get_arxiv_papers() +
            self.get_newsapi_articles() +
            self.get_github_trending()
        )
        sent_urls = self.load_sent_urls()
        new_items = [item for item in all_items if item['url'] not in sent_urls]
        new_items.sort(key=lambda x: x['points'], reverse=True)
        logging.info(f"Filtered {len(new_items)} new items.")
        return new_items[:20]

    def create_email_content(self, trends):
        date = datetime.now().strftime("%B %d, %Y")
        html = f"<html><body><h2> Daily AI/ML Trends - {date}</h2><ul>"
        for i, t in enumerate(trends, 1):
            score = f"⭐ {t['points']}" if t['points'] else ""
            html += f"<li><a href='{t['url']}'>{t['title']}</a> - {t['source']} {score}</li>"
        html += "</ul><p><i>Auto-generated daily digest</i></p></body></html>"
        return html

    def send_email(self, trends):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f" AI/ML Trends - {datetime.now().strftime('%b %d, %Y')}"
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            msg.attach(MIMEText(self.create_email_content(trends), 'html'))

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            logging.info("Email sent successfully.")
            return True
        except Exception as e:
            logging.error(f"Email error: {e}")
            return False

    def run(self):
        logging.info("=== Starting Daily Tech Trends Monitor ===")
        if not all([self.email_user, self.email_password, self.recipient_email]):
            logging.error("Missing environment variables.")
            return False

        trends = self.compile_trends()
        if not trends:
            logging.warning("No new trends to send.")
            return False

        if self.send_email(trends):
            sent_urls = self.load_sent_urls()
            sent_urls.update([t['url'] for t in trends])
            self.save_sent_urls(sent_urls)
            logging.info("Sent URLs saved.")
            return True
        return False

if __name__ == "__main__":
    monitor = TechTrendsMonitor()
    monitor.run()
