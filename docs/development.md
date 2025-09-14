# Development Setup Guide

This guide will help you set up the Roofing Platform development environment on your local machine.

## Prerequisites

### System Requirements
- **Operating System**: macOS 10.15+, Windows 10+, or Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **Node.js**: 18.0 or higher
- **PostgreSQL**: 12 or higher
- **Redis**: 6.0 or higher (for Celery)
- **Git**: 2.25 or higher

### Development Tools
- **Code Editor**: VS Code, PyCharm, or similar
- **Terminal**: Built-in terminal or iTerm2
- **Browser**: Chrome, Firefox, or Safari (latest version)

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd roof-platform
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Database Setup
```bash
# Install PostgreSQL (if not already installed)
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Create database
createdb roof_platform

# Or using psql
psql -c "CREATE DATABASE roof_platform;"
```

#### Environment Configuration
```bash
cp env.example .env
# Edit .env with your local configuration
```

**Required .env variables:**
```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=roof_platform
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration (for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

#### Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

#### Create Superuser
```bash
python manage.py createsuperuser
```

#### Start Backend Server
```bash
python manage.py runserver
```

### 3. Frontend Setup

#### Install Node Dependencies
```bash
cd ../frontend
npm install
```

#### Environment Configuration
```bash
cp env.example .env.local
# Edit .env.local with your configuration
```

**.env.local content:**
```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# App Configuration
NEXT_PUBLIC_APP_NAME=Roofing Platform
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

#### Start Frontend Server
```bash
npm run dev
```

## Detailed Setup Instructions

### Backend Configuration

#### 1. Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. PostgreSQL Setup
```bash
# Create database user (optional)
psql -c "CREATE USER roof_user WITH PASSWORD 'your_password';"
psql -c "ALTER ROLE roof_user CREATEDB;"

# Create database
psql -c "CREATE DATABASE roof_platform OWNER roof_user;"
```

#### 4. Environment Variables
Create a `.env` file in the `backend/` directory:

```env
# Django Settings
SECRET_KEY=django-insecure-dev-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DB_NAME=roof_platform
DB_USER=roof_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password

# Third-party APIs (get from respective services)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-key
STRIPE_SECRET_KEY=sk_test_your-stripe-key
```

#### 5. Database Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 6. Load Initial Data (Optional)
```bash
python manage.py loaddata fixtures/initial_data.json
```

### Frontend Configuration

#### 1. Install Dependencies
```bash
npm install
```

#### 2. Environment Variables
Create `.env.local` in the `frontend/` directory:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# App Configuration
NEXT_PUBLIC_APP_NAME=Roofing Platform
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Authentication
NEXT_PUBLIC_JWT_ACCESS_TOKEN_KEY=access_token
NEXT_PUBLIC_JWT_REFRESH_TOKEN_KEY=refresh_token

# Development
NODE_ENV=development
```

## Running the Application

### Development Mode

#### Backend
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```
Server will be available at: http://localhost:8000

#### Frontend
```bash
cd frontend
npm run dev
```
Application will be available at: http://localhost:3000

### Additional Services

#### Redis (for Celery)
```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping
```

#### Celery Worker
```bash
cd backend
source venv/bin/activate
celery -A roof_platform worker -l info
```

#### Celery Beat (Periodic Tasks)
```bash
cd backend
source venv/bin/activate
celery -A roof_platform beat -l info
```

## Testing

### Backend Tests
```bash
cd backend
source venv/bin/activate
python manage.py test
```

### Frontend Tests
```bash
cd frontend
npm test
```

### End-to-End Tests
```bash
# Install Playwright (if using)
npx playwright install
npm run test:e2e
```

## Code Quality

### Linting and Formatting

#### Backend
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run linting
flake8 .
black .
isort .
```

#### Frontend
```bash
# Run ESLint
npm run lint

# Fix ESLint issues
npm run lint:fix

# Run TypeScript checking
npm run type-check
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -l

# Reset database
dropdb roof_platform
createdb roof_platform
python manage.py migrate
```

#### 2. Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Start Redis service
# macOS
brew services start redis
# Linux
sudo systemctl start redis-server
```

#### 3. Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Check what's using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>
```

#### 4. Dependency Issues
```bash
# Backend
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# Frontend
rm -rf node_modules package-lock.json
npm install
```

#### 5. Migration Issues
```bash
# Reset migrations
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
python manage.py makemigrations
python manage.py migrate
```

### Debug Mode

#### Backend Debug
```python
# In settings.py, ensure DEBUG=True
DEBUG = True

# Add to settings.py for better error pages
if DEBUG:
    import logging
    logging.basicConfig(level=logging.DEBUG)
```

#### Frontend Debug
```bash
# Enable React DevTools
npm install -D @types/react-devtools
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow the coding standards
- Write tests for new features
- Update documentation if needed

### 3. Test Changes
```bash
# Backend tests
python manage.py test

# Frontend tests
npm test

# Manual testing
# - Test all user roles
# - Test on different screen sizes
# - Test offline functionality
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.org/)

## Support

If you encounter issues not covered in this guide:

1. Check the project README
2. Search existing issues
3. Create a new issue with detailed information
4. Include your environment details and error messages
