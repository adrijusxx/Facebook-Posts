"""
News fetching system for USA trucking industry news
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
from newspaper import Article
from models import db, Post, NewsSource, PostingLog
import hashlib
import re
from ai_content_enhancer import AIContentEnhancer

logger = logging.getLogger(__name__)

class NewsFetcher:
    """Fetches news from various sources about USA trucking industry"""
    
    def __init__(self):
        self.trucking_keywords = [
            'trucking', 'logistics', 'freight', 'transportation', 'shipping', 
            'supply chain', 'cargo', 'delivery', 'fleet', 'driver', 'trucker',
            'commercial vehicle', 'semi truck', 'trailer', 'dispatch',
            'CDL', 'DOT', 'FMCSA', 'hours of service', 'ELD'
        ]
        self.ai_enhancer = AIContentEnhancer()
    
    def fetch_latest_news(self):
        """Fetch latest news from all enabled sources"""
        articles = []
        sources = NewsSource.query.filter_by(enabled=True).all()
        
        for source in sources:
            try:
                if source.type == 'rss':
                    source_articles = self._fetch_from_rss(source)
                else:
                    source_articles = self._fetch_from_website(source)
                
                articles.extend(source_articles)
                source.last_fetched = datetime.utcnow()
                source.total_articles_fetched += len(source_articles)
                
                logger.info(f"Fetched {len(source_articles)} articles from {source.name}")
                
            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                self._log_action('error', f"Failed to fetch from {source.name}: {e}")
        
        # Filter and save unique articles
        saved_articles = self._process_and_save_articles(articles)
        db.session.commit()
        
        return saved_articles
    
    def _fetch_from_rss(self, source):
        """Fetch articles from RSS feed"""
        articles = []
        
        try:
            feed = feedparser.parse(source.url)
            
            for entry in feed.entries[:10]:  # Limit to 10 most recent
                # Check if article is trucking-related
                if self._is_trucking_related(entry.title + ' ' + getattr(entry, 'summary', '')):
                    article = {
                        'title': entry.title,
                        'url': entry.link,
                        'summary': getattr(entry, 'summary', ''),
                        'published': getattr(entry, 'published', ''),
                        'source': source.name
                    }
                    
                    # Try to extract more content
                    try:
                        full_article = Article(entry.link)
                        full_article.download()
                        full_article.parse()
                        
                        if full_article.text:
                            article['content'] = full_article.text[:1000]  # Limit content length
                        if full_article.top_image:
                            article['image_url'] = full_article.top_image
                            
                    except Exception as e:
                        logger.warning(f"Could not extract full content for {entry.link}: {e}")
                        article['content'] = article['summary']
                    
                    articles.append(article)
                    
        except Exception as e:
            logger.error(f"Error parsing RSS from {source.url}: {e}")
            raise
        
        return articles
    
    def _fetch_from_website(self, source):
        """Fetch articles from website (for non-RSS sources)"""
        articles = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(source.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for article links (this is a basic implementation)
            links = soup.find_all('a', href=True)
            
            for link in links[:20]:  # Limit to 20 links
                href = link.get('href')
                if not href:
                    continue
                
                # Make absolute URL
                if href.startswith('/'):
                    href = f"{source.url.rstrip('/')}{href}"
                elif not href.startswith('http'):
                    continue
                
                # Check if link text suggests trucking content
                link_text = link.get_text().strip()
                if self._is_trucking_related(link_text) and len(link_text) > 10:
                    try:
                        article = Article(href)
                        article.download()
                        article.parse()
                        
                        if article.title and article.text:
                            articles.append({
                                'title': article.title,
                                'url': href,
                                'content': article.text[:1000],
                                'summary': article.text[:300],
                                'image_url': article.top_image,
                                'source': source.name,
                                'published': ''
                            })
                            
                    except Exception as e:
                        logger.warning(f"Could not extract article from {href}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching from website {source.url}: {e}")
            raise
        
        return articles
    
    def _is_trucking_related(self, text):
        """Check if text is related to trucking industry"""
        text_lower = text.lower()
        
        # Check for trucking keywords
        for keyword in self.trucking_keywords:
            if keyword in text_lower:
                return True
        
        # Check for USA-specific content
        usa_indicators = ['usa', 'united states', 'america', 'us ', 'federal', 'dot', 'fmcsa']
        has_usa_indicator = any(indicator in text_lower for indicator in usa_indicators)
        
        # More flexible matching for transportation-related content
        transport_terms = ['transport', 'deliver', 'ship', 'cargo', 'fleet', 'driver']
        has_transport_term = any(term in text_lower for term in transport_terms)
        
        return has_usa_indicator and has_transport_term
    
    def _process_and_save_articles(self, articles):
        """Process and save unique articles to database"""
        saved_articles = []
        
        for article_data in articles:
            # Create a hash of the title and URL to check for duplicates
            content_hash = hashlib.md5(
                (article_data['title'] + article_data['url']).encode()
            ).hexdigest()
            
            # Check if we already have this article
            existing = Post.query.filter_by(title=article_data['title']).first()
            if existing:
                continue
            
            # Create formatted content for Facebook post
            formatted_content = self._format_for_facebook(article_data)
            
            # Create new post
            post = Post(
                title=article_data['title'],
                content=formatted_content,
                url=article_data['url'],
                image_url=article_data.get('image_url'),
                source=article_data['source'],
                status='pending'
            )
            
            db.session.add(post)
            saved_articles.append(article_data)
            
            self._log_action('fetch', f"Saved article: {article_data['title']}")
        
        return saved_articles
    
    def _format_for_facebook(self, article):
        """Format article content for Facebook posting using AI enhancement"""
        from models import Settings
        
        title = article['title']
        content = article.get('content', article.get('summary', ''))
        url = article['url']
        source = article['source']
        
        # Check if AI enhancement is enabled
        settings = Settings.query.first()
        if settings and settings.ai_enhancement_enabled and settings.openai_api_key:
            try:
                # Use AI to enhance the content
                enhanced_content = self.ai_enhancer.enhance_post_content(
                    title, content, url, source
                )
                return enhanced_content
            except Exception as e:
                logger.error(f"AI enhancement failed, using basic formatting: {e}")
                # Fall back to basic formatting
        
        # Basic formatting (fallback)
        # Clean and truncate content
        if content:
            # Remove extra whitespace and newlines
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Truncate to reasonable length for Facebook
            if len(content) > 400:
                content = content[:400] + '...'
        
        # Create Facebook post content
        facebook_post = f"🚛 {title}\n\n"
        
        if content and content != title:
            facebook_post += f"{content}\n\n"
        
        facebook_post += f"Read more: {url}\n\n"
        facebook_post += f"#TruckingNews #Logistics #Transportation #USATrucking #FreightNews"
        
        if source:
            facebook_post += f"\n\nSource: {source}"
        
        return facebook_post
    
    def _log_action(self, action, message, post_id=None):
        """Log an action to the database"""
        log = PostingLog(
            post_id=post_id,
            action=action,
            message=message
        )
        db.session.add(log)
    
    def cleanup_old_posts(self, days_old=30):
        """Clean up old posts to prevent database bloat"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        old_posts = Post.query.filter(Post.created_at < cutoff_date).all()
        
        for post in old_posts:
            db.session.delete(post)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(old_posts)} old posts")