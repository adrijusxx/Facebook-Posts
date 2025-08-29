#!/usr/bin/env python3
"""
Facebook Trucking News Automation
Main Flask application for managing automated Facebook posts about USA trucking news
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import schedule
import time
import threading
from news_fetcher import NewsFetcher
from facebook_poster import FacebookPoster
from ai_content_enhancer import AIContentEnhancer
from models import db, Post, Settings, NewsSource

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app)
db.init_app(app)

# Initialize components
news_fetcher = NewsFetcher()
facebook_poster = FacebookPoster()
ai_enhancer = AIContentEnhancer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Dashboard view"""
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
    # Convert Post objects to dictionaries for JSON serialization
    posts_data = [{
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'url': post.url,
        'image_url': post.image_url,
        'facebook_post_id': post.facebook_post_id,
        'status': post.status,
        'source': post.source,
        'created_at': post.created_at.isoformat() if post.created_at else None,
        'posted_at': post.posted_at.isoformat() if post.posted_at else None,
        'error_message': post.error_message
    } for post in recent_posts]
    
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
    
    return render_template('dashboard.html', posts=posts_data, settings=settings)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings management"""
    if request.method == 'POST':
        settings_obj = Settings.query.first()
        if not settings_obj:
            settings_obj = Settings()
            db.session.add(settings_obj)
        
        settings_obj.posts_per_day = int(request.form.get('posts_per_day', 3))
        settings_obj.facebook_page_id = request.form.get('facebook_page_id', '')
        settings_obj.facebook_access_token = request.form.get('facebook_access_token', '')
        settings_obj.posting_hours = request.form.get('posting_hours', '9,14,19')
        settings_obj.enabled = 'enabled' in request.form
        settings_obj.openai_api_key = request.form.get('openai_api_key', '')
        settings_obj.ai_enhancement_enabled = 'ai_enhancement_enabled' in request.form
        settings_obj.ai_post_style = request.form.get('ai_post_style', 'informative')
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    settings_obj = Settings.query.first()
    if not settings_obj:
        settings_obj = Settings()
        db.session.add(settings_obj)
        db.session.commit()
    
    news_sources = NewsSource.query.all()
    return render_template('settings.html', settings=settings_obj, news_sources=news_sources)

@app.route('/news_sources', methods=['POST'])
def add_news_source():
    """Add a new news source"""
    url = request.form.get('url')
    name = request.form.get('name')
    source_type = request.form.get('type', 'rss')
    
    if url and name:
        source = NewsSource(url=url, name=name, type=source_type, enabled=True)
        db.session.add(source)
        db.session.commit()
        flash('News source added successfully!', 'success')
    else:
        flash('Please provide both URL and name for the news source.', 'error')
    
    return redirect(url_for('settings'))

@app.route('/news_sources/<int:source_id>/toggle', methods=['POST'])
def toggle_news_source(source_id):
    """Toggle news source enabled/disabled"""
    source = NewsSource.query.get_or_404(source_id)
    source.enabled = not source.enabled
    db.session.commit()
    
    status = 'enabled' if source.enabled else 'disabled'
    flash(f'News source {source.name} {status}!', 'success')
    return redirect(url_for('settings'))

@app.route('/news_sources/<int:source_id>/delete', methods=['POST'])
def delete_news_source(source_id):
    """Delete a news source"""
    source = NewsSource.query.get_or_404(source_id)
    db.session.delete(source)
    db.session.commit()
    flash(f'News source {source.name} deleted!', 'success')
    return redirect(url_for('settings'))

@app.route('/api/posts')
def api_posts():
    """API endpoint for posts"""
    posts = Post.query.order_by(Post.created_at.desc()).limit(50).all()
    return jsonify([{
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'facebook_post_id': post.facebook_post_id,
        'status': post.status,
        'created_at': post.created_at.isoformat(),
        'posted_at': post.posted_at.isoformat() if post.posted_at else None
    } for post in posts])

@app.route('/api/fetch_news', methods=['POST'])
def api_fetch_news():
    """Manually trigger news fetching"""
    try:
        articles = news_fetcher.fetch_latest_news()
        return jsonify({
            'success': True,
            'message': f'Fetched {len(articles)} articles',
            'articles': articles[:5]  # Return first 5 for preview
        })
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/post_now', methods=['POST'])
def api_post_now():
    """Manually trigger a post"""
    try:
        # Get the latest unposted article
        unposted = Post.query.filter_by(status='pending').first()
        if not unposted:
            # Fetch new articles if none pending
            articles = news_fetcher.fetch_latest_news()
            if articles:
                unposted = Post.query.filter_by(status='pending').first()
        
        if unposted:
            result = facebook_poster.post_to_facebook(unposted)
            if result['success']:
                return jsonify({'success': True, 'message': 'Post published successfully!'})
            else:
                return jsonify({'success': False, 'error': result['error']}), 500
        else:
            return jsonify({'success': False, 'error': 'No articles available to post'}), 400
            
    except Exception as e:
        logger.error(f"Error posting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/post_single', methods=['POST'])
def api_post_single():
    """Post a single article by ID"""
    try:
        post_id = request.json.get('post_id')
        if not post_id:
            return jsonify({'success': False, 'error': 'Post ID is required'}), 400
        
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        if post.status == 'posted':
            return jsonify({'success': False, 'error': 'Post has already been published'}), 400
        
        # Post to Facebook
        result = facebook_poster.post_to_facebook(post)
        if result['success']:
            return jsonify({'success': True, 'message': 'Post published successfully!'})
        else:
            return jsonify({'success': False, 'error': result['error']}), 500
            
    except Exception as e:
        logger.error(f"Error posting single article: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_openai', methods=['POST'])
def api_test_openai():
    """Test OpenAI API connection"""
    api_key = request.json.get('api_key')
    if not api_key:
        return jsonify({'success': False, 'error': 'API key required'}), 400
    
    result = ai_enhancer.test_openai_connection(api_key)
    return jsonify(result)

@app.route('/api/test_facebook_token', methods=['POST'])
def api_test_facebook_token():
    """Test Facebook access token validity"""
    try:
        access_token = request.json.get('access_token')
        if not access_token:
            return jsonify({'success': False, 'error': 'Access token required'}), 400
        
        result = facebook_poster.check_token_validity(access_token)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing Facebook token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify_facebook_page', methods=['POST'])
def api_verify_facebook_page():
    """Verify Facebook page access"""
    try:
        page_id = request.json.get('page_id')
        access_token = request.json.get('access_token')
        
        if not page_id or not access_token:
            return jsonify({'success': False, 'error': 'Page ID and access token required'}), 400
        
        result = facebook_poster.verify_facebook_credentials(page_id, access_token)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error verifying Facebook page: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_custom_post', methods=['POST'])
def api_generate_custom_post():
    """Generate a custom post using AI"""
    try:
        topic = request.json.get('topic')
        style = request.json.get('style', 'informative')
        
        if not topic:
            return jsonify({'success': False, 'error': 'Topic is required'}), 400
        
        content = ai_enhancer.generate_custom_post(topic, style)
        
        if content:
            return jsonify({'success': True, 'content': content})
        else:
            return jsonify({'success': False, 'error': 'Failed to generate content'}), 500
            
    except Exception as e:
        logger.error(f"Error generating custom post: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/content_suggestions', methods=['POST'])
def api_content_suggestions():
    """Get content suggestions based on keywords"""
    try:
        keywords = request.json.get('keywords', [])
        if not keywords:
            keywords = ['trucking', 'logistics', 'transportation']
        
        suggestions = ai_enhancer.get_content_suggestions(keywords)
        return jsonify({'success': True, 'suggestions': suggestions})
        
    except Exception as e:
        logger.error(f"Error getting content suggestions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/enhance_content', methods=['POST'])
def api_enhance_content():
    """Enhance existing content with AI"""
    try:
        title = request.json.get('title', '')
        content = request.json.get('content', '')
        url = request.json.get('url', '')
        source = request.json.get('source', '')
        
        if not title and not content:
            return jsonify({'success': False, 'error': 'Title or content required'}), 400
        
        enhanced = ai_enhancer.enhance_post_content(title, content, url, source)
        return jsonify({'success': True, 'enhanced_content': enhanced})
        
    except Exception as e:
        logger.error(f"Error enhancing content: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_rss/<int:source_id>', methods=['POST'])
def api_test_rss(source_id):
    """Test a specific RSS feed"""
    try:
        source = NewsSource.query.get_or_404(source_id)
        
        # Use the enhanced test method from NewsFetcher
        result = news_fetcher.test_rss_source(source)
        
        if result.get('error'):
            return jsonify({
                'success': False,
                'error': result['error'],
                'details': result
            }), 400
        else:
            return jsonify({
                'success': True,
                'message': f'RSS feed working: {result["total_entries"]} entries found, {result.get("trucking_entries", 0)} trucking-related',
                'total_entries': result['total_entries'],
                'trucking_entries': result.get('trucking_entries', 0),
                'preview': result['entries_preview'],
                'details': result
            })
            
    except Exception as e:
        logger.error(f"Error testing RSS feed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_all_rss', methods=['POST'])
def api_test_all_rss():
    """Test all RSS feeds at once"""
    try:
        sources = NewsSource.query.filter_by(enabled=True).all()
        
        if not sources:
            return jsonify({'success': False, 'error': 'No enabled news sources found'}), 400
        
        results = []
        for source in sources:
            if source.type == 'rss':
                result = news_fetcher.test_rss_source(source)
                results.append(result)
        
        # Summary
        total_sources = len(results)
        working_sources = sum(1 for r in results if not r.get('error'))
        total_entries = sum(r.get('total_entries', 0) for r in results)
        total_trucking_entries = sum(r.get('trucking_entries', 0) for r in results)
        
        return jsonify({
            'success': True,
            'summary': {
                'total_sources': total_sources,
                'working_sources': working_sources,
                'total_entries': total_entries,
                'total_trucking_entries': total_trucking_entries
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error testing all RSS feeds: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate_rss', methods=['POST'])
def api_validate_rss():
    """Validate an RSS feed URL"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        url = data['url']
        validation_result = news_fetcher.validate_rss_feed(url)
        
        if validation_result['is_valid']:
            return jsonify({
                'success': True,
                'message': f'RSS feed is valid: {validation_result["info"]["entry_count"]} entries found',
                'validation': validation_result
            })
        else:
            return jsonify({
                'success': False,
                'error': 'RSS feed validation failed',
                'validation': validation_result
            }), 400
            
    except Exception as e:
        logger.error(f"Error validating RSS feed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/source_health', methods=['GET'])
def api_source_health():
    """Get health status of all news sources"""
    try:
        health_data = news_fetcher._get_source_health_status()
        
        # Calculate overall health summary
        total_sources = len(health_data)
        healthy_sources = sum(1 for s in health_data if s.get('status') == 'healthy')
        warning_sources = sum(1 for s in health_data if s.get('status') == 'warning')
        critical_sources = sum(1 for s in health_data if s.get('status') == 'critical')
        enabled_sources = sum(1 for s in health_data if s.get('enabled'))
        
        summary = {
            'total_sources': total_sources,
            'enabled_sources': enabled_sources,
            'healthy_sources': healthy_sources,
            'warning_sources': warning_sources,
            'critical_sources': critical_sources,
            'overall_status': 'healthy' if critical_sources == 0 and warning_sources < 2 else ('warning' if critical_sources == 0 else 'critical')
        }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'sources': health_data
        })
        
    except Exception as e:
        logger.error(f"Error getting source health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recover_sources', methods=['POST'])
def api_recover_sources():
    """Manually trigger source recovery process"""
    try:
        news_fetcher.auto_recover_sources()
        return jsonify({
            'success': True,
            'message': 'Source recovery process completed'
        })
        
    except Exception as e:
        logger.error(f"Error in source recovery: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Get basic stats
        total_posts = Post.query.count()
        pending_posts = Post.query.filter_by(status='pending').count()
        posted_posts = Post.query.filter_by(status='posted').count()
        
        # Check news sources
        total_sources = NewsSource.query.count()
        enabled_sources = NewsSource.query.filter_by(enabled=True).count()
        
        # Get recent activity
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        recent_activity = [{
            'title': post.title,
            'status': post.status,
            'created_at': post.created_at.isoformat() if post.created_at else None
        } for post in recent_posts]
        
        # Get source health summary
        try:
            health_data = news_fetcher._get_source_health_status()
            critical_sources = sum(1 for s in health_data if s.get('status') == 'critical')
            warning_sources = sum(1 for s in health_data if s.get('status') == 'warning')
            source_health_status = 'healthy' if critical_sources == 0 and warning_sources < 2 else ('warning' if critical_sources == 0 else 'critical')
        except:
            source_health_status = 'unknown'
            critical_sources = 0
            warning_sources = 0
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'stats': {
                'total_posts': total_posts,
                'pending_posts': pending_posts,
                'posted_posts': posted_posts,
                'total_sources': total_sources,
                'enabled_sources': enabled_sources
            },
            'source_health': {
                'status': source_health_status,
                'critical_sources': critical_sources,
                'warning_sources': warning_sources
            },
            'recent_activity': recent_activity,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def run_scheduler():
    """Run the post scheduler in a separate thread"""
    def job():
        """Scheduled job to post content"""
        settings_obj = Settings.query.first()
        if not settings_obj or not settings_obj.enabled:
            return
        
        try:
            # Check if we should post now
            current_hour = datetime.now().hour
            posting_hours = [int(h.strip()) for h in settings_obj.posting_hours.split(',')]
            
            if current_hour in posting_hours:
                # Check if we already posted this hour
                last_post = Post.query.filter(
                    Post.posted_at >= datetime.now().replace(minute=0, second=0, microsecond=0),
                    Post.status == 'posted'
                ).first()
                
                if not last_post:
                    # Get pending post or fetch new content
                    pending_post = Post.query.filter_by(status='pending').first()
                    if not pending_post:
                        news_fetcher.fetch_latest_news()
                        pending_post = Post.query.filter_by(status='pending').first()
                    
                    if pending_post:
                        facebook_poster.post_to_facebook(pending_post)
                        logger.info(f"Automatically posted: {pending_post.title}")
        
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
    
    # Schedule posts every hour, the job function will check if it should actually post
    schedule.every().hour.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Initialize database and defaults
with app.app_context():
    db.create_all()
    
    # Add default news sources if none exist
    if not NewsSource.query.first():
        default_sources = [
            NewsSource(name="Transport Topics", url="https://www.ttnews.com/rss.xml", type="rss", enabled=True),
            NewsSource(name="Trucking Info", url="https://www.truckinginfo.com/rss", type="rss", enabled=True),
            NewsSource(name="Fleet Owner", url="https://www.fleetowner.com/rss.xml", type="rss", enabled=True),
            NewsSource(name="Commercial Carrier Journal", url="https://www.ccjdigital.com/feed/", type="rss", enabled=True),
            NewsSource(name="Overdrive Magazine", url="https://www.overdriveonline.com/feed/", type="rss", enabled=True),
            # Add some alternative sources that might be more reliable
            NewsSource(name="Truck News", url="https://www.trucknews.com/feed/", type="rss", enabled=True),
            NewsSource(name="Trucking.com", url="https://www.trucking.com/feed/", type="rss", enabled=True),
        ]
        for source in default_sources:
            db.session.add(source)
        db.session.commit()
        logger.info(f"Added {len(default_sources)} default news sources")
        
        # Test RSS feeds to see which ones are working
        logger.info("Testing RSS feeds...")
        for source in default_sources:
            try:
                import feedparser
                feed = feedparser.parse(source.url)
                if feed.entries:
                    logger.info(f"✓ {source.name}: {len(feed.entries)} entries found")
                else:
                    logger.warning(f"✗ {source.name}: No entries found in RSS feed")
                    # Try to disable sources that don't work
                    source.enabled = False
                    logger.info(f"Disabled {source.name} due to no entries")
            except Exception as e:
                logger.error(f"✗ {source.name}: Error testing RSS feed: {e}")
                # Disable problematic sources
                source.enabled = False
                logger.info(f"Disabled {source.name} due to error: {e}")
        
        # Commit the changes
        db.session.commit()

# Start scheduler in background thread (only if not in serverless environment)
if not os.getenv('GAE_ENV'):  # Not on App Engine
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Background scheduler started")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)