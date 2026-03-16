# Docker Deployment Guide for TradeLink

## Quick Start

### Development Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd tradelink

# 2. Create environment file
cp .env.docker .env

# 3. Start services
docker-compose up -d

# 4. Access the application
# Web: http://localhost:8000
# API Docs: http://localhost:8000/api/docs/
# pgAdmin: http://localhost:5050
```

### Production Setup

```bash
# 1. Create production environment file
cp .env.production.example .env

# 2. Configure your environment variables
nano .env

# 3. Set up SSL certificates
./scripts/setup-ssl.sh tradelink.uz admin@tradelink.uz

# 4. Start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. Check health
./scripts/docker-helper.sh health
```

## Services Overview

### PostgreSQL Database
- **Image**: postgis/postgis:15-3.4
- **Port**: 5432
- **Features**: PostGIS for geolocation
- **Volume**: postgres_data (persistent)

### Redis
- **Image**: redis:7-alpine
- **Port**: 6379
- **Purpose**: Cache, message broker, session storage
- **Volume**: redis_data (persistent)

### Django Web Application
- **Image**: Built from Dockerfile
- **Port**: 8000
- **WSGI**: Gunicorn (4 workers)
- **ASGI**: Daphne (optional, for WebSocket)
- **Healthcheck**: API docs endpoint

### Celery Worker
- **Image**: Built from Dockerfile
- **Purpose**: Async task processing (notifications, emails, etc.)
- **Concurrency**: 4 processes
- **Broker**: Redis
- **Result Backend**: Redis

### Celery Beat
- **Image**: Built from Dockerfile
- **Purpose**: Scheduled task execution
- **Scheduler**: Django ORM database scheduler
- **One instance**: Must run only once

### Nginx Reverse Proxy
- **Image**: nginx:alpine
- **Port**: 80 (HTTP), 443 (HTTPS)
- **Purpose**: Reverse proxy, static file serving, SSL termination
- **Config**: nginx/nginx.conf

## Docker Helper Script

The `scripts/docker-helper.sh` provides convenient commands:

```bash
# Start services
./scripts/docker-helper.sh up
./scripts/docker-helper.sh prod-up

# Stop services
./scripts/docker-helper.sh down

# View logs
./scripts/docker-helper.sh logs
./scripts/docker-helper.sh logs-web
./scripts/docker-helper.sh logs-celery

# Run commands
./scripts/docker-helper.sh migrate
./scripts/docker-helper.sh createsuperuser
./scripts/docker-helper.sh shell

# Maintenance
./scripts/docker-helper.sh rebuild
./scripts/docker-helper.sh health
./scripts/docker-helper.sh clean  # WARNING: Deletes all data
```

## Environment Variables

### Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| ENVIRONMENT | development | Environment: development, production |
| DEBUG | False | Django debug mode |
| SECRET_KEY | - | Django secret key (required in production) |
| DATABASE_URL | - | PostgreSQL connection string |
| REDIS_URL | - | Redis connection string |
| ALLOWED_HOSTS | localhost | Comma-separated allowed hosts |
| JWT_ACCESS_TOKEN_LIFETIME_MINUTES | 15 | JWT access token lifetime |
| FIREBASE_CREDENTIALS_PATH | - | Path to Firebase Service Account JSON |
| FIREBASE_PROJECT_ID | - | Firebase Project ID |

See `.env.example` and `.env.production.example` for complete lists.

## SSL/TLS Configuration

### Development
- Uses self-signed certificates (auto-generated)
- HTTP only via Nginx

### Production with Let's Encrypt

```bash
# Method 1: Using Certbot standalone
certbot certonly --standalone -d tradelink.uz -d www.tradelink.uz --agree-tos -m admin@tradelink.uz

# Copy certificates to nginx/ssl/
cp /etc/letsencrypt/live/tradelink.uz/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/tradelink.uz/privkey.pem nginx/ssl/key.pem

# Update nginx.conf to use SSL (uncomment HTTPS section)
# Restart Nginx
docker-compose restart nginx
```

### Automatic Renewal
Uncomment the Certbot service in `docker-compose.yml` for automatic certificate renewal.

## Database Operations

### Create Database Dump
```bash
docker-compose exec db pg_dump -U postgres tradelink > backup.sql
```

### Restore Database
```bash
docker-compose exec -T db psql -U postgres tradelink < backup.sql
```

### Database Shell
```bash
docker-compose exec db psql -U postgres -d tradelink
```

## Monitoring and Logs

### View Service Logs
```bash
docker-compose logs -f web      # Django
docker-compose logs -f celery   # Celery worker
docker-compose logs -f db       # PostgreSQL
docker-compose logs -f redis    # Redis
docker-compose logs -f nginx    # Nginx
```

### Check Logs File
Production logs are typically in `/var/log/tradelink/` (as configured in production.py)

## Performance Tuning

### Gunicorn Workers
Adjust in `docker-compose.yml`:
```bash
command: gunicorn config.wsgi:application --workers 8 --timeout 120
```

**Formula**: workers = (2 × CPU_count) + 1
- For 4 CPU system: (2 × 4) + 1 = 9 workers

### Celery Concurrency
Adjust in `docker-compose.yml`:
```bash
command: celery -A config worker -l info --concurrency=8
```

### Redis Memory
Adjust client configuration in `docker-compose.yml`

## Troubleshooting

### Database Connection Issues
```bash
# Check if DB is running
docker-compose ps db

# Check logs
docker-compose logs db

# Test connection
docker-compose exec web python manage.py dbshell
```

### Service Not Starting
```bash
# Check logs
docker-compose logs [service-name]

# Rebuild images
docker-compose build --no-cache

# Restart service
docker-compose restart [service-name]
```

### Permission Issues
```bash
# Check file permissions
ls -la nginx/

# Fix permissions
chmod +x entrypoint.sh
chmod +x scripts/*.sh
```

### Storage Issues
```bash
# Check disk usage
docker system df

# Clean up unused resources
docker system prune
docker volume prune
```

## Security Considerations

1. **Change Default Credentials**
   - Database password
   - Redis password
   - Superuser credentials

2. **Environment Variables**
   - Never commit `.env` to git
   - Use `.env.example` as template
   - Rotate SECRET_KEY regularly

3. **SSL/TLS**
   - Use HTTPS in production
   - Configure HSTS headers
   - Let's Encrypt for free certificates

4. **Database**
   - Regular backups
   - Restrict network access
   - Use strong passwords

5. **Docker**
   - Keep images updated
   - Use specific version tags (not 'latest')
   - Run containers as non-root

## Scaling

### Multiple Gunicorn Workers
Increase workers in docker-compose.yml:
```yaml
command: gunicorn config.wsgi:application --workers 8
```

### Celery Scale
Run multiple Celery workers (requires load balancing):
```bash
docker-compose up -d --scale celery=3
```

### Load Balancing
Add HAProxy or similar in front of Nginx for multiple instances.

## CI/CD Integration

### GitHub Actions Example
See `.github/workflows/` for automated deployment examples.

### Manual Deployment
```bash
docker-compose pull
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Support & Debugging

### Get Debug Information
```bash
docker-compose ps
docker-compose logs --tail=100 web
docker-compose exec web env | grep ENVIRONMENT
```

### Update Documentation
Keep this guide updated as deployment practices evolve.

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Nginx Documentation](https://nginx.org/docs/)
- [Celery Documentation](https://docs.celeryproject.io/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
