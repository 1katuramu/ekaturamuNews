import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import json
import time

class TechTrendsMonitor:
    def __init__(self):
        self.email_user = os.environ.get('EMAIL_USER')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.recipient_email = os.environ.get('RECIPIENT_EMAIL')
        self.newsapi_key = os.environ.get('NEWSAPI_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.sent_log_file = 'sent_trends_log.json'

    def load_sent_urls(self):
        if not os.path.exists(self.sent_log_file):
            return set()
        with open(self.sent_log_file, 'r') as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()

    def save_sent_urls(self, urls):
        with open(self.sent_log_file, 'w') as f:
            json.dump(list(urls), f)

    def get_hacker_news_ai_posts(self):
        try:
            url = "https://hn.algolia.com/api/v1/search?query=AI%20OR%20machine%20learning%20OR%20data%20science%20OR%20artificial%20intelligence&tags=story&hitsPerPage=10"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            posts = []
            for hit in data.get('hits', []):
                if hit.get('title') and hit.get('url'):
                    posts.append({
                        'title': hit['title'],
                        'url': hit['url'],
                        'points': hit.get('points', 0),
                        'source': 'Hacker News'
                    })
            return posts
        except Exception as e:
            print(f"Error fetching Hacker News: {e}")
            return []

    def get_reddit_ml_posts(self):
        try:
            subreddits = ['MachineLearning', 'artificial', 'datascience']
            all_posts = []
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=5"
                response = requests.get(url, headers=self.headers, timeout=10)
                data = response.json()
                for post in data.get('data', {}).get('children', []):
                    post_data = post.get('data', {})
                    if post_data.get('title') and not post_data.get('is_self'):
                        all_posts.append({
                            'title': post_data['title'],
                            'url': f"https://reddit.com{post_data['permalink']}",
                            'points': post_data.get('score', 0),
                            'source': f'r/{subreddit}'
                        })
                time.sleep(1)
            return all_posts
        except Exception as e:
            print(f"Error fetching Reddit posts: {e}")
            return []

    def get_arxiv_papers(self):
        try:
            url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CV+OR+cat:cs.CL&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url, timeout=10)
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            papers = []
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                link = entry.find('{http://www.w3.org/2005/Atom}id').text
                papers.append({
                    'title': title,
                    'url': link,
                    'points': 0,
                    'source': 'arXiv'
                })
            return papers
        except Exception as e:
            print(f"Error fetching arXiv papers: {e}")
            return []

    def get_newsapi_articles(self):
        if not self.newsapi_key:
            print("NewsAPI key not found, skipping news articles")
            return []
        try:
            keywords = "artificial intelligence OR machine learning OR data science OR deep learning OR neural networks OR AI"
            url = f"https://newsapi.org/v2/everything?q={keywords}&sortBy=popularity&language=en&pageSize=10&apiKey={self.newsapi_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get('status') != 'ok':
                print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            articles = []
            for article in data.get('articles', []):
                if article.get('title') and article.get('url') and '[Removed]' not in article['title']:
                    articles.append({
                        'title': article['title'],
                        'url': article['url'],
                        'points': 0,
                        'source': f"News: {article.get('source', {}).get('name', 'Unknown')}"
                    })
            return articles
        except Exception as e:
            print(f"Error fetching NewsAPI articles: {e}")
            return []

    def get_github_trending(self):
        try:
            url = "https://api.github.com/search/repositories?q=machine+learning+OR+artificial+intelligence+OR+data+science&sort=stars&order=desc&per_page=5"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            repos = []
            for repo in data.get('items', []):
                repos.append({
                    'title': f"{repo['name']} - {repo['description'][:100]}..." if repo.get('description') else repo['name'],
                    'url': repo['html_url'],
                    'points': repo.get('stargazers_count', 0),
                    'source': 'GitHub Trending'
                })
            return repos
        except Exception as e:
            print(f"Error fetching GitHub trending: {e}")
            return []

    def compile_trends(self):
        print("Fetching trends from various sources...")
        all_trends = (
            self.get_hacker_news_ai_posts() +
            self.get_reddit_ml_posts() +
            self.get_arxiv_papers() +
            self.get_github_trending() +
            self.get_newsapi_articles()
        )

        sent_urls = self.load_sent_urls()
        new_trends = [item for item in all_trends if item['url'] not in sent_urls]
        new_trends.sort(key=lambda x: x['points'], reverse=True)
        return new_trends[:20]

    def create_email_content(self, trends):
        current_date = datetime.now().strftime("%B %d, %Y")
        html_content = f"""
        <html><body>
        <h2> KATURAMU Daily AI/ML Tech Trends - {current_date}</h2>
        <p>Here are the top new stories:</p>
        <ul>
        """
        for i, trend in enumerate(trends, 1):
            points = f"⭐ {trend['points']}" if trend['points'] > 0 else ""
            html_content += f"<li><a href='{trend['url']}' target='_blank'>{trend['title']}</a> - {trend['source']} {points}</li>"
        html_content += "</ul><p><em>This email was automatically generated.</em></p></body></html>"
        return html_content

    def send_email(self, trends):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f" KATURAMU Daily AI/ML Tech Trends - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            html_content = self.create_email_content(trends)
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            print(f"✅ Email sent successfully to {self.recipient_email}")
            return True
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False

    def run(self):
        print("🔍 Starting Tech Trends Monitor...")

        if not all([self.email_user, self.email_password, self.recipient_email]):
            print("❌ Missing environment variables.")
            return False

        trends = self.compile_trends()
        print(f"📊 Found {len(trends)} new trends.")

        if not trends:
            print("📭 No new content to send.")
            return False

        if self.send_email(trends):
            sent_urls = self.load_sent_urls()
            sent_urls.update([t['url'] for t in trends])
            self.save_sent_urls(sent_urls)
            print("🎉 Done!")
            return True
        else:
            return False

if __name__ == "__main__":
    monitor = TechTrendsMonitor()
    monitor.run()
