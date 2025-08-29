"""
Facebook Token Management System
Handles automatic token renewal for long-lived Facebook access tokens
"""

import requests
import logging
from datetime import datetime, timezone, timedelta
from models import db, Settings
import os

logger = logging.getLogger(__name__)

class FacebookTokenManager:
    """Manages Facebook access token renewal and validation"""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.token_renewal_days = 50  # Renew every 50 days as requested
    
    def get_long_lived_token(self, app_id, app_secret, short_lived_token):
        """
        Exchange a short-lived token for a long-lived token
        Long-lived tokens are valid for 60 days
        """
        try:
            endpoint = f"{self.base_url}/oauth/access_token"
            params = {
                'grant_type': 'fb_exchange_token',
                'client_id': app_id,
                'client_secret': app_secret,
                'fb_exchange_token': short_lived_token
            }
            
            response = requests.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')
                expires_in = data.get('expires_in')  # Seconds until expiration
                
                if access_token:
                    # Calculate expiration date
                    expiry_date = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None
                    
                    logger.info(f"Successfully obtained long-lived token, expires in {expires_in} seconds")
                    return {
                        'success': True,
                        'access_token': access_token,
                        'expires_in': expires_in,
                        'expiry_date': expiry_date,
                        'message': 'Long-lived token obtained successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No access token in response'
                    }
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    return {
                        'success': False,
                        'error': f"Token exchange failed: {error_message}"
                    }
                except:
                    return {
                        'success': False,
                        'error': f"Token exchange failed: {response.status_code} - {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting long-lived token: {str(e)}")
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    def renew_page_access_token(self, app_id, app_secret, user_access_token, page_id):
        """
        Get a fresh page access token using the app credentials and user token
        This method can be used to renew page tokens
        """
        try:
            # First, get a long-lived user access token if needed
            long_lived_result = self.get_long_lived_token(app_id, app_secret, user_access_token)
            if not long_lived_result['success']:
                return long_lived_result
            
            long_lived_token = long_lived_result['access_token']
            
            # Get page access token using the long-lived user token
            endpoint = f"{self.base_url}/me/accounts"
            params = {
                'access_token': long_lived_token
            }
            
            response = requests.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get('data', [])
                
                # Find the specific page
                for page in pages:
                    if page.get('id') == page_id:
                        page_token = page.get('access_token')
                        if page_token:
                            logger.info(f"Successfully renewed page access token for page {page_id}")
                            return {
                                'success': True,
                                'access_token': page_token,
                                'page_name': page.get('name'),
                                'page_id': page.get('id'),
                                'renewed_at': datetime.now(timezone.utc),
                                'message': 'Page access token renewed successfully'
                            }
                
                return {
                    'success': False,
                    'error': f'Page {page_id} not found in accessible pages'
                }
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    return {
                        'success': False,
                        'error': f"Failed to get page token: {error_message}"
                    }
                except:
                    return {
                        'success': False,
                        'error': f"Failed to get page token: {response.status_code} - {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error renewing page access token: {str(e)}")
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    def validate_token_and_get_info(self, access_token):
        """
        Validate a token and get detailed information about it
        """
        try:
            # Get token info including expiration
            endpoint = f"{self.base_url}/debug_token"
            params = {
                'input_token': access_token,
                'access_token': access_token  # Can use the same token for debugging itself
            }
            
            response = requests.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                is_valid = data.get('is_valid', False)
                expires_at = data.get('expires_at')
                app_id = data.get('app_id')
                user_id = data.get('user_id')
                scopes = data.get('scopes', [])
                
                # Convert expires_at to datetime if available
                expiry_date = None
                if expires_at and expires_at != 0:
                    expiry_date = datetime.fromtimestamp(expires_at, tz=timezone.utc)
                
                return {
                    'success': True,
                    'is_valid': is_valid,
                    'expires_at': expires_at,
                    'expiry_date': expiry_date,
                    'app_id': app_id,
                    'user_id': user_id,
                    'scopes': scopes,
                    'days_until_expiry': self._calculate_days_until_expiry(expiry_date) if expiry_date else None
                }
            else:
                return {
                    'success': False,
                    'error': f"Token validation failed: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
    
    def check_if_renewal_needed(self, settings=None):
        """
        Check if token renewal is needed based on expiry date
        """
        if not settings:
            settings = Settings.query.first()
        
        if not settings or not hasattr(settings, 'facebook_token_expires_at'):
            return {
                'renewal_needed': True,
                'reason': 'No expiry date tracked'
            }
        
        if not settings.facebook_token_expires_at:
            return {
                'renewal_needed': True,
                'reason': 'No expiry date set'
            }
        
        days_until_expiry = (settings.facebook_token_expires_at - datetime.now(timezone.utc)).days
        
        if days_until_expiry <= self.token_renewal_days:
            return {
                'renewal_needed': True,
                'reason': f'Token expires in {days_until_expiry} days (threshold: {self.token_renewal_days} days)',
                'days_until_expiry': days_until_expiry
            }
        
        return {
            'renewal_needed': False,
            'reason': f'Token valid for {days_until_expiry} more days',
            'days_until_expiry': days_until_expiry
        }
    
    def auto_renew_token_if_needed(self):
        """
        Automatically renew token if it's close to expiry
        This function should be called by the scheduler
        """
        try:
            settings = Settings.query.first()
            if not settings:
                logger.warning("No settings found for token renewal")
                return {
                    'success': False,
                    'error': 'No settings configured'
                }
            
            # Check if renewal is needed
            renewal_check = self.check_if_renewal_needed(settings)
            
            if not renewal_check['renewal_needed']:
                logger.info(f"Token renewal not needed: {renewal_check['reason']}")
                return {
                    'success': True,
                    'message': f"No renewal needed: {renewal_check['reason']}",
                    'renewed': False
                }
            
            # Check if we have the necessary credentials for renewal
            if not hasattr(settings, 'facebook_app_id') or not hasattr(settings, 'facebook_app_secret'):
                logger.error("App ID and App Secret required for automatic token renewal")
                return {
                    'success': False,
                    'error': 'App ID and App Secret not configured for automatic renewal'
                }
            
            app_id = getattr(settings, 'facebook_app_id', None)
            app_secret = getattr(settings, 'facebook_app_secret', None)
            current_token = settings.facebook_access_token
            page_id = settings.facebook_page_id
            
            if not all([app_id, app_secret, current_token, page_id]):
                return {
                    'success': False,
                    'error': 'Missing required credentials for token renewal'
                }
            
            # Attempt to renew the token
            logger.info(f"Attempting automatic token renewal: {renewal_check['reason']}")
            renewal_result = self.renew_page_access_token(app_id, app_secret, current_token, page_id)
            
            if renewal_result['success']:
                # Update settings with new token
                settings.facebook_access_token = renewal_result['access_token']
                
                # Try to get expiry info for the new token
                token_info = self.validate_token_and_get_info(renewal_result['access_token'])
                if token_info['success'] and token_info.get('expiry_date'):
                    if hasattr(settings, 'facebook_token_expires_at'):
                        settings.facebook_token_expires_at = token_info['expiry_date']
                
                if hasattr(settings, 'facebook_token_last_renewed'):
                    settings.facebook_token_last_renewed = datetime.now(timezone.utc)
                
                db.session.commit()
                
                logger.info("Successfully renewed Facebook access token automatically")
                return {
                    'success': True,
                    'message': 'Token renewed automatically',
                    'renewed': True,
                    'new_token_info': token_info if token_info['success'] else None
                }
            else:
                logger.error(f"Failed to renew token automatically: {renewal_result['error']}")
                return {
                    'success': False,
                    'error': f"Automatic renewal failed: {renewal_result['error']}"
                }
                
        except Exception as e:
            logger.error(f"Error during automatic token renewal: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def manual_token_setup(self, page_id, access_token, app_id, app_secret):
        """
        Manually set up a new token with all required information
        This is useful for initial setup or manual renewal
        """
        try:
            # Validate the provided token
            token_info = self.validate_token_and_get_info(access_token)
            if not token_info['success']:
                return {
                    'success': False,
                    'error': f"Token validation failed: {token_info['error']}"
                }
            
            if not token_info['is_valid']:
                return {
                    'success': False,
                    'error': 'Provided token is not valid'
                }
            
            # Update or create settings
            settings = Settings.query.first()
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            # Update token information
            settings.facebook_page_id = page_id
            settings.facebook_access_token = access_token
            
            # Add new fields if they don't exist (will need database migration)
            if not hasattr(settings, 'facebook_app_id'):
                # This will be handled by the database migration
                pass
            else:
                settings.facebook_app_id = app_id
                settings.facebook_app_secret = app_secret
                settings.facebook_token_expires_at = token_info.get('expiry_date')
                settings.facebook_token_last_renewed = datetime.now(timezone.utc)
            
            db.session.commit()
            
            logger.info("Successfully set up Facebook token manually")
            return {
                'success': True,
                'message': 'Token configured successfully',
                'token_info': token_info
            }
            
        except Exception as e:
            logger.error(f"Error setting up token manually: {str(e)}")
            return {
                'success': False,
                'error': f"Setup error: {str(e)}"
            }
    
    def get_token_status(self):
        """
        Get current token status and renewal information
        """
        try:
            settings = Settings.query.first()
            if not settings or not settings.facebook_access_token:
                return {
                    'success': False,
                    'error': 'No Facebook token configured'
                }
            
            # Validate current token
            token_info = self.validate_token_and_get_info(settings.facebook_access_token)
            
            # Check renewal status
            renewal_check = self.check_if_renewal_needed(settings)
            
            return {
                'success': True,
                'token_valid': token_info.get('is_valid', False) if token_info['success'] else False,
                'token_info': token_info if token_info['success'] else None,
                'renewal_check': renewal_check,
                'page_id': settings.facebook_page_id,
                'last_renewed': getattr(settings, 'facebook_token_last_renewed', None),
                'expires_at': getattr(settings, 'facebook_token_expires_at', None)
            }
            
        except Exception as e:
            logger.error(f"Error getting token status: {str(e)}")
            return {
                'success': False,
                'error': f"Status check error: {str(e)}"
            }
    
    def _calculate_days_until_expiry(self, expiry_date):
        """Calculate days until token expiry"""
        if not expiry_date:
            return None
        
        delta = expiry_date - datetime.now(timezone.utc)
        return delta.days