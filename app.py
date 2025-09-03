#!/usr/bin/env python3
"""
Facebook Trucking News Automation
Main Flask application for managing automated Facebook posts about USA trucking news
"""

import os
import logging
import json
import time
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_caching import Cache
from dotenv import load_dotenv
import schedule
import threading
from news_fetcher import NewsFetcher
from facebook_poster import FacebookPoster
from ai_content_enhancer import AIContentEnhancer
from facebook_token_manager import FacebookTokenManager
from models import db, Post, Settings, NewsSource, OperationLog, Profile
from werkzeug.exceptions import HTTPException
import traceback

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database configuration with connection pooling
database_url = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
if database_url.startswith('postgresql://'):
    # PostgreSQL with connection pooling
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
else:
    # SQLite fallback
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_RECORD_QUERIES'] = False  # Disable query recording for performance

# Initialize extensions
CORS(app)
db.init_app(app)

# Initialize cache for performance
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes
    'CACHE_THRESHOLD': 1000  # Max number of items
})

socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global operation tracking
active_operations = {}
operation_counter = 0
current_profile_id = None  # Track current active profile

class OperationTracker:
    """Tracks operations and provides real-time updates"""
    
    def __init__(self, operation_id, operation_type, description, profile_id=None):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.description = description
        self.profile_id = profile_id
        self.start_time = datetime.now()
        self.status = "running"
        self.progress = 0
        self.current_step = ""
        self.total_steps = 0
        self.completed_steps = 0
        self.error_message = None
        self.result = None
        
    def update_progress(self, progress, current_step, completed_steps=None, total_steps=None):
        """Update operation progress"""
        self.progress = progress
        self.current_step = current_step
        if completed_steps is not None:
            self.completed_steps = completed_steps
        if total_steps is not None:
            self.total_steps = total_steps
            
        # Emit real-time update
        socketio.emit('operation_update', {
            'operation_id': self.operation_id,
            'progress': self.progress,
            'current_step': self.current_step,
            'completed_steps': self.completed_steps,
            'total_steps': self.total_steps,
            'status': self.status,
            'profile_id': self.profile_id
        })
        
    def complete(self, result=None, error_message=None):
        """Mark operation as complete"""
        self.status = "completed" if error_message is None else "failed"
        self.result = result
        self.error_message = error_message
        self.progress = 100 if error_message is None else 0
        
        # Log operation
        self._log_operation()
        
        # Emit completion update
        socketio.emit('operation_complete', {
            'operation_id': self.operation_id,
            'status': self.status,
            'result': self.result,
            'error_message': self.error_message,
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'profile_id': self.profile_id
        })
        
        # Clean up
        if self.operation_id in active_operations:
            del active_operations[self.operation_id]
    
    def _log_operation(self):
        """Log operation to database"""
        try:
            log_entry = OperationLog(
                operation_id=self.operation_id,
                operation_type=self.operation_type,
                description=self.description,
                status=self.status,
                start_time=self.start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - self.start_time).total_seconds(),
                progress=self.progress,
                error_message=self.error_message,
                result=json.dumps(self.result) if self.result else None,
                profile_id=self.profile_id
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error logging operation: {e}")

def create_operation(operation_type, description, profile_id=None):
    """Create a new operation tracker"""
    global operation_counter
    operation_counter += 1
    operation_id = f"op_{operation_counter}_{int(time.time())}"
    
    tracker = OperationTracker(operation_id, operation_type, description, profile_id)
    active_operations[operation_id] = tracker
    
    # Emit operation start
    socketio.emit('operation_start', {
        'operation_id': operation_id,
        'operation_type': operation_type,
        'description': description,
        'start_time': tracker.start_time.isoformat(),
        'profile_id': profile_id
    })
    
    return tracker

def get_current_profile():
    """Get the currently active profile"""
    global current_profile_id
    
    if current_profile_id is None:
        # Try to get from session or default profile
        profile = Profile.query.filter_by(is_default=True).first()
        if profile:
            current_profile_id = profile.id
        else:
            # Create default profile if none exists
            profile = create_default_profile()
            current_profile_id = profile.id
    
    return Profile.query.get(current_profile_id)

