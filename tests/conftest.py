"""
Pytest configuration and shared fixtures for the entire test suite.

Fixtures organize by:
- Users: manufacturer_user, dealer_user, store_user with JWT tokens
- Categories/Products: sample_category, sample_product, product_with_images
- Cart: sample_cart, cart_with_items
- Orders: sample_order, pending_order
- Dealers: dealer_profile_with_location
"""

import json
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.cart.models import Cart, CartItem
from apps.dealers.models import DealerProfile
from apps.locations.models import Location
from apps.notifications.models import Notification
from apps.orders.models import Order, OrderItem
from apps.products.models import Category, Product, ProductImage
from apps.users.models import OTPCode

User = get_user_model()


# ============================================================================
# USER FIXTURES
# ============================================================================


@pytest.fixture
def api_client():
    """DRF API client for making HTTP requests in tests."""
    return APIClient()


def get_jwt_tokens(user):
    """Generate JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@pytest.fixture
def manufacturer_user(db):
    """Create a manufacturer user with JWT tokens."""
    user = User.objects.create_user(
        phone='+998901234567',
        full_name='Abdulloh Manufakturer',
        role='manufacturer',
        password='Test@1234567',
    )
    user.is_verified = True
    user.save()
    
    tokens = get_jwt_tokens(user)
    user.access_token = tokens['access']
    user.refresh_token = tokens['refresh']
    
    return user


@pytest.fixture
def dealer_user(db):
    """Create a dealer user with JWT tokens."""
    user = User.objects.create_user(
        phone='+998902345678',
        full_name='Qora Diller',
        role='dealer',
        password='Test@1234567',
    )
    user.is_verified = True
    user.save()
    
    tokens = get_jwt_tokens(user)
    user.access_token = tokens['access']
    user.refresh_token = tokens['refresh']
    
    return user


@pytest.fixture
def store_user(db):
    """Create a store owner user with JWT tokens."""
    user = User.objects.create_user(
        phone='+998903456789',
        full_name="Do'kon Egasi",
        role='store',
        password='Test@1234567',
    )
    user.is_verified = True
    user.save()
    
    tokens = get_jwt_tokens(user)
    user.access_token = tokens['access']
    user.refresh_token = tokens['refresh']
    
    return user


@pytest.fixture
def authenticated_client(api_client, manufacturer_user):
    """APIClient with manufacturer authentication set."""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {manufacturer_user.access_token}')
    api_client.user = manufacturer_user
    return api_client


@pytest.fixture
def dealer_client(api_client, dealer_user):
    """APIClient with dealer authentication set."""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {dealer_user.access_token}')
    api_client.user = dealer_user
    return api_client


@pytest.fixture
def store_client(api_client, store_user):
    """APIClient with store owner authentication set."""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {store_user.access_token}')
    api_client.user = store_user
    return api_client


# ============================================================================
# LOCATION FIXTURES
# ============================================================================


@pytest.fixture
def sample_location(db):
    """Create a sample location (Tashkent)."""
    return Location.objects.create(
        city='Tashkent',
        latitude=Decimal('41.2995'),
        longitude=Decimal('69.2401'),
        is_active=True,
    )


@pytest.fixture
def sample_region(db):
    """Create a sample region."""
    return Location.objects.create(
        city='Samarkand',
        latitude=Decimal('39.6549'),
        longitude=Decimal('66.9597'),
        is_active=True,
    )


# ============================================================================
# CATEGORY & PRODUCT FIXTURES
# ============================================================================


@pytest.fixture
def sample_category(db):
    """Create a sample product category."""
    return Category.objects.create(
        name='Elektronika',
        slug='elektronika',
        description='Elektronik mahsulotlar',
        is_active=True,
        order=1,
    )


@pytest.fixture
def sample_category_subcategory(db, sample_category):
    """Create a subcategory under sample_category."""
    return Category.objects.create(
        name='Telefonlar',
        slug='telefonlar',
        parent=sample_category,
        description='Mobil telefonlar',
        is_active=True,
        order=1,
    )


@pytest.fixture
def sample_product(db, manufacturer_user, sample_category):
    """Create a sample product with stock."""
    return Product.objects.create(
        name='Samsung Galaxy S24',
        slug='samsung-galaxy-s24',
        category=sample_category,
        manufacturer=manufacturer_user,
        description='Eng yangi Samsung telefon',
        price=Decimal('5000.00'),
        stock=100,
        is_active=True,
    )


@pytest.fixture
def low_stock_product(db, manufacturer_user, sample_category):
    """Create a product with low stock."""
    return Product.objects.create(
        name='iPhone 15 Pro',
        slug='iphone-15-pro',
        category=sample_category,
        manufacturer=manufacturer_user,
        description='Apple iPhone 15 Pro',
        price=Decimal('7500.00'),
        stock=2,
        is_active=True,
    )


@pytest.fixture
def out_of_stock_product(db, manufacturer_user, sample_category):
    """Create a product with no stock."""
    return Product.objects.create(
        name='Google Pixel 8',
        slug='google-pixel-8',
        category=sample_category,
        manufacturer=manufacturer_user,
        description='Google Pixel 8 Pro',
        price=Decimal('4500.00'),
        stock=0,
        is_active=True,
    )


@pytest.fixture
def product_with_images(db, sample_product):
    """Create a product with images."""
    # Create test image
    image_data = BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(image_data, format='JPEG')
    image_data.seek(0)
    
    # Create ProductImage
    ProductImage.objects.create(
        product=sample_product,
        image=image_data,
        is_primary=True,
    )
    
    return sample_product


# ============================================================================
# CART FIXTURES
# ============================================================================


@pytest.fixture
def sample_cart(db, store_user):
    """Create a cart for a store user."""
    return Cart.objects.create(user=store_user)


@pytest.fixture
def cart_with_items(db, sample_cart, sample_product, low_stock_product):
    """Create a cart with multiple items."""
    CartItem.objects.create(
        cart=sample_cart,
        product=sample_product,
        quantity=5,
    )
    CartItem.objects.create(
        cart=sample_cart,
        product=low_stock_product,
        quantity=1,
    )
    return sample_cart


# ============================================================================
# ORDER FIXTURES
# ============================================================================


@pytest.fixture
def sample_order(db, store_user, dealer_user, sample_product):
    """Create a pending order."""
    order = Order.objects.create(
        user=store_user,
        dealer=dealer_user,
        status='pending',
        total_amount=Decimal('5000.00'),
        delivery_address='Tashkent, Chilonzor',
        notes='Tezda yetkazib bering',
    )
    
    OrderItem.objects.create(
        order=order,
        product=sample_product,
        quantity=1,
        unit_price=sample_product.price,
    )
    
    return order


@pytest.fixture
def accepted_order(db, store_user, dealer_user, sample_product):
    """Create an accepted order."""
    order = Order.objects.create(
        user=store_user,
        dealer=dealer_user,
        status='accepted',
        total_amount=Decimal('5000.00'),
        delivery_address='Tashkent, Chilonzor',
        accepted_by=dealer_user,
        accepted_at=timezone.now(),
    )
    
    OrderItem.objects.create(
        order=order,
        product=sample_product,
        quantity=1,
        unit_price=sample_product.price,
    )
    
    return order


@pytest.fixture
def delivered_order(db, store_user, dealer_user, sample_product):
    """Create a delivered order."""
    order = Order.objects.create(
        user=store_user,
        dealer=dealer_user,
        status='delivered',
        total_amount=Decimal('5000.00'),
        delivery_address='Tashkent, Chilonzor',
        accepted_by=dealer_user,
        accepted_at=timezone.now() - timedelta(days=1),
        delivered_at=timezone.now(),
    )
    
    OrderItem.objects.create(
        order=order,
        product=sample_product,
        quantity=1,
        unit_price=sample_product.price,
    )
    
    return order


# ============================================================================
# DEALER PROFILE FIXTURES
# ============================================================================


@pytest.fixture
def dealer_profile_with_location(db, dealer_user, sample_location):
    """Create a dealer profile with coverage area."""
    profile = DealerProfile.objects.create(
        user=dealer_user,
        business_name='Qora Diller Kompaniyasi',
        location=sample_location,
        coverage_radius=Decimal('10.5'),  # 10.5 km radius
        is_available=True,
        phone_number=dealer_user.phone,
    )
    return profile


@pytest.fixture
def unavailable_dealer_profile(db, sample_location):
    """Create an unavailable dealer profile."""
    user = User.objects.create_user(
        phone='+998904567890',
        full_name='Faol bo\'lmagan Diller',
        role='dealer',
        password='Test@1234567',
    )
    user.is_verified = True
    user.save()
    
    profile = DealerProfile.objects.create(
        user=user,
        business_name='Faol bo\'lmagan Kompaniya',
        location=sample_location,
        coverage_radius=Decimal('5.0'),
        is_available=False,
        phone_number=user.phone,
    )
    return profile


# ============================================================================
# NOTIFICATION FIXTURES
# ============================================================================


@pytest.fixture
def unread_notification(db, store_user):
    """Create an unread notification."""
    return Notification.objects.create(
        user=store_user,
        title='Test Bildirishnoma',
        body='Bu test bildirishnomasi',
        notification_type='order',
        is_read=False,
    )


@pytest.fixture
def read_notification(db, store_user):
    """Create a read notification."""
    return Notification.objects.create(
        user=store_user,
        title='O\'qilgan Bildirishnoma',
        body='Bu o\'qilgan bildirishnomasi',
        notification_type='order',
        is_read=True,
    )


# ============================================================================
# OTP FIXTURES
# ============================================================================


@pytest.fixture
def valid_otp(db, store_user):
    """Create a valid OTP for a user."""
    otp = OTPCode.objects.create(
        user=store_user,
        code='123456',
        is_used=False,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    return otp


@pytest.fixture
def expired_otp(db, store_user):
    """Create an expired OTP for a user."""
    otp = OTPCode.objects.create(
        user=store_user,
        code='654321',
        is_used=False,
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    return otp


@pytest.fixture
def used_otp(db, store_user):
    """Create a used OTP for a user."""
    otp = OTPCode.objects.create(
        user=store_user,
        code='111111',
        is_used=True,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    return otp


# ============================================================================
# DJANGO DB CONFIGURATION
# ============================================================================


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Configure test database - can be customized if needed."""
    with django_db_blocker.unblock():
        pass
