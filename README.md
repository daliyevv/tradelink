# TradeLink Backend

A Django 5.x REST API backend for the TradeLink B2B mobile trading platform.

## Overview

TradeLink connects manufacturers, dealers, and store owners in a unified B2B marketplace. This backend provides:

- User management with role-based access (Manufacturer, Dealer, Store Owner)
- Product catalog and inventory management
- Order management with status tracking
- Shopping cart functionality
- Real-time location-based dealer discovery using PostGIS
- Push notifications via Firebase Cloud Messaging
- Async task processing with Celery

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15 + PostGIS (or SQLite for development)
- Redis 7+
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd tradelink
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements/base.txt
# For development:
pip install -r requirements/development.txt
# For production:
pip install -r requirements/production.txt
```

4. Create .env file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/v1/`

## Project Structure

```
tradelink/
├── config/
│   ├── settings/
│   │   ├── base.py          # Common settings
│   │   ├── development.py   # Development-specific
│   │   └── production.py    # Production-specific
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI application
│   └── asgi.py              # ASGI application (WebSocket support)
├── apps/
│   ├── users/               # User authentication and profiles
│   ├── products/            # Product catalog
│   ├── orders/              # Order management
│   ├── cart/                # Shopping cart
│   ├── dealers/             # Dealer profiles and management
│   ├── locations/           # Geolocation (PostGIS)
│   ├── notifications/       # Push notifications
│   └── analytics/           # Analytics and reporting
├── requirements/
│   ├── base.txt             # Core dependencies
│   └── production.txt       # Production dependencies
├── manage.py                # Django management script
└── .env.example             # Environment variables template
```

## Technology Stack

### Backend
- **Django 5.x** - Web framework
- **Django REST Framework** - API development
- **PostgreSQL + PostGIS** - Database with geospatial support
- **Redis** - Caching and message broker
- **Celery** - Async task processing
- **django-channels** - WebSocket support (optional)

### Authentication & Security
- **SimpleJWT** - JWT token authentication
- **django-cors-headers** - CORS configuration
- **Argon2** - Password hashing

### API & Documentation
- **drf-spectacular** - OpenAPI/Swagger documentation
- **django-filter** - Advanced filtering

### Additional Services
- **Firebase Cloud Messaging** - Push notifications
- **Google Maps API** - Map integration
- **Sentry** - Error tracking (optional)

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection string
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` - JWT token lifetime
- `FIREBASE_CREDENTIALS_PATH` - Path to Firebase Service Account JSON
- `FIREBASE_PROJECT_ID` - Firebase Project ID for Admin SDK
- `GOOGLE_MAPS_API_KEY` - Google Maps API key

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8
isort .
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Celery Tasks (Development)
```bash
# Terminal 1: Start Celery worker
celery -A config worker -l info

# Terminal 2: Start Celery beat (scheduled tasks)
celery -A config beat -l info
```

## Deployment

### Using Docker
```bash
docker-compose up -d
```

### Manual Deployment
1. Install production requirements: `pip install -r requirements/production.txt`
2. Set `ENVIRONMENT=production` in .env
3. Collect static files: `python manage.py collectstatic`
4. Run with Gunicorn: `gunicorn config.wsgi:application`
5. Run Celery worker: `celery -A config worker -l info`

### HTTPS & SSL
- Use Let's Encrypt for free SSL certificates
- Configure Nginx as reverse proxy
- Enable HSTS in production settings

## Features

### Phase 1 - MVP (6-8 weeks)
- [x] User registration with SMS OTP
- [x] Product CRUD operations
- [x] Shopping cart and checkout
- [x] Order creation and tracking
- [x] Nearby dealers discovery (PostGIS)
- [x] API documentation

### Phase 2 - Enhancement (4-6 weeks)
- [ ] FCM push notifications
- [ ] Real-time status updates (WebSocket)
- [ ] Orders analytics dashboard
- [ ] Image optimization (CDN)

### Phase 3 - Scale
- [ ] Multi-country support
- [ ] Multi-currency support
- [ ] Payment gateway integration
- [ ] Rating and review system
- [ ] B2B contract management

## Security

- All endpoints require JWT authentication
- Role-based access control (RBAC)
- HTTPS/SSL enforced in production
- CORS properly configured
- SQL injection prevention via ORM
- CSRF protection enabled
- Rate limiting on API endpoints
- Secure password hashing (Argon2)

## Performance

- Database query optimization (select_related, prefetch_related)
- Redis caching for frequent queries
- Async task processing with Celery
- PostGIS indexes for location queries
- Static file CDN support

## Support & Tips

### Troubleshooting

**"Module not found" error:**
```bash
pip install -r requirements/base.txt
```

**PostgreSQL connection issues:**
- Ensure PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format in .env
- Verify password and host/port

**Redis connection issues:**
- Ensure Redis is running: `redis-cli ping`
- Check REDIS_URL in .env

### Common Commands

```bash
# Create superuser
python manage.py createsuperuser

# Access Django shell
python manage.py shell

# Create backup
pg_dump -U postgres tradelink > backup.sql

# Restore backup
psql -U postgres tradelink < backup.sql
```

## Contributing

1. Create a feature branch: `git checkout -b feature/amazing-feature`
2. Commit changes: `git commit -m 'Add amazing feature'`
3. Push to branch: `git push origin feature/amazing-feature`
4. Open a Pull Request

## License

This project is proprietary and confidential.

## Contact

For questions or support, contact the development team.
