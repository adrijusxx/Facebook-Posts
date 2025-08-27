#!/usr/bin/env python3
"""
Production startup script for Facebook Trucking News Automation
"""

import os
import sys
from app import app, db
from models import Settings, NewsSource

def create_default_data():
    """Create default settings and news sources if they don't exist"""
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create default settings if none exist
        if not Settings.query.first():
            settings = Settings(
                posts_per_day=3,
                posting_hours='9,14,19',
                enabled=False,  # Start disabled until configured
                ai_enhancement_enabled=True,
                ai_post_style='informative'
            )
            db.session.add(settings)
            print("✓ Created default settings")
        
        # Create default news sources if none exist
        if not NewsSource.query.first():
            default_sources = [
                NewsSource(
                    name="Transport Topics",
                    url="https://www.ttnews.com/rss.xml",
                    type="rss",
                    enabled=True
                ),
                NewsSource(
                    name="Trucking Info",
                    url="https://www.truckinginfo.com/rss",
                    type="rss",
                    enabled=True
                ),
                NewsSource(
                    name="Fleet Owner",
                    url="https://www.fleetowner.com/rss.xml",
                    type="rss",
                    enabled=True
                ),
                NewsSource(
                    name="Commercial Carrier Journal",
                    url="https://www.ccjdigital.com/feed/",
                    type="rss",
                    enabled=True
                ),
                NewsSource(
                    name="Overdrive Magazine",
                    url="https://www.overdriveonline.com/feed/",
                    type="rss",
                    enabled=True
                )
            ]
            
            for source in default_sources:
                db.session.add(source)
            
            print(f"✓ Created {len(default_sources)} default news sources")
        
        db.session.commit()
        print("✓ Database initialization complete")

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['SECRET_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("   Consider creating a .env file with your configuration")
    
    # Check for optional but recommended variables
    optional_vars = {
        'FACEBOOK_PAGE_ID': 'Facebook integration',
        'FACEBOOK_ACCESS_TOKEN': 'Facebook posting',
        'OPENAI_API_KEY': 'AI content enhancement'
    }
    
    for var, purpose in optional_vars.items():
        if not os.getenv(var):
            print(f"ℹ️  Optional: {var} not set (needed for {purpose})")

def main():
    """Main startup function"""
    print("🚛 Facebook Trucking News Automation")
    print("=" * 50)
    
    # Check environment
    check_environment()
    
    # Initialize database
    create_default_data()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"\n🌐 Starting server on http://{host}:{port}")
    print(f"📊 Debug mode: {debug}")
    print("\n✨ Features available:")
    print("   - Automated news fetching from trucking sources")
    print("   - AI-enhanced content generation with OpenAI")
    print("   - Scheduled Facebook posting")
    print("   - Web-based management interface")
    print("\n📋 Next steps:")
    print("   1. Open the web interface")
    print("   2. Go to Settings to configure Facebook and OpenAI")
    print("   3. Test news fetching and posting")
    print("   4. Enable automatic posting when ready")
    print("\n" + "=" * 50)
    
    # Start the application
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()