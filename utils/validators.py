"""
Reusable validators for TradeLink API.

Includes validators for:
- Phone numbers (Uzbek format +998XXXXXXXXX)
- Prices (positive values)
- Quantities (non-negative, respecting min/max)
- Image uploads (file size, MIME types)
- Geographic data (coordinates, radius)
"""

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


# ===========================
# Phone Number Validators
# ===========================

def validate_phone_number(value):
    """
    Validate phone number in Uzbek format: +998[0-9]{9}
    
    Valid examples:
    - +998901234567
    - +998331234567
    - 998901234567 (without +)
    
    Raises:
        ValidationError: If phone format is invalid
    """
    # Remove leading + if present
    phone = value.lstrip('+')
    
    # Check if it matches the pattern: 998XXXXXXXXX (11 digits)
    pattern = r'^998[0-9]{9}$'
    
    if not re.match(pattern, phone):
        raise ValidationError(
            _('Telefon raqam noto\'g\'ri format. O\'zbek raqami: +998XXXXXXXXX'),
            code='invalid_phone_format',
            params={'value': value}
        )


def validate_phone_starts_with_code(value):
    """
    Validate that phone starts with valid Uzbekistani carrier code.
    """
    phone = value.lstrip('+')
    valid_codes = ['90', '91', '92', '93', '94', '95', '96', '97', '98', '99']
    
    if not any(phone.startswith(f'998{code}') for code in valid_codes):
        raise ValidationError(
            _('Telefon operatori noto\'g\'ri'),
            code='invalid_carrier_code'
        )


# ===========================
# Price Validators
# ===========================

def validate_product_price(value):
    """
    Validate that price is positive (> 0).
    
    Raises:
        ValidationError: If price <= 0
    """
    if value <= 0:
        raise ValidationError(
            _('Narx 0 dan katta bo\'lishi kerak'),
            code='invalid_price',
            params={'value': value}
        )


def validate_max_price(max_value):
    """
    Factory function to create a validator that checks price <= max_value.
    
    Usage:
        price = DecimalField(validators=[validate_product_price, validate_max_price(10000000)])
    """
    def validator(value):
        if value > max_value:
            raise ValidationError(
                _('Narx %(max_value)s dan oshmasligi kerak'),
                code='price_exceeds_max',
                params={'max_value': max_value, 'value': value}
            )
    return validator


# ===========================
# Quantity Validators
# ===========================

def validate_quantity(value):
    """
    Validate quantity is positive integer.
    """
    if not isinstance(value, int) or value <= 0:
        raise ValidationError(
            _('Miqdor musbat butun son bo\'lishi kerak'),
            code='invalid_quantity'
        )


def validate_quantity_range(min_qty=1, max_qty=None):
    """
    Factory function to create a validator checking quantity is within range.
    
    Usage:
        quantity = IntegerField(validators=[validate_quantity_range(min_qty=5, max_qty=1000)])
    """
    def validator(value):
        if value < min_qty:
            raise ValidationError(
                _('Miqdor kamida %(min_qty)s bo\'lishi kerak'),
                code='quantity_below_min',
                params={'min_qty': min_qty, 'value': value}
            )
        if max_qty and value > max_qty:
            raise ValidationError(
                _('Miqdor %(max_qty)s dan oshmasligi kerak'),
                code='quantity_exceeds_max',
                params={'max_qty': max_qty, 'value': value}
            )
    return validator


# ===========================
# Image Upload Validators
# ===========================

def validate_image_file_size(max_size_mb=5):
    """
    Factory function to validate image file size (default 5MB).
    
    Usage:
        image = ImageField(validators=[validate_image_file_size(max_size_mb=5)])
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    def validator(file_obj):
        if file_obj.size > max_size_bytes:
            raise ValidationError(
                _('Rasm hajmi %(max_mb)sMB dan oshmasligi kerak'),
                code='image_too_large',
                params={'max_mb': max_size_mb}
            )
    return validator


def validate_image_mime_type(allowed_types=None):
    """
    Factory function to validate image MIME type.
    
    Default allowed types: jpeg, png, webp
    
    Usage:
        image = ImageField(validators=[validate_image_mime_type(['image/jpeg', 'image/png'])])
    """
    if allowed_types is None:
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    
    def validator(file_obj):
        if file_obj.content_type not in allowed_types:
            raise ValidationError(
                _('Rasm formati noto\'g\'ri. Ruxsat etilgan: %(allowed)s'),
                code='invalid_image_type',
                params={'allowed': ', '.join(allowed_types)}
            )
    return validator


# ===========================
# Geographic Validators
# ===========================

def validate_latitude(value):
    """
    Validate latitude is within valid range: -90 to 90.
    """
    if not (-90 <= value <= 90):
        raise ValidationError(
            _('Kenglik -90 dan 90 gacha bo\'lishi kerak'),
            code='invalid_latitude'
        )


def validate_longitude(value):
    """
    Validate longitude is within valid range: -180 to 180.
    """
    if not (-180 <= value <= 180):
        raise ValidationError(
            _('Uzunlik -180 dan 180 gacha bo\'lishi kerak'),
            code='invalid_longitude'
        )


def validate_coverage_radius(value):
    """
    Validate coverage radius is between 0.5 and 100 km.
    """
    if not (0.5 <= value <= 100):
        raise ValidationError(
            _('Xizmat radiusi 0.5 dan 100 km gacha bo\'lishi kerak'),
            code='invalid_radius',
            params={'value': value}
        )


# ===========================
# Slug/Username Validators
# ===========================

def validate_username(value):
    """
    Validate username: alphanumeric, underscore, hyphen. 3-30 chars.
    """
    pattern = r'^[a-zA-Z0-9_-]{3,30}$'
    
    if not re.match(pattern, value):
        raise ValidationError(
            _('Foydalanuvchi nomi faqat harf, raqam, _ va - ga o\'z toladi (3-30 ta belgi)'),
            code='invalid_username'
        )


# ===========================
# Text Content Validators
# ===========================

def validate_no_xss(value):
    """
    Basic XSS prevention: reject common HTML/JS patterns.
    NOTE: This is NOT a comprehensive XSS filter. Use template escaping in frontend.
    """
    dangerous_patterns = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',  # onclick, onload, etc.
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_lower, re.IGNORECASE):
            raise ValidationError(
                _('Matn samarali HTML tag yoki skriptlarni o\'z olmaydi'),
                code='xss_detected'
            )


def validate_business_name_length(value):
    """
    Business name: 3-200 characters, no excessive punctuation.
    """
    if len(value) < 3 or len(value) > 200:
        raise ValidationError(
            _('Biznes nomi 3 dan 200 ta belgigacha bo\'lishi kerak'),
            code='invalid_name_length'
        )
    
    # Check for excessive punctuation
    punctuation_count = sum(1 for c in value if c in '.,!?;:')
    if punctuation_count > 5:
        raise ValidationError(
            _('Juda ko\'p tinish belgilari mavjud'),
            code='excessive_punctuation'
        )
