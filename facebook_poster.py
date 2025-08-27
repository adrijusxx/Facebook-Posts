"""
Facebook posting system using Facebook Graph API
"""

import requests
import logging
from datetime import datetime
from models import db, Post, Settings, PostingLog
import os

logger = logging.getLogger(__name__)

class FacebookPoster:
    """Handles posting to Facebook pages using Graph API"""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        
    def post_to_facebook(self, post):
        """Post content to Facebook page"""
        settings = Settings.query.first()
        if not settings:
            logger.error("No settings found")
            return {'success': False, 'error': 'No settings configured'}
        
        if not settings.facebook_access_token or not settings.facebook_page_id:
            logger.error("Facebook credentials not configured")
            return {'success': False, 'error': 'Facebook credentials not configured'}
        
        try:
            # Prepare the post data
            post_data = {
                'message': post.content,
                'access_token': settings.facebook_access_token
            }
            
            # Add link if available
            if post.url:
                post_data['link'] = post.url
            
            # Add image if available
            if post.image_url:
                post_data['picture'] = post.image_url
            
            # Make the API request
            endpoint = f"{self.base_url}/{settings.facebook_page_id}/feed"
            response = requests.post(endpoint, data=post_data, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                facebook_post_id = response_data.get('id')
                
                # Update post in database
                post.facebook_post_id = facebook_post_id
                post.status = 'posted'
                post.posted_at = datetime.utcnow()
                
                db.session.commit()
                
                self._log_action('post', f"Successfully posted: {post.title}", post.id)
                logger.info(f"Successfully posted to Facebook: {post.title}")
                
                return {
                    'success': True, 
                    'facebook_post_id': facebook_post_id,
                    'message': 'Post published successfully'
                }
            else:
                error_msg = f"Facebook API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # Update post status
                post.status = 'failed'
                post.error_message = error_msg
                db.session.commit()
                
                self._log_action('error', error_msg, post.id)
                
                return {'success': False, 'error': error_msg}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            
            post.status = 'failed'
            post.error_message = error_msg
            db.session.commit()
            
            self._log_action('error', error_msg, post.id)
            
            return {'success': False, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            
            post.status = 'failed'
            post.error_message = error_msg
            db.session.commit()
            
            self._log_action('error', error_msg, post.id)
            
            return {'success': False, 'error': error_msg}
    
    def verify_facebook_credentials(self, page_id, access_token):
        """Verify Facebook page credentials"""
        try:
            # Test the credentials by making a simple API call
            endpoint = f"{self.base_url}/{page_id}"
            params = {
                'fields': 'name,id',
                'access_token': access_token
            }
            
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                page_data = response.json()
                return {
                    'success': True,
                    'page_name': page_data.get('name'),
                    'page_id': page_data.get('id')
                }
            else:
                return {
                    'success': False,
                    'error': f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    def get_posting_permissions(self, access_token):
        """Check what permissions the access token has"""
        try:
            endpoint = f"{self.base_url}/me/permissions"
            params = {'access_token': access_token}
            
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                permissions = response.json().get('data', [])
                granted_permissions = [p['permission'] for p in permissions if p['status'] == 'granted']
                return {
                    'success': True,
                    'permissions': granted_permissions
                }
            else:
                return {
                    'success': False,
                    'error': f"Could not fetch permissions: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error checking permissions: {str(e)}"
            }
    
    def delete_post(self, facebook_post_id, access_token):
        """Delete a Facebook post"""
        try:
            endpoint = f"{self.base_url}/{facebook_post_id}"
            params = {'access_token': access_token}
            
            response = requests.delete(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f"Could not delete post: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error deleting post: {str(e)}"
            }
    
    def get_page_insights(self, page_id, access_token):
        """Get basic insights for the Facebook page"""
        try:
            endpoint = f"{self.base_url}/{page_id}/insights"
            params = {
                'metric': 'page_fans,page_impressions',
                'access_token': access_token
            }
            
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                insights = response.json().get('data', [])
                metrics = {}
                
                for insight in insights:
                    name = insight.get('name')
                    values = insight.get('values', [])
                    if values:
                        metrics[name] = values[-1].get('value', 0)
                
                return {
                    'success': True,
                    'metrics': metrics
                }
            else:
                return {
                    'success': False,
                    'error': f"Could not fetch insights: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Error fetching insights: {str(e)}"
            }
    
    def _log_action(self, action, message, post_id=None):
        """Log an action to the database"""
        log = PostingLog(
            post_id=post_id,
            action=action,
            message=message
        )
        db.session.add(log)