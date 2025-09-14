# 🏠 Roof Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Django](https://img.shields.io/badge/Django-4.2+-092e20.svg)](https://www.djangoproject.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)

> **Enterprise Roofing Contractor Scheduling & Management Platform**

A comprehensive SaaS solution designed to transform roofing business operations through intelligent scheduling, real-time job tracking, and seamless team coordination. Built for contractors who demand efficiency, reliability, and professional-grade management tools.

## 📋 Table of Contents

- [🏗️ Architecture](#-architecture)
- [✨ Key Features](#-key-features)
- [👥 User Roles](#-user-roles)
- [🚀 Quick Start](#-quick-start)
- [🔧 Configuration](#-configuration)
- [🛠️ Development](#️-development)
- [🧪 Testing](#-testing)
- [🚀 Deployment](#-deployment)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)
- [📞 Support](#-support)

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

Get up and running with Roof Platform in minutes using our automated setup process.

### 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - Backend runtime environment
- **Node.js 18+** - Frontend runtime environment
- **Docker & Docker Compose** (optional) - For containerized development
- **Git** - Version control system

### ⚡ One-Command Setup (Recommended)

For the fastest setup experience, use our automated script:

```bash
# Clone the repository
git clone https://github.com/bantoinese83/Roofing-Platform.git
cd roof-platform

# Run automated setup (handles everything)
./setup-env.sh && npm run setup

# Start development environment
npm run dev
```

**That's it!** 🎉 Your application will be running at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin

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

## ✨ Key Features

### 🔄 Core Business Operations
- **🗓️ Interactive Scheduling Dashboard**
  - Calendar-based job scheduling with drag-and-drop functionality
  - Real-time conflict detection and resource allocation
  - Multi-view calendar (day, week, month) with filtering options

- **📋 Job Management System**
  - Comprehensive job tracking with customer details and project scope
  - Material inventory tracking and job-specific notes
  - Real-time status updates and progress monitoring
  - Photo and document attachments for job documentation

- **👷 Technician & Crew Management**
  - Team profiles with skills, certifications, and availability tracking
  - Crew grouping and dynamic assignment capabilities
  - Time-off request management and scheduling optimization

- **🏢 Customer Relationship Management**
  - Customer profiles with complete service history
  - Communication logs and interaction tracking
  - Automated follow-ups and service reminders

### 🔧 Technical Capabilities
- **🔐 Enterprise-Grade Security**
  - JWT authentication with role-based access control (RBAC)
  - Multi-factor authentication (MFA) support
  - Data encryption at rest and in transit

- **📱 Modern User Experience**
  - Responsive design optimized for desktop and mobile devices
  - Progressive Web App (PWA) capabilities for field technicians
  - Intuitive drag-and-drop interfaces and real-time updates

- **⚡ High-Performance Architecture**
  - RESTful API with comprehensive OpenAPI documentation
  - Asynchronous task processing with Celery and Redis
  - Optimized database queries and caching strategies

- **🔗 Third-Party Integrations**
  - Google Maps Platform for route optimization and geocoding
  - Twilio integration for SMS notifications
  - SendGrid for email communications
  - Stripe payment processing (planned)

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

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or suggesting enhancements, your input is valuable.

### 🚀 Getting Started

1. **Fork the Repository**
   - Click the "Fork" button on GitHub
   - Clone your fork locally

2. **Set Up Development Environment**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Roofing-Platform.git
   cd roof-platform
   ./setup-env.sh && npm run setup
   npm run dev
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-number-description
   ```

### 📝 Development Guidelines

#### Code Quality
- Follow our [coding standards](./docs/development.md)
- Write meaningful commit messages using [Conventional Commits](https://conventionalcommits.org/)
- Add tests for new features and bug fixes
- Ensure all tests pass before submitting

#### Pull Request Process
1. **Update Documentation**: Update relevant documentation for any new features
2. **Test Thoroughly**: Ensure your changes work across all supported environments
3. **Code Review**: Request review from maintainers
4. **Merge**: Once approved, your PR will be merged

#### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
- `feat(scheduling): add drag-and-drop calendar functionality`
- `fix(auth): resolve JWT token expiration issue`
- `docs(readme): update installation instructions`

### 🐛 Reporting Issues

Found a bug? Have a feature request? Please [open an issue](https://github.com/bantoinese83/Roofing-Platform/issues) with:

- Clear title and description
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Screenshots (if applicable)
- Environment details (OS, browser, etc.)

### 📋 Development Roadmap

Check our [development roadmap](./docs/feature_roadmap.md) to see planned features and contribute to ongoing initiatives.

### 🎯 Areas for Contribution

- **Frontend Development**: React components, UI/UX improvements
- **Backend Development**: API endpoints, database optimization
- **Testing**: Unit tests, integration tests, E2E tests
- **Documentation**: API docs, user guides, tutorials
- **DevOps**: CI/CD improvements, deployment automation

### 📞 Community

- **Discussions**: Join our [GitHub Discussions](https://github.com/bantoinese83/Roofing-Platform/discussions) for questions and ideas
- **Discord**: Connect with the community on our Discord server
- **Newsletter**: Subscribe for updates and release announcements

### 📄 Code of Conduct

Please read and follow our [Code of Conduct](./CODE_OF_CONDUCT.md) to ensure a welcoming environment for all contributors.

---

**Thank you for contributing to Roof Platform!** 🙏

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

### 🛠️ Technology Stack
- **Django** & **Django REST Framework** - Robust backend framework
- **Next.js** & **React** - Modern frontend framework with App Router
- **PostgreSQL** - Reliable database solution
- **Redis** & **Celery** - Asynchronous task processing
- **Tailwind CSS** & **Radix UI** - Beautiful, accessible UI components
- **TanStack Query** - Powerful data fetching and caching

### 📚 Third-Party Services
Special thanks to our integration partners:
- **Google Maps Platform** - Route optimization and mapping
- **Twilio** - SMS communication services
- **SendGrid** - Email delivery services
- **Stripe** - Payment processing (planned)

### 👥 Community Contributors
We extend our gratitude to all contributors who have helped shape Roof Platform into what it is today.

### 🎓 Inspiration
Built with the needs of roofing contractors in mind, inspired by the challenges faced in traditional roofing business management.

## 📞 Support

### 🆘 Getting Help

- **📖 Documentation**: Comprehensive guides in our [docs](./docs/) directory
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/bantoinese83/Roofing-Platform/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/bantoinese83/Roofing-Platform/discussions)
- **📧 Email**: Contact the development team

### 🔍 Troubleshooting

Common issues and solutions:
- **Environment Setup**: Run `./verify-env.sh` to check your configuration
- **Database Issues**: Ensure PostgreSQL is running and credentials are correct
- **Frontend Build Errors**: Clear node_modules and reinstall with `npm run reset`

### 📊 System Requirements

- **Minimum**: 4GB RAM, 2 CPU cores, 10GB storage
- **Recommended**: 8GB RAM, 4 CPU cores, 20GB SSD storage
- **Production**: 16GB+ RAM, 8+ CPU cores, dedicated database server

---

<div align="center">

**🏠 Roof Platform** - *Transforming roofing business operations, one job at a time*

**Built with ❤️ for roofing contractors everywhere**

[🌟 Star us on GitHub](https://github.com/bantoinese83/Roofing-Platform) • [📖 Read the Docs](./docs/) • [🚀 Get Started](#-quick-start)

</div>
