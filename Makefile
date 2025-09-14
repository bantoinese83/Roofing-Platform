# ===========================================
# Roof Platform - Development Makefile
# ===========================================

.PHONY: help setup setup-frontend setup-backend dev dev-frontend dev-backend \
        build build-frontend build-backend test test-frontend test-backend \
        migrate makemigrations createsuperuser shell dbshell collectstatic \
        clean clean-frontend clean-backend reset docker-build docker-up \
        docker-down docker-logs prod-build prod-start lint type-check

# Default target
help:
	@echo "Available commands:"
	@echo "  setup           - Setup both frontend and backend"
	@echo "  setup-frontend  - Install frontend dependencies"
	@echo "  setup-backend   - Setup Python virtual environment"
	@echo "  dev             - Start both frontend and backend in development"
	@echo "  dev-frontend    - Start frontend development server"
	@echo "  dev-backend     - Start backend development server"
	@echo "  build           - Build for production"
	@echo "  build-frontend  - Build frontend for production"
	@echo "  build-backend   - Collect backend static files"
	@echo "  test            - Run all tests"
	@echo "  test-frontend   - Run frontend tests"
	@echo "  test-backend    - Run backend tests"
	@echo "  migrate         - Run Django migrations"
	@echo "  makemigrations  - Create new Django migrations"
	@echo "  createsuperuser - Create Django admin user"
	@echo "  shell           - Open Django shell"
	@echo "  dbshell         - Open database shell"
	@echo "  collectstatic   - Collect Django static files"
	@echo "  lint            - Run frontend linting"
	@echo "  type-check      - Run TypeScript type checking"
	@echo "  clean           - Clean all build artifacts"
	@echo "  clean-frontend  - Clean frontend build artifacts"
	@echo "  clean-backend   - Clean backend build artifacts"
	@echo "  reset           - Reset entire environment"
	@echo "  docker-build    - Build Docker images"
	@echo "  docker-up       - Start all Docker services"
	@echo "  docker-down     - Stop all Docker services"
	@echo "  docker-logs     - View Docker container logs"
	@echo "  prod-build      - Build for production deployment"
	@echo "  prod-start      - Start production services"

# Setup commands
setup: setup-backend setup-frontend
	@echo "✅ Setup complete!"

setup-frontend:
	cd frontend && npm install

setup-backend:
	cd backend && python -m venv venv
	cd backend && source venv/bin/activate && pip install -r requirements.txt

# Development commands
dev:
	npm run dev

dev-frontend:
	npm run dev:frontend

dev-backend:
	npm run dev:backend

# Build commands
build: build-frontend build-backend

build-frontend:
	npm run build:frontend

build-backend:
	npm run build:backend

# Testing commands
test: test-backend test-frontend

test-frontend:
	npm run test:frontend

test-backend:
	npm run test:backend

# Database commands
migrate:
	npm run migrate

makemigrations:
	npm run makemigrations

createsuperuser:
	npm run createsuperuser

shell:
	npm run shell

dbshell:
	npm run dbshell

collectstatic:
	npm run collectstatic

# Code quality commands
lint:
	npm run lint

type-check:
	npm run type-check

# Cleanup commands
clean: clean-frontend clean-backend

clean-frontend:
	npm run clean:frontend

clean-backend:
	npm run clean:backend

reset:
	npm run reset

# Docker commands
docker-build:
	npm run docker:build

docker-up:
	npm run docker:up

docker-down:
	npm run docker:down

docker-logs:
	npm run docker:logs

# Production commands
prod-build:
	npm run prod:build

prod-start:
	npm run prod:start
