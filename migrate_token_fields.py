#!/usr/bin/env python3
"""
Database migration script for Facebook token management fields
Run this script to add the new token management fields to existing databases
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app (minimal setup for migration)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

def migrate_database():
    """Add new token management fields to existing settings table"""
    
    with app.app_context():
        try:
            # Get database connection
            connection = db.engine.connect()
            
            # Check if the new columns already exist
            result = connection.execute(db.text("PRAGMA table_info(settings)"))
            existing_columns = [row[1] for row in result.fetchall()]
            
            new_columns = [
                'facebook_app_id',
                'facebook_app_secret', 
                'facebook_token_expires_at',
                'facebook_token_last_renewed',
                'facebook_token_auto_renew'
            ]
            
            # Add missing columns
            for column in new_columns:
                if column not in existing_columns:
                    if column == 'facebook_app_id':
                        connection.execute(db.text(f"ALTER TABLE settings ADD COLUMN {column} VARCHAR(100)"))
                    elif column == 'facebook_app_secret':
                        connection.execute(db.text(f"ALTER TABLE settings ADD COLUMN {column} TEXT"))
                    elif column in ['facebook_token_expires_at', 'facebook_token_last_renewed']:
                        connection.execute(db.text(f"ALTER TABLE settings ADD COLUMN {column} DATETIME"))
                    elif column == 'facebook_token_auto_renew':
                        connection.execute(db.text(f"ALTER TABLE settings ADD COLUMN {column} BOOLEAN DEFAULT 1"))
                    
                    print(f"Added column: {column}")
                else:
                    print(f"Column already exists: {column}")
            
            connection.commit()
            connection.close()
            
            print("Database migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"Migration error: {str(e)}")
            return False

def setup_initial_token_data(page_id, access_token, app_id, app_secret):
    """Set up initial token data for existing installation"""
    
    with app.app_context():
        try:
            # Import models after app context is established
            from models import Settings
            
            settings = Settings.query.first()
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            # Update with provided credentials
            settings.facebook_page_id = page_id
            settings.facebook_access_token = access_token
            settings.facebook_app_id = app_id
            settings.facebook_app_secret = app_secret
            settings.facebook_token_last_renewed = datetime.now(timezone.utc)
            settings.facebook_token_auto_renew = True
            
            # Try to determine token expiry (assume 60 days for long-lived tokens)
            # This will be updated when the token manager validates the token
            from datetime import timedelta
            settings.facebook_token_expires_at = datetime.now(timezone.utc) + timedelta(days=60)
            
            db.session.commit()
            
            print("Initial token data set up successfully!")
            print(f"Page ID: {page_id}")
            print(f"App ID: {app_id}")
            print("Token auto-renewal: Enabled")
            
            return True
            
        except Exception as e:
            print(f"Setup error: {str(e)}")
            return False

if __name__ == '__main__':
    print("Facebook Token Management - Database Migration")
    print("=" * 50)
    
    # Run migration
    if migrate_database():
        print("\nMigration successful!")
        
        # Check if initial setup is requested
        if len(sys.argv) > 4:
            page_id = sys.argv[1]
            access_token = sys.argv[2] 
            app_id = sys.argv[3]
            app_secret = sys.argv[4]
            
            print(f"\nSetting up initial token data...")
            setup_initial_token_data(page_id, access_token, app_id, app_secret)
        else:
            print("\nTo set up initial token data, run:")
            print("python migrate_token_fields.py <page_id> <access_token> <app_id> <app_secret>")
    else:
        print("\nMigration failed!")
        sys.exit(1)