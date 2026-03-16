#!/bin/bash

# TradeLink Docker Compose Helper Script
# Provides convenient commands for common Docker operations

set -e

DOCKER_COMPOSE_CMD="docker-compose"
PROJECT_NAME="tradelink"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Help function
show_help() {
    cat << EOF
TradeLink Docker Helper Script

Usage: ./scripts/docker-helper.sh [COMMAND] [OPTIONS]

Commands:
    up              Start all services (development mode)
    down            Stop all services
    prod-up         Start services in production mode
    prod-down       Stop production services
    logs            View logs from all services
    logs-web        View Django app logs
    logs-celery     View Celery worker logs
    logs-db         View PostgreSQL logs
    shell           Open Django shell
    migrate         Run database migrations
    createsuperuser Create a new superuser
    collectstatic   Collect static files
    test            Run tests
    clean           Clean up volumes and containers (⚠️ WARNING: deletes data)
    rebuild         Rebuild Docker images
    push            Push built images to registry
    health          Check health of all services
    help            Show this help message

Examples:
    ./scripts/docker-helper.sh up
    ./scripts/docker-helper.sh logs-web
    ./scripts/docker-helper.sh shell
    ./scripts/docker-helper.sh migrate
EOF
}

# Function to run Django management command
run_django_cmd() {
    $DOCKER_COMPOSE_CMD exec -T web python manage.py "$@"
}

# Function to check service health
check_health() {
    echo -e "${YELLOW}Checking service health...${NC}"
    
    local services=("db" "redis" "web")
    
    for service in "${services[@]}"; do
        if $DOCKER_COMPOSE_CMD exec -T "$service" sh -c 'exit 0' 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $service is running"
        else
            echo -e "${RED}✗${NC} $service is not running"
        fi
    done
}

# Parse command
case "${1:-help}" in
    up)
        echo -e "${YELLOW}Starting services in ${GREEN}development${YELLOW} mode...${NC}"
        $DOCKER_COMPOSE_CMD up -d
        echo -e "${GREEN}Services started!${NC}"
        echo "Web: http://localhost:8000"
        echo "Docs: http://localhost:8000/api/docs/"
        echo "pgAdmin: http://localhost:5050"
        ;;
    
    down)
        echo -e "${YELLOW}Stopping all services...${NC}"
        $DOCKER_COMPOSE_CMD down
        echo -e "${GREEN}Services stopped!${NC}"
        ;;
    
    prod-up)
        echo -e "${YELLOW}Starting services in ${RED}production${YELLOW} mode...${NC}"
        $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml up -d
        echo -e "${GREEN}Production services started!${NC}"
        echo "Web: https://tradelink.uz"
        ;;
    
    prod-down)
        echo -e "${YELLOW}Stopping production services...${NC}"
        $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml down
        echo -e "${GREEN}Production services stopped!${NC}"
        ;;
    
    logs)
        $DOCKER_COMPOSE_CMD logs -f
        ;;
    
    logs-web)
        $DOCKER_COMPOSE_CMD logs -f web
        ;;
    
    logs-celery)
        $DOCKER_COMPOSE_CMD logs -f celery
        ;;
    
    logs-db)
        $DOCKER_COMPOSE_CMD logs -f db
        ;;
    
    shell)
        echo -e "${YELLOW}Opening Django shell...${NC}"
        run_django_cmd shell
        ;;
    
    migrate)
        echo -e "${YELLOW}Running migrations...${NC}"
        run_django_cmd migrate
        echo -e "${GREEN}Migrations complete!${NC}"
        ;;
    
    makemigrations)
        echo -e "${YELLOW}Making migrations...${NC}"
        run_django_cmd makemigrations "${@:2}"
        echo -e "${GREEN}Migrations created!${NC}"
        ;;
    
    createsuperuser)
        echo -e "${YELLOW}Creating superuser...${NC}"
        run_django_cmd createsuperuser
        ;;
    
    collectstatic)
        echo -e "${YELLOW}Collecting static files...${NC}"
        run_django_cmd collectstatic --noinput
        echo -e "${GREEN}Static files collected!${NC}"
        ;;
    
    test)
        echo -e "${YELLOW}Running tests...${NC}"
        $DOCKER_COMPOSE_CMD exec -T web pytest "${@:2}"
        ;;
    
    clean)
        echo -e "${RED}WARNING: This will delete all volumes and data!${NC}"
        read -p "Are you sure? (type 'yes' to confirm): " confirm
        if [ "$confirm" = "yes" ]; then
            $DOCKER_COMPOSE_CMD down -v
            echo -e "${GREEN}All volumes and containers removed!${NC}"
        else
            echo "Cancelled."
        fi
        ;;
    
    rebuild)
        echo -e "${YELLOW}Rebuilding Docker images...${NC}"
        $DOCKER_COMPOSE_CMD build --no-cache
        echo -e "${GREEN}Images rebuilt!${NC}"
        ;;
    
    health)
        check_health
        ;;
    
    help|*)
        show_help
        ;;
esac
