# TradeLink Backend Development Setup Guide

Quick start guide for setting up the TradeLink Django backend locally.

## Prerequisites

- Python 3.10+ installed
- PostgreSQL 15 with PostGIS extension (for production)
- Redis 7 (for caching and Celery)
- Git

## Step 1: Clone and Install Dependencies

```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd tradelink

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements/base.txt

# For development, install dev dependencies too
pip install -r requirements/development.txt
```

## Step 2: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
nano .env  # On Linux/Mac
# or
edit .env  # On Windows
```

**Minimal .env for local development:**

```
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-this
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
FCM_SERVER_KEY=dummy-for-dev
TWILIO_ACCOUNT_SID=dummy
TWILIO_AUTH_TOKEN=dummy
TWILIO_PHONE_NUMBER=+998901234567
```

## Step 3: Set Up Database

```bash
# Apply migrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser
# Follow prompts:
# Username: admin
# Email: admin@example.com
# Password: your-password

# Load initial data (optional)
python manage.py loaddata initial_data.json
```

## Step 4: Start Redis (for caching and Celery)

In a separate terminal:

```bash
# On Linux
redis-server

# On macOS
redis-server --port 6379

# On Windows (if installed)
redis-server.exe
```

## Step 5: Run Development Server

```bash
# In your main terminal (with venv activated)
python manage.py runserver
```

**Expected output:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

## Step 6: Test the API

Visit the Swagger documentation:
```
http://localhost:8000/api/docs/
```

Or test with curl:
```bash
# Get categories (public endpoint)
curl http://localhost:8000/api/v1/categories/

# Get products (requires authentication)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/products/
```

## Step 7: Run Celery (Optional, for async tasks)

In a separate terminal:

```bash
# Start Celery worker
celery -A config worker -l info

# In another terminal, start Celery Beat (scheduler)
celery -A config beat -l info
```

## Project Structure

```
tradelink/
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared settings
│   │   ├── development.py   # Dev-specific (DEBUG=True, SQLite)
│   │   └── production.py    # Prod-specific (security hardened)
│   ├── asgi.py              # ASGI config (for async)
│   └── wsgi.py              # WSGI config (traditional)
│
├── apps/
│   ├── users/               # User authentication, profiles
│   ├── products/            # Product catalog
│   ├── orders/              # Order processing
│   ├── cart/                # Shopping cart
│   ├── dealers/             # Dealer profiles
│   ├── locations/           # Geolocation
│   ├── notifications/       # Push notifications
│   └── analytics/           # Dashboard metrics
│
├── utils/
│   ├── exception_handler.py # Custom DRF exception handling
│   ├── responses.py         # Response mixins for ViewSets
│   ├── permissions.py       # Custom permission classes
│   ├── validators.py        # Field validators
│   └── pagination.py        # Custom pagination
│
├── static/                  # CSS, JS, images (collected by collectstatic)
├── media/                   # User uploads (product images, avatars)
├── logs/                    # Application logs
│
├── requirements/
│   ├── base.txt            # All environments
│   ├── development.txt     # Dev only (includes debug tools)
│   └── production.txt      # Prod only (includes Gunicorn)
│
├── manage.py               # Django CLI
├── docker-compose.yml      # Docker services (PostgreSQL, Redis, etc)
├── .env.example            # Environment variables template
└── README.md               # Project documentation
```

## Common Commands

```bash
# Database migrations
python manage.py makemigrations          # Create migration files
python manage.py migrate                 # Apply migrations
python manage.py migrate --zero app      # Rollback all migrations

# Admin panel
python manage.py createsuperuser         # Create admin user
python manage.py changepassword username # Change password

# Development data
python manage.py shell                   # Django Python shell
python manage.py dumpdata app > data.json # Export data
python manage.py loaddata data.json      # Import data

# Static files
python manage.py collectstatic           # Collect static for production
python manage.py findstatic filename     # Find static file location

# Testing
python manage.py test                    # Run all tests
python manage.py test app.tests.TestClass # Run specific test

# Debugging
python manage.py runserver 0.0.0.0:8000 # Accessible from other machines
python manage.py shell_plus              # Enhanced shell (requires django-extensions)

# Database
python manage.py dbshell                 # PostgreSQL/SQLite CLI
python manage.py sqlmigrate app 0002     # See SQL from migration
```

## Troubleshooting

### Port 8000 already in use
```bash
# Use different port
python manage.py runserver 8001

