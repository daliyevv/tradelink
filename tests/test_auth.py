"""
Authentication tests including OTP flow, token verification, and logout.

Test coverage:
- OTP sending (valid/invalid phone, rate limiting)
- OTP verification (success, expired, wrong code)
- Token refresh and blacklist on logout
- Invalid credentials
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status

from apps.users.models import OTPCode

User = get_user_model()

pytestmark = pytest.mark.auth


class TestSendOTP:
    """Tests for sending OTP codes via SMS."""

    def test_send_otp_success(self, api_client):
        """Successfully send OTP for new user."""
        response = api_client.post('/api/v1/auth/send-otp/', {
            'phone': '+998901234567'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'is_new_user' in response.data['data']
        assert response.data['data']['is_new_user'] is True
        
        # User should be created with default role 'store'
        user = User.objects.get(phone='+998901234567')
        assert user.role == 'store'
        
        # OTP should be created
        otp = OTPCode.objects.filter(user=user).first()
        assert otp is not None
        assert len(otp.code) == 6

    def test_send_otp_existing_user(self, api_client, store_user):
        """Send OTP for existing user returns is_new_user=False."""
        response = api_client.post('/api/v1/auth/send-otp/', {
            'phone': store_user.phone
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['is_new_user'] is False

    def test_send_otp_invalid_phone_format(self, api_client):
        """Reject invalid phone number format."""
        invalid_phones = [
            '98901234567',  # Missing +
            '+9989012345',  # Too short
            '+99890123456789',  # Too long
            '+998901234a67',  # Contains letter
            '+9989 01 234567',  # Contains space
            'invalid',  # Not a phone
        ]

        for phone in invalid_phones:
            response = api_client.post('/api/v1/auth/send-otp/', {
                'phone': phone
            })
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['success'] is False

    def test_send_otp_missing_phone(self, api_client):
        """Reject request without phone."""
        response = api_client.post('/api/v1/auth/send-otp/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone' in response.data['errors']

    def test_send_otp_rate_limiting(self, api_client):
        """Enforce 5 OTP requests per hour limit."""
        phone = '+998901234567'
        
        # Send 5 OTP requests (should succeed)
        for i in range(5):
            response = api_client.post('/api/v1/auth/send-otp/', {'phone': phone})
            assert response.status_code == status.HTTP_200_OK, f"Request {i+1} failed"

        # 6th request should be throttled
        response = api_client.post('/api/v1/auth/send-otp/', {'phone': phone})
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestVerifyOTP:
    """Tests for OTP verification and token generation."""

    def test_verify_otp_success_new_user(self, db, api_client):
        """Successfully verify OTP and create account for new user."""
        # Send OTP
        api_client.post('/api/v1/auth/send-otp/', {'phone': '+998901234567'})
        
        # Get the OTP code (in dev mode, returned in response)
        user = User.objects.get(phone='+998901234567')
        otp_code = OTPCode.objects.get(user=user).code
        
        # Verify OTP with new user details
        response = api_client.post('/api/v1/auth/verify-otp/', {
            'phone': '+998901234567',
            'otp': otp_code,
            'full_name': 'Qora Diller',
            'role': 'dealer',
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'access' in response.data['data']
        assert 'refresh' in response.data['data']
        
        # User should be updated
        user.refresh_from_db()
        assert user.full_name == 'Qora Diller'
        assert user.role == 'dealer'
        assert user.is_verified is True

    def test_verify_otp_success_existing_user(self, db, api_client, store_user):
        """Successfully verify OTP and return tokens for existing user."""
        # Send OTP
        api_client.post('/api/v1/auth/send-otp/', {'phone': store_user.phone})
        
        # Get OTP code
        otp_code = OTPCode.objects.filter(user=store_user).first().code
        
        # Verify OTP
        response = api_client.post('/api/v1/auth/verify-otp/', {
            'phone': store_user.phone,
            'otp': otp_code,
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'access' in response.data['data']
        assert 'refresh' in response.data['data']
        
        user_data = response.data['data']['user']
        assert user_data['phone'] == store_user.phone
        assert user_data['role'] == 'store'

    def test_verify_otp_invalid_code(self, db, api_client, store_user):
        """Reject verification with wrong OTP code."""
        api_client.post('/api/v1/auth/send-otp/', {'phone': store_user.phone})
        
        response = api_client.post('/api/v1/auth/verify-otp/', {
            'phone': store_user.phone,
            'otp': '000000',  # Wrong code
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert 'otp' in response.data['errors']

    def test_verify_otp_expired(self, db, api_client, store_user, expired_otp):
        """Reject verification with expired OTP."""
        response = api_client.post('/api/v1/auth/verify-otp/', {
            'phone': store_user.phone,
            'otp': expired_otp.code,
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False

    def test_verify_otp_already_used(self, db, api_client, store_user, used_otp):
        """Reject verification with already used OTP."""
        response = api_client.post('/api/v1/auth/verify-otp/', {
            'phone': store_user.phone,
            'otp': used_otp.code,
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False

    def test_verify_otp_missing_fields(self, api_client):
        """Reject incomplete OTP verification."""
        response = api_client.post('/api/v1/auth/verify-otp/', {
            'phone': '+998901234567',
            # Missing otp field
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'otp' in response.data['errors']


class TestLogout:
    """Tests for token blacklisting and logout."""

    def test_logout_blacklists_token(self, authenticated_client, manufacturer_user):
        """Logout successfully blacklists the refresh token."""
        refresh_token = manufacturer_user.refresh_token
        
        # Logout should blacklist the token
        response = authenticated_client.post('/api/v1/auth/logout/', {
            'refresh': refresh_token
        })

        assert response.status_code == status.HTTP_200_OK

    def test_cannot_use_blacklisted_token(self, authenticated_client, manufacturer_user):
        """Cannot refresh with a blacklisted token."""
        refresh_token = manufacturer_user.refresh_token
        
        # Logout
        authenticated_client.post('/api/v1/auth/logout/', {
            'refresh': refresh_token
        })

        # Try to refresh - should fail
        api_client = authenticated_client._client.__class__()
        response = api_client.post('/api/v1/auth/token/refresh/', {
            'refresh': refresh_token
        })

        # Should get 401 or similar error
        assert response.status_code != status.HTTP_200_OK

    def test_logout_missing_token(self, authenticated_client):
        """Logout without refresh token should fail."""
        response = authenticated_client.post('/api/v1/auth/logout/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestTokenRefresh:
    """Tests for JWT token refresh."""

    def test_refresh_token_success(self, api_client, manufacturer_user):
        """Successfully refresh access token with refresh token."""
        response = api_client.post('/api/v1/auth/token/refresh/', {
            'refresh': manufacturer_user.refresh_token
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert response.data['access'] != manufacturer_user.access_token

    def test_refresh_token_invalid(self, api_client):
        """Reject refresh with invalid token."""
        response = api_client.post('/api/v1/auth/token/refresh/', {
            'refresh': 'invalid.token.here'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_missing(self, api_client):
        """Reject refresh without token."""
        response = api_client.post('/api/v1/auth/token/refresh/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAuthenticatedEndpoints:
    """Tests for endpoints requiring authentication."""

    def test_profile_requires_authentication(self, api_client):
        """Profile endpoint requires valid token."""
        response = api_client.get('/api/v1/users/profile/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_profile_with_valid_token(self, authenticated_client, manufacturer_user):
        """Profile endpoint succeeds with valid token."""
        response = authenticated_client.get('/api/v1/users/profile/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['phone'] == manufacturer_user.phone
