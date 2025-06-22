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
        
    def get_hacker_news_ai_posts(self):
        """Scrape AI/ML related posts from Hacker News"""
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
        """Get posts from Reddit ML/AI subreddits"""
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
                
                time.sleep(1)  # Rate limiting
            
            return all_posts
        except Exception as e:
            print(f"Error fetching Reddit posts: {e}")
            return []
    
    def get_arxiv_papers(self):
        """Get latest AI/ML papers from arXiv"""
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
        """Get AI/ML/Data Science news from NewsAPI"""
        if not self.newsapi_key:
            print("NewsAPI key not found, skipping news articles")
            return []
            
        try:
            # Search for AI/ML related news from the past 24 hours
            keywords = "artificial intelligence OR machine learning OR data science OR deep learning OR neural networks OR AI"
            url = f"https://newsapi.org/v2/everything?q={keywords}&sortBy=popularity&language=en&pageSize=10&apiKey={self.newsapi_key}"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') != 'ok':
                print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = []
            for article in data.get('articles', []):
                if article.get('title') and article.get('url'):
                    # Skip articles with [Removed] title (common in NewsAPI)
                    if '[Removed]' not in article['title']:
                        articles.append({
                            'title': article['title'],
                            'url': article['url'],
                            'points': 0,  # NewsAPI doesn't provide popularity scores
                            'source': f"News: {article.get('source', {}).get('name', 'Unknown')}"
                        })
            
            return articles
        except Exception as e:
            print(f"Error fetching NewsAPI articles: {e}")
            return []
    
    def get_github_trending(self):
        """Get trending AI/ML repositories from GitHub"""
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
        """Compile all trends from different sources"""
        print("Fetching trends from various sources...")
        
        all_trends = []
        
        # Fetch from all sources
        all_trends.extend(self.get_hacker_news_ai_posts())
        all_trends.extend(self.get_reddit_ml_posts())
        all_trends.extend(self.get_arxiv_papers())
        all_trends.extend(self.get_github_trending())
        all_trends.extend(self.get_newsapi_articles())  # Add NewsAPI articles
        
        # Sort by points/popularity
        all_trends.sort(key=lambda x: x['points'], reverse=True)
        
        return all_trends[:20]  # Top 20 trends
    
    def create_email_content(self, trends):
        """Create HTML email content"""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .trend-item {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; background-color: #f9f9f9; }}
                .source {{ color: #666; font-size: 12px; }}
                .points {{ color: #007acc; font-weight: bold; }}
                .title {{ color: #333; font-size: 16px; margin-bottom: 5px; }}
                a {{ color: #007acc; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 Daily AI/ML Tech Trends</h1>
                <p>Your daily digest of the latest in AI, Machine Learning, and Data Science</p>
                <p><strong>Date:</strong> {current_date}</p>
            </div>
        """
        
        if not trends:
            html_content += "<p>No trends found today. Please check your internet connection or try again later.</p>"
        else:
            for i, trend in enumerate(trends, 1):
                points_display = f"⭐ {trend['points']}" if trend['points'] > 0 else ""
                html_content += f"""
                <div class="trend-item">
                    <div class="title"><strong>{i}. <a href="{trend['url']}" target="_blank">{trend['title']}</a></strong></div>
                    <div class="source">Source: {trend['source']} {points_display}</div>
                </div>
                """
        
        html_content += """
            <div style="margin-top: 30px; padding: 20px; background-color: #f4f4f4; border-radius: 5px;">
                <p><strong>💡 Pro Tip:</strong> Click on any title to read the full article or paper!</p>
                <p><em>This email was automatically generated by your Tech Trends Monitor</em></p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_email(self, trends):
        """Send email with trends"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚀 Daily AI/ML Tech Trends - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.email_user
            msg['To'] = self.recipient_email
            
            # Create HTML content
            html_content = self.create_email_content(trends)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
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
        """Main execution function"""
        print("🔍 Starting Tech Trends Monitor...")
        
        # Validate environment variables
        if not all([self.email_user, self.email_password, self.recipient_email]):
            print("❌ Missing required environment variables")
            print("Required: EMAIL_USER, EMAIL_PASSWORD, RECIPIENT_EMAIL")
            return False
        
        # Compile trends
        trends = self.compile_trends()
        print(f"📊 Found {len(trends)} trends")
        
        # Send email
        success = self.send_email(trends)
        
        if success:
            print("🎉 Daily tech trends report sent successfully!")
        else:
            print("😞 Failed to send report")
        
        return success

if __name__ == "__main__":
    monitor = TechTrendsMonitor()
    monitor.run()
