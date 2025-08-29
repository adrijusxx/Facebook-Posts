#!/usr/bin/env python3
"""
Simple test script for new features - no external dependencies
"""

import os
import sys

def test_python_syntax():
    """Test that all Python files have valid syntax"""
    print("🔍 Testing Python syntax...")
    import py_compile
    
    files_to_test = [
        'app.py',
        'facebook_poster.py', 
        'facebook_token_manager.py',
        'models.py',
        'news_fetcher.py',
        'migrate_new_fields.py'
    ]
    
    for file in files_to_test:
        try:
            py_compile.compile(file, doraise=True)
            print(f"✅ {file} - syntax OK")
        except py_compile.PyCompileError as e:
            print(f"❌ {file} - syntax error: {e}")
            return False
    
    return True

def test_freightwaves_in_code():
    """Test that FreightWaves is properly added to app.py"""
    print("🔍 Testing FreightWaves in app.py...")
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        if 'FreightWaves' in content and 'freightwaves.com/feed' in content:
            print("✅ FreightWaves RSS feed found in app.py")
            return True
        else:
            print("❌ FreightWaves RSS feed not found in app.py")
            return False
    except Exception as e:
        print(f"❌ Error reading app.py: {str(e)}")
        return False

def test_new_routes_in_code():
    """Test that new routes are defined in app.py"""
    print("🔍 Testing new routes in app.py...")
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        required_routes = [
            '/refresh_facebook_token',
            '/prepopulate_settings',
            '/check_token_status'
        ]
        
        missing_routes = []
        for route in required_routes:
            if route in content:
                print(f"✅ Route {route} found")
            else:
                print(f"❌ Route {route} missing")
                missing_routes.append(route)
        
        return len(missing_routes) == 0
        
    except Exception as e:
        print(f"❌ Error checking routes: {str(e)}")
        return False

def test_model_fields():
    """Test that new model fields are defined"""
    print("🔍 Testing model fields in models.py...")
    try:
        with open('models.py', 'r') as f:
            content = f.read()
        
        required_fields = [
            'facebook_app_id',
            'facebook_app_secret',
            'facebook_token_expires_at',
            'facebook_token_last_renewed',
            'facebook_token_auto_renew'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field in content:
                print(f"✅ Field {field} found")
            else:
                print(f"❌ Field {field} missing")
                missing_fields.append(field)
        
        return len(missing_fields) == 0
        
    except Exception as e:
        print(f"❌ Error checking model fields: {str(e)}")
        return False

def test_template_updates():
    """Test that template has been updated with new features"""
    print("🔍 Testing template updates...")
    try:
        with open('templates/settings.html', 'r') as f:
            content = f.read()
        
        required_elements = [
            'facebook_app_id',
            'facebook_app_secret', 
            'facebook_token_auto_renew',
            'refreshFacebookToken',
            'prepopulateSettings',
            'checkTokenStatus',
            'Helpful Links'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element in content:
                print(f"✅ Template element {element} found")
            else:
                print(f"❌ Template element {element} missing")
                missing_elements.append(element)
        
        return len(missing_elements) == 0
        
    except Exception as e:
        print(f"❌ Error checking template: {str(e)}")
        return False

def test_token_manager_updates():
    """Test that token manager has proper field handling"""
    print("🔍 Testing token manager field handling...")
    try:
        with open('facebook_token_manager.py', 'r') as f:
            content = f.read()
        
        # Check for proper hasattr/getattr usage
        required_patterns = [
            'hasattr(settings, \'facebook_app_id\')',
            'hasattr(settings, \'facebook_app_secret\')', 
            'hasattr(settings, \'facebook_token_expires_at\')',
            'getattr(settings, \'facebook_app_id\'',
            'getattr(settings, \'facebook_app_secret\''
        ]
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern in content:
                print(f"✅ Field handling pattern '{pattern[:30]}...' found")
            else:
                print(f"❌ Field handling pattern '{pattern[:30]}...' missing")
                missing_patterns.append(pattern)
        
        return len(missing_patterns) == 0
        
    except Exception as e:
        print(f"❌ Error checking token manager: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting simple test suite for new features...\n")
    
    tests = [
        ("Python Syntax", test_python_syntax),
        ("FreightWaves in Code", test_freightwaves_in_code),
        ("New Routes", test_new_routes_in_code),
        ("Model Fields", test_model_fields),
        ("Template Updates", test_template_updates),
        ("Token Manager Updates", test_token_manager_updates)
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
        print("🎉 All tests passed! The new features are properly implemented.")
        print("\n📝 NEXT STEPS:")
        print("1. Run the migration script: python3 migrate_new_fields.py")
        print("2. Start the application: python3 app.py")
        print("3. Go to settings and click 'Prepopulate Settings'")
        print("4. Test the new token management features")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)