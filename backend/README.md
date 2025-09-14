# Roofing Platform Backend

Django REST API backend for the Enterprise Roofing Contractor Scheduling & Management Platform.

## Features

- JWT-based authentication with role-based access control
- PostgreSQL database with Django ORM
- Celery for asynchronous task processing
- RESTful API with Django REST Framework
- CORS support for frontend integration
- Comprehensive user management system

## Tech Stack

- **Framework**: Django 4.2
- **API**: Django REST Framework
- **Authentication**: Django REST Framework Simple JWT
- **Database**: PostgreSQL
- **Async Tasks**: Celery with Redis
- **Environment**: Python Decouple for configuration

## Setup

1. **Clone and navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   # From project root, run the setup script (recommended)
   ../setup-env.sh

   # Or copy and edit manually
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentication
- `POST /api/auth/token/` - Obtain JWT token
- `POST /api/auth/token/refresh/` - Refresh JWT token

### Users
- `GET /api/accounts/users/` - List users
- `POST /api/accounts/users/` - Create user
- `GET /api/accounts/users/<id>/` - Get user details
- `PUT /api/accounts/users/<id>/` - Update user
- `DELETE /api/accounts/users/<id>/` - Delete user
- `POST /api/accounts/register/` - Register new user
- `POST /api/accounts/login/` - Login user
- `GET /api/accounts/profile/` - Get current user profile
- `PUT /api/accounts/profile/` - Update current user profile
- `POST /api/accounts/change-password/` - Change password

## User Roles

- **Admin**: Full system access
- **Owner**: Business owner with management access
- **Manager**: Office manager with scheduling access
- **Technician**: Field technician with limited access

## Development

### Running Celery Worker
```bash
celery -A roof_platform worker -l info
```

### Running Celery Beat
```bash
celery -A roof_platform beat -l info
```

### Running Tests
```bash
python manage.py test
```

## Environment Variables

See `env.example` for all required environment variables including database, Redis, and third-party service configurations.