def get_cached_current_profile():
    """Get the currently active profile from cache"""
    if 'current_profile_id' in session:
        profile_id = session['current_profile_id']
        return Profile.query.get(profile_id).to_dict() if profile_id else None
    return None

def get_cached_profiles():
    """Get all profiles from cache"""
    if 'all_profiles' in session:
        return session['all_profiles']
    return {}

def create_default_profile():
    """Create a default profile for backward compatibility"""
    try:
        # Check if we have old settings to migrate
        old_settings = Settings.query.first()
        
        default_profile = Profile(
            name='default',
            display_name='Main Trucking Page',
            description='Default Facebook page for trucking news',
            primary_color='#3B82F6',
            secondary_color='#1E40AF',
            background_color='#F8FAFC',
            accent_color='#F59E0B',
            icon='🚛',
            is_default=True
        )
        
        # Migrate old settings if they exist
        if old_settings:
            # Try to get old settings from the old model structure
            # This is a simplified migration - in production you'd want more robust handling
            pass
        
        db.session.add(default_profile)
        db.session.commit()
        logger.info("Created default profile")
        return default_profile
        
    except Exception as e:
        logger.error(f"Error creating default profile: {e}")
        # Create minimal profile
        default_profile = Profile(
            name='default',
            display_name='Main Trucking Page',
            is_default=True
        )
        db.session.add(default_profile)
        db.session.commit()
        return default_profile

# Initialize components with error handling
try:
    news_fetcher = NewsFetcher()
    token_manager = FacebookTokenManager()
    facebook_poster = FacebookPoster(token_manager)
    ai_enhancer = AIContentEnhancer()
    logger.info("All components initialized successfully")
except Exception as e:
    logger.error(f"Error initializing components: {e}")
    # Initialize with None to prevent crashes
    news_fetcher = None
    token_manager = None
    facebook_poster = None
    ai_enhancer = None

# Initialize database and defaults
with app.app_context():
    try:
        db.create_all()
        
        # Add default news sources if none exist
        if not NewsSource.query.first():
            default_sources = [
                # Major Industry Publications
                NewsSource(name="Transport Topics", url="https://ttnews.com/rss.xml", type="rss", enabled=True),
                NewsSource(name="Trucking Info", url="https://www.truckinginfo.com/rss", type="rss", enabled=True),
                NewsSource(name="Fleet Owner", url="https://www.fleetowner.com/rss/rss.xml", type="rss", enabled=True),
                NewsSource(name="Truckers News", url="https://truckersnews.com/feed", type="rss", enabled=True),
                NewsSource(name="Logistics Management", url="https://feeds.feedburner.com/logisticsmgmt/latest", type="rss", enabled=True),
                
                # Digital-First Sources
                NewsSource(name="FreightWaves", url="https://feeds.feedburner.com/FreightWaves", type="rss", enabled=True),
                NewsSource(name="DAT Blog", url="https://dat.com/blog/feed", type="rss", enabled=True),
                NewsSource(name="Journal of Commerce", url="https://joc.com/rssfeed", type="rss", enabled=True),
                NewsSource(name="Container News", url="https://container-news.com/feed", type="rss", enabled=True),
                
                # Government Sources
                NewsSource(name="DOT News", url="https://www.transportation.gov/rss", type="rss", enabled=True),
                
                # Specialty/Regional Sources
                NewsSource(name="Truck News Canada", url="https://trucknews.com/blogs/feed", type="rss", enabled=True),
                NewsSource(name="Merchants Fleet", url="https://merchantsfleet.com/feed", type="rss", enabled=True),
                
                # Alternative Sources (as backups)
                NewsSource(name="Commercial Carrier Journal", url="https://www.ccjdigital.com/feed/", type="rss", enabled=True),
                NewsSource(name="Overdrive Magazine", url="https://www.overdriveonline.com/feed/", type="rss", enabled=True),
            ]
            for source in default_sources:
                db.session.add(source)
            db.session.commit()
            logger.info(f"Added {len(default_sources)} default news sources")
            
            # Test RSS feeds in background to avoid blocking startup
            def test_rss_feeds_async():
                try:
                    logger.info("Testing RSS feeds in background...")
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
                    logger.info("RSS feed testing completed in background")
                except Exception as e:
                    logger.error(f"Error in background RSS testing: {e}")
            
            # Start RSS testing in background thread
            import threading
            rss_thread = threading.Thread(target=test_rss_feeds_async, daemon=True)
            rss_thread.start()
            logger.info("RSS feed testing started in background thread")
        else:
            logger.info("Default news sources already exist, skipping addition.")
    except Exception as e:
        logger.error(f"Error initializing database or default data: {e}")

