#!/usr/bin/env python3
"""
Migration script to add new Facebook token management fields to existing databases
Run this script after updating the code to add the new fields
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Settings

# Initialize Flask app for migration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def migrate_database():
    """Add new fields to existing database"""
    with app.app_context():
        try:
            # Try to create all tables (this will add new columns if they don't exist)
            db.create_all()
            
            # Get existing settings
            settings = Settings.query.first()
            if settings:
                # Set default values for new fields if they're None
                if not hasattr(settings, 'facebook_app_id') or settings.facebook_app_id is None:
                    settings.facebook_app_id = ""
                
                if not hasattr(settings, 'facebook_app_secret') or settings.facebook_app_secret is None:
                    settings.facebook_app_secret = ""
                
                if not hasattr(settings, 'facebook_token_auto_renew') or settings.facebook_token_auto_renew is None:
                    settings.facebook_token_auto_renew = True
                
                db.session.commit()
                print("✅ Successfully migrated existing settings")
            else:
                print("ℹ️  No existing settings found, migration not needed")
            
            print("✅ Database migration completed successfully")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
        
        return True

if __name__ == "__main__":
    print("🔄 Starting database migration...")
    success = migrate_database()
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)