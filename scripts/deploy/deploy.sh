#!/bin/bash

# Roofing Platform Deployment Script
# This script handles deployment to AWS ECS

set -e

# Configuration
ENVIRONMENT=${1:-staging}
AWS_REGION=${AWS_REGION:-us-east-1}
CLUSTER_NAME="roofing-platform-${ENVIRONMENT}"
BACKEND_SERVICE="roofing-platform-backend-${ENVIRONMENT}"
FRONTEND_SERVICE="roofing-platform-frontend-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured or invalid."
        exit 1
    fi

    log_info "Prerequisites check passed."
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."

    # Get the current Git commit hash
    GIT_COMMIT=$(git rev-parse --short HEAD)
    BACKEND_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/roofing-platform-backend:${GIT_COMMIT}"
    FRONTEND_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/roofing-platform-frontend:${GIT_COMMIT}"

    # Build backend image
    log_info "Building backend image..."
    docker build -f infrastructure/docker/backend.Dockerfile -t $BACKEND_IMAGE .

    # Build frontend image
    log_info "Building frontend image..."
    docker build -f infrastructure/docker/frontend.Dockerfile -t $FRONTEND_IMAGE .

    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

    # Push images
    log_info "Pushing backend image..."
    docker push $BACKEND_IMAGE

    log_info "Pushing frontend image..."
    docker push $FRONTEND_IMAGE

    # Export image variables for later use
    export BACKEND_IMAGE
    export FRONTEND_IMAGE
}

# Update ECS services
update_ecs_services() {
    log_info "Updating ECS services..."

    # Update backend service
    log_info "Updating backend service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $BACKEND_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION

    # Update frontend service
    log_info "Updating frontend service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $FRONTEND_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION
}

# Run database migrations
run_migrations() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "Running database migrations..."

        # Run migration task
        aws ecs run-task \
            --cluster $CLUSTER_NAME \
            --task-definition roofing-platform-migration \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-abcdef]}" \
            --overrides "containerOverrides=[{name=backend,command=[\"python\",\"manage.py\",\"migrate\"]}]" \
            --region $AWS_REGION

        log_info "Waiting for migration to complete..."
        sleep 30
    fi
}

# Health checks
run_health_checks() {
    log_info "Running health checks..."

    # Wait for services to be stable
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $BACKEND_SERVICE $FRONTEND_SERVICE \
        --region $AWS_REGION

    log_info "Services are stable. Deployment completed successfully!"
}

# Rollback function
rollback() {
    log_error "Deployment failed. Initiating rollback..."

    # Rollback backend service
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $BACKEND_SERVICE \
        --task-definition roofing-platform-backend-${ENVIRONMENT}-previous \
        --region $AWS_REGION

    # Rollback frontend service
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $FRONTEND_SERVICE \
        --task-definition roofing-platform-frontend-${ENVIRONMENT}-previous \
        --region $AWS_REGION

    log_info "Rollback completed."
    exit 1
}

# Main deployment function
main() {
    log_info "Starting deployment to $ENVIRONMENT environment..."

    # Set trap for rollback on error
    trap rollback ERR

    check_prerequisites
    build_and_push_images
    run_migrations
    update_ecs_services
    run_health_checks

    log_info "Deployment completed successfully! 🎉"

    # Send notification (if Slack webhook is configured)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Successfully deployed Roofing Platform to $ENVIRONMENT\"}" \
            $SLACK_WEBHOOK_URL
    fi
}

# Validate environment
if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    log_error "Invalid environment. Must be 'staging' or 'production'."
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Run main deployment
main "$@"