# Start scheduler in background thread (only if not in serverless environment)
def start_scheduler():
    """Start the background scheduler for automated tasks"""
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except Exception as e:
        logger.error(f"Scheduler error: {e}")

# Start scheduler in background
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()
logger.info("Background scheduler started")

@app.route('/')
def index():
    """Dashboard view"""
    try:
        # Use cached profiles for better performance
        current_profile = get_cached_current_profile()
        all_profiles = list(get_cached_profiles().values())
        
        if not current_profile:
            # Fallback to database if cache fails
            current_profile = get_current_profile()
            if current_profile:
                current_profile = current_profile.to_dict()
                all_profiles = [profile.to_dict() for profile in Profile.query.all()]
            else:
                return f"""
                <html>
                <head><title>Service Starting</title></head>
                <body>
                    <h1>🚛 Facebook Trucking News Bot</h1>
                    <p>The service is starting up. Please wait a moment and refresh the page.</p>
                    <p>If this persists, check the service logs.</p>
                </body>
                </html>
                """, 503
        
        # Get posts for current profile
        recent_posts = Post.query.filter_by(profile_id=current_profile['id']).order_by(Post.created_at.desc()).limit(10).all()
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
        
        # Get recent operation logs for current profile
        recent_operations = OperationLog.query.filter_by(profile_id=current_profile['id']).order_by(OperationLog.start_time.desc()).limit(20).all()
        operations_data = [{
            'operation_id': op.operation_id,
            'operation_type': op.operation_type,
            'description': op.description,
            'status': op.status,
            'start_time': op.start_time.isoformat() if op.start_time else None,
            'duration': op.duration,
            'progress': op.progress,
            'error_message': op.error_message
        } for op in recent_operations]
        
        return render_template('dashboard.html', 
                             posts=posts_data, 
                             current_profile=current_profile,
                             all_profiles=all_profiles,
                             operations=operations_data,
                             active_operations=len(active_operations))
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return f"""
        <html>
        <head><title>Service Starting</title></head>
        <body>
            <h1>🚛 Facebook Trucking News Bot</h1>
            <p>The service is starting up. Please wait a moment and refresh the page.</p>
            <p>If this persists, check the service logs.</p>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """, 503

