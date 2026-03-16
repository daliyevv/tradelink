import re
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPCode

User = get_user_model()


class SendOTPSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP.
    Validates phone number format and existence.
    """

    phone = serializers.CharField(
        max_length=13,
        min_length=13,
        help_text='Format: +998XXXXXXXXX'
    )

    def validate_phone(self, value):
        """Validate phone number format."""
        pattern = r'^\+998\d{9}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                'Noto\'g\'ri telefon raqam. Format: +998XXXXXXXXX'
            )
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for verifying OTP and obtaining tokens.
    Used for both login and registration.
    """

    phone = serializers.CharField(
        max_length=13,
        min_length=13,
        help_text='Format: +998XXXXXXXXX'
    )
    otp = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text='6-digit OTP code'
    )
    full_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text='Required for new users'
    )
    role = serializers.ChoiceField(
        choices=['manufacturer', 'dealer', 'store'],
        required=False,
        help_text='Required for new users'
    )

    def validate_phone(self, value):
        """Validate phone format."""
        pattern = r'^\+998\d{9}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                'Noto\'g\'ri telefon raqam. Format: +998XXXXXXXXX'
            )
        return value

    def validate_otp(self, value):
        """Validate OTP format (6 digits)."""
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError(
                'OTP 6 raqamdan iborat bo\'lishi kerak'
            )
        return value

    def validate(self, data):
        """
        Validate OTP code existence and validity.
        Also validate that new users provide role and full_name.
        """
        phone = data.get('phone')
        otp_code = data.get('otp')

        # Find OTP code
        otp = OTPCode.objects.filter(
            user__phone=phone,
            code=otp_code
        ).first()

        if not otp:
            raise serializers.ValidationError({
                'otp': 'OTP noto\'g\'ri yoki topilmadi'
            })

        if not otp.is_valid():
            raise serializers.ValidationError({
                'otp': 'OTP amal qilish muddati tugagan'
            })

        # Check if user is new
        try:
            user = User.objects.get(phone=phone)
            data['is_new_user'] = False
        except User.DoesNotExist:
            # For new users, require role and full_name
            data['is_new_user'] = True
            if not data.get('role'):
                raise serializers.ValidationError({
                    'role': 'Yangi foydalanuvchilar uchun role talab qilinadi'
                })
            if not data.get('full_name'):
                raise serializers.ValidationError({
                    'full_name': 'Yangi foydalanuvchilar uchun ism-familya talab qilinadi'
                })

        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Basic user information serializer.
    Used in token response and profile endpoints.
    """

    role_display = serializers.CharField(
        source='get_role_display',
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'email',
            'full_name',
            'role',
            'role_display',
            'avatar',
            'is_verified',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_verified']


class TokenResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token response.
    Contains access token, refresh token, and user info.
    """

    access = serializers.CharField(
        help_text='JWT access token (15 minutes)'
    )
    refresh = serializers.CharField(
        help_text='JWT refresh token (30 days)'
    )
    user = UserSerializer(
        help_text='Authenticated user information'
    )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Only allows updating: full_name, email, avatar.
    Prevents modification of phone (unique identifier) and role (access control).
    """

    class Meta:
        model = User
        fields = ['full_name', 'email', 'avatar']
        extra_kwargs = {
            'full_name': {
                'required': False,
                'allow_blank': False,
            },
            'email': {
                'required': False,
                'allow_blank': False,
            },
            'avatar': {
                'required': False,
                'allow_null': True,
            },
        }

    def validate_email(self, value):
        """
        Ensure email uniqueness, excluding the current user.
        """
        if not value:
            return value
        
        user = self.instance
        if User.objects.exclude(id=user.id).filter(email=value).exists():
            raise serializers.ValidationError(
                'Bu email manzili allaqachon ro\'yxatdan o\'tgan.'
            )
        return value

    def validate_full_name(self, value):
        """
        Validate full name is not empty.
        """
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError(
                'To\'liq ism kamida 2 ta belgi bo\'lishi kerak.'
            )
        return value
