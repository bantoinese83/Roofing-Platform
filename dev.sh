#!/bin/bash

# ===========================================
# Roof Platform Development Script
# ===========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to setup environment
setup_environment() {
    print_info "Setting up development environment..."

    # Check prerequisites
    if ! command_exists node; then
        print_error "Node.js is not installed. Please install Node.js 18+ first."
        exit 1
    fi

    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.11+ first."
        exit 1
    fi

    # Copy environment files
    if [ ! -f .env ]; then
        cp env.example .env
        print_warning "Please edit .env file with your configuration before running the application."
    fi

    # Setup frontend
    print_info "Setting up frontend..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install
        print_success "Frontend dependencies installed"
    else
        print_info "Frontend dependencies already installed"
    fi
    cd ..

    # Setup backend
    print_info "Setting up backend..."
    cd backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        print_success "Backend virtual environment created and dependencies installed"
    else
        print_info "Backend virtual environment already exists"
    fi
    cd ..

    print_success "Environment setup complete!"
    print_info "Run './dev.sh start' to start the development servers"
}

# Function to start development servers
start_development() {
    print_info "Starting development servers..."

    # Check if environment is set up
    if [ ! -d "frontend/node_modules" ]; then
        print_error "Frontend not set up. Run './dev.sh setup' first."
        exit 1
    fi

    if [ ! -d "backend/venv" ]; then
        print_error "Backend not set up. Run './dev.sh setup' first."
        exit 1
    fi

    # Start both services with concurrently
    npm run dev
}

# Function to run tests
run_tests() {
    print_info "Running tests..."

    # Frontend tests
    print_info "Running frontend tests..."
    cd frontend
    npm test
    cd ..

    # Backend tests
    print_info "Running backend tests..."
    cd backend
    source venv/bin/activate
    python manage.py test
    cd ..

    print_success "All tests completed!"
}

# Function to clean up
cleanup() {
    print_info "Cleaning up development environment..."

    # Clean frontend
    cd frontend
    rm -rf node_modules .next
    print_info "Frontend cleaned"
    cd ..

    # Clean backend
    cd backend
    rm -rf venv __pycache__ *.pyc
    print_info "Backend cleaned"
    cd ..

    print_success "Cleanup complete!"
}

# Function to show help
show_help() {
    echo "Roof Platform Development Script"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - Setup development environment"
    echo "  start     - Start development servers"
    echo "  test      - Run all tests"
    echo "  clean     - Clean development environment"
    echo "  help      - Show this help message"
    echo ""
    echo "Alternative usage with npm:"
    echo "  npm run setup    - Setup environment"
    echo "  npm run dev      - Start development servers"
    echo "  npm run test     - Run tests"
    echo "  npm run clean    - Clean environment"
}

# Main script logic
case "${1:-help}" in
    "setup")
        setup_environment
        ;;
    "start")
        start_development
        ;;
    "test")
        run_tests
        ;;
    "clean")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac
