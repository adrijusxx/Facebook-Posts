"""
Database models for the Facebook Trucking News Automation system
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
    
    def __repr__(self):
        return f'<Post {self.id}: {self.title[:50]}...>'

class Settings(db.Model):
    """Model for storing application settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    posts_per_day = db.Column(db.Integer, default=3)
    facebook_page_id = db.Column(db.String(100), nullable=True)
    facebook_access_token = db.Column(db.Text, nullable=True)
    posting_hours = db.Column(db.String(50), default='9,14,19')  # Default: 9 AM, 2 PM, 7 PM
    enabled = db.Column(db.Boolean, default=True)
    openai_api_key = db.Column(db.Text, nullable=True)
    ai_enhancement_enabled = db.Column(db.Boolean, default=True)
    ai_post_style = db.Column(db.String(50), default='informative')  # informative, motivational, question, tip
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Facebook token management fields
    facebook_app_id = db.Column(db.String(100), nullable=True)
    facebook_app_secret = db.Column(db.Text, nullable=True)
    facebook_token_expires_at = db.Column(db.DateTime, nullable=True)
    facebook_token_last_renewed = db.Column(db.DateTime, nullable=True)
    facebook_token_auto_renew = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Settings: {self.posts_per_day} posts/day>'

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
    action = db.Column(db.String(50), nullable=False)  # fetch, post, error, skip
    message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    post = db.relationship('Post', backref=db.backref('logs', lazy=True))
    
    def __repr__(self):
        return f'<PostingLog {self.action}: {self.message[:50]}...>'