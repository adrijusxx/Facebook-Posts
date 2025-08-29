"""
News fetching system for USA trucking industry news
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta, timezone
from newspaper import Article
from models import db, Post, NewsSource, PostingLog
import hashlib
import re
from ai_content_enhancer import AIContentEnhancer
import time

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
        # Rate limiting settings
        self.min_delay_between_requests = 2  # seconds
        self.last_request_time = 0
    
    def fetch_latest_news(self, max_retries=2):
        """Fetch latest news from all enabled sources with retry logic"""
        articles = []
        sources = NewsSource.query.filter_by(enabled=True).all()
        
        if not sources:
            logger.warning("No enabled news sources found")
            return articles
        
        logger.info(f"Starting news fetch from {len(sources)} enabled sources")
        
        # Try to auto-recover disabled sources before fetching
        self.auto_recover_sources()
        
        for source in sources:
            retry_count = 0
            source_articles = []
            
            while retry_count <= max_retries and not source_articles:
                try:
                    logger.info(f"Processing source: {source.name} (attempt {retry_count + 1})")
                    
                    if source.type == 'rss':
                        source_articles = self._fetch_from_rss(source)
                    else:
                        source_articles = self._fetch_from_website(source)
                    
                    if source_articles:
                        articles.extend(source_articles)
                        source.last_fetched = datetime.now(timezone.utc)
                        source.total_articles_fetched += len(source_articles)
                        
                        logger.info(f"Fetched {len(source_articles)} articles from {source.name}")
                        break  # Success, no need to retry
                    else:
                        logger.warning(f"No articles fetched from {source.name}")
                        if retry_count < max_retries:
                            logger.info(f"Retrying {source.name} in 5 seconds...")
                            time.sleep(5)
                        else:
                            # Still update last_fetched to avoid repeated failures
                            source.last_fetched = datetime.now(timezone.utc)
                            logger.warning(f"Failed to fetch from {source.name} after {max_retries + 1} attempts")
                
                except Exception as e:
                    error_info = self._handle_fetch_error(source, e, retry_count + 1)
                    if retry_count < max_retries:
                        logger.info(f"Retrying {source.name} in 5 seconds... (Error: {error_info['error_type']})")
                        time.sleep(5)
                    else:
                        logger.warning(f"Failed to fetch from {source.name} after {max_retries + 1} attempts: {error_info['error_message']}")
                        
                        # Auto-disable sources with persistent errors (except temporary network issues)
                        if error_info['error_type'] in ['access_denied', 'not_found']:
                            self._consider_disabling_source(source, error_info)
                        
                        # Continue with other sources instead of failing completely
                
                retry_count += 1
        
        # Filter and save unique articles
        if articles:
            saved_articles = self._process_and_save_articles(articles)
            logger.info(f"Successfully processed and saved {len(saved_articles)} articles")
        else:
            logger.warning("No articles were fetched from any source")
            saved_articles = []
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            db.session.rollback()
            # Try to save articles one by one if batch commit fails
            for article in articles:
                try:
                    self._save_single_article(article)
                except Exception as save_e:
                    logger.error(f"Failed to save article {article.get('title', 'Unknown')}: {save_e}")
        
        return saved_articles
    
    def _fetch_from_rss(self, source):
        """Fetch articles from RSS feed"""
        articles = []
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            logger.info(f"Fetching RSS from {source.name}: {source.url}")
            feed = feedparser.parse(source.url)
            
            if not feed.entries:
                logger.warning(f"No entries found in RSS feed for {source.name}")
                return articles
            
            logger.info(f"Found {len(feed.entries)} entries in RSS feed for {source.name}")
            
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
                    
                    # Try to extract more content with better error handling
                    try:
                        full_article = Article(entry.link)
                        # Add more robust headers to avoid 403 errors
                        full_article.config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        full_article.config.request_timeout = 15
                        
                        full_article.download()
                        full_article.parse()
                        
                        if full_article.text:
                            article['content'] = full_article.text[:1000]  # Limit content length
                        if full_article.top_image:
                            article['image_url'] = full_article.top_image
                            
                    except Exception as e:
                        logger.warning(f"Could not extract full content for {entry.link}: {e}")
                        # Use summary as fallback content
                        article['content'] = article['summary']
                        
                        # Try alternative method for blocked sites
                        try:
                            alt_content = self._fetch_with_requests(entry.link)
                            if alt_content:
                                article['content'] = alt_content[:1000]
                        except Exception as alt_e:
                            logger.debug(f"Alternative fetch also failed for {entry.link}: {alt_e}")
                    
                    articles.append(article)
                else:
                    logger.debug(f"Skipping non-trucking article: {entry.title}")
                    
        except Exception as e:
            logger.error(f"Error parsing RSS from {source.url}: {e}")
            raise
        
        logger.info(f"Successfully processed {len(articles)} trucking-related articles from {source.name}")
        return articles
    
    def _fetch_from_website(self, source):
        """Fetch articles from website (for non-RSS sources)"""
        articles = []
        
        try:
            # Apply rate limiting
            self._rate_limit()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = requests.get(source.url, headers=headers, timeout=15)
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
                        # Try newspaper first
                        article = Article(href)
                        article.config.browser_user_agent = headers['User-Agent']
                        article.config.request_timeout = 15
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
                        else:
                            # Fallback to requests method
                            alt_content = self._fetch_with_requests(href)
                            if alt_content:
                                # Try to extract title from the page
                                title = link_text if len(link_text) > 10 else href.split('/')[-1].replace('-', ' ').title()
                                articles.append({
                                    'title': title,
                                    'url': href,
                                    'content': alt_content[:1000],
                                    'summary': alt_content[:300],
                                    'image_url': None,
                                    'source': source.name,
                                    'published': ''
                                })
                            
                    except Exception as e:
                        logger.warning(f"Could not extract article from {href}: {e}")
                        # Try alternative method
                        try:
                            alt_content = self._fetch_with_requests(href)
                            if alt_content:
                                title = link_text if len(link_text) > 10 else href.split('/')[-1].replace('-', ' ').title()
                                articles.append({
                                    'title': title,
                                    'url': href,
                                    'content': alt_content[:1000],
                                    'summary': alt_content[:300],
                                    'image_url': None,
                                    'source': source.name,
                                    'published': ''
                                })
                        except Exception as alt_e:
                            logger.debug(f"Alternative fetch also failed for {href}: {alt_e}")
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
        transport_terms = ['transport', 'deliver', 'ship', 'cargo', 'fleet', 'driver', 'truck', 'logistics', 'freight']
        has_transport_term = any(term in text_lower for term in transport_terms)
        
        # Industry-specific terms that might not be caught by general keywords
        industry_terms = ['cdl', 'eld', 'hours of service', 'commercial vehicle', 'semi', 'trailer', 'dispatch', 'carrier']
        has_industry_term = any(term in text_lower for term in industry_terms)
        
        # If it has industry terms, it's likely relevant regardless of USA context
        if has_industry_term:
            return True
        
        # If it has both transport terms and USA context, it's likely relevant
        if has_transport_term and has_usa_indicator:
            return True
        
        # Additional check for business/economic terms that might indicate industry news
        business_terms = ['market', 'industry', 'business', 'company', 'fleet', 'driver', 'pay', 'salary', 'regulation']
        has_business_term = any(term in text_lower for term in business_terms)
        
        if has_business_term and has_transport_term:
            return True
        
        return False
    
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
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        old_posts = Post.query.filter(Post.created_at < cutoff_date).all()
        
        for post in old_posts:
            db.session.delete(post)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(old_posts)} old posts")

    def _save_single_article(self, article_data):
        """Save a single article to the database"""
        try:
            # Create a hash of the title and URL to check for duplicates
            content_hash = hashlib.md5(
                (article_data['title'] + article_data['url']).encode()
            ).hexdigest()
            
            # Check if we already have this article
            existing = Post.query.filter_by(title=article_data['title']).first()
            if existing:
                logger.debug(f"Article already exists: {article_data['title']}")
                return None
            
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
            db.session.commit()
            
            self._log_action('fetch', f"Saved article: {article_data['title']}")
            logger.info(f"Successfully saved article: {article_data['title']}")
            
            return post
            
        except Exception as e:
            logger.error(f"Error saving single article {article_data.get('title', 'Unknown')}: {e}")
            db.session.rollback()
            return None

    def _fetch_with_requests(self, url):
        """Alternative content fetching method using requests and BeautifulSoup"""
        try:
            # Apply rate limiting for individual article requests
            self._rate_limit()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find article content in common containers
            content_selectors = [
                'article', '.article-content', '.post-content', '.entry-content',
                '.content', '.story-content', '.article-body', '.post-body'
            ]
            
            content = None
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text()
                    break
            
            # If no specific content container found, try to get main content
            if not content:
                # Remove navigation, header, footer, etc.
                for tag in soup(['nav', 'header', 'footer', 'aside', 'menu']):
                    tag.decompose()
                
                # Get text from body or main
                main_content = soup.find('body') or soup.find('main') or soup
                if main_content:
                    content = main_content.get_text()
            
            if content:
                # Clean up the content
                content = re.sub(r'\s+', ' ', content).strip()
                return content
                
        except Exception as e:
            logger.debug(f"Alternative fetch failed for {url}: {e}")
            return None
        
        return None

    def _rate_limit(self):
        """Ensure minimum delay between requests to avoid overwhelming sources"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay_between_requests:
            sleep_time = self.min_delay_between_requests - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def test_rss_source(self, source):
        """Test a specific RSS source and return detailed information"""
        try:
            logger.info(f"Testing RSS source: {source.name} ({source.url})")
            
            import feedparser
            feed = feedparser.parse(source.url)
            
            result = {
                'source_name': source.name,
                'url': source.url,
                'feed_status': getattr(feed, 'status', 'unknown'),
                'feed_bozo': getattr(feed, 'bozo', 'unknown'),
                'feed_bozo_exception': getattr(feed, 'bozo_exception', None),
                'total_entries': len(feed.entries),
                'feed_title': getattr(feed.feed, 'title', 'Unknown'),
                'feed_description': getattr(feed.feed, 'description', 'No description'),
                'entries_preview': []
            }
            
            if feed.entries:
                # Show first few entries for debugging
                for entry in feed.entries[:3]:
                    entry_info = {
                        'title': entry.title,
                        'link': entry.link,
                        'summary': getattr(entry, 'summary', '')[:200] + '...' if getattr(entry, 'summary', '') else 'No summary',
                        'published': getattr(entry, 'published', 'No date'),
                        'is_trucking_related': self._is_trucking_related(entry.title + ' ' + getattr(entry, 'summary', ''))
                    }
                    result['entries_preview'].append(entry_info)
                
                # Count trucking-related entries
                trucking_entries = sum(1 for entry in feed.entries if self._is_trucking_related(entry.title + ' ' + getattr(entry, 'summary', '')))
                result['trucking_entries'] = trucking_entries
                
                logger.info(f"✓ {source.name}: {len(feed.entries)} total entries, {trucking_entries} trucking-related")
            else:
                logger.warning(f"✗ {source.name}: No entries found in RSS feed")
                result['error'] = 'No entries found'
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing RSS source {source.name}: {e}")
            return {
                'source_name': source.name,
                'url': source.url,
                'error': str(e),
                'total_entries': 0
            }

    def _handle_fetch_error(self, source, error, attempt=1):
        """Handle and categorize fetch errors for better debugging"""
        error_str = str(error)
        
        # Categorize errors
        if '403' in error_str or 'Forbidden' in error_str:
            error_type = 'access_denied'
            error_message = f"Access denied (403) - {source.name} may be blocking automated requests"
            logger.warning(f"Access denied for {source.name}: {error_message}")
        elif '404' in error_str or 'Not Found' in error_str:
            error_type = 'not_found'
            error_message = f"RSS feed not found (404) - {source.name} URL may be incorrect"
            logger.warning(f"RSS feed not found for {source.name}: {error_message}")
        elif 'timeout' in error_str.lower() or 'timed out' in error_str.lower():
            error_type = 'timeout'
            error_message = f"Request timeout - {source.name} may be slow or unresponsive"
            logger.warning(f"Timeout for {source.name}: {error_message}")
        elif 'connection' in error_str.lower() or 'refused' in error_str.lower():
            error_type = 'connection_error'
            error_message = f"Connection error - {source.name} may be down or unreachable"
            logger.warning(f"Connection error for {source.name}: {error_message}")
        else:
            error_type = 'unknown'
            error_message = f"Unknown error: {error_str}"
            logger.error(f"Unknown error for {source.name}: {error_message}")
        
        # Log the error with context
        self._log_action('error', f"Fetch attempt {attempt} failed for {source.name}: {error_message}")
        
        return {
            'error_type': error_type,
            'error_message': error_message,
            'source_name': source.name,
            'attempt': attempt
        }
    
    def _consider_disabling_source(self, source, error_info):
        """Consider disabling a news source based on error patterns"""
        try:
            # Check if this source has been failing consistently
            from sqlalchemy import text
            
            # Count recent errors for this source
            recent_errors = db.session.execute(
                text("""
                SELECT COUNT(*) FROM posting_logs 
                WHERE message LIKE :pattern 
                AND timestamp > datetime('now', '-7 days')
                """),
                {'pattern': f'%{source.name}%error%'}
            ).scalar()
            
            # If we have many recent errors and this is a persistent issue, disable the source
            if recent_errors >= 10 and error_info['error_type'] in ['access_denied', 'not_found']:
                logger.warning(f"Disabling {source.name} due to persistent {error_info['error_type']} errors ({recent_errors} in last 7 days)")
                source.enabled = False
                self._log_action('disable', f"Auto-disabled {source.name} due to persistent {error_info['error_type']} errors")
                
        except Exception as e:
            logger.error(f"Error checking source failure history: {e}")
    
    def _get_source_health_status(self):
        """Get health status of all news sources"""
        sources = NewsSource.query.all()
        health_data = []
        
        for source in sources:
            try:
                # Get recent error count
                from sqlalchemy import text
                recent_errors = db.session.execute(
                    text("""
                    SELECT COUNT(*) FROM posting_logs 
                    WHERE message LIKE :pattern 
                    AND timestamp > datetime('now', '-24 hours')
                    """),
                    {'pattern': f'%{source.name}%error%'}
                ).scalar()
                
                # Calculate success rate
                success_rate = 100.0
                if source.total_articles_fetched > 0:
                    success_rate = max(0, 100 - (recent_errors * 10))  # Rough estimation
                
                health_data.append({
                    'name': source.name,
                    'enabled': source.enabled,
                    'last_fetched': source.last_fetched.isoformat() if source.last_fetched else None,
                    'total_articles': source.total_articles_fetched,
                    'recent_errors': recent_errors,
                    'success_rate': success_rate,
                    'status': 'healthy' if recent_errors == 0 else ('warning' if recent_errors < 5 else 'critical')
                })
                
            except Exception as e:
                logger.error(f"Error getting health status for {source.name}: {e}")
                health_data.append({
                    'name': source.name,
                    'enabled': source.enabled,
                    'status': 'unknown',
                    'error': str(e)
                })
        
        return health_data
    
    def auto_recover_sources(self):
        """Automatically re-enable sources that might have recovered"""
        try:
            # Get disabled sources that were auto-disabled
            from sqlalchemy import text
            
            # Find sources that were disabled due to errors but might have recovered
            disabled_sources = NewsSource.query.filter_by(enabled=False).all()
            
            for source in disabled_sources:
                # Check if it's been disabled for more than 24 hours
                if source.last_fetched and (datetime.now(timezone.utc) - source.last_fetched).total_seconds() > 86400:
                    # Test if the source is working now
                    try:
                        test_result = self.test_rss_source(source)
                        if not test_result.get('error') and test_result.get('total_entries', 0) > 0:
                            logger.info(f"Re-enabling {source.name} - appears to be working again")
                            source.enabled = True
                            self._log_action('enable', f"Auto-enabled {source.name} - source appears to be working again")
                    except Exception as e:
                        logger.debug(f"Source {source.name} still not working: {e}")
                        
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error in auto-recovery process: {e}")
            db.session.rollback()

    def validate_rss_feed(self, url):
        """Validate an RSS feed URL and return detailed information"""
        try:
            import feedparser
            feed = feedparser.parse(url)
            
            validation_result = {
                'url': url,
                'is_valid': False,
                'feed_type': 'unknown',
                'issues': [],
                'warnings': [],
                'info': {}
            }
            
            # Check if feed has entries
            if not feed.entries:
                validation_result['issues'].append('No entries found in feed')
                return validation_result
            
            # Check feed structure
            if hasattr(feed.feed, 'title'):
                validation_result['info']['title'] = feed.feed.title
            else:
                validation_result['warnings'].append('No feed title found')
            
            if hasattr(feed.feed, 'description'):
                validation_result['info']['description'] = feed.feed.description
            else:
                validation_result['warnings'].append('No feed description found')
            
            # Check entry structure
            sample_entry = feed.entries[0]
            required_fields = ['title', 'link']
            for field in required_fields:
                if not hasattr(sample_entry, field) or not getattr(sample_entry, field):
                    validation_result['issues'].append(f'Missing required field: {field}')
            
            # Check for common RSS issues
            if hasattr(feed, 'bozo') and feed.bozo:
                validation_result['warnings'].append(f'Feed has parsing issues: {getattr(feed, "bozo_exception", "Unknown error")}')
            
            # Determine feed type
            if 'rss' in url.lower() or 'xml' in url.lower():
                validation_result['feed_type'] = 'RSS'
            elif 'feed' in url.lower() or 'atom' in url.lower():
                validation_result['feed_type'] = 'Atom'
            else:
                validation_result['feed_type'] = 'Unknown'
            
            # If no critical issues, mark as valid
            if not validation_result['issues']:
                validation_result['is_valid'] = True
                validation_result['info']['entry_count'] = len(feed.entries)
                validation_result['info']['sample_entries'] = [
                    {
                        'title': entry.title,
                        'link': entry.link,
                        'summary': getattr(entry, 'summary', '')[:100] + '...' if getattr(entry, 'summary', '') else 'No summary'
                    }
                    for entry in feed.entries[:3]
                ]
            
            return validation_result
            
        except Exception as e:
            return {
                'url': url,
                'is_valid': False,
                'feed_type': 'unknown',
                'issues': [f'Failed to parse feed: {str(e)}'],
                'warnings': [],
                'info': {}
            }