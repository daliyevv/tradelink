# TradeLink API - Deployment Guide

Complete step-by-step instructions for deploying TradeLink API to production.

---

## Table of Contents

1. [Server Setup](#server-setup)
2. [Application Setup](#application-setup)
3. [Nginx Configuration](#nginx-configuration)
4. [SSL/HTTPS Setup](#ssl-https-setup)
5. [Systemd Services](#systemd-services)
6. [Database & Cache](#database--cache)
7. [Updates & Maintenance](#updates--maintenance)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)

---

## Server Setup

### Prerequisites

- Ubuntu 20.04+ or Debian 11+
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Nginx 1.20+
- 2GB RAM (minimum), 4GB+ recommended

### Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    supervisor \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    build-essential \
    libpq-dev \
    libssl-dev

# Create application user
sudo useradd -m -s /bin/bash tradelink
sudo usermod -aG sudo tradelink
```

### Clone Repository

```bash
cd /home/tradelink
sudo -u tradelink git clone https://github.com/yourusername/tradelink.git
cd tradelink
sudo -u tradelink mkdir -p logs media static
```

---

## Application Setup

### Create Virtual Environment

```bash
cd /home/tradelink/tradelink
sudo -u tradelink python3.11 -m venv venv
sudo -u tradelink venv/bin/pip install --upgrade pip setuptools wheel
sudo -u tradelink venv/bin/pip install -r requirements/production.txt
```

### Environment Variables

```bash
# Create .env file
sudo -u tradelink nano /home/tradelink/tradelink/.env

# Add the following:
SECRET_KEY=your-very-long-random-secret-key-here-min-50-chars
DEBUG=False
ALLOWED_HOSTS=azizdali.uz,www.azizdali.uz,api.azizdali.uz

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tradelink_db
DB_USER=tradelink_user
DB_PASSWORD=your-secure-database-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Firebase Admin SDK (Push Notifications - HTTP v1 API)
FIREBASE_CREDENTIALS_PATH=/home/tradelink/tradelink/firebase-credentials.json
FIREBASE_PROJECT_ID=your-firebase-project-id

# Google Maps & SMS
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
SMS_PROVIDER=eskiz
SMS_API_KEY=your-sms-api-key

# Monitoring
SENTRY_DSN=your-sentry-dsn

# AWS/S3 (if using)
USE_S3=False
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_STORAGE_BUCKET_NAME=...

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### PostgreSQL Setup

```bash
# Login as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE tradelink_db;
CREATE USER tradelink_user WITH PASSWORD 'your-secure-password';
ALTER ROLE tradelink_user SET client_encoding TO 'utf8';
ALTER ROLE tradelink_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tradelink_user SET default_transaction_deferrable TO on;
ALTER ROLE tradelink_user SET default_transaction_level TO 'read committed';
ALTER ROLE tradelink_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tradelink_db TO tradelink_user;
\q

# Run migrations
cd /home/tradelink/tradelink
sudo -u tradelink venv/bin/python manage.py migrate --settings=config.settings.production

# Create superuser
sudo -u tradelink venv/bin/python manage.py createsuperuser --settings=config.settings.production

# Collect static files
sudo -u tradelink venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production

# Seed demo data (optional)
sudo -u tradelink venv/bin/python manage.py seed_data --settings=config.settings.production

# Run health check
sudo -u tradelink venv/bin/python manage.py health_check --settings=config.settings.production
```

### Redis Setup

```bash
# Enable and start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Test Redis connection
redis-cli ping
# Output: PONG
```

### Firebase Admin SDK Setup (Push Notifications)

Firebase Admin SDK requires a Service Account JSON file for authentication via HTTP v1 API.

#### 1. Generate Firebase Service Account Key

```bash
# 1. Go to: https://console.firebase.google.com/
# 2. Select your project
# 3. Go to Project Settings > Service Accounts tab
# 4. Click "Generate New Private Key"
# 5. A JSON file will be downloaded
# 6. Copy it to your server
```

#### 2. Place Credentials File

```bash
# Copy the downloaded firebase-credentials.json to the server
scp firebase-credentials.json user@server:/home/tradelink/tradelink/

# Set proper permissions
sudo chown tradelink:tradelink /home/tradelink/tradelink/firebase-credentials.json
sudo chmod 600 /home/tradelink/tradelink/firebase-credentials.json

# Verify it's NOT in git (checked in .gitignore)
cat /home/tradelink/tradelink/.gitignore | grep firebase-credentials.json
```

#### 3. Update .env with Firebase Configuration

```bash
sudo nano /home/tradelink/tradelink/.env

# Add:
FIREBASE_CREDENTIALS_PATH=/home/tradelink/tradelink/firebase-credentials.json
FIREBASE_PROJECT_ID=your-firebase-project-id
```

Get your Firebase Project ID from:
- Firebase Console > Project Settings > General tab
- Format: `my-project-123456`

#### 4. Install Firebase Admin SDK

This is already in `requirements/base.txt`:
```bash
firebase-admin>=6.0
```

It will be installed when you run:
```bash
pip install -r requirements/production.txt
```

#### 5. Verify Firebase Connection

```bash
# The health_check command now includes Firebase validation
sudo -u tradelink venv/bin/python manage.py health_check --settings=config.settings.production
```

Expected output:
```
✓ Database connection: OK
✓ Redis connection: OK
✓ Firebase initialization: OK
✓ Environment variables: OK
✓ Media directory: OK
```

---

## Nginx Configuration

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/tradelink
```

**Add the following configuration:**

```nginx
# Upstream gunicorn
upstream gunicorn {
    server unix:/home/tradelink/tradelink/gunicorn.sock fail_timeout=0;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name azizdali.uz www.azizdali.uz api.azizdali.uz;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name azizdali.uz www.azizdali.uz api.azizdali.uz;
    
    # SSL certificates (certbot generated)
    ssl_certificate /etc/letsencrypt/live/azizdali.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/azizdali.uz/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /home/tradelink/tradelink/logs/nginx_access.log;
    error_log /home/tradelink/tradelink/logs/nginx_error.log;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
    
    # Client upload size
    client_max_body_size 100M;
    
    # Static files
    location /static/ {
        alias /home/tradelink/tradelink/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /home/tradelink/tradelink/media/;
        expires 7d;
    }
    
    # Proxy to gunicorn
    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Health check endpoint (no logging)
    location /health/ {
        proxy_pass http://gunicorn;
        access_log off;
    }
}
```

### Enable Nginx Configuration

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/tradelink /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Enable Nginx auto-start
sudo systemctl enable nginx
```

---

## SSL/HTTPS Setup

### Install SSL Certificate with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (before Nginx is fully configured)
sudo certbot certonly --standalone -d azizdali.uz -d www.azizdali.uz -d api.azizdali.uz \

# Auto-renewal
sudo certbot renew --dry-run

# Check renewal status
sudo systemctl status certbot.timer
sudo systemctl enable certbot.timer
```

### Certificate Renewal Cron Job (Alternative)

```bash
# Add to crontab
sudo crontab -e

# Add line:
0 3 * * * /usr/bin/certbot renew --quiet && /usr/sbin/systemctl reload nginx
```

---

## Systemd Services

### Gunicorn Service

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

**Add the following:**

```ini
[Unit]
Description=TradeLink Gunicorn Application Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=tradelink
Group=www-data
WorkingDirectory=/home/tradelink/tradelink

# Python virtual environment
Environment="PATH=/home/tradelink/tradelink/venv/bin"
EnvironmentFile=/home/tradelink/tradelink/.env

# Gunicorn configuration
ExecStart=/home/tradelink/tradelink/venv/bin/gunicorn \
    --workers=4 \
    --worker-class=gthread \
    --threads=2 \
    --bind=unix:/home/tradelink/tradelink/gunicorn.sock \
    --timeout=120 \
    --access-logfile=/home/tradelink/tradelink/logs/gunicorn_access.log \
    --error-logfile=/home/tradelink/tradelink/logs/gunicorn_error.log \
    --log-level=info \
    config.wsgi:application

# Restart policy
Restart=on-failure
RestartSec=5s

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

### Celery Worker Service

```bash
sudo nano /etc/systemd/system/celery.service
```

**Add the following:**

```ini
[Unit]
Description=TradeLink Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=tradelink
Group=www-data
WorkingDirectory=/home/tradelink/tradelink

# Python virtual environment
Environment="PATH=/home/tradelink/tradelink/venv/bin"
EnvironmentFile=/home/tradelink/tradelink/.env

# Celery configuration
ExecStart=/home/tradelink/tradelink/venv/bin/celery -A celery_app worker \
    --loglevel=info \
    --logfile=/home/tradelink/tradelink/logs/celery_worker.log \
    --pidfile=/var/run/celery_worker.pid \
    --concurrency=4 \
    --max-tasks-per-child=1000

# Restart policy
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### Celery Beat Service (for scheduled tasks)

```bash
sudo nano /etc/systemd/system/celery-beat.service
```

**Add the following:**

```ini
[Unit]
Description=TradeLink Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=tradelink
Group=www-data
WorkingDirectory=/home/tradelink/tradelink

# Python virtual environment
Environment="PATH=/home/tradelink/tradelink/venv/bin"
EnvironmentFile=/home/tradelink/tradelink/.env

# Celery beat configuration
ExecStart=/home/tradelink/tradelink/venv/bin/celery -A celery_app beat \
    --loglevel=info \
    --logfile=/home/tradelink/tradelink/logs/celery_beat.log \
    --pidfile=/var/run/celery_beat.pid \
    --scheduler=django_celery_beat.schedulers:DatabaseScheduler

# Restart policy
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services on boot
sudo systemctl enable gunicorn celery celery-beat

# Start services
sudo systemctl start gunicorn celery celery-beat

# Check status
sudo systemctl status gunicorn
sudo systemctl status celery
sudo systemctl status celery-beat

# View logs
sudo journalctl -u gunicorn -n 50 -f
sudo journalctl -u celery -n 50 -f
```

---

## Database & Cache

### PostgreSQL Backup

```bash
# Daily backup script
sudo nano /usr/local/bin/backup_db.sh
```

**Add the following:**

```bash
#!/bin/bash
BACKUP_DIR="/home/tradelink/backups"
DB_NAME="tradelink_db"
DB_USER="tradelink_user"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/tradelink_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Database backed up: $BACKUP_DIR/tradelink_$DATE.sql.gz"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup_db.sh

# Add to crontab
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup_db.sh
```

### Redis Persistence

```bash
# Configure Redis persistence in /etc/redis/redis.conf
sudo nano /etc/redis/redis.conf

# Uncomment and set:
#save 900 1
#save 300 10
#save 60 10000

# Or use append-only mode:
#appendonly yes

# Restart Redis
sudo systemctl restart redis-server
```

---

## Updates & Maintenance

### Update Application

```bash
cd /home/tradelink/tradelink

# Stop services
sudo systemctl stop gunicorn celery celery-beat

# Pull latest code
git fetch origin
git pull origin main

# Update dependencies
venv/bin/pip install -r requirements/production.txt

# Run migrations
venv/bin/python manage.py migrate --settings=config.settings.production

# Collect static files
venv/bin/python manage.py collectstatic --noinput --settings=config.settings.production

# Restart services
sudo systemctl start gunicorn celery celery-beat

# Verify health
venv/bin/python manage.py health_check --settings=config.settings.production
```

### Database Maintenance

```bash
# Analyze database performance
sudo -u postgres vacuumdb -d tradelink_db -a -z

# Check database size
sudo -u postgres psql -d tradelink_db -c "SELECT pg_size_pretty(pg_database_size('tradelink_db'));"

# Monitor connections
sudo -u postgres psql -d tradelink_db -c "SELECT datname, usename, count(*) FROM pg_stat_activity GROUP BY datname, usename;"
```

---

## Monitoring & Logs

### Log Files Location

```
/home/tradelink/tradelink/logs/
├── gunicorn_access.log
├── gunicorn_error.log
├── nginx_access.log
├── nginx_error.log
├── celery_worker.log
├── celery_beat.log
└── django_debug.log
```

### View Logs

```bash
# Gunicorn
sudo tail -f /home/tradelink/tradelink/logs/gunicorn_error.log

# Celery
sudo tail -f /home/tradelink/tradelink/logs/celery_worker.log

# Nginx
sudo tail -f /var/log/nginx/error.log

# System journal
sudo journalctl -u gunicorn -f
```

### Monitoring with Supervisor (Optional)

```bash
sudo apt install supervisor

sudo nano /etc/supervisor/conf.d/tradelink.conf
```

**Add:**

```ini
[program:gunicorn]
directory=/home/tradelink/tradelink
command=/home/tradelink/tradelink/venv/bin/gunicorn -c config.gunicorn_config config.wsgi:application
user=tradelink
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/tradelink/tradelink/logs/gunicorn.log
```

---

## Troubleshooting

### Gunicorn Issues

```bash
# Check gunicorn socket
ls -la /home/tradelink/tradelink/gunicorn.sock

# Permission error?
sudo chown tradelink:www-data /home/tradelink/tradelink/gunicorn.sock

# Restart both nginx and gunicorn
sudo systemctl restart gunicorn nginx
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
sudo -u tradelink psql -h localhost -U tradelink_user -d tradelink_db

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli ping

# Check Redis configuration
sudo systemctl status redis-server

# View Redis logs
sudo journalctl -u redis-server -f
```

### Firebase Push Notifications Issues

#### Issue: Firebase credentials file not found

```bash
# Check file exists and permissions
ls -la /home/tradelink/tradelink/firebase-credentials.json

# Fix permissions if needed
sudo chown tradelink:tradelink /home/tradelink/tradelink/firebase-credentials.json
sudo chmod 600 /home/tradelink/tradelink/firebase-credentials.json

# Verify JSON format
cat /home/tradelink/tradelink/firebase-credentials.json | python -m json.tool
```

#### Issue: Push notification failing (invalid token)

```bash
# Check FCM tokens in database
sudo -u tradelink venv/bin/python manage.py shell --settings=config.settings.production

# In Django shell:
>>> from apps.notifications.models import FCMToken
>>> FCMToken.objects.filter(is_active=True).count()
>>> FCMToken.objects.filter(is_active=False).count()

# Clear old/invalid tokens
>>> FCMToken.objects.filter(is_active=False).delete()
```

#### Issue: Firebase initialization error

```bash
# Check logs
tail -f /home/tradelink/tradelink/logs/celery.log
tail -f /home/tradelink/tradelink/logs/gunicorn.log

# Test Firebase connection manually
cd /home/tradelink/tradelink
sudo -u tradelink venv/bin/python - <<'EOF'
import firebase_admin
from firebase_admin import credentials
import os

cred_path = '/home/tradelink/tradelink/firebase-credentials.json'
if os.path.exists(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
        app = firebase_admin.initialize_app(cred)
        print("✓ Firebase initialized successfully")
    except Exception as e:
        print(f"✗ Firebase error: {e}")
else:
    print(f"✗ Credentials file not found: {cred_path}")
EOF
```

### Static Files Not Loading

```bash
# Collect static files again
cd /home/tradelink/tradelink
venv/bin/python manage.py collectstatic --noinput --clear --settings=config.settings.production

# Fix permissions
sudo chown -R tradelink:www-data /home/tradelink/tradelink/static

# Reload Nginx
sudo systemctl reload nginx
```

### High Memory Usage

```bash
# Check process memory
ps aux | grep gunicorn | grep -v grep

# Reduce gunicorn workers in systemd service
# Change: --workers=4 to --workers=2

# Reduce Celery concurrency
# Change: --concurrency=4 to --concurrency=2
```

### Performance Optimization

```bash
# 1. Enable caching
# Redis already configured in settings

# 2. Use CDN for static files
# Configure AWS CloudFront or similar in settings.py

# 3. Database query optimization
# Run: python manage.py debug_toolbar (development only)

# 4. Monitor with:
sudo systemctl status gunicorn
redis-cli info stats
sudo -u postgres psql -d tradelink_db -c "SELECT * FROM pg_stat_statements LIMIT 10;"
```

---

## Checklist Before Launch

- [ ] SSL certificate installed and working
- [ ] Database backups automated
- [ ] Redis is running and persistent
- [ ] All services start on reboot
- [ ] Static files collected
- [ ] Media directory has proper permissions
- [ ] Health check passes: `python manage.py health_check`
- [ ] Logs are being written to files
- [ ] Nginx configured with security headers
- [ ] Database indexes created
- [ ] Admin interface accessible
- [ ] API endpoints responding
- [ ] Email sending working
- [ ] Celery tasks processing

---

## Quick Reference

```bash
# Start all services
sudo systemctl start gunicorn celery celery-beat nginx

# Stop all services
sudo systemctl stop gunicorn celery celery-beat nginx

# Restart all services
sudo systemctl restart gunicorn celery celery-beat nginx

# View all services
sudo systemctl status gunicorn celery celery-beat nginx

# Run health check
cd /home/tradelink/tradelink
DJANGO_SETTINGS_MODULE=config.settings.production venv/bin/python manage.py health_check

# Update application
cd /home/tradelink/tradelink && git pull origin main && venv/bin/python manage.py migrate && sudo systemctl restart gunicorn
```

---

**For support or issues, contact: admin@azizdali.uz**