@app.route('/profile/<int:profile_id>')
def switch_profile(profile_id):
    """Switch to a different profile"""
    try:
        global current_profile_id
        profile = Profile.query.get_or_404(profile_id)
        current_profile_id = profile_id
        
        # Store in session for persistence
        session['current_profile_id'] = profile_id
        
        flash(f'Switched to profile: {profile.display_name}', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error switching profile: {e}")
        flash(f'Error switching profile: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/profiles')
def profiles():
    """Profile management page"""
    try:
        all_profiles = Profile.query.all()
        current_profile = get_current_profile()
        
        # Convert Profile objects to dictionaries for template rendering
        current_profile_dict = current_profile.to_dict() if current_profile else None
        all_profiles_dicts = [profile.to_dict() for profile in all_profiles] if all_profiles else []
        
        return render_template('profiles.html', profiles=all_profiles_dicts, current_profile=current_profile_dict, all_profiles=all_profiles_dicts)
    except Exception as e:
        logger.error(f"Error in profiles route: {e}")
        flash(f'Error loading profiles: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/profiles/create', methods=['GET', 'POST'])
def create_profile():
    """Create a new profile"""
    if request.method == 'POST':
        try:
            data = request.form
            
            # Generate unique name
            base_name = data.get('name', '').lower().replace(' ', '_')
            name = base_name
            counter = 1
            while Profile.query.filter_by(name=name).first():
                name = f"{base_name}_{counter}"
                counter += 1
            
            profile = Profile(
                name=name,
                display_name=data.get('display_name', ''),
                description=data.get('description', ''),
                primary_color=data.get('primary_color', '#3B82F6'),
                secondary_color=data.get('secondary_color', '#1E40AF'),
                background_color=data.get('background_color', '#F8FAFC'),
                accent_color=data.get('accent_color', '#F59E0B'),
                icon=data.get('icon', '🚛'),
                facebook_page_id=data.get('facebook_page_id', ''),
                facebook_page_name=data.get('facebook_page_name', ''),
                facebook_access_token=data.get('facebook_access_token', ''),
                openai_api_key=data.get('openai_api_key', ''),
                ai_enhancement_enabled='ai_enhancement_enabled' in data,
                ai_post_style=data.get('ai_post_style', 'informative'),
                posts_per_day=int(data.get('posts_per_day', 3)),
                posting_hours=data.get('posting_hours', '9,14,19'),
                enabled='enabled' in data
            )
            
            db.session.add(profile)
            db.session.commit()
            
            flash(f'Profile "{profile.display_name}" created successfully!', 'success')
            return redirect(url_for('profiles'))
            
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            flash(f'Error creating profile: {str(e)}', 'error')
    
    current_profile_dict = get_current_profile().to_dict()
    all_profiles = Profile.query.all()
    all_profiles_dicts = [profile.to_dict() for profile in all_profiles]
    return render_template('create_profile.html', current_profile=current_profile_dict, all_profiles=all_profiles_dicts)

@app.route('/profiles/<int:profile_id>/edit', methods=['GET', 'POST'])
def edit_profile(profile_id):
    """Edit an existing profile"""
    profile = Profile.query.get_or_404(profile_id)
    
    if request.method == 'POST':
        try:
            data = request.form
            
            profile.display_name = data.get('display_name', '')
            profile.description = data.get('description', '')
            profile.primary_color = data.get('primary_color', '#3B82F6')
            profile.secondary_color = data.get('secondary_color', '#1E40AF')
            profile.background_color = data.get('background_color', '#F8FAFC')
            profile.accent_color = data.get('accent_color', '#F59E0B')
            profile.icon = data.get('icon', '🚛')
            profile.facebook_page_id = data.get('facebook_page_id', '')
            profile.facebook_page_name = data.get('facebook_page_name', '')
            profile.facebook_access_token = data.get('facebook_access_token', '')
            profile.openai_api_key = data.get('openai_api_key', '')
            profile.ai_enhancement_enabled = 'ai_enhancement_enabled' in data
            profile.ai_post_style = data.get('ai_post_style', 'informative')
            profile.posts_per_day = int(data.get('posts_per_day', 3))
            profile.posting_hours = data.get('posting_hours', '9,14,19')
            profile.enabled = 'enabled' in data
            
            db.session.commit()
            
            flash(f'Profile "{profile.display_name}" updated successfully!', 'success')
            return redirect(url_for('profiles'))
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            flash(f'Error updating profile: {str(e)}', 'error')
    
    # Get current profile and all profiles for the base template
    current_profile = get_current_profile()
    all_profiles = Profile.query.all()
    
    # Convert Profile objects to dictionaries for template rendering
    current_profile_dict = current_profile.to_dict() if current_profile else None
    all_profiles_dicts = [profile.to_dict() for profile in all_profiles] if all_profiles else []
    
    return render_template('edit_profile.html', profile=profile, current_profile=current_profile_dict, all_profiles=all_profiles_dicts)

@app.route('/profiles/<int:profile_id>/delete', methods=['POST'])
def delete_profile(profile_id):
    """Delete a profile"""
    try:
        profile = Profile.query.get_or_404(profile_id)
        
        if profile.is_default:
            flash('Cannot delete the default profile', 'error')
            return redirect(url_for('profiles'))
        
        # Check if profile has posts
        post_count = Post.query.filter_by(profile_id=profile_id).count()
        if post_count > 0:
            flash(f'Cannot delete profile with {post_count} posts. Please reassign or delete posts first.', 'error')
            return redirect(url_for('profiles'))
        
        db.session.delete(profile)
        db.session.commit()
        
        flash(f'Profile "{profile.display_name}" deleted successfully!', 'success')
        return redirect(url_for('profiles'))
        
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        flash(f'Error deleting profile: {str(e)}', 'error')
        return redirect(url_for('profiles'))

@app.route('/profiles/<int:profile_id>/set_default', methods=['POST'])
def set_default_profile(profile_id):
    """Set a profile as default"""
    try:
        # Remove default from all profiles
        Profile.query.update({Profile.is_default: False})
        
        # Set new default
        profile = Profile.query.get_or_404(profile_id)
        profile.is_default = True
        db.session.commit()
        
        flash(f'Profile "{profile.display_name}" set as default!', 'success')
        return redirect(url_for('profiles'))
        
    except Exception as e:
        logger.error(f"Error setting default profile: {e}")
        flash(f'Error setting default profile: {str(e)}', 'error')
        return redirect(url_for('profiles'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Global settings management"""
    if request.method == 'POST':
        try:
            settings_obj = Settings.query.first()
            if not settings_obj:
                settings_obj = Settings()
                db.session.add(settings_obj)
            
            settings_obj.app_name = request.form.get('app_name', 'Facebook Trucking News Bot')
            settings_obj.app_theme = request.form.get('app_theme', 'light')
            settings_obj.language = request.form.get('language', 'en')
            settings_obj.timezone = request.form.get('timezone', 'UTC')
            settings_obj.news_fetch_interval = int(request.form.get('news_fetch_interval', 60))
            settings_obj.max_articles_per_fetch = int(request.form.get('max_articles_per_fetch', 100))
            settings_obj.enable_auto_fetch = 'enable_auto_fetch' in request.form
            settings_obj.enable_logging = 'enable_logging' in request.form
            settings_obj.log_level = request.form.get('log_level', 'INFO')
            settings_obj.enable_analytics = 'enable_analytics' in request.form
            
            db.session.commit()
            flash('Global settings updated successfully!', 'success')
            return redirect(url_for('settings'))
        except Exception as e:
            logger.error(f"Error updating global settings: {e}")
            flash(f'Error updating global settings: {str(e)}', 'error')
            return redirect(url_for('settings'))
    
    settings_obj = Settings.query.first()
    if not settings_obj:
        settings_obj = Settings()
        db.session.add(settings_obj)
        db.session.commit()
    
    # For now, pass empty profile data to avoid the error
    return render_template('settings.html', settings=settings_obj, current_profile=None, all_profiles=[])

@app.route('/news_sources', methods=['GET'])
def news_sources():
    """Display and manage news sources"""
    try:
        sources = NewsSource.query.all()
        current_profile = get_current_profile()
        all_profiles = Profile.query.all()
        return render_template('news_sources.html', sources=sources, current_profile=current_profile, all_profiles=all_profiles)
    except Exception as e:
        logger.error(f"Error loading news sources: {e}")
        flash(f'Error loading news sources: {str(e)}', 'error')
        return redirect(url_for('settings'))

@app.route('/add_news_source', methods=['POST'])
def add_news_source():
    """Add a new news source"""
    try:
        name = request.form.get('name')
        url = request.form.get('url')
        source_type = request.form.get('type', 'rss')
        
        if not name or not url:
            flash('Name and URL are required', 'error')
            return redirect(url_for('news_sources'))
        
        # Check if source already exists
        existing = NewsSource.query.filter_by(url=url).first()
        if existing:
            flash('A news source with this URL already exists', 'error')
            return redirect(url_for('news_sources'))
        
        # Create new source
        new_source = NewsSource(
            name=name,
            url=url,
            type=source_type,
            enabled=True
        )
        
        db.session.add(new_source)
        db.session.commit()
        
        flash(f'News source "{name}" added successfully!', 'success')
        return redirect(url_for('news_sources'))
        
    except Exception as e:
        logger.error(f"Error adding news source: {e}")
        flash(f'Error adding news source: {str(e)}', 'error')
        return redirect(url_for('news_sources'))

@app.route('/news_sources/<int:source_id>/toggle', methods=['POST'])
def toggle_news_source(source_id):
    """Enable/disable a news source"""
    try:
        source = NewsSource.query.get_or_404(source_id)
        source.enabled = not source.enabled
        db.session.commit()
        
        status = "enabled" if source.enabled else "disabled"
        flash(f'News source "{source.name}" {status}', 'success')
        return redirect(url_for('news_sources'))
        
    except Exception as e:
        logger.error(f"Error toggling news source: {e}")
        flash(f'Error updating news source: {str(e)}', 'error')
        return redirect(url_for('news_sources'))

@app.route('/news_sources/<int:source_id>/delete', methods=['POST'])
def delete_news_source(source_id):
    """Delete a news source"""
    try:
        source = NewsSource.query.get_or_404(source_id)
        name = source.name
        db.session.delete(source)
        db.session.commit()
        
        flash(f'News source "{name}" deleted successfully!', 'success')
        return redirect(url_for('news_sources'))
        
    except Exception as e:
        logger.error(f"Error deleting news source: {e}")
        flash(f'Error deleting news source: {str(e)}', 'error')
        return redirect(url_for('news_sources'))

@app.route('/fetch_news', methods=['POST'])
def fetch_news():
    """Fetch news from all sources with progress tracking"""
    try:
        current_profile = get_current_profile()
        
        # Create operation tracker
        tracker = create_operation("fetch_news", "Fetching news from all sources", current_profile.id)
        
        def fetch_news_async():
            try:
                if not news_fetcher:
                    tracker.complete(error_message="News fetcher not initialized")
                    return
                
                # Get enabled sources
                sources = NewsSource.query.filter_by(enabled=True).all()
                tracker.update_progress(0, f"Starting news fetch from {len(sources)} sources", 0, len(sources))
                
                articles = []
                for i, source in enumerate(sources):
                    try:
                        tracker.update_progress(
                            (i / len(sources)) * 100,
                            f"Fetching from {source.name}",
                            i,
                            len(sources)
                        )
                        
                        # Fetch articles from source
                        if source.type == 'rss':
                            source_articles = news_fetcher._fetch_from_rss(source)
                        else:
                            source_articles = news_fetcher._fetch_from_website(source)
                        
                        if source_articles:
                            articles.extend(source_articles)
                            source.last_fetched = datetime.now(timezone.utc)
                            source.total_articles_fetched += len(source_articles)
                            logger.info(f"Fetched {len(source_articles)} articles from {source.name}")
                        
                        # Small delay to avoid overwhelming sources
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error fetching from {source.name}: {e}")
                        continue
                
                # Process and save articles with profile association
                tracker.update_progress(90, "Processing and saving articles", len(sources), len(sources))
                if articles:
                    # Associate articles with current profile
                    for article in articles:
                        if hasattr(article, 'profile_id'):
                            article.profile_id = current_profile.id
                    
                    saved_articles = news_fetcher._process_and_save_articles(articles)
                    tracker.complete(result=f"Successfully fetched and saved {len(saved_articles)} articles")
                else:
                    tracker.complete(result="No new articles found")
                    
            except Exception as e:
                logger.error(f"Error in news fetch: {e}")
                tracker.complete(error_message=str(e))
        
        # Start fetch in background thread
        thread = threading.Thread(target=fetch_news_async, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'operation_id': tracker.operation_id,
            'message': 'News fetch started'
        })
        
    except Exception as e:
        logger.error(f"Error starting news fetch: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/post_to_facebook', methods=['POST'])
def post_to_facebook():
    """Post selected news to Facebook with progress tracking"""
    try:
        post_id = request.form.get('post_id')
        if not post_id:
            return jsonify({'success': False, 'error': 'No post ID provided'}), 400
        
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        current_profile = get_current_profile()
        
        # Create operation tracker
        tracker = create_operation("post_to_facebook", f"Posting '{post.title[:50]}...' to Facebook", current_profile.id)
        
        def post_async():
            try:
                if not facebook_poster:
                    tracker.complete(error_message="Facebook poster not initialized")
                    return
                
                tracker.update_progress(20, "Preparing content for Facebook", 1, 4)
                
                # Use profile-specific settings
                if current_profile.ai_enhancement_enabled and ai_enhancer:
                    tracker.update_progress(40, "Enhancing content with AI", 2, 4)
                    enhanced_content = ai_enhancer.enhance_content(post.content, current_profile.ai_post_style)
                    post.content = enhanced_content
                
                tracker.update_progress(60, "Posting to Facebook", 3, 4)
                
                # Post to Facebook using profile credentials
                result = facebook_poster.post_article(post, current_profile)
                
                if result.get('success'):
                    post.status = 'posted'
                    post.facebook_post_id = result.get('facebook_post_id')
                    post.posted_at = datetime.now(timezone.utc)
                    post.profile_id = current_profile.id
                    db.session.commit()
                    tracker.update_progress(100, "Posted successfully", 4, 4)
                    tracker.complete(result=f"Posted to Facebook: {result.get('facebook_post_id')}")
                else:
                    post.status = 'failed'
                    post.error_message = result.get('error', 'Unknown error')
                    post.profile_id = current_profile.id
                    db.session.commit()
                    tracker.complete(error_message=result.get('error', 'Unknown error'))
                    
            except Exception as e:
                logger.error(f"Error posting to Facebook: {e}")
                post.status = 'failed'
                post.error_message = str(e)
                post.profile_id = current_profile.id
                db.session.commit()
                tracker.complete(error_message=str(e))
        
        # Start posting in background thread
        thread = threading.Thread(target=post_async, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'operation_id': tracker.operation_id,
            'message': 'Facebook posting started'
        })
        
    except Exception as e:
        logger.error(f"Error starting Facebook post: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/profiles')
def get_profiles():
    """Get all profiles"""
    try:
        profiles = Profile.query.all()
        return jsonify({
            'success': True,
            'profiles': [profile.to_dict() for profile in profiles],
            'current_profile_id': current_profile_id
        })
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<int:profile_id>')
def get_profile(profile_id):
    """Get a specific profile"""
    try:
        profile = Profile.query.get_or_404(profile_id)
        return jsonify({
            'success': True,
            'profile': profile.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/operations')
def get_operations():
    """Get all operations (active and recent)"""
    try:
        # Get active operations
        active_ops = []
        for op_id, tracker in active_operations.items():
            active_ops.append({
                'operation_id': op_id,
                'operation_type': tracker.operation_type,
                'description': tracker.description,
                'status': tracker.status,
                'progress': tracker.progress,
                'current_step': tracker.current_step,
                'start_time': tracker.start_time.isoformat(),
                'completed_steps': tracker.completed_steps,
                'total_steps': tracker.total_steps,
                'profile_id': tracker.profile_id
            })
        
        # Get recent completed operations
        recent_ops = OperationLog.query.order_by(OperationLog.start_time.desc()).limit(50).all()
        completed_ops = [{
            'operation_id': op.operation_id,
            'operation_type': op.operation_type,
            'description': op.description,
            'status': op.status,
            'start_time': op.start_time.isoformat() if op.start_time else None,
            'duration': op.duration,
            'progress': op.progress,
            'error_message': op.error_message,
            'profile_id': op.profile_id
        } for op in recent_ops]
        
        return jsonify({
            'active_operations': active_ops,
            'recent_operations': completed_ops
        })
        
    except Exception as e:
        logger.error(f"Error getting operations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        
        # Check components
        components_status = {
            'news_fetcher': news_fetcher is not None,
            'token_manager': token_manager is not None,
            'facebook_poster': facebook_poster is not None,
            'ai_enhancer': ai_enhancer is not None
        }
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': components_status,
            'active_operations': len(active_operations)
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_operations')
def handle_join_operations():
    """Handle client joining operations room"""
    logger.info(f"Client joined operations room: {request.sid}")

# Error handlers
@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Handle HTTP errors gracefully"""
    logger.error(f"HTTP error: {error.code} - {error.description}")
    return jsonify({
        'error': error.description,
        'code': error.code
    }), error.code

@app.errorhandler(Exception)
def handle_generic_error(error):
    """Handle generic errors gracefully"""
    logger.error(f"Generic error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)