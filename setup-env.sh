#!/bin/bash

# =================================
# Roof Platform Environment Setup
# =================================
# This script helps set up environment variables for development
# It generates a .env file with development defaults

set -e

echo "🏗️  Setting up Roof Platform Environment Variables"
echo "=================================================="

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Generate a random SECRET_KEY
echo "🔑 Generating Django SECRET_KEY..."
SECRET_KEY="django-insecure-$(openssl rand -hex 32)"

# Create .env file
cat > .env << EOF
# =================================
# Roof Platform Development Environment
# =================================
# This file contains development defaults.
# NEVER use these values in production!

# =================================
# BACKEND (Django) Configuration
# =================================

# Django Settings
DEBUG=True
SECRET_KEY=${SECRET_KEY}
DJANGO_SETTINGS_MODULE=roof_platform.settings

# Database Configuration (PostgreSQL for development)
DATABASE_URL=postgresql://postgres:postgres@db:5432/roof_platform
POSTGRES_DB=roof_platform
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis Configuration
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Email Configuration (Development - uses console backend)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# SMS Configuration (Development - placeholder values)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number

# Google Maps API (Development - placeholder)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# =================================
# FRONTEND (Next.js) Configuration
# =================================

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_APP_NAME=Roofing Platform
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_ENVIRONMENT=development

# Authentication
NEXT_PUBLIC_JWT_ACCESS_TOKEN_KEY=access_token
NEXT_PUBLIC_JWT_REFRESH_TOKEN_KEY=refresh_token

# External API Keys (Public - Safe to expose in development)
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your-google-maps-api-key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key

# Stack Auth Configuration (Development)
NEXT_PUBLIC_STACK_PROJECT_ID=your-stack-project-id
NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY=your-stack-publishable-key
STACK_SECRET_SERVER_KEY=your-stack-secret-key

# =================================
# PAYMENT PROCESSING (Stripe)
# =================================

STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-publishable-key
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key

# =================================
# DEVELOPMENT NOTES
# =================================
# 1. This .env file is for development only
# 2. Never commit this file to version control
# 3. For production, use strong, randomly generated secrets
# 4. Update placeholder values with your actual credentials
# 5. Consider using a secret management service for production
EOF

echo "✅ .env file created successfully!"
echo ""
echo "🔧 Next Steps:"
echo "1. Review the .env file and update placeholder values"
echo "2. Run: npm run setup"
echo "3. Run: npm run dev"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "- Never commit the .env file to version control"
echo "- Use different values for production"
echo "- Consider using AWS Secrets Manager or similar for production"
echo ""
echo "📚 For production deployment:"
echo "- Generate strong, random SECRET_KEY"
echo "- Use secure database credentials"
echo "- Configure proper CORS and ALLOWED_HOSTS"
echo "- Set up SSL/TLS certificates"
