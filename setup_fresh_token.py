#!/usr/bin/env python3
"""
Facebook Token Setup Script
This script helps you get a fresh Facebook token and set it up in the system
"""

import requests
import json
from app import app, db
from models import Settings
from facebook_token_manager import FacebookTokenManager

def get_long_lived_token(app_id, app_secret, short_lived_token):
    """Exchange short-lived token for long-lived token"""
    try:
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': app_id,
            'client_secret': app_secret,
            'fb_exchange_token': short_lived_token
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'access_token': data.get('access_token'),
                'expires_in': data.get('expires_in')
            }
        else:
            return {
                'success': False,
                'error': f"Failed to get long-lived token: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error: {str(e)}"
        }

def get_page_access_token(user_access_token, page_id):
    """Get page access token using user access token"""
    try:
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            'access_token': user_access_token
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            pages = data.get('data', [])
            
            for page in pages:
                if page.get('id') == page_id:
                    return {
                        'success': True,
                        'access_token': page.get('access_token'),
                        'page_name': page.get('name')
                    }
            
            return {
                'success': False,
                'error': f"Page {page_id} not found in accessible pages"
            }
        else:
            return {
                'success': False,
                'error': f"Failed to get pages: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error: {str(e)}"
        }

def setup_token_in_database(page_id, access_token, app_id, app_secret):
    """Set up the token in the database"""
    try:
        with app.app_context():
            db.create_all()
            
            # Get or create settings
            settings = Settings.query.first()
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            # Update token information
            settings.facebook_page_id = page_id
            settings.facebook_access_token = access_token
            settings.facebook_app_id = app_id
            settings.facebook_app_secret = app_secret
            settings.facebook_token_auto_renew = True
            
            # Validate and get token info
            token_manager = FacebookTokenManager()
            token_info = token_manager.validate_token_and_get_info(access_token)
            
            if token_info['success']:
                settings.facebook_token_expires_at = token_info.get('expiry_date')
                settings.facebook_token_last_renewed = token_info.get('expiry_date')
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Token successfully configured in database',
                'token_info': token_info if token_info['success'] else None
            }
    except Exception as e:
        return {
            'success': False,
            'error': f"Database setup error: {str(e)}"
        }

def main():
    print("Facebook Token Setup Script")
    print("=" * 40)
    print()
    
    # Your Facebook app credentials (from the error message)
    APP_ID = "1173190721520267"
    APP_SECRET = "f90fd5f582a74db3b857396e1b718a63"
    PAGE_ID = "534295833110036"
    
    print(f"App ID: {APP_ID}")
    print(f"Page ID: {PAGE_ID}")
    print()
    
    print("Step 1: Get a fresh User Access Token")
    print("-" * 40)
    print("1. Go to: https://developers.facebook.com/tools/explorer/")
    print("2. Select your app: '1173190721520267'")
    print("3. Get a User Access Token with these permissions:")
    print("   - pages_show_list")
    print("   - pages_read_engagement")
    print("   - pages_manage_posts")
    print("   - publish_to_groups")
    print("4. Click 'Generate Access Token' and authorize")
    print("5. Copy the short-lived token")
    print()
    
    # Get short-lived token from user
    short_lived_token = input("Enter your short-lived token: ").strip()
    
    if not short_lived_token:
        print("No token provided. Exiting.")
        return
    
    print("\nStep 2: Exchange for long-lived token")
    print("-" * 40)
    
    long_lived_result = get_long_lived_token(APP_ID, APP_SECRET, short_lived_token)
    
    if not long_lived_result['success']:
        print(f"❌ Failed to get long-lived token: {long_lived_result['error']}")
        return
    
    long_lived_token = long_lived_result['access_token']
    expires_in = long_lived_result['expires_in']
    
    print(f"✅ Long-lived token obtained successfully")
    print(f"   Expires in: {expires_in} seconds ({expires_in/86400:.1f} days)")
    
    print("\nStep 3: Get page access token")
    print("-" * 40)
    
    page_token_result = get_page_access_token(long_lived_token, PAGE_ID)
    
    if not page_token_result['success']:
        print(f"❌ Failed to get page access token: {page_token_result['error']}")
        return
    
    page_access_token = page_token_result['access_token']
    page_name = page_token_result['page_name']
    
    print(f"✅ Page access token obtained successfully")
    print(f"   Page: {page_name}")
    
    print("\nStep 4: Set up token in database")
    print("-" * 40)
    
    db_result = setup_token_in_database(PAGE_ID, page_access_token, APP_ID, APP_SECRET)
    
    if not db_result['success']:
        print(f"❌ Failed to set up token in database: {db_result['error']}")
        return
    
    print("✅ Token successfully configured in database!")
    
    if db_result.get('token_info'):
        token_info = db_result['token_info']
        print(f"\nToken Information:")
        print(f"   Valid: {token_info.get('is_valid', 'Unknown')}")
        print(f"   Expires: {token_info.get('expiry_date', 'Unknown')}")
        print(f"   Days until expiry: {token_info.get('days_until_expiry', 'Unknown')}")
    
    print("\n🎉 Setup complete! Your Facebook token is now configured and will auto-renew.")
    print("\nYou can now:")
    print("• Run the main application")
    print("• Check token status at /api/token/status")
    print("• The system will automatically renew tokens before they expire")

if __name__ == '__main__':
    main()
