#!/bin/bash

# SSL Certificate Setup and Renewal Script for TradeLink
# This script sets up Let's Encrypt SSL certificates using Certbot

set -e

DOMAIN="${1:-azizdali.uz}"
EMAIL="${2:-admin@azizdali.uz}"
CERT_DIR="./nginx/ssl"
RENEWAL_DAYS=30

echo "TradeLink SSL Certificate Setup"
echo "================================"
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo "Certificate Directory: $CERT_DIR"
echo ""

# Create SSL directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Function to check if certificate exists and is valid
check_certificate() {
    if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
        local expiry=$(openssl x509 -in "$CERT_DIR/cert.pem" -noout -enddate | cut -d= -f2)
        echo "Certificate found. Expiry date: $expiry"
        return 0
    fi
    return 1
}

# Function to check certificate age
check_cert_age() {
    if check_certificate; then
        local expiry_timestamp=$(date -d "$(openssl x509 -in "$CERT_DIR/cert.pem" -noout -enddate | cut -d= -f2)" +%s)
        local current_timestamp=$(date +%s)
        local days_left=$(( ($expiry_timestamp - $current_timestamp) / 86400 ))
        echo "Days until certificate expiry: $days_left"
        
        if [ $days_left -lt $RENEWAL_DAYS ]; then
            echo "Certificate expires in less than $RENEWAL_DAYS days. Renewing..."
            return 0
        fi
        return 1
    fi
    return 0
}

# Function to generate self-signed certificate for development
generate_self_signed() {
    echo "Generating self-signed certificate for development..."
    openssl req -x509 -newkey rsa:2048 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 365 -nodes \
        -subj "/C=UZ/ST=Tashkent/L=Tashkent/O=TradeLink/CN=$DOMAIN"
    echo "Self-signed certificate created."
}

# Check for required tools
if ! command -v openssl &> /dev/null; then
    echo "Error: openssl is required but not installed."
    exit 1
fi

# Generate certificate (for now, use self-signed in development)
if check_certificate; then
    if check_cert_age; then
        echo "Certificate renewal needed."
        generate_self_signed
    else
        echo "Certificate is still valid. No action needed."
    fi
else
    echo "No certificate found."
    if [ "$3" == "production" ]; then
        echo "For production, set up Let's Encrypt manually:"
        echo "1. Use Certbot:"
        echo "   certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --agree-tos -m $EMAIL"
        echo "2. Copy certificates to $CERT_DIR/"
        exit 1
    else
        generate_self_signed
    fi
fi

echo ""
echo "SSL setup complete!"
echo "Certificate location: $CERT_DIR/cert.pem"
echo "Key location: $CERT_DIR/key.pem"
echo ""
echo "For production with Let's Encrypt:"
echo "1. Uncomment Certbot service in docker-compose.yml"
echo "2. Run: certbot certonly --standalone -d $DOMAIN -m $EMAIL"
echo "3. Update nginx configuration for SSL"
