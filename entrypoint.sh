#!/bin/bash
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}TradeLink - Starting application...${NC}"

# Function to check if database is ready
wait_for_db() {
    echo -e "${YELLOW}Waiting for PostgreSQL database to be ready...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if pg_isready -h ${DB_HOST:-db} -U ${DB_USER:-postgres} -d ${DB_NAME:-tradelink} 2>/dev/null; then
            echo -e "${GREEN}Database is ready!${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts: Waiting for database..."
        sleep 2
    done
    
    echo -e "${RED}Failed to connect to database after $max_attempts attempts${NC}"
    return 1
}

# Function to check if Redis is ready
wait_for_redis() {
    echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
    local max_attempts=10
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if redis-cli -h ${REDIS_HOST:-redis} ping >/dev/null 2>&1; then
            echo -e "${GREEN}Redis is ready!${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts: Waiting for Redis..."
        sleep 1
    done
    
    echo -e "${YELLOW}Warning: Could not connect to Redis after $max_attempts attempts${NC}"
    return 0  # Don't fail on Redis, as it's optional for some deployments
}

# Wait for dependencies
wait_for_db || exit 1
wait_for_redis

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py migrate --noinput

# Collect static files (in production)
if [ "${ENVIRONMENT}" = "production" ]; then
    echo -e "${YELLOW}Collecting static files...${NC}"
    python manage.py collectstatic --noinput
fi

# Create superuser if it doesn't exist and credentials are provided
if [ -n "${SUPERUSER_USERNAME}" ] && [ -n "${SUPERUSER_PASSWORD}" ] && [ -n "${SUPERUSER_EMAIL}" ]; then
    echo -e "${YELLOW}Checking for superuser...${NC}"
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${SUPERUSER_USERNAME}').exists():
    User.objects.create_superuser(
        username='${SUPERUSER_USERNAME}',
        email='${SUPERUSER_EMAIL}',
        password='${SUPERUSER_PASSWORD}'
    )
    print(f"Superuser '${SUPERUSER_USERNAME}' created successfully!")
else:
    print(f"Superuser '${SUPERUSER_USERNAME}' already exists.")
END
fi

# Load initial data if fixtures exist
if [ -f "/app/fixtures/initial_data.json" ]; then
    echo -e "${YELLOW}Loading initial fixtures...${NC}"
    python manage.py loaddata /app/fixtures/initial_data.json
fi

echo -e "${GREEN}Application startup complete!${NC}"
echo -e "${GREEN}Starting gunicorn...${NC}"

# Start the application with gunicorn (or override with docker command)
exec "$@"
