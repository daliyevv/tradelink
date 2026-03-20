import uuid
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.core.validators import RegexValidator


class CustomUserManager(BaseUserManager):
    """
    Custom user manager for phone-based authentication.
    """

    def create_user(self, phone, full_name, role, password=None, **extra_fields):
        """
        Create and save a regular user.
        
        Args:
            phone: User's phone number (+998XXXXXXXXX format)
            full_name: User's full name
            role: User's role (manufacturer, dealer, or store)
            password: Optional password (may be None for OTP-only auth)
            **extra_fields: Additional fields
        
        Returns:
            User instance
        """
        if not phone:
            raise ValueError("Phone number is required")
        if not full_name:
            raise ValueError("Full name is required")
        if role not in ['manufacturer', 'dealer', 'store']:
            raise ValueError("Invalid role. Must be: manufacturer, dealer, or store")

        user = self.model(
            phone=phone,
            full_name=full_name,
            role=role,
            **extra_fields
        )
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name, password, **extra_fields):
        """
        Create and save a superuser.
        
        Args:
            phone: Admin's phone number
            full_name: Admin's full name
            password: Admin's password (required)
        
        Returns:
            User instance
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', 'manufacturer')

        if password is None:
            raise ValueError("Superuser must have a password")

        return self.create_user(
            phone=phone,
            full_name=full_name,
            role=extra_fields.get('role', 'manufacturer'),
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using phone number as primary identifier.
    Supports three roles: manufacturer, dealer, store owner.
    """

    ROLE_CHOICES = [
        ('manufacturer', 'Ishlab chiqaruvchi'),
        ('dealer', 'Diller'),
        ('store', 'Do\'kon egasi'),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication fields
    phone = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\+998\d{9}$',
                message='Phone must be in format +998XXXXXXXXX',
                code='invalid_phone'
            )
        ],
        help_text='Format: +998XXXXXXXXX (Uzbekistan)'
    )
    password = models.CharField(max_length=128)  # From AbstractBaseUser
    email = models.EmailField(
        blank=True,
        null=True,
        unique=True,
        help_text='Optional, but must be unique if provided'
    )

    # Profile fields
    full_name = models.CharField(max_length=150)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text='User role determines permissions'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text='User profile picture'
    )

    # Status fields
    is_verified = models.BooleanField(
        default=False,
        help_text='True if phone verified via OTP'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Set to False to soft-delete user'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Can access Django admin'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager
    objects = CustomUserManager()

    # Authentication configuration
    USERNAME_FIELD = 'phone'  # Use phone as unique identifier
    REQUIRED_FIELDS = ['full_name']  # Required for createsuperuser (role auto-assigned)

    class Meta:
        db_table = 'users_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone}) - {self.get_role_display()}"

    def get_short_name(self):
        """Return user's first name (for compatibility)."""
        return self.full_name.split()[0] if self.full_name else ''

    def get_full_name(self):
        """Return user's full name."""
        return self.full_name.strip() if self.full_name else ''

    @property
    def is_manufacturer(self):
        """Check if user is a manufacturer."""
        return self.role == 'manufacturer'

    @property
    def is_dealer(self):
        """Check if user is a dealer."""
        return self.role == 'dealer'

    @property
    def is_store_owner(self):
        """Check if user is a store owner."""
        return self.role == 'store'


class OTPCode(models.Model):
    """
    One-Time Password model for phone verification.
    
    Used for:
    - Initial registration
    - Password reset
    - Phone number change
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_codes',
        help_text='User this OTP belongs to'
    )
    code = models.CharField(
        max_length=6,
        help_text='6-digit OTP code'
    )
    expires_at = models.DateTimeField(
        help_text='When OTP expires'
    )
    is_used = models.BooleanField(
        default=False,
        help_text='True if OTP was successfully verified'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_otpcode'
        verbose_name = 'OTP Code'
        verbose_name_plural = 'OTP Codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_used']),
            models.Index(fields=['code']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"OTP for {self.user.phone} (expires: {self.expires_at})"

    def is_valid(self):
        """
        Check if OTP is valid (not used and not expired).
        
        Returns:
            bool: True if valid, False otherwise
        """
        now = timezone.now()
        return not self.is_used and self.expires_at > now

    def mark_as_used(self):
        """Mark this OTP as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])

    @classmethod
    def create_otp(cls, user, code, expiry_minutes=10):
        """
        Create a new OTP code for a user.
        
        Args:
            user: User instance
            code: 6-digit code
            expiry_minutes: Minutes until OTP expires (default: 10)
        
        Returns:
            OTPCode instance
        """
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )

    @classmethod
    def get_valid_otp(cls, user, code):
        """
        Retrieve and validate an OTP for a user.
        
        Args:
            user: User instance
            code: OTP code to verify
        
        Returns:
            OTPCode instance if valid, None otherwise
        """
        otp = cls.objects.filter(
            user=user,
            code=code,
            is_used=False
        ).first()

        if otp and otp.is_valid():
            return otp
        return None
