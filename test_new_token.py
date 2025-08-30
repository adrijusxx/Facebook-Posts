#!/usr/bin/env python3
"""
Test the newly configured Facebook token
"""

from app import app, db
from models import Settings
from facebook_token_manager import FacebookTokenManager

def test_token():
    """Test the configured Facebook token"""
    with app.app_context():
        db.create_all()
        settings = Settings.query.first()
        
        if not settings or not settings.facebook_access_token:
            print("❌ No Facebook token configured")
            return False
        
        print("Testing Facebook token...")
        print("=" * 30)
        
        token_manager = FacebookTokenManager()
        
        # Test 1: Validate token
        print("1. Validating token...")
        token_info = token_manager.validate_token_and_get_info(settings.facebook_access_token)
        
        if not token_info['success']:
            print(f"❌ Token validation failed: {token_info['error']}")
            return False
        
        print(f"✅ Token is valid")
        print(f"   App ID: {token_info.get('app_id')}")
        print(f"   User ID: {token_info.get('user_id')}")
        print(f"   Expires: {token_info.get('expiry_date')}")
        print(f"   Days until expiry: {token_info.get('days_until_expiry')}")
        
        # Test 2: Check renewal status
        print("\n2. Checking renewal status...")
        renewal_check = token_manager.check_if_renewal_needed(settings)
        print(f"   Renewal needed: {renewal_check['renewal_needed']}")
        print(f"   Reason: {renewal_check['reason']}")
        
        # Test 3: Test page access
        print("\n3. Testing page access...")
        try:
            import requests
            url = f"https://graph.facebook.com/v18.0/{settings.facebook_page_id}"
            params = {
                'access_token': settings.facebook_access_token,
                'fields': 'id,name,access_token'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Page access successful")
                print(f"   Page: {data.get('name')}")
                print(f"   Page ID: {data.get('id')}")
            else:
                print(f"❌ Page access failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Page access test error: {str(e)}")
            return False
        
        print("\n🎉 All tests passed! Your Facebook token is working correctly.")
        return True

if __name__ == '__main__':
    test_token()
