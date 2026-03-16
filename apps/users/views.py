import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from .models import OTPCode
from .serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    UserSerializer,
    TokenResponseSerializer,
    ProfileUpdateSerializer,
)
from utils.sms import send_sms
from utils.responses import success_response, error_response

User = get_user_model()


class OTPRateThrottle(UserRateThrottle):
    """
    Rate limiting for OTP requests.
    Max 5 OTP requests per phone per hour.
    """
    scope = 'otp'
    rate = '5/hour'


class SendOTPView(APIView):
    """
    Request OTP code for phone verification.
    Creates user account if doesn't exist, generates OTP.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        summary='Send OTP via SMS',
        tags=['auth'],
        request=SendOTPSerializer,
        responses={
            200: OpenApiResponse(description='OTP sent successfully'),
            400: OpenApiResponse(description='Invalid phone number'),
            429: OpenApiResponse(description='Rate limit exceeded (5/hour)'),
        },
        examples=[
            OpenApiExample(
                'OTP sent',
                value={
                    'success': True,
                    'message': 'SMS yuborildi',
                    'data': {'is_new_user': True, 'otp': '123456'},
                },
                status_codes=['200'],
            ),
        ],
    )
    def post(self, request):
        """Handle OTP request."""
        serializer = SendOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Validatsiya xatosi',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        phone = serializer.validated_data['phone']

        # Create or get user
        user, is_new_user = User.objects.get_or_create(
            phone=phone,
            defaults={
                'full_name': '',  # Will be set during verification
                'role': 'store',  # Default role
            }
        )

        # Generate 6-digit OTP
        otp_code = str(secrets.randbelow(1000000)).zfill(6)

        # Create OTP record (5-minute expiry)
        OTPCode.create_otp(
            user=user,
            code=otp_code,
            expiry_minutes=5
        )

        # Send OTP via SMS
        message_uz = f"TradeLink tasdiqlash kodi: {otp_code}"
        send_sms(phone=phone, message=message_uz)

        response_data = {
            'is_new_user': is_new_user,
        }

        # In development, return OTP for testing
        if settings.DEBUG:
            response_data['otp'] = otp_code

        return success_response(
            data=response_data,
            message='SMS yuborildi',
            status_code=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    """
    Verify OTP code and obtain JWT tokens.
    For new users, completes registration (sets role, full_name).
    For existing users, logs them in.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Verify OTP and get JWT tokens',
        tags=['auth'],
        request=VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(description='OTP verified, tokens returned'),
            400: OpenApiResponse(description='Invalid or expired OTP'),
        },
        examples=[
            OpenApiExample(
                'Login successful',
                value={
                    'success': True,
                    'data': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'user': {
                            'id': '550e8400-e29b-41d4-a716-...',
                            'phone': '+998901234567',
                            'full_name': 'Abdulloh Shodmonov',
                            'role': 'dealer',
                            'is_verified': True,
                        },
                    },
                    'message': 'Muvaffaqiyatli kirdi',
                },
                status_codes=['200'],
            ),
        ],
    )
    def post(self, request):
        """Handle OTP verification and token generation."""
        serializer = VerifyOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='OTP tasdiqlash muvaffaq bo\'lmadi',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        phone = serializer.validated_data['phone']
        is_new_user = serializer.validated_data['is_new_user']
        otp_code = serializer.validated_data['otp']

        # Get OTP and mark as used
        otp = OTPCode.objects.filter(
            user__phone=phone,
            code=otp_code
        ).first()
        otp.mark_as_used()

        # Get user
        user = User.objects.get(phone=phone)

        # Update user if new (complete registration)
        if is_new_user:
            user.full_name = serializer.validated_data.get('full_name', '')
            user.role = serializer.validated_data.get('role', 'store')
            user.is_verified = True
            user.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response_data = {
            'access': access_token,
            'refresh': refresh_token,
            'user': UserSerializer(user).data,
        }

        return success_response(
            data=response_data,
            message='Muvaffaqiyatli kirdi' if not is_new_user else 'Muvaffaqiyatli ro\'yxatdan o\'tdingiz',
            status_code=status.HTTP_200_OK
        )


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh access token using refresh token.
    Inherits from SimpleJWT TokenRefreshView but wraps response.
    """

    @extend_schema(
        summary='Refresh JWT access token',
        tags=['auth'],
        responses={
            200: OpenApiResponse(description='Token refreshed'),
            401: OpenApiResponse(description='Invalid refresh token'),
        },
    )
    def post(self, request, *args, **kwargs):
        """Handle token refresh."""
        try:
            response = super().post(request, *args, **kwargs)

            # If successful, wrap in standard format
            if response.status_code == 200:
                return success_response(
                    data=response.data,
                    message='Token yangilandi',
                    status_code=status.HTTP_200_OK
                )
            return response

        except TokenError as e:
            return error_response(
                errors={'refresh': ['Noto\'g\'ri yoki tugagan refresh token']},
                message='Token yangilash muvaffaq bo\'lmadi',
                status_code=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """
    Logout user and blacklist refresh token.
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Logout and blacklist token',
        tags=['auth'],
        responses={
            200: OpenApiResponse(description='Logged out successfully'),
            400: OpenApiResponse(description='Missing refresh token'),
        },
    )
    def post(self, request):
        """Handle logout and token blacklist."""
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return error_response(
                errors={'refresh': ['Refresh token talab qilinadi']},
                message='Refresh token talab qilinadi',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return success_response(
                message='Chiqildi',
                status_code=status.HTTP_200_OK
            )

        except TokenError as e:
            return error_response(
                errors={'refresh': ['Noto\'g\'ri token']},
                message='Logout muvaffaq bo\'lmadi',
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    """
    GET /api/v1/profile/me/
    
    Retrieve authenticated user's profile.
    Requires authentication.
    
    Response:
        {
            "success": true,
            "data": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "phone": "+998911234567",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "manufacturer",
                "role_display": "Ishlab chiqaruvchi",
                "avatar": "https://...",
                "is_verified": true,
                "created_at": "2025-01-15T10:30:00Z"
            },
            "message": "Profil olingan"
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve user profile."""
        serializer = UserSerializer(request.user)
        
        return success_response(
            data=serializer.data,
            message='Profil olingan',
            status_code=status.HTTP_200_OK
        )


class UpdateProfileView(APIView):
    """
    PATCH /api/v1/profile/me/
    
    Update authenticated user's profile.
    Allows updating: full_name, email, avatar.
    Does NOT allow: phone (unique identifier), role (access control).
    Requires authentication.
    
    Request:
        {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "avatar": <file>  (multipart/form-data)
        }
    
    Response:
        {
            "success": true,
            "data": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "phone": "+998911234567",
                "email": "jane@example.com",
                "full_name": "Jane Doe",
                "role": "manufacturer",
                "role_display": "Ishlab chiqaruvchi",
                "avatar": "https://...",
                "is_verified": true,
                "created_at": "2025-01-15T10:30:00Z"
            },
            "message": "Profil yangilandi"
        }
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """Update user profile."""
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            return error_response(
                errors=serializer.errors,
                message='Profil yangilashda xato',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        updated_user = serializer.save()
        response_serializer = UserSerializer(updated_user)

        return success_response(
            data=response_serializer.data,
            message='Profil yangilandi',
            status_code=status.HTTP_200_OK
        )
