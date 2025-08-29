#!/usr/bin/env python3
"""
Test script for the Facebook Token Renewal System
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app for testing
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from models import db, Settings
from facebook_token_manager import FacebookTokenManager

db.init_app(app)

def test_system():
    """Test the token renewal system"""
    
    print("Facebook Token Renewal System - Test")
    print("=" * 40)
    
    with app.app_context():
        try:
            # Initialize token manager
            token_manager = FacebookTokenManager()
            
            # Check database setup
            print("1. Checking database setup...")
            settings = Settings.query.first()
            if settings:
                print("   ✓ Settings table exists")
                
                # Check new fields
                has_token_fields = all([
                    hasattr(settings, 'facebook_app_id'),
                    hasattr(settings, 'facebook_app_secret'),
                    hasattr(settings, 'facebook_token_expires_at'),
                    hasattr(settings, 'facebook_token_last_renewed'),
                    hasattr(settings, 'facebook_token_auto_renew')
                ])
                
                if has_token_fields:
                    print("   ✓ Token management fields added")
                else:
                    print("   ✗ Token management fields missing")
                    return False
            else:
                print("   ! No settings found - creating default settings")
                settings = Settings()
                db.session.add(settings)
                db.session.commit()
            
            # Test token manager methods
            print("\n2. Testing token manager...")
            
            # Test renewal check (should work even without token)
            try:
                renewal_check = token_manager.check_if_renewal_needed()
                print(f"   ✓ Renewal check: {renewal_check['reason']}")
            except Exception as e:
                print(f"   ✗ Renewal check failed: {e}")
                return False
            
            # Test token status
            try:
                status = token_manager.get_token_status()
                print(f"   ✓ Token status check: {'Token configured' if status['success'] else 'No token configured'}")
            except Exception as e:
                print(f"   ✗ Token status check failed: {e}")
                return False
            
            # Test configuration
            print("\n3. Current configuration:")
            print(f"   Page ID: {getattr(settings, 'facebook_page_id', 'Not set')}")
            print(f"   App ID: {getattr(settings, 'facebook_app_id', 'Not set')}")
            print(f"   Token expires: {getattr(settings, 'facebook_token_expires_at', 'Not set')}")
            print(f"   Last renewed: {getattr(settings, 'facebook_token_last_renewed', 'Never')}")
            print(f"   Auto-renewal: {'Enabled' if getattr(settings, 'facebook_token_auto_renew', False) else 'Disabled'}")
            
            print("\n4. System status:")
            if settings.facebook_access_token:
                print("   ✓ Access token configured")
                if getattr(settings, 'facebook_app_id') and getattr(settings, 'facebook_app_secret'):
                    print("   ✓ App credentials configured")
                    print("   ✓ System ready for automatic renewal")
                else:
                    print("   ! App credentials missing - manual setup only")
            else:
                print("   ! No access token configured")
                print("   → Run get_fresh_token.py for setup instructions")
            
            print("\n" + "=" * 40)
            print("System test completed successfully!")
            print("\nNext steps:")
            if not settings.facebook_access_token:
                print("1. Get a fresh Facebook token (see get_fresh_token.py)")
                print("2. Set up token using API or migration script")
            print("3. Start the application to begin automatic renewal")
            print("4. Monitor logs for renewal activities")
            
            return True
            
        except Exception as e:
            print(f"\nSystem test failed: {str(e)}")
            return False

if __name__ == '__main__':
    success = test_system()
    sys.exit(0 if success else 1)