"""
Authentication module for Upstox and Angel One APIs.
"""
import os
import time
from typing import Optional, Dict
from utils.logger import get_logger
from config.config import (
    API_PROVIDER, UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI,
    UPSTOX_ACCESS_TOKEN, ANGEL_ONE_API_KEY, ANGEL_ONE_CLIENT_ID,
    ANGEL_ONE_PIN, ANGEL_ONE_TOTP_SECRET
)

logger = get_logger(__name__)

class UpstoxAuth:
    """Handle Upstox API authentication."""
    
    def __init__(self):
        self.api_key = UPSTOX_API_KEY
        self.api_secret = UPSTOX_API_SECRET
        self.redirect_uri = UPSTOX_REDIRECT_URI
        self.access_token = UPSTOX_ACCESS_TOKEN
        self.session = None
        
    def authenticate(self) -> Optional[str]:
        """
        Authenticate with Upstox API.
        Returns access token if successful.
        """
        try:
            from upstox_client.api.login_api import LoginApi
            from upstox_client.rest import ApiException
            from upstox_client import ApiClient, Configuration
            
            if self.access_token:
                logger.info("Using existing access token")
                return self.access_token
            
            # For first-time authentication, user needs to authorize via browser
            logger.warning("Access token not found. Please authorize via browser:")
            logger.warning(f"Visit: https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={self.api_key}&redirect_uri={self.redirect_uri}")
            
            # After authorization, exchange code for token
            # This should be done via a callback server or manually
            return None
            
        except ImportError:
            logger.error("upstox-python-sdk not installed. Install with: pip install upstox-python-sdk")
            return None
        except Exception as e:
            logger.error(f"Upstox authentication failed: {e}")
            return None
    
    def get_session(self):
        """Get authenticated session."""
        if not self.session:
            token = self.authenticate()
            if token:
                from upstox_client import ApiClient, Configuration
                configuration = Configuration()
                configuration.access_token = token
                self.session = ApiClient(configuration)
        return self.session


class AngelOneAuth:
    """Handle Angel One SmartAPI authentication."""
    
    def __init__(self):
        self.api_key = ANGEL_ONE_API_KEY
        self.client_id = ANGEL_ONE_CLIENT_ID
        self.pin = ANGEL_ONE_PIN
        self.totp_secret = ANGEL_ONE_TOTP_SECRET
        self.session = None
        self.jwt_token = None
        self.feed_token = None
        
    def generate_totp(self) -> str:
        """Generate TOTP for 2FA."""
        try:
            import pyotp
            totp = pyotp.TOTP(self.totp_secret)
            return totp.now()
        except ImportError:
            logger.error("pyotp not installed. Install with: pip install pyotp")
            return ""
        except Exception as e:
            logger.error(f"TOTP generation failed: {e}")
            return ""
    
    def authenticate(self) -> Optional[Dict]:
        """
        Authenticate with Angel One SmartAPI.
        Returns session dict with jwt_token and feed_token.
        """
        try:
            from smartapi import SmartConnect
            
            smart_api = SmartConnect(self.api_key)
            
            # Generate TOTP
            totp = self.generate_totp()
            if not totp:
                return None
            
            # Login
            data = smart_api.generateSession(self.client_id, self.pin, totp)
            
            if data['status']:
                self.jwt_token = data['data']['jwtToken']
                self.feed_token = data['data']['feedToken']
                self.session = smart_api
                logger.info("Angel One authentication successful")
                return {
                    'jwt_token': self.jwt_token,
                    'feed_token': self.feed_token,
                    'session': self.session
                }
            else:
                logger.error(f"Angel One authentication failed: {data.get('message', 'Unknown error')}")
                return None
                
        except ImportError:
            logger.error("smartapi-python not installed. Install with: pip install smartapi-python")
            return None
        except Exception as e:
            logger.error(f"Angel One authentication failed: {e}")
            return None
    
    def get_session(self):
        """Get authenticated session."""
        if not self.session:
            result = self.authenticate()
            if result:
                return result['session']
        return self.session


def get_auth_handler():
    """Get appropriate authentication handler based on config."""
    if API_PROVIDER.lower() == "upstox":
        return UpstoxAuth()
    elif API_PROVIDER.lower() == "angel_one":
        return AngelOneAuth()
    else:
        logger.error(f"Unknown API provider: {API_PROVIDER}")
        return None
