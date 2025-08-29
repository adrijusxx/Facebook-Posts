#!/usr/bin/env python3
"""
Facebook Token System Setup Script
This script sets up the automatic token renewal system with the provided credentials
"""

import sys
import os
from datetime import datetime, timezone

def setup_token_system():
    """Set up the Facebook token renewal system"""
    
    print("Facebook Token Renewal System Setup")
    print("=" * 40)
    
    # Your provided credentials
    page_id = "534295833110036"
    access_token = "EAAQrAsA1wosBPK5HVZBFUaNhrqJd2mQtv4Nmppm6f2LxlnCZCMaEfzASMncXpdcriUqWYO9bP21BEjkWHeZAHyjdYVhSivmYIpeNY2mBuv2vbQb97QHkOei5v5YE9TT8DUyy7VcynB4pqZAxs6vu2xOCrNn9NIwYsgBFmk3OsmwGwiYmiPI5BcWZBk0nUMp9cbOoXorgzJzPWJyZC9S05FdnTxFa4Fh24TCiqZAYCZAa8Xm9BAZDZD"
    app_id = "1173190721520267"
    app_secret = "f90fd5f582a74db3b857396e1b718a63"
    
    print(f"Page ID: {page_id}")
    print(f"App ID: {app_id}")
    print("Setting up token renewal system...")
    
    try:
        # First, run the database migration
        print("\n1. Running database migration...")
        os.system("python3 migrate_token_fields.py")
        
        # Then set up the token data
        print("\n2. Setting up token data...")
        os.system(f'python3 migrate_token_fields.py "{page_id}" "{access_token}" "{app_id}" "{app_secret}"')
        
        print("\n3. Validating token setup...")
        
        # Import and test the token manager
        from facebook_token_manager import FacebookTokenManager
        from flask import Flask
        from models import db, Settings
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Initialize Flask app for testing
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            token_manager = FacebookTokenManager()
            
            # Test token validation
            token_info = token_manager.validate_token_and_get_info(access_token)
            if token_info['success']:
                print("✓ Token validation successful!")
                print(f"  Token is valid: {token_info['is_valid']}")
                if token_info.get('expiry_date'):
                    print(f"  Expires: {token_info['expiry_date']}")
                if token_info.get('days_until_expiry'):
                    print(f"  Days until expiry: {token_info['days_until_expiry']}")
            else:
                print(f"✗ Token validation failed: {token_info['error']}")
            
            # Test renewal check
            renewal_check = token_manager.check_if_renewal_needed()
            print(f"\nRenewal needed: {renewal_check['renewal_needed']}")
            print(f"Reason: {renewal_check['reason']}")
            
            # Get token status
            status = token_manager.get_token_status()
            if status['success']:
                print("\n✓ Token system setup successful!")
                print(f"  Auto-renewal: {'Enabled' if status.get('last_renewed') else 'Configured'}")
                print(f"  Token valid: {status['token_valid']}")
            else:
                print(f"\n✗ Token system setup failed: {status['error']}")
        
        print("\n" + "=" * 40)
        print("Setup Complete!")
        print("\nThe token renewal system is now configured to:")
        print("• Check token status every 6 hours")
        print("• Automatically renew tokens when they have 50 days or less remaining")
        print("• Log all renewal activities")
        print("\nAPI Endpoints available:")
        print("• GET /api/token/status - Check token status")
        print("• POST /api/token/renew - Manually trigger renewal")
        print("• POST /api/token/setup - Set up new token")
        print("• POST /api/token/validate - Validate a token")
        
        return True
        
    except Exception as e:
        print(f"\nSetup failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = setup_token_system()
    sys.exit(0 if success else 1)