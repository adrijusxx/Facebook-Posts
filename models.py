"""
Database models for the Facebook Trucking News Automation system
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Profile(db.Model):
    """Model for managing multiple Facebook page profiles"""
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Visual customization
    primary_color = db.Column(db.String(7), default='#3B82F6')  # Hex color
    secondary_color = db.Column(db.String(7), default='#1E40AF')
    background_color = db.Column(db.String(7), default='#F8FAFC')
    accent_color = db.Column(db.String(7), default='#F59E0B')
    icon = db.Column(db.String(100), default='🚛')  # Emoji or icon
    
    # Facebook configuration
    facebook_page_id = db.Column(db.String(100), nullable=True)
    facebook_page_name = db.Column(db.String(200), nullable=True)
    facebook_access_token = db.Column(db.Text, nullable=True)
    facebook_app_id = db.Column(db.String(100), nullable=True)
    facebook_app_secret = db.Column(db.Text, nullable=True)
    
    # AI configuration
    openai_api_key = db.Column(db.Text, nullable=True)
    ai_enhancement_enabled = db.Column(db.Boolean, default=True)
    ai_post_style = db.Column(db.String(50), default='informative')
    
    # Posting configuration
    posts_per_day = db.Column(db.Integer, default=3)
    posting_hours = db.Column(db.String(50), default='9,14,19')
    enabled = db.Column(db.Boolean, default=True)
    
    # Token management
    facebook_token_expires_at = db.Column(db.DateTime, nullable=True)
    facebook_token_last_renewed = db.Column(db.DateTime, nullable=True)
    facebook_token_auto_renew = db.Column(db.Boolean, default=True)
    
    # Metadata
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Profile {self.name}: {self.display_name}>'
    
    def to_dict(self):
        """Convert profile to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'background_color': self.background_color,
            'accent_color': self.accent_color,
            'icon': self.icon,
            'facebook_page_id': self.facebook_page_id,
            'facebook_page_name': self.facebook_page_name,
            'facebook_access_token': self.facebook_access_token,
            'openai_api_key': self.openai_api_key,
            'ai_enhancement_enabled': self.ai_enhancement_enabled,
            'ai_post_style': self.ai_post_style,
            'posts_per_day': self.posts_per_day,
            'posting_hours': self.posting_hours,
            'enabled': self.enabled,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Post(db.Model):
    """Model for storing news posts"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(1000), nullable=True)
    image_url = db.Column(db.String(1000), nullable=True)
    facebook_post_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, posted, failed, skipped
    source = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    posted_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Profile association
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)
    profile = db.relationship('Profile', backref=db.backref('posts', lazy=True))
    
    def __repr__(self):
        return f'<Post {self.id}: {self.title[:50]}...>'

class Settings(db.Model):
    """Model for storing global application settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Global settings
    app_name = db.Column(db.String(200), default='Facebook Trucking News Bot')
    app_theme = db.Column(db.String(50), default='light')  # light, dark, auto
    language = db.Column(db.String(10), default='en')
    timezone = db.Column(db.String(50), default='UTC')
    
    # News fetching settings
    news_fetch_interval = db.Column(db.Integer, default=60)  # minutes
    max_articles_per_fetch = db.Column(db.Integer, default=100)
    enable_auto_fetch = db.Column(db.Boolean, default=True)
    
    # Default profile settings (for backward compatibility)
    default_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)
    default_profile = db.relationship('Profile', foreign_keys=[default_profile_id])
    
    # System settings
    enable_logging = db.Column(db.Boolean, default=True)
    log_level = db.Column(db.String(20), default='INFO')
    enable_analytics = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Settings: {self.app_name}>'

class NewsSource(db.Model):
    """Model for storing news sources"""
    __tablename__ = 'news_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    type = db.Column(db.String(20), default='rss')  # rss, website, api
    enabled = db.Column(db.Boolean, default=True)
    last_fetched = db.Column(db.DateTime, nullable=True)
    total_articles_fetched = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<NewsSource {self.name}: {self.url}>'

class PostingLog(db.Model):
    """Model for logging posting activities"""
    __tablename__ = 'posting_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # fetch, post, error, skip
    message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    post = db.relationship('Post', backref=db.backref('logs', lazy=True))
    profile = db.relationship('Profile', backref=db.backref('posting_logs', lazy=True))
    
    def __repr__(self):
        return f'<PostingLog {self.action}: {self.message[:50]}...>'

class OperationLog(db.Model):
    """Model for logging operations with progress tracking"""
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.String(100), nullable=False, unique=True)
    operation_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False)  # running, completed, failed
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=True)  # seconds
    progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    
    # Profile association
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)
    profile = db.relationship('Profile', backref=db.backref('operation_logs', lazy=True))
    
    def __repr__(self):
        return f'<OperationLog {self.operation_id}: {self.operation_type}>'