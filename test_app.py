#!/usr/bin/env python3
"""
Simple test to check if the Flask app can start
"""

import os
import sys

# Set environment variables for testing
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['FLASK_ENV'] = 'development'

try:
    print("Testing Flask app startup...")
    
    # Try to import the app
    from app import app
    
    print("✅ App imported successfully")
    
    # Try to create a test context
    with app.test_client() as client:
        print("✅ Test client created successfully")
        
        # Try to access the root route
        response = client.get('/')
        print(f"✅ Root route response: {response.status_code}")
        
    print("🎉 App is working correctly!")
    
except Exception as e:
    print(f"❌ Error starting app: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
