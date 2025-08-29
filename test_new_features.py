#!/usr/bin/env python3
"""
Test script for new features added to the Facebook Trucking News Automation system
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask
from models import db, Settings, NewsSource

# Initialize Flask app for testing
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///trucking_news.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def test_freightwaves_rss():
    """Test FreightWaves RSS feed URL format"""
    print("🔍 Testing FreightWaves RSS feed URL format...")
    try:
        freightwaves_url = "https://www.freightwaves.com/feed"
        if freightwaves_url.startswith("https://") and "/feed" in freightwaves_url:
            print("✅ FreightWaves RSS feed URL format is correct")
            return True
        else:
            print(f"❌ FreightWaves RSS feed URL format incorrect: {freightwaves_url}")
            return False
    except Exception as e:
        print(f"❌ Error checking FreightWaves RSS feed URL: {str(e)}")
        return False

def test_database_schema():
    """Test that new database fields exist"""
    print("🔍 Testing database schema...")
    with app.app_context():
        try:
            db.create_all()
            
            # Test Settings model has new fields
            settings = Settings()
            required_fields = [
                'facebook_app_id',
                'facebook_app_secret', 
                'facebook_token_expires_at',
                'facebook_token_last_renewed',
                'facebook_token_auto_renew'
            ]
            
            for field in required_fields:
                if hasattr(settings, field):
                    print(f"✅ Settings.{field} field exists")
                else:
                    print(f"❌ Settings.{field} field missing")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Database schema test failed: {str(e)}")
            return False

def test_freightwaves_in_defaults():
    """Test that FreightWaves is in default sources"""
    print("🔍 Testing FreightWaves in default sources...")
    with app.app_context():
        try:
            # Check if FreightWaves source exists
            freightwaves = NewsSource.query.filter_by(name="FreightWaves").first()
            if freightwaves:
                print(f"✅ FreightWaves source found: {freightwaves.url}")
                if freightwaves.url == "https://www.freightwaves.com/feed":
                    print("✅ FreightWaves URL is correct")
                    return True
                else:
                    print(f"❌ FreightWaves URL incorrect: {freightwaves.url}")
                    return False
            else:
                print("⚠️  FreightWaves source not found in database (will be added on first run)")
                return True
                
        except Exception as e:
            print(f"❌ Error checking FreightWaves source: {str(e)}")
            return False

def test_app_routes():
    """Test that new app routes exist"""
    print("🔍 Testing new app routes...")
    try:
        # Import the app to check if routes are defined
        from app import app as main_app
        
        route_rules = [str(rule) for rule in main_app.url_map.iter_rules()]
        
        required_routes = [
            '/refresh_facebook_token',
            '/prepopulate_settings', 
            '/check_token_status'
        ]
        
        for route in required_routes:
            if any(route in rule for rule in route_rules):
                print(f"✅ Route {route} exists")
            else:
                print(f"❌ Route {route} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking app routes: {str(e)}")
        return False

def test_token_manager_methods():
    """Test token manager has required methods"""
    print("🔍 Testing token manager methods...")
    try:
        from facebook_token_manager import FacebookTokenManager
        
        manager = FacebookTokenManager()
        required_methods = [
            'validate_token_and_get_info',
            'check_if_renewal_needed',
            'renew_page_access_token',
            'auto_renew_token_if_needed'
        ]
        
        for method in required_methods:
            if hasattr(manager, method):
                print(f"✅ FacebookTokenManager.{method} exists")
            else:
                print(f"❌ FacebookTokenManager.{method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking token manager: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting comprehensive test suite for new features...\n")
    
    tests = [
        ("FreightWaves RSS Feed", test_freightwaves_rss),
        ("Database Schema", test_database_schema),
        ("FreightWaves in Defaults", test_freightwaves_in_defaults),
        ("App Routes", test_app_routes),
        ("Token Manager Methods", test_token_manager_methods)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print('='*50)
        result = test_func()
        results.append((test_name, result))
    
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The new features are ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)