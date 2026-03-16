"""
Custom throttling/rate limiting for TradeLink API.

Implements:
- OTP Send: 5 requests per phone per hour
- Login: 10 attempts per IP per 5 minutes
- General API: 100 requests per user per minute
"""

from rest_framework.throttling import SimpleRateThrottle
from django.core.cache import cache
import hashlib


class OTPSendThrottle(SimpleRateThrottle):
    """
    Rate limit OTP send requests: 5 per phone per hour.
    
    Tests:
    - First 5 requests: 200 OK
    - 6th request: 429 Too Many Requests
    """
    scope = 'otp_send'  # Can be configured in settings
    THROTTLE_RATES = {'otp_send': '5/hour'}

    def get_cache_key(self):
        """Use phone number as rate limit key."""
        phone = self.request.data.get('phone') or self.request.query_params.get('phone')
        
        if not phone:
            return None  # Let request through if no phone provided (will fail validation)
        
        # Hash phone to keep cache key short
        return f'throttle_{self.scope}__{hashlib.md5(phone.encode()).hexdigest()}'


class LoginThrottle(SimpleRateThrottle):
    """
    Rate limit login attempts: 10 per IP per 5 minutes.
    
    Tests:
    - First 10 requests: 200 OK
    - 11th request: 429 Too Many Requests
    """
    scope = 'login'
    THROTTLE_RATES = {'login': '10/5m'}

    def get_cache_key(self):
        """Use client IP as rate limit key."""
        if self.request.user and self.request.user.is_authenticated:
            return None  # Don't throttle authenticated users trying to login again

        return f'throttle_{self.scope}__{self.get_ident(self.request)}'


class APIUserThrottle(SimpleRateThrottle):
    """
    Rate limit general API: 100 requests per user per minute.
    
    Tests:
    - First 100 requests in 1 minute: 200 OK
    - 101st request: 429 Too Many Requests
    """
    scope = 'api_user'
    THROTTLE_RATES = {'api_user': '100/m'}

    def get_cache_key(self):
        """Rate limit per authenticated user or IP."""
        if self.request.user and self.request.user.is_authenticated:
            identifier = f'user_{self.request.user.id}'
        else:
            identifier = self.get_ident(self.request)  # Use IP for unauthenticated

        return f'throttle_{self.scope}__{identifier}'


class APIAnonThrottle(SimpleRateThrottle):
    """
    Rate limit anonymous API: 30 requests per IP per minute.
    
    Tests:
    - First 30 requests in 1 minute: 200 OK
    - 31st request: 429 Too Many Requests
    """
    scope = 'api_anon'
    THROTTLE_RATES = {'api_anon': '30/m'}

    def get_cache_key(self):
        """Rate limit per IP for anonymous users."""
        if self.request.user and self.request.user.is_authenticated:
            return None  # Only throttle anonymous users

        return f'throttle_{self.scope}__{self.get_ident(self.request)}'


class StrictAPIThrottle(SimpleRateThrottle):
    """
    Strict rate limiting: 50 requests per IP per minute globally.
    Used on sensitive endpoints (registration, password reset, etc).
    
    Tests:
    - First 50 requests in 1 minute: 200 OK
    - 51st request: 429 Too Many Requests
    """
    scope = 'strict_api'
    THROTTLE_RATES = {'strict_api': '50/m'}

    def get_cache_key(self):
        """Rate limit per IP."""
        return f'throttle_{self.scope}__{self.get_ident(self.request)}'
