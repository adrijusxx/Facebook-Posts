#!/usr/bin/env python3
"""
Database migration script to transition from old Settings model to new Profile-based system
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Settings, Profile, Post, OperationLog, PostingLog

def migrate_database():
    """Migrate the database from old Settings model to new Profile system"""
    print("🚀 Starting database migration...")
    
    with app.app_context():
        try:
            # Check if we need to create the new tables
            db.create_all()
            print("✅ Database tables created/updated")
            
            # Check if we already have profiles
            existing_profiles = Profile.query.count()
            if existing_profiles > 0:
                print(f"✅ Found {existing_profiles} existing profiles, skipping migration")
                return
            
            # Get old settings
            old_settings = Settings.query.first()
            
            if old_settings:
                print("📋 Found old settings, migrating to new profile system...")
                
                # Create default profile from old settings
                default_profile = Profile(
                    name='default',
                    display_name='Main Trucking Page',
                    description='Migrated from old settings',
                    primary_color='#3B82F6',
                    secondary_color='#1E40AF',
                    background_color='#F8FAFC',
                    accent_color='#F59E0B',
                    icon='🚛',
                    is_default=True,
                    enabled=True
                )
                
                # Try to migrate old settings if they exist
                try:
                    # Check if old settings has the old attributes
                    if hasattr(old_settings, 'posts_per_day'):
                        default_profile.posts_per_day = old_settings.posts_per_day
                    if hasattr(old_settings, 'facebook_page_id'):
                        default_profile.facebook_page_id = old_settings.facebook_page_id
                    if hasattr(old_settings, 'facebook_access_token'):
                        default_profile.facebook_access_token = old_settings.facebook_access_token
                    if hasattr(old_settings, 'posting_hours'):
                        default_profile.posting_hours = old_settings.posting_hours
                    if hasattr(old_settings, 'enabled'):
                        default_profile.enabled = old_settings.enabled
                    if hasattr(old_settings, 'openai_api_key'):
                        default_profile.openai_api_key = old_settings.openai_api_key
                    if hasattr(old_settings, 'ai_enhancement_enabled'):
                        default_profile.ai_enhancement_enabled = old_settings.ai_enhancement_enabled
                    if hasattr(old_settings, 'ai_post_style'):
                        default_profile.ai_post_style = old_settings.ai_post_style
                    
                    print("✅ Migrated old settings to default profile")
                except Exception as e:
                    print(f"⚠️  Warning: Could not migrate some old settings: {e}")
                
                db.session.add(default_profile)
                db.session.commit()
                print("✅ Default profile created successfully")
                
                # Update existing posts to use the default profile
                try:
                    posts_updated = Post.query.update({Post.profile_id: default_profile.id})
                    if posts_updated > 0:
                        print(f"✅ Updated {posts_updated} existing posts to use default profile")
                except Exception as e:
                    print(f"⚠️  Warning: Could not update existing posts: {e}")
                
                # Update existing operation logs to use the default profile
                try:
                    logs_updated = OperationLog.query.update({OperationLog.profile_id: default_profile.id})
                    if logs_updated > 0:
                        print(f"✅ Updated {logs_updated} existing operation logs to use default profile")
                except Exception as e:
                    print(f"⚠️  Warning: Could not update existing operation logs: {e}")
                
                # Update existing posting logs to use the default profile
                try:
                    posting_logs_updated = PostingLog.query.update({PostingLog.profile_id: default_profile.id})
                    if posting_logs_updated > 0:
                        print(f"✅ Updated {posting_logs_updated} existing posting logs to use default profile")
                except Exception as e:
                    print(f"⚠️  Warning: Could not update existing posting logs: {e}")
                
            else:
                print("📋 No old settings found, creating default profile...")
                
                # Create a basic default profile
                default_profile = Profile(
                    name='default',
                    display_name='Main Trucking Page',
                    description='Default Facebook page for trucking news',
                    primary_color='#3B82F6',
                    secondary_color='#1E40AF',
                    background_color='#F8FAFC',
                    accent_color='#F59E0B',
                    icon='🚛',
                    is_default=True,
                    enabled=True,
                    posts_per_day=3,
                    posting_hours='9,14,19',
                    ai_enhancement_enabled=True,
                    ai_post_style='informative'
                )
                
                db.session.add(default_profile)
                db.session.commit()
                print("✅ Default profile created successfully")
            
            # Create some example profiles for demonstration
            print("🎨 Creating example profiles for demonstration...")
            
            # Professional profile
            professional_profile = Profile(
                name='professional',
                display_name='Professional Trucking',
                description='Professional trucking industry insights and analysis',
                primary_color='#1F2937',
                secondary_color='#374151',
                background_color='#F9FAFB',
                accent_color='#10B981',
                icon='🚚',
                enabled=True,
                posts_per_day=2,
                posting_hours='8,17',
                ai_enhancement_enabled=True,
                ai_post_style='industry_insight'
            )
            db.session.add(professional_profile)
            
            # Community profile
            community_profile = Profile(
                name='community',
                display_name='Trucking Community',
                description='Community-focused content for truck drivers and enthusiasts',
                primary_color='#DC2626',
                secondary_color='#B91C1C',
                background_color='#FEF2F2',
                accent_color='#F59E0B',
                icon='👥',
                enabled=True,
                posts_per_day=4,
                posting_hours='7,12,18,21',
                ai_enhancement_enabled=True,
                ai_post_style='motivational'
            )
            db.session.add(community_profile)
            
            # News profile
            news_profile = Profile(
                name='news',
                display_name='Trucking News Hub',
                description='Breaking news and updates from the trucking industry',
                primary_color='#2563EB',
                secondary_color='#1D4ED8',
                background_color='#EFF6FF',
                accent_color='#7C3AED',
                icon='📰',
                enabled=True,
                posts_per_day=5,
                posting_hours='6,9,12,15,18',
                ai_enhancement_enabled=True,
                ai_post_style='informative'
            )
            db.session.add(news_profile)
            
            db.session.commit()
            print("✅ Example profiles created successfully")
            
            # Print summary
            total_profiles = Profile.query.count()
            print(f"\n🎉 Migration completed successfully!")
            print(f"📊 Total profiles created: {total_profiles}")
            print(f"🔵 Default profile: {default_profile.display_name}")
            print(f"📱 You can now switch between profiles and customize each one individually")
            print(f"🌐 Visit /profiles to manage your profiles")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    try:
        migrate_database()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
