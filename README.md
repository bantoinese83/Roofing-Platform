# Roofing Platform

Enterprise Roofing Contractor Scheduling & Management Platform

A comprehensive web and mobile application designed to empower roofing businesses by centralizing and streamlining their entire operational workflow. This platform eliminates inefficiencies in manual scheduling, dispatch, and job management processes.

## 🏗️ Architecture

### Backend
- **Framework**: Django 4.2 with Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT with role-based access control
- **Async Tasks**: Celery with Redis
- **API**: RESTful API with comprehensive documentation

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand + TanStack Query
- **Forms**: React Hook Form with Zod validation

### Infrastructure (Planned)
- **Cloud**: AWS (EC2, RDS, S3, CloudFront, Route 53)
- **CI/CD**: GitHub Actions
- **Monitoring**: AWS CloudWatch

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional, for containerized setup)
- Git

### Root-Level Setup (Recommended)

```bash
# Clone and setup from project root
git clone <repository-url>
cd roof-platform

# Setup environment variables (generates .env file)
./setup-env.sh
# Review and edit .env with your actual credentials

# Setup both frontend and backend
npm run setup

# Start development servers (both frontend and backend)
npm run dev
```

### Environment Variables

The application uses environment variables for configuration. A comprehensive setup is provided:

1. **Run the setup script**: `./setup-env.sh`
   - Generates a `.env` file with development defaults
   - Creates a secure random SECRET_KEY

2. **Review and update values**: Edit `.env` with your actual credentials

3. **Required environment variables**:
   - `SECRET_KEY`: Django secret key (auto-generated)
   - `DATABASE_URL`: PostgreSQL connection string
   - `NEXT_PUBLIC_API_URL`: Frontend API endpoint
   - `GOOGLE_MAPS_API_KEY`: For route optimization
   - `STRIPE_SECRET_KEY`: For payment processing

**⚠️ Security Notes:**
- Never commit `.env` files to version control
- Use strong, randomly generated secrets in production
- Consider AWS Secrets Manager for production deployments

### Manual Setup (Alternative)

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

#### Frontend Setup
```bash
cd frontend
npm install
cp env.example .env.local
```

### Docker Setup (Production Ready)

```bash
# Development with Docker
docker-compose up

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Development URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/docs/

## 📋 Features

### Core Functionality
- ✅ **Interactive Scheduling Dashboard** - Calendar-based job scheduling with drag-and-drop
- ✅ **Job Management** - Comprehensive job tracking with customer details, materials, and status
- ✅ **Technician & Crew Management** - Team profiles, skills, availability, and assignments
- ✅ **Customer Relationship Management** - Customer profiles, service history, and communication logs
- ✅ **Real-time Notifications** - SMS and email notifications for appointments and updates

### Technical Features
- ✅ **JWT Authentication** - Secure token-based authentication with role-based access
- ✅ **Responsive Design** - Mobile-first design optimized for field technicians
- ✅ **API-First Architecture** - RESTful APIs with comprehensive documentation
- ✅ **Real-time Updates** - Live job tracking and status updates
- ✅ **Offline Support** - Basic offline functionality for field operations

## 👥 User Roles

- **Business Owner**: Full system access, financial reporting, business analytics
- **Office Manager**: Scheduling, dispatch, customer management, team coordination
- **Field Technician**: Mobile access to schedules, job details, time tracking

## 🛠️ Development

### Project Structure
```
roof-platform/
├── backend/              # Django REST API
│   ├── roof_platform/   # Django project settings
│   ├── accounts/        # User authentication & profiles
│   ├── scheduling/      # Job scheduling logic
│   ├── jobs/           # Job management
│   ├── customers/      # Customer management
│   └── technicians/    # Technician management
├── frontend/            # Next.js application
│   ├── src/
│   │   ├── app/        # Next.js App Router pages
│   │   ├── components/ # Reusable React components
│   │   ├── lib/        # Utilities and API client
│   │   ├── stores/     # Zustand state management
│   │   └── types/      # TypeScript definitions
└── docs/               # Documentation
```

### Available Scripts

From the project root, you can use these npm scripts:

```bash
# Development
npm run dev                 # Start both frontend and backend
npm run dev:frontend        # Start only frontend
npm run dev:backend         # Start only backend

# Building
npm run build              # Build frontend for production
npm run build:frontend     # Build frontend
npm run build:backend      # Collect static files

# Testing
npm run test               # Run all tests
npm run test:frontend      # Run frontend tests
npm run test:backend       # Run backend tests

# Database
npm run migrate            # Run Django migrations
npm run makemigrations     # Create new migrations
npm run createsuperuser    # Create Django admin user

# Setup & Cleanup
npm run setup              # Setup both frontend and backend
npm run setup:frontend     # Install frontend dependencies
npm run setup:backend      # Setup Python virtual environment
npm run clean              # Clean build artifacts
npm run reset              # Reset entire environment

# Docker
npm run docker:build       # Build Docker images
npm run docker:up          # Start all services
npm run docker:down        # Stop all services
npm run docker:logs        # View container logs
```

### Development Workflow

1. **Root-level Development (Recommended)**
   ```bash
   npm run dev  # Starts both frontend and backend simultaneously
   ```

2. **Separate Development**
   ```bash
   # Terminal 1 - Backend
   npm run dev:backend

   # Terminal 2 - Frontend
   npm run dev:frontend
   ```

3. **Database Operations**
   ```bash
   npm run makemigrations  # Create new migrations
   npm run migrate         # Apply migrations
   npm run createsuperuser # Create admin user
   ```

### Testing

```bash
# Run all tests
npm run test

# Run specific test suites
npm run test:frontend
npm run test:backend
```

## 🚀 Deployment

### Production Checklist
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] SSL certificates installed
- [ ] Domain configured
- [ ] Monitoring and logging set up

### AWS Infrastructure (Planned)
- **EC2**: Application servers
- **RDS**: PostgreSQL database
- **S3**: Media storage
- **CloudFront**: CDN
- **Route 53**: DNS management
- **ELB**: Load balancing

## 📚 Documentation

- [Backend API Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)
- [Development Setup](./docs/development.md)
- [Deployment Guide](./docs/deployment.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support or questions, please contact the development team.

---

**Built with ❤️ for roofing contractors everywhere**
