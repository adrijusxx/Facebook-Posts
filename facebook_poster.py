"""
Facebook posting system using Facebook Graph API
"""

import requests
import logging
from datetime import datetime, timezone
from models import db, Post, Settings, PostingLog
import os

logger = logging.getLogger(__name__)

class FacebookPoster:
    """Handles posting to Facebook pages using Graph API"""
    
    def __init__(self, token_manager=None):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.token_manager = token_manager
        
    def post_to_facebook(self, post):
        """Post content to Facebook page"""
        settings = Settings.query.first()
        if not settings:
            logger.error("No settings found")
            return {'success': False, 'error': 'No settings configured'}
        
        if not settings.facebook_access_token or not settings.facebook_page_id:
            logger.error("Facebook credentials not configured")
            return {'success': False, 'error': 'Facebook credentials not configured'}
        
        # Check and renew token if needed (and token manager is available)
        if self.token_manager:
            try:
                renewal_result = self.token_manager.auto_renew_token_if_needed()
                if renewal_result['success'] and renewal_result.get('renewed', False):
                    logger.info("Token was renewed before posting")
                    # Refresh settings to get updated token
                    db.session.refresh(settings)
            except Exception as e:
                logger.warning(f"Token renewal check failed: {e}")
                # Continue with posting attempt using current token
        
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
                post.posted_at = datetime.now(timezone.utc)
                
                db.session.commit()
                
                self._log_action('post', f"Successfully posted: {post.title}", post.id)
                logger.info(f"Successfully posted to Facebook: {post.title}")
                
                return {
                    'success': True, 
                    'facebook_post_id': facebook_post_id,
                    'message': 'Post published successfully'
                }
            else:
                # Parse error response for better handling
                try:
                    error_data = response.json()
                    error_info = error_data.get('error', {})
                    error_code = error_info.get('code')
                    error_type = error_info.get('type')
                    error_message = error_info.get('message', 'Unknown error')
                    
                    # Check for token expiration errors
                    if error_code == 190 or 'expired' in error_message.lower():
                        error_msg = f"Facebook access token has expired. Please update your token in settings. Error: {error_message}"
                        logger.warning(error_msg)
                    else:
                        error_msg = f"Facebook API error ({error_code}): {error_message}"
                        logger.error(error_msg)
                        
                except:
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
                # Parse error response for better handling
                try:
                    error_data = response.json()
                    error_info = error_data.get('error', {})
                    error_code = error_info.get('code')
                    error_message = error_info.get('message', 'Unknown error')
                    
                    if error_code == 190 or 'expired' in error_message.lower():
                        return {
                            'success': False,
                            'error': f"Access token has expired: {error_message}"
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"API error ({error_code}): {error_message}"
                        }
                except:
                    return {
                        'success': False,
                        'error': f"API error: {response.status_code} - {response.text}"
                    }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    def check_token_validity(self, access_token):
        """Check if the access token is still valid"""
        try:
            endpoint = f"{self.base_url}/me"
            params = {
                'fields': 'id,name',
                'access_token': access_token
            }
            
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'success': True,
                    'valid': True,
                    'user_id': user_data.get('id'),
                    'user_name': user_data.get('name')
                }
            else:
                try:
                    error_data = response.json()
                    error_info = error_data.get('error', {})
                    error_code = error_info.get('code')
                    error_message = error_info.get('message', 'Unknown error')
                    
                    if error_code == 190:
                        return {
                            'success': True,
                            'valid': False,
                            'reason': 'Token expired',
                            'message': error_message
                        }
                    else:
                        return {
                            'success': True,
                            'valid': False,
                            'reason': f'API error ({error_code})',
                            'message': error_message
                        }
                except:
                    return {
                        'success': False,
                        'error': f"Could not parse error response: {response.text}"
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