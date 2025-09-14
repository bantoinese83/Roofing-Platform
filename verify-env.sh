#!/bin/bash

# =================================
# Environment Variables Verification
# =================================
# This script verifies that all required environment variables are set

set -e

echo "🔍 Verifying Roof Platform Environment Variables"
echo "================================================"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Run './setup-env.sh' first to create the environment file."
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

echo "📋 Checking required environment variables..."
echo ""

# Track missing variables
MISSING_VARS=()

# Check Django settings
echo "🐍 Django Backend Configuration:"
check_var "SECRET_KEY" "$SECRET_KEY"
check_var "DEBUG" "$DEBUG"
check_var "DATABASE_URL" "$DATABASE_URL"

# Check Redis/Celery
echo ""
echo "🔴 Redis & Celery Configuration:"
check_var "REDIS_URL" "$REDIS_URL"
check_var "CELERY_BROKER_URL" "$CELERY_BROKER_URL"

# Check CORS
echo ""
echo "🌐 CORS Configuration:"
check_var "CORS_ALLOWED_ORIGINS" "$CORS_ALLOWED_ORIGINS"
check_var "ALLOWED_HOSTS" "$ALLOWED_HOSTS"

# Check Next.js settings
echo ""
echo "⚛️  Next.js Frontend Configuration:"
check_var "NEXT_PUBLIC_API_URL" "$NEXT_PUBLIC_API_URL"
check_var "NEXT_PUBLIC_APP_URL" "$NEXT_PUBLIC_APP_URL"

# Check optional third-party services
echo ""
echo "🔧 Third-party Services (Optional but recommended):"
check_optional "GOOGLE_MAPS_API_KEY" "$GOOGLE_MAPS_API_KEY"
check_optional "STRIPE_SECRET_KEY" "$STRIPE_SECRET_KEY"
check_optional "TWILIO_AUTH_TOKEN" "$TWILIO_AUTH_TOKEN"
check_optional "EMAIL_HOST_PASSWORD" "$EMAIL_HOST_PASSWORD"

echo ""
echo "📊 Summary:"

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "✅ All required environment variables are configured!"
    echo ""
    echo "🚀 You can now run:"
    echo "   npm run setup    # Setup both frontend and backend"
    echo "   npm run dev      # Start development servers"
else
    echo "❌ Missing ${#MISSING_VARS[@]} required environment variable(s):"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "📝 Please update your .env file with the missing values."
    echo "   You can find examples in env.example"
    exit 1
fi

# Function to check required variables
check_var() {
    local name="$1"
    local value="$2"

    if [ -z "$value" ]; then
        echo "❌ $name: NOT SET"
        MISSING_VARS+=("$name")
    else
        echo "✅ $name: SET"
    fi
}

# Function to check optional variables
check_optional() {
    local name="$1"
    local value="$2"

    if [ -z "$value" ] || [ "$value" = "your-*" ]; then
        echo "⚠️  $name: NOT CONFIGURED (optional)"
    else
        echo "✅ $name: CONFIGURED"
    fi
}