# Or find and kill process
lsof -i :8000      # Find process ID
kill -9 <PID>      # Kill it
```

### Database error: "no such table"
```bash
# Run migrations
python manage.py migrate
```

### Redis connection refused
```bash
# Make sure Redis is running
redis-server

# Or check if running on Windows:
redis-cli ping  # Should return PONG
```

### "ModuleNotFoundError" upon import
```bash
# Ensure venv is activated and dependencies installed
source venv/bin/activate
pip install -r requirements/base.txt
```

### Permission denied on manage.py (Linux/Mac)
```bash
chmod +x manage.py
```

### Import errors from apps
```bash
# Ensure PYTHONPATH includes project directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root
pwd  # Should be /path/to/tradelink
python manage.py runserver
```

## API Endpoints

After starting the server, explore endpoints:

### Documentation
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### Authentication
- **Register**: `POST /api/v1/auth/register/`
- **Verify OTP**: `POST /api/v1/auth/verify-otp/`
- **Refresh Token**: `POST /api/v1/auth/token/refresh/`
- **Logout**: `POST /api/v1/auth/logout/`

### Products
- **List**: `GET /api/v1/products/`
- **Search**: `GET /api/v1/products/?search=samsung`
- **Filter**: `GET /api/v1/products/?category=uuid`
- **Create**: `POST /api/v1/products/`
- **Detail**: `GET /api/v1/products/{id}/`
- **Update**: `PATCH /api/v1/products/{id}/`
- **Delete**: `DELETE /api/v1/products/{id}/`

### Orders
- **List My Orders**: `GET /api/v1/orders/`
- **Create Order**: `POST /api/v1/orders/`
- **Order Detail**: `GET /api/v1/orders/{id}/`
- **Cancel Order**: `POST /api/v1/orders/{id}/cancel/`

### Cart
- **Get Cart**: `GET /api/v1/cart/`
- **Add Item**: `POST /api/v1/cart/items/`
- **Update Quantity**: `PATCH /api/v1/cart/items/{id}/`
- **Remove Item**: `DELETE /api/v1/cart/items/{id}/`
- **Checkout**: `POST /api/v1/cart/checkout/`

More endpoints available in Swagger UI documentation.

## Response Format

All API responses follow this format:

**Success Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-here",
    "name": "Product Name",
    ...
  },
  "message": "Operation successful"
}
```

**List Response:**
```json
{
  "success": true,
  "data": {
    "count": 100,
    "next": "http://localhost:8000/api/v1/products/?page=2",
    "previous": null,
    "results": [...]
  },
  "message": "Retrieved successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "name": ["This field is required"],
    "price": ["Enter a valid decimal number"]
  }
}
```

## Authentication

API uses JWT (JSON Web Tokens):

1. User logs in → receives `access` token (15 min) and `refresh` token (30 days)
2. Use `access` token in `Authorization: Bearer <token>` header
3. When `access` expires, use `refresh` to get new `access` token
4. Tokens rotate on refresh for security

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+998901234567", "otp": "123456"}'

# Use token
curl http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."}'
```

## Docker Development (Alternative)

Instead of manual setup, use Docker Compose:

```bash
# Start all services (Django, PostgreSQL, Redis, Nginx)
docker-compose up -d

# View logs
docker-compose logs -f django

# Run migrations inside container
docker-compose exec django python manage.py migrate

# Create superuser inside container
docker-compose exec django python manage.py createsuperuser

# Stop services
docker-compose down
```

**Access:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/api/docs/
- Admin Panel: http://localhost:8000/admin

## Next Steps

1. ✅ Setup is complete
2. 📖 Read [DRF_CONFIGURATION.md](DRF_CONFIGURATION.md) for API details
3. 📖 Check [EXAMPLE_VIEWSET.md](EXAMPLE_VIEWSET.md) for ViewSet patterns
4. 📖 Review [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md) for testing
5. 🔨 Start implementing endpoints for your use case
6. ✅ Run tests: `python manage.py test`
7. 🚀 Deploy to production (see [DOCKER.md](DOCKER.md))

## Support

For issues:

1. Check Django logs in console
2. Check database: `python manage.py dbshell`
3. Test with curl or Postman first
4. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) (if exists)
5. Review code in [EXAMPLE_VIEWSET.md](EXAMPLE_VIEWSET.md)

Good luck! 🚀
