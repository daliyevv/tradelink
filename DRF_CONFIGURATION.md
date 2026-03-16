"""
DRF (Django REST Framework) Configuration Guide

This module documents the Django REST Framework configuration for TradeLink API.
"""

# ===========================
# REST_FRAMEWORK Settings
# ===========================

"""
Configuration in config/settings/base.py:

REST_FRAMEWORK = {
    # Authentication: Only JWT tokens allowed
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    
    # Permissions: All endpoints require authentication by default
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    
    # Filtering and Search
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',  # for ?field=value
        'rest_framework.filters.SearchFilter',                # for ?search=term
        'rest_framework.filters.OrderingFilter',              # for ?ordering=-created_at
    ),
    
    # Pagination: 20 items per page by default
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    
    # Rate Limiting: Prevent abuse
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',      # Anonymous users: 100 requests/hour
        'user': '1000/hour',     # Authenticated users: 1000 requests/hour
    },
    
    # OpenAPI/Swagger Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Custom Exception Handler
    'EXCEPTION_HANDLER': 'utils.exception_handler.custom_exception_handler',
    
    # Response format: JSON only
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}
"""

# ===========================
# SIMPLE_JWT Settings
# ===========================

"""
Configuration in config/settings/base.py:

SIMPLE_JWT = {
    # Token Lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),   # Short-lived access token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),     # Long-lived refresh token
    
    # Token Rotation: Get new refresh token on refresh
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,  # Blacklist old refresh token
    
    # Algorithm and Keys
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    
    # Standard Claims
    'AUDIENCE': None,
    'ISSUER': None,
    'JTI_CLAIM': 'jti',  # Token ID for blacklisting
    
    # Token Classes
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'AUTH_REFRESH_CLASS': 'rest_framework_simplejwt.tokens.RefreshToken',
    
    # HttpOnly Cookies (for web frontend)
    'AUTH_COOKIE': 'jwt-auth-cookie',
    'AUTH_COOKIE_REFRESH': 'jwt-refresh-cookie',
    'AUTH_COOKIE_SECURE': True,        # HTTPS only
    'AUTH_COOKIE_HTTP_ONLY': True,     # Cannot access from JavaScript
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Strict',  # CSRF protection
}

Usage:
1. User registers with phone number
2. User verifies OTP
3. Backend returns access_token and refresh_token
4. Client includes access_token in Authorization header:
   Authorization: Bearer <access_token>
5. When access_token expires, use refresh_token:
   POST /api/v1/auth/token/refresh/
   Body: {"refresh": "<refresh_token>"}
6. Get new access_token (and optionally new refresh_token if rotation enabled)
"""

# ===========================
# SPECTACULAR Settings
# ===========================

"""
Configuration in config/settings/base.py:

SPECTACULAR_SETTINGS = {
    'TITLE': 'TradeLink API',
    'DESCRIPTION': 'B2B Trading Platform API',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SCHEMA_PATH_PREFIX': '/api/v1/',
}

Access:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/
"""

# ===========================
# CORS Configuration
# ===========================

"""
Configuration in config/settings/base.py:

CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000,http://localhost:8080'
).split(',')

CORS_ALLOW_CREDENTIALS = True  # Allow sending cookies

.env example:
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://tradelink.uz,https://www.tradelink.uz

This allows:
- React/Vue frontend on port 3000
- TradeLink production domain
- Prevents CORS errors when frontend calls API
"""

# ===========================
# Custom Exception Handler
# ===========================

"""
Located in: utils/exception_handler.py

Returns standardized error format for all exceptions:

{
    "success": false,
    "message": "Validatsiya xatosi",
    "errors": {
        "field_name": ["error message 1", "error message 2"],
        "email": ["This field must be unique."]
    }
}

Error Messages (Uzbek):
- 400: Noto'g'ri so'rov
- 401: Autentifikatsiya talab qilinadi
- 403: Bu amalga ruxsat yo'q
- 404: Resurs topilmadi
- 429: Juda ko'p so'rovlar
- 500: Server xatosi yuz berdi
"""

# ===========================
# Response Mixins
# ===========================

"""
Located in: utils/responses.py

Two mixins available for ViewSets:

1. StandardResponseMixin:
   Wraps list(), retrieve(), create(), update(), partial_update(), destroy()
   
   Example:
   from utils.responses import StandardResponseMixin, CombinedResponseMixin
   from rest_framework import viewsets
   
   class ProductViewSet(StandardResponseMixin, viewsets.ModelViewSet):
       queryset = Product.objects.all()
       serializer_class = ProductSerializer
   
   Response format:
   {
       "success": true,
       "data": {...},
       "message": "Muvaffaqiyatli olingan"
   }

2. ActionResponseMixin:
   For custom @action methods
   
   Example:
   @action(detail=False, methods=['post'])
   def my_action(self, request):
       # Do something
       return self.action_success(
           data={'result': 'value'},
           message='Muvaffaqiyatli'
       )

3. CombinedResponseMixin (Recommended):
   Includes both StandardResponseMixin and ActionResponseMixin
   
   class ProductViewSet(CombinedResponseMixin, viewsets.ModelViewSet):
       # All standard CRUD and custom actions are wrapped
       pass
"""

