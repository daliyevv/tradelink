# TradeLink Backend - Complete Architecture & Status

This document provides a comprehensive overview of the TradeLink backend structure, configuration, and implementation status.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Implementation Status](#implementation-status)
5. [Module Descriptions](#module-descriptions)
6. [API Standards](#api-standards)
7. [Authentication & Security](#authentication--security)
8. [Configuration System](#configuration-system)
9. [Deployment](#deployment)
10. [Development Workflow](#development-workflow)

---

## Project Overview

**Project Name:** TradeLink  
**Type:** B2B E-commerce Platform for Wholesale Trading  
**Target Market:** Uzbekistan  
**Primary Language:** Python/Django  
**API Version:** 1.0  
**Status:** In Development

### Key Features

- 👥 User role-based access (Manufacturer, Dealer, Store Owner)
- 📦 Product catalog with categories and suppliers
- 🛒 Shopping cart and checkout system
- 📋 Order management with status workflow
- 📍 Geolocation-based dealer discovery (PostGIS)
- 🔔 Push notifications (Firebase Cloud Messaging)
- ⚡ Async task processing (Celery)
- 📊 Analytics and reporting

### Business Logic

```
Manufacturer → Product Catalog
               ↓
            Dealer ← Customer Order
               ↓
         Store Owner → Order Fulfillment
```

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                       │
│            (Mobile App, Web Dashboard, Admin)            │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────┐
│              API Gateway (Nginx)                         │
│  - SSL/TLS Termination                                  │
│  - Request Routing                                       │
│  - Static File Serving                                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           Django Application Server                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │ REST API Endpoints (DRF)                         │   │
│  │ - Authentication                                 │   │
│  │ - Products, Orders, Cart                         │   │
│  │ - User Management                                │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Business Logic Layer                             │   │
│  │ - Permissions & Access Control                   │   │
│  │ - Geolocation Queries (PostGIS)                 │   │
│  │ - OTP & SMS Verification                         │   │
│  │ - Cart & Checkout Atomic Transactions            │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Data Access Layer                                │   │
│  │ - ORM (Django Models)                            │   │
│  │ - Query Optimization                             │   │
│  │ - Caching                                        │   │
│  └──────────────────────────────────────────────────┘   │
└────────────┬─────────────┬─────────────┬────────────────┘
             │             │             │
             ▼             ▼             ▼
        ┌────────┐    ┌────────┐   ┌─────────┐
        │Database│    │ Cache  │   │Message  │
        │(PG+GIS)│    │(Redis) │   │Broker   │
        └────────┘    └────────┘   │(Redis)  │
                                    └────┬────┘
                                         │
                                    ┌────▼────┐
                                    │  Celery  │
                                    │  Worker  │
                                    └──────────┘
```

### 8-App Modular Structure

```
tradelink/
├── config/                    # Project configuration
│   ├── settings/
│   │   ├── base.py           # Shared settings (all envs)
│   │   ├── development.py    # Dev overrides (DEBUG=True)
│   │   └── production.py     # Prod overrides (security)
│   ├── asgi.py               # Async server
│   ├── wsgi.py               # Sync server
│   └── urls.py               # Main URL router
│
├── apps/
│   ├── users/                # User accounts & authentication
│   │   ├── models.py         # Custom User model (AbstractBaseUser)
│   │   ├── serializers.py    # Serializers (Register, Login, Profile)
│   │   ├── views.py          # Auth endpoints (register, verify_otp, logout)
│   │   ├── urls.py           # /api/v1/auth/*
│   │   └── permissions.py    # Custom permission classes
│   │
│   ├── products/             # Product catalog
│   │   ├── models.py         # Product, Category, ProductImage, Review
│   │   ├── serializers.py    # ProductSerializer, CategorySerializer
│   │   ├── views.py          # ProductViewSet, CategoryViewSet
│   │   ├── urls.py           # /api/v1/products/*, /api/v1/categories/*
│   │   ├── filters.py        # Custom filters (category, price range)
│   │   └── signals.py        # Auto-actions (cache invalidation)
│   │
│   ├── orders/               # Order management
│   │   ├── models.py         # Order, OrderItem, OrderStatus
│   │   ├── serializers.py    # OrderSerializer, OrderItemSerializer
│   │   ├── views.py          # OrderViewSet (with status workflow)
│   │   ├── urls.py           # /api/v1/orders/*
│   │   ├── tasks.py          # Celery tasks (send notification, generate invoice)
│   │   └── signals.py        # Update stock on order
│   │
│   ├── cart/                 # Shopping cart
│   │   ├── models.py         # Cart, CartItem
│   │   ├── serializers.py    # CartSerializer, CartItemSerializer
│   │   ├── views.py          # CartViewSet with checkout action
│   │   ├── urls.py           # /api/v1/cart/*
│   │   └── tasks.py          # Async cart cleanup
│   │
│   ├── dealers/              # Dealer profiles & management
│   │   ├── models.py         # DealerProfile, DealerRating
│   │   ├── serializers.py    # DealerSerializer
│   │   ├── views.py          # DealerViewSet with nearby() action
│   │   ├── urls.py           # /api/v1/dealers/*
│   │   └── filters.py        # PostGIS distance filtering
│   │
│   ├── locations/            # Geolocation
│   │   ├── models.py         # Location (Point), Address
│   │   ├── serializers.py    # LocationSerializer
│   │   ├── views.py          # LocationViewSet
│   │   ├── urls.py           # /api/v1/locations/*
│   │   └── utils.py          # Distance calculation, geocoding
│   │
│   ├── notifications/        # Push notifications
│   │   ├── models.py         # Notification, NotificationLog
│   │   ├── serializers.py    # NotificationSerializer
│   │   ├── views.py          # Read notifications, mark as read
│   │   ├── urls.py           # /api/v1/notifications/*
│   │   ├── fcm.py            # Firebase Cloud Messaging integration
│   │   └── tasks.py          # Celery task for sending FCM
│   │
│   └── analytics/            # Reporting & metrics
│       ├── models.py         # Analytics, UserActivity
│       ├── serializers.py    # ReportSerializer
│       ├── views.py          # Dashboard endpoints
│       ├── urls.py           # /api/v1/analytics/*
│       └── tasks.py          # Periodic aggregation (Celery Beat)
│
├── utils/                    # Shared utilities
│   ├── exception_handler.py  # Custom DRF exception handler
│   │                          # Returns: {"success": false, "message": "...", "errors": {...}}
│   ├── responses.py          # Response wrapper mixins
│   │                          # StandardResponseMixin (CRUD)
│   │                          # ActionResponseMixin (custom @actions)
│   │                          # CombinedResponseMixin (both)
│   ├── permissions.py        # Role-based permissions
│   │                          # IsManufacturer, IsDealer, IsStoreOwner
│   ├── validators.py         # Field validators
│   │                          # Phone format, email, image size, etc.
│   ├── pagination.py         # Custom pagination
│   │                          # PageNumberPagination (20 items/page)
│   ├── filters.py            # Custom filters
│   │                          # DateRangeFilter, PriceRangeFilter
│   └── constants.py          # Application constants
│                              # Status choices, unit types, error codes
│
├── static/                   # Static files (CSS, JS, images)
├── media/                    # User uploads
├── logs/                     # Application logs
│
└── requirements/
    ├── base.txt              # All environments
    ├── development.txt       # Dev tools
    └── production.txt        # Gunicorn, monitoring
```

---

## Technology Stack

### Backend Framework

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.10+ | Programming language |
| **Django** | 5.0.0 | Web framework |
| **Django REST Framework** | 3.14.0 | API development |
| **djangorestframework-simplejwt** | 5.3.2 | JWT authentication |
| **drf-spectacular** | 0.27.0 | OpenAPI/Swagger documentation |
| **django-cors-headers** | 4.3.1 | CORS handling |
| **django-filter** | 24.1 | Advanced filtering |

### Database & Geolocation

| Component | Version | Purpose |
|-----------|---------|---------|
| **PostgreSQL** | 15 | Primary database |
| **PostGIS** | 3.4 | Geospatial queries (nearby dealers) |
| **GeoDjango** | Built-in | Django + PostGIS integration |

### Caching & Message Queue

| Component | Version | Purpose |
|-----------|---------|---------|
| **Redis** | 7 | Cache, message broker, sessions |
| **Celery** | 5.3.4 | Async task processing |
| **django-celery-beat** | 2.5.0 | Periodic tasks scheduler |

### Production Servers

| Component | Version | Purpose |
|-----------|---------|---------|
| **Gunicorn** | 21.2.0 | WSGI server (sync requests) |
| **Daphne** | 4.0.0 | ASGI server (async ready) |
| **Nginx** | Latest | Reverse proxy, static files, SSL |

### External Services

| Service | Purpose | Configuration |
|---------|---------|-------|
| **Firebase Cloud Messaging** | Push notifications | `FCM_SERVER_KEY` env var |
| **Twilio** | SMS/OTP delivery | `TWILIO_*` env vars |
| **AWS S3 / Cloudflare R2** | File storage (optional) | `AWS_*` env vars |

### Development Tools

| Tool | Purpose |
|------|---------|
| **django-debug-toolbar** | Development profiling |
| **django-extensions** | Extra management commands |
| **Black** | Code formatting |
| **Flake8** | Linting |
| **Pytest** | Testing |

---

## Implementation Status

### ✅ Phase 1: Foundation (COMPLETE)

- [x] Django 5.x project structure with 8 apps
- [x] Configuration system (base, development, production settings)
- [x] Environment variable management (.env system)
- [x] Requirements files organization
- [x] Utilities module structure

**Files Created:**
- `manage.py`, project structure
- `config/settings/base.py`, `development.py`, `production.py`
- All 8 app directories with `apps.py`, `urls.py`, `models.py`, `admin.py`
- `utils/` with exception_handler, responses, permissions, validators

### ✅ Phase 2: Docker & DevOps (COMPLETE)

- [x] Docker Compose orchestration (6 services)
- [x] Dockerfile for Django application
- [x] PostgreSQL + PostGIS setup
- [x] Redis configuration
- [x] Celery worker and beat services
- [x] Nginx reverse proxy with SSL
- [x] Health checks and restart policies
- [x] Production Docker Compose variant
- [x] .dockerignore and entrypoint script
- [x] Helper scripts (reset-db.sh, backup.sh)
- [x] DOCKER.md deployment guide

**Services:**
```
postgres:5432         - PostgreSQL with PostGIS
redis:6379           - Redis cache & message broker
django:8000          - Gunicorn + Django application
celery-worker        - Async task processing
celery-beat          - Periodic task scheduler
nginx:80/443         - Reverse proxy & static files
```

### ✅ Phase 3: DRF & API Standardization (COMPLETE)

- [x] REST_FRAMEWORK configuration
  - JWTAuthentication
  - IsAuthenticated default permission
  - PageNumberPagination (20 items/page)
  - DjangoFilterBackend + SearchFilter + OrderingFilter
  - Throttling (100/hr anon, 1000/hr user)

- [x] SIMPLE_JWT configuration
  - ACCESS_TOKEN_LIFETIME: 15 minutes
  - REFRESH_TOKEN_LIFETIME: 30 days
  - ROTATE_REFRESH_TOKENS: True (new token on refresh)
  - BLACKLIST_AFTER_ROTATION: True (old tokens invalid)

- [x] drf-spectacular (OpenAPI/Swagger)
  - Title: "TradeLink API"
  - Version: "1.0.0"
  - Schema path: `/api/v1/`
  - Endpoints: /api/docs/, /api/redoc/, /api/schema/

- [x] Custom exception handler
  - Standardized error format: `{"success": false, "message": "...", "errors": {...}}`
  - Uzbek error messages
  - Handles: 400, 401, 403, 404, 429, 500, etc.

- [x] Response wrapper mixins
  - StandardResponseMixin: Wraps CRUD operations (list, retrieve, create, update, partial_update, destroy)
  - ActionResponseMixin: Wraps custom @action methods
  - CombinedResponseMixin: Combines both (recommended for production)

- [x] CORS configuration
  - From environment variables
  - Allow credentials enabled
  - Development: localhost:3000, localhost:8000
  - Production: yourdomain.com

**Configuration Files Created:**
- `utils/exception_handler.py` (custom handler with Uzbek messages)
- `utils/responses.py` (three mixin classes for automatic response wrapping)
- `DRF_CONFIGURATION.md` (300+ line comprehensive guide)
- `EXAMPLE_VIEWSET.md` (350+ line implementation examples)

### 🟡 Phase 4: Authentication & User Management (IN PROGRESS - NEXT)

**Status:** Scaffolding ready, awaiting implementation

**Planned:**
```python
# Custom User Model
class User(AbstractBaseUser):
    id = UUIDField(primary_key=True)
    phone = CharField(+998XXXXXXXXX, unique=True)
    email = EmailField()
    full_name = CharField()
    role = CharField(choices=[('manufacturer', ...), ('dealer', ...), ('store', ...)])
    avatar = ImageField(optional)
    is_verified = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
```

**Endpoints:**
- `POST /api/v1/auth/register/` - Send OTP to phone
- `POST /api/v1/auth/verify-otp/` - Get access + refresh tokens
- `POST /api/v1/auth/token/refresh/` - Refresh access token
- `POST /api/v1/auth/logout/` - Blacklist refresh token

**Permission Classes:**
- `IsManufacturer` - Role check
- `IsDealer` - Role check
- `IsStoreOwner` - Role check

### 🟡 Phase 5: Product Catalog (NOT STARTED)

**Planned Models:**
```python
class Category(models.Model):
    id = UUIDField(primary_key=True)
    name = CharField()
    parent = ForeignKey('self', null=True)  # Hierarchical
    image = ImageField()
    created_at = DateTimeField(auto_now_add=True)

class Product(models.Model):
    id = UUIDField(primary_key=True)
    name = CharField()
    description = TextField()
    manufacturer = ForeignKey(User)  # Creator
    category = ForeignKey(Category)
    price = DecimalField(12, 2)
    stock = IntegerField()
    unit = CharField(choices=[('dona', 'Dona'), ('kg', 'Kilogram')])
    min_order_qty = IntegerField()
    images = OneToManyField(ProductImage)
    rating = DecimalField(default=0)
    created_at = DateTimeField(auto_now_add=True)

class ProductImage(models.Model):
    product = ForeignKey(Product)
    image = ImageField()
    is_primary = BooleanField(default=False)
```

**Endpoints:**
- `GET /api/v1/products/` (list, search, filter, order, paginate)
- `POST /api/v1/products/` (create by manufacturer)
- `GET /api/v1/products/{id}/` (retrieve)
- `PATCH /api/v1/products/{id}/` (update by owner)
- `DELETE /api/v1/products/{id}/` (delete by owner)

### 🟡 Phase 6: Shopping Cart & Checkout (NOT STARTED)

**Planned Models:**
```python
class Cart(models.Model):
    id = UUIDField(primary_key=True)
    user = OneToOneField(User)
    dealer = ForeignKey(DealerProfile, null=True)  # Selected for checkout
    items = OneToManyField(CartItem)
    created_at = DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    id = UUIDField(primary_key=True)
    cart = ForeignKey(Cart)
    product = ForeignKey(Product)
    quantity = IntegerField(min=1)
    price_snapshot = DecimalField()  # Price at time of add
    created_at = DateTimeField(auto_now_add=True)
```

**Key Requirement:** Checkout must be **atomic transaction**
```python
@transaction.atomic
def checkout(cart):
    # 1. Validate items in stock
    # 2. Create Order + OrderItems
    # 3. Decrease product stock
    # 4. Clear cart
    # All succeed or all fail
```

**Endpoints:**
- `GET /api/v1/cart/` (retrieve cart)
- `POST /api/v1/cart/items/` (add to cart)
- `PATCH /api/v1/cart/items/{id}/` (update quantity)
- `DELETE /api/v1/cart/items/{id}/` (remove item)
- `POST /api/v1/cart/checkout/` (create order, clear cart)

### 🟡 Phase 7: Order Management (NOT STARTED)

**Planned Models:**
```python
class Order(models.Model):
    id = UUIDField(primary_key=True)
    buyer = ForeignKey(User)
    seller = ForeignKey(DealerProfile)
    items = OneToManyField(OrderItem)
    total_price = DecimalField()
    status = CharField(choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('preparing', 'Preparing'),
        ('delivering', 'On Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ])
    delivery_address = CharField()
    delivery_location = PointField()  # PostGIS Point
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class OrderItem(models.Model):
    order = ForeignKey(Order)
    product = ForeignKey(Product)
    quantity = IntegerField()
    price = DecimalField()
    total = DecimalField()
```

**Endpoints:**
- `GET /api/v1/orders/` (list user's orders)
- `POST /api/v1/orders/` (create order)
- `GET /api/v1/orders/{id}/` (order details)
- `POST /api/v1/orders/{id}/cancel/` (cancel order)
- `POST /api/v1/orders/{id}/accept/` (dealer accept)
- `POST /api/v1/orders/{id}/complete/` (mark delivered)

### 🟡 Phase 8: Geolocation & Dealers (NOT STARTED)

**Planned Models:**
```python
class DealerProfile(models.Model):
    id = UUIDField(primary_key=True)
    user = OneToOneField(User, limit_choices_to={'role': 'dealer'})
    location = PointField()  # PostGIS Point
    coverage_radius_km = IntegerField(default=10)
    manufacturers = ManyToManyField(User)  # Carries products from
    rating = DecimalField(default=0)
    approved = BooleanField(default=False)
```

**Key Feature:** PostGIS-based nearby dealer search
```python
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance

nearby = DealerProfile.objects \
    .filter(location__distance_lte=(user_point, D(km=radius))) \
    .annotate(distance=Distance('location', user_point)) \
    .order_by('distance')
```

**Endpoints:**
- `GET /api/v1/dealers/` (list all)
- `POST /api/v1/dealers/nearby/` (PostGIS distance query)
- `GET /api/v1/dealers/{id}/` (profile)
- `PATCH /api/v1/dealers/{id}/` (update profile)

### 🟡 Phase 9: Push Notifications (NOT STARTED)

**Planned:**
- Firebase Cloud Messaging integration
- Notification model + API
- Celery task for async sending
- User device token management

**Endpoints:**
- `GET /api/v1/notifications/` (list)
- `POST /api/v1/notifications/{id}/read/` (mark read)
- `DELETE /api/v1/notifications/{id}/` (delete)

### 🟡 Phase 10: Analytics & Reporting (NOT STARTED)

**Planned Metrics:**
- Daily/monthly sales
- Top products
- User activity
- Geolocation heatmaps

---

## Module Descriptions

### apps/users/

**Purpose:** User authentication, profiles, role management

**Models:**
- `User` (AbstractBaseUser) - Custom user with phone + OTP auth
- `UserProfile` (extends User) - Additional user data
- `OTPVerification` - Track OTP attempts and expiry

**Key Methods:**
- `generate_otp()` - 6-digit code, 10-min expiry
- `verify_otp()` - Check code, rate limit attempts
- `rotate_tokens()` - Issue new refresh when expired

**Permissions:**
- `IsOwner` - Can only access own data
- `IsManufacturer` / `IsDealer` / `IsStoreOwner` - Role checks

### apps/products/

**Purpose:** Product catalog with categories, images, reviews

**Models:**
- `Category` - Hierarchical product categories
- `Product` - Main product with price, stock, units
- `ProductImage` - Multiple images per product
- `Review` - Customer reviews + ratings

**Queryset Optimizations:**
```python
Product.objects.select_related('category', 'manufacturer') \
              .prefetch_related('images', 'reviews')
```

**Filtering:**
- By category, manufacturer, price range
- Search by name, description
- Order by price, rating, created

### apps/orders/

**Purpose:** Order lifecycle from creation to delivery

**Models:**
- `Order` - Master order record
- `OrderItem` - Individual items in order
- `OrderStatusLog` - History of status changes

**Status Workflow:**
```
pending → accepted → preparing → delivering → delivered
   ↓________________________↓_____________↓_______________
                          cancelled
```

**Atomic Operations:**
- Checkout: Create order + decrease stock (all or nothing)
- Cancel: Refund stock + update status
- Complete: Update status + send notification

### apps/cart/

**Purpose:** Shopping cart management

**Models:**
- `Cart` - User's shopping cart
- `CartItem` - Individual products in cart

**Features:**
- Add/remove/update quantity
- Price snapshot (prevent price changes on checkout)
- Dealer selection (user picks dealer before checkout)
- Automatic cleanup (remove old carts)

### apps/dealers/

**Purpose:** Dealer profiles and location-based search

**Models:**
- `DealerProfile` - Business details + location
- `DealerRating` - Customer ratings per dealer

**PostGIS Integration:**
```python
# Find dealers within 10km
DealerProfile.objects \
    .filter(location__distance_lte=(point, D(km=10))) \
    .annotate(distance=Distance('location', point)) \
    .order_by('distance')
```

### apps/notifications/

**Purpose:** Push notifications via Firebase

**Models:**
- `Notification` - Notification record
- `NotificationLog` - Delivery logs

**Async Tasks:**
```python
# Send FCM notification asynchronously
send_fcm_notification.delay(user_id, title, body)
```

### apps/analytics/

**Purpose:** Business intelligence and reporting

**Metrics:**
- Sales per day/month
- Top products
- User activity heatmap
- Geolocation cluster analysis

**Celery Beat Scheduled Tasks:**
```python
# Daily at midnight: Aggregate sales
celery_beat schedule: {
    'aggregate-daily-sales': {
        'task': 'analytics.tasks.aggregate_sales',
        'schedule': crontab(hour=0, minute=0),
    }
}
```

---

## API Standards

### Response Format

All responses follow this standard:

**Success:**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Product Name",
    ...
  },
  "message": "Operation successful"
}
```

**List/Paginated:**
```json
{
  "success": true,
  "data": {
    "count": 150,
    "next": "http://api.example.com/api/v1/products/?page=2",
    "previous": null,
    "results": [...]
  },
  "message": "Retrieved successfully"
}
```

**Error (Validation):**
```json
{
  "success": false,
  "errors": {
    "email": ["Enter a valid email address"],
    "age": ["Ensure this value is greater than 18"]
  },
  "message": "Validation errors"
}
```

**Error (Permission/Server):**
```json
{
  "success": false,
  "message": "You do not have permission to perform this action",
  "errors": null
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | GET, PATCH successful |
| 201 | Created | POST successful |
| 204 | No Content | DELETE successful |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many | Rate limit exceeded |
| 500 | Server Error | Unexpected error |

### Filtering, Searching, Ordering

```bash
# Filter by category
GET /api/v1/products/?category=550e8400-e29b-41d4-a716-446655440000

# Search by name/description
GET /api/v1/products/?search=samsung

# Order by price (descending)
GET /api/v1/products/?ordering=-price

# Paginate (20 items/page default)
GET /api/v1/products/?page=2

# Combine
GET /api/v1/products/?category=uuid&search=phone&ordering=-price&page=1
```

### Rate Limiting

```
Anonymous users: 100 requests/hour
Authenticated users: 1000 requests/hour
```

On limit exceeded: HTTP 429 response

---

## Authentication & Security

### JWT Flow

```
1. User calls: POST /api/v1/auth/register/
   - Server sends OTP via SMS

2. User verifies: POST /api/v1/auth/verify-otp/
   - Server returns: {access: "...", refresh: "..."}
   - access: Valid 15 minutes
   - refresh: Valid 30 days

3. User makes API call with:
   Authorization: Bearer <access_token>

4. When access expires, user calls: POST /api/v1/auth/token/refresh/
   with: {refresh: <refresh_token>}
   - Server returns new access token
   - New refresh token issued
   - Old refresh token blacklisted

5. To logout: POST /api/v1/auth/logout/
   - Old refresh token blacklisted
   - User must login again
```

### Token Rotation

**Why:** Improve security by limiting token lifetime

**How:** On refresh, old token added to blacklist
```python
SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

**Result:** Need to store refresh token on client, update on each refresh

### Permission Classes

```python
# Role-based permissions
class IsManufacturer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'manufacturer'

class IsDealer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'dealer'

# Usage in ViewSet
class ProductViewSet(CombinedResponseMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsManufacturer]
```

### Security Settings

**Development:**
```python
DEBUG = True                          # Detailed error pages
SECURE_SSL_REDIRECT = False          # Allow plain HTTP
SESSION_COOKIE_SECURE = False        # Cookies over HTTP
CSRF_COOKIE_SECURE = False           # CSRF over HTTP
```

**Production:**
```python
DEBUG = False                        # No error details exposed
SECURE_SSL_REDIRECT = True           # Force HTTPS
SESSION_COOKIE_SECURE = True         # Cookies over HTTPS only
CSRF_COOKIE_SECURE = True            # CSRF over HTTPS only
SECURE_HSTS_SECONDS = 31536000      # HSTS for 1 year
```

---

## Configuration System

### Environment-Based Settings

```
settings/
├── base.py          # Shared (all envs)
├── development.py   # Overrides (DEBUG=True, SQLite)
└── production.py    # Overrides (security, PostgreSQL)
```

### Loading Settings

```python
# wsgi.py and asgi.py specify:
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

# development.py imports and extends base.py:
from .base import *

DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}
```

### Environment Variables

All sensitive values in `.env`:

```bash
# Copy .env.example to .env
cp .env.example .env

# Fill in your values
SECRET_KEY=<generate-new>
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
```

**Critical Variables:**
- `ENVIRONMENT` - development or production
- `SECRET_KEY` - Cryptographic key (change in prod!)
- `DEBUG` - Never True in production
- `ALLOWED_HOSTS` - Trusted domains
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Cache + message broker
- `JWT_*` - Token lifetimes
- `FCM_SERVER_KEY` - Push notifications
- `TWILIO_*` - SMS delivery

---

## Deployment

### Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt

# Run
python manage.py migrate
python manage.py runserver

# Access
http://localhost:8000/api/docs/
```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# View logs
docker-compose logs -f
```

**What Starts:**
- PostgreSQL (postgres:5432)
- Redis (redis:6379)
- Django (django:8000) via Gunicorn
- Celery Worker
- Celery Beat (scheduler)
- Nginx (nginx:80, nginx:443)

### Database Backup/Restore

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres tradelink_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres tradelink_db < backup.sql
```

### SSL/HTTPS

**Development:** Self-signed certificate (already in docker-compose)

**Production:**
```bash
# Generate Let's Encrypt certificate
./scripts/generate-ssl.sh yourdomain.com

# Auto-renewal via Certbot
certbot renew --noninteractive --agree-tos
```

---

## Development Workflow

### Creating a New Endpoint

**1. Create Model** (apps/products/models.py):
```python
class Product(models.Model):
    name = CharField(max_length=255)
    price = DecimalField(max_digits=10, decimal_places=2)
    # ... fields
```

**2. Create Serializer** (apps/products/serializers.py):
```python
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', ...]
```

**3. Create ViewSet** (apps/products/views.py):
```python
class ProductViewSet(CombinedResponseMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']
```

**4. Register URL** (apps/products/urls.py):
```python
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = router.urls
```

**5. Test Endpoint**:
```bash
curl http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer <token>"
```

### Adding Custom Action

```python
class ProductViewSet(...):
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        product = self.get_object()
        product.is_active = True
        product.save()
        
        return self.action_success(
            data=ProductSerializer(product).data,
            message='Product activated'
        )
```

### Writing Tests

```python
# tests.py
from django.test import TestCase
from rest_framework.test import APITestCase

class ProductAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.product = Product.objects.create(...)
    
    def test_list_products(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
```

### Running Tests

```bash
# All tests
python manage.py test

# Specific app
python manage.py test apps.products

# Specific class
python manage.py test apps.products.tests.ProductTestCase

# With coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Management Commands

```bash
# Create demo data
python manage.py create_demo_data

# Clear old data
python manage.py clear_old_data

# Send test notification
python manage.py send_test_notification {user_id}

# Check database
python manage.py dbshell
```

---

## Performance Considerations

### Database Optimization

```python
# Use select_related for ForeignKey
Product.objects.select_related('manufacturer', 'category')

# Use prefetch_related for reverse relations
Product.objects.prefetch_related('images', 'reviews')

# Index on frequently searched fields
class Product(models.Model):
    name = CharField(db_index=True)
    created_at = DateTimeField(db_index=True)
```

### Caching

```python
from django.core.cache import cache

# Cache expensive query
products = cache.get('all_products')
if not products:
    products = Product.objects.all()
    cache.set('all_products', products, 60*60)  # 1 hour
```

### Query Analysis

```bash
# See SQL queries in development
python manage.py debugsqlshell

# Or use Django Debug Toolbar
pip install django-debug-toolbar
```

### Pagination

Default: 20 items per page
```python
GET /api/v1/products/?page=1
GET /api/v1/products/?page=2
```

### Throttling

Rate limiting for abuse prevention:
```
Anonymous: 100 req/hour
Authenticated: 1000 req/hour
```

---

## Monitoring & Logging

### Log Levels

- **DEBUG:** Verbose, development only
- **INFO:** Normal operation events
- **WARNING:** Something unexpected
- **ERROR:** Significant problem
- **CRITICAL:** System is failing

### Sample Log Lines

```python
# In your views
import logging

logger = logging.getLogger(__name__)
logger.info(f"User {user_id} logged in")
logger.error(f"Database connection failed: {e}")
```

### Location of Logs

- **Local:** `./logs/django.log`
- **Docker:** Check `docker-compose logs django`
- **Production:** Monitor service logs (Sentry, DataDog, etc.)

### Sentry Integration

Connect to Sentry for error tracking:
```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production",
)
```

---

##

## Quick Reference

### Most Common Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate && pip install -r requirements/base.txt

# Develop
python manage.py runserver
python manage.py makemigrations
python manage.py migrate

# Test
python manage.py test
python manage.py test apps.products.tests

# Docker
docker-compose up -d
docker-compose logs -f django
docker-compose down

# Database
python manage.py dbshell
python manage.py dumpdata > backup.json
python manage.py loaddata backup.json
```

### Useful URLs

| URL | Purpose |
|-----|---------|
| /admin/ | Django admin panel |
| /api/docs/ | Swagger API docs |
| /api/redoc/ | ReDoc API docs |
| /api/schema/ | OpenAPI schema |
| /api/v1/auth/ | Authentication endpoints |
| /api/v1/products/ | Product catalog |
| /api/v1/orders/ | Order management |

### Email Support

For help with errors:
1. Check server logs: `python manage.py runserver`
2. Test with curl first
3. Check .env configuration
4. Review EXAMPLE_VIEWSET.md for patterns
5. Check DRF_CONFIGURATION.md for API details

---

## Summary

TradeLink is a production-grade B2B e-commerce platform backend built with Django 5, DRF, PostgreSQL+PostGIS, Redis, and Celery. Complete infrastructure, API standardization, and Docker orchestration are in place. Next phase is implementing user authentication and product catalog endpoints.

For questions, refer to:
- **Setup:** DEVELOPMENT_SETUP.md
- **API:** DRF_CONFIGURATION.md + EXAMPLE_VIEWSET.md
- **Testing:** API_TESTING_GUIDE.md
- **Deployment:** DOCKER.md

Good luck! 🚀