# ===========================
# Authentication Flow
# ===========================

"""
1. User Registration (requires phone + SMS OTP):
   POST /api/v1/auth/register/
   {
       "phone": "+998901234567",
       "full_name": "John Doe",
       "role": "store"  # manufacturer, dealer, or store
   }
   
   Response:
   {
       "success": true,
       "data": {
           "id": "uuid-here",
           "phone": "+998901234567"
       },
       "message": "OTP yuborildi"
   }

2. OTP Verification:
   POST /api/v1/auth/verify-otp/
   {
       "phone": "+998901234567",
       "otp": "123456"
   }
   
   Response:
   {
       "success": true,
       "data": {
           "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
           "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
       },
       "message": "Muvaffaqiyatli kirish"
   }

3. Subsequent API Calls:
   Include access token in header:
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

4. Token Refresh (when access token expires):
   POST /api/v1/auth/token/refresh/
   {
       "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
   
   Response:
   {
       "success": true,
       "data": {
           "access": "new-access-token",
           "refresh": "new-refresh-token"  # if rotation enabled
       },
       "message": "Token yangilandi"
   }

5. Logout (blacklist refresh token):
   POST /api/v1/auth/logout/
   {
       "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
   
   Response:
   {
       "success": true,
       "data": null,
       "message": "Muvaffaqiyatli chiqish"
   }
"""

# ===========================
# Filtering and Search Examples
# ===========================

"""
1. Filter by field:
   GET /api/v1/products/?category=uuid-here

2. Search across fields:
   GET /api/v1/products/?search=samsung
   (searches name, description by default)

3. Order results:
   GET /api/v1/products/?ordering=-created_at
   (descending by created_at; use - for descending)
   GET /api/v1/products/?ordering=name
   (ascending by name)

4. Pagination:
   GET /api/v1/products/?page=2&page_size=50
   (default page_size is 20, max is configurable)

5. Combine multiple filters:
   GET /api/v1/products/?category=uuid&search=phone&ordering=-price&page=1
"""

# ===========================
# Permissions
# ===========================

"""
Available permission classes in utils/permissions.py:

1. IsManufacturer:
   Only users with role='manufacturer' can access
   
   Usage in ViewSet:
   from utils.permissions import IsManufacturer
   from rest_framework.permissions import IsAuthenticated
   
   class ProductViewSet(viewsets.ModelViewSet):
       permission_classes = [IsAuthenticated, IsManufacturer]

2. IsDealer:
   Only users with role='dealer' can access

3. IsStoreOwner:
   Only users with role='store' can access

4. IsOwnerOrReadOnly:
   Owner can modify, others get read-only access
   
   class ProfileViewSet(viewsets.ViewSet):
       permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

Custom permissions can be created similarly:
from rest_framework.permissions import BasePermission

class MyCustomPermission(BasePermission):
    message = 'Ruxsat yo\'q'
    
    def has_permission(self, request, view):
        # Check user permission
        return request.user.has_perm('some.permission')
    
    def has_object_permission(self, request, view, obj):
        # Check object-level permission
        return obj.owner == request.user
"""

# ===========================
# Testing the API
# ===========================

"""
Using curl:

1. Register:
curl -X POST http://localhost:8000/api/v1/auth/register/ \\
  -H "Content-Type: application/json" \\
  -d '{"phone": "+998901234567", "full_name": "Test", "role": "store"}'

2. Verify OTP:
curl -X POST http://localhost:8000/api/v1/auth/verify-otp/ \\
  -H "Content-Type: application/json" \\
  -d '{"phone": "+998901234567", "otp": "123456"}'

3. Get products:
curl -X GET http://localhost:8000/api/v1/products/ \\
  -H "Authorization: Bearer <access_token>"

Using Python requests:
import requests

# Login
resp = requests.post(
    'http://localhost:8000/api/v1/auth/verify-otp/',
    json={'phone': '+998901234567', 'otp': '123456'}
)
tokens = resp.json()['data']
access = tokens['access']

# API call
headers = {'Authorization': f'Bearer {access}'}
resp = requests.get(
    'http://localhost:8000/api/v1/products/',
    headers=headers
)
products = resp.json()['data']['results']
"""
