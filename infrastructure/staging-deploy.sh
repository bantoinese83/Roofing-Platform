#!/bin/bash

# Roofing Platform MVP Staging Deployment Script
# This script deploys the MVP to AWS staging environment

set -e

# Configuration
STACK_NAME="roofing-platform-staging"
ENVIRONMENT="staging"
REGION="us-east-1"
DOMAIN_NAME="staging.roofingplatform.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Roofing Platform MVP Staging Deployment${NC}"
echo "=================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists aws; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI is not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Create S3 bucket for static files and media
echo -e "${YELLOW}Creating S3 bucket for static files...${NC}"
STATIC_BUCKET="${STACK_NAME}-static"
aws s3 mb "s3://${STATIC_BUCKET}" --region ${REGION} 2>/dev/null || true
aws s3 website "s3://${STATIC_BUCKET}" --index-document index.html --error-document error.html

# Enable versioning on the bucket
aws s3api put-bucket-versioning \
    --bucket ${STATIC_BUCKET} \
    --versioning-configuration Status=Enabled

echo -e "${GREEN}✅ S3 bucket created: ${STATIC_BUCKET}${NC}"

# Create CloudFormation stack for infrastructure
echo -e "${YELLOW}Creating CloudFormation infrastructure stack...${NC}"

# Check if stack exists
if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} >/dev/null 2>&1; then
    echo -e "${YELLOW}Stack ${STACK_NAME} already exists. Updating...${NC}"
    OPERATION="update-stack"
else
    echo -e "${YELLOW}Creating new stack ${STACK_NAME}...${NC}"
    OPERATION="create-stack"
fi

# Deploy infrastructure stack
aws cloudformation ${OPERATION} \
    --stack-name ${STACK_NAME} \
    --template-body file://infrastructure/aws/main.yaml \
    --parameters \
        ParameterKey=EnvironmentName,ParameterValue=${ENVIRONMENT} \
        ParameterKey=DomainName,ParameterValue=${DOMAIN_NAME} \
        ParameterKey=StaticBucketName,ParameterValue=${STATIC_BUCKET} \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region ${REGION}

echo -e "${GREEN}✅ CloudFormation stack deployment initiated${NC}"

# Wait for stack creation/update to complete
echo -e "${YELLOW}Waiting for CloudFormation stack to be ready...${NC}"
aws cloudformation wait stack-${OPERATION//-stack/}-complete --stack-name ${STACK_NAME} --region ${REGION}

echo -e "${GREEN}✅ CloudFormation stack is ready${NC}"

# Get stack outputs
echo -e "${YELLOW}Getting stack outputs...${NC}"
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} --query 'Stacks[0].Outputs')

# Extract important values
DB_HOST=$(echo ${STACK_OUTPUTS} | jq -r '.[] | select(.OutputKey=="DBHost") | .OutputValue')
DB_NAME=$(echo ${STACK_OUTPUTS} | jq -r '.[] | select(.OutputKey=="DBName") | .OutputValue')
ECS_CLUSTER=$(echo ${STACK_OUTPUTS} | jq -r '.[] | select(.OutputKey=="ECSClusterName") | .OutputValue')
ECS_SERVICE=$(echo ${STACK_OUTPUTS} | jq -r '.[] | select(.OutputKey=="ECSServiceName") | .OutputValue')
ALB_DNS=$(echo ${STACK_OUTPUTS} | jq -r '.[] | select(.OutputKey=="LoadBalancerDNS") | .OutputValue')

echo -e "${GREEN}✅ Stack outputs retrieved${NC}"

# Build and push Docker images
echo -e "${YELLOW}Building and pushing Docker images...${NC}"

# Get ECR repository URI
ECR_URI=$(aws ecr describe-repositories --repository-names roofing-platform-backend roofing-platform-frontend --region ${REGION} --query 'repositories[].repositoryUri' --output text)

BACKEND_ECR_URI=$(echo ${ECR_URI} | awk '{print $1}')
FRONTEND_ECR_URI=$(echo ${ECR_URI} | awk '{print $2}')

# Authenticate Docker with ECR
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${BACKEND_ECR_URI%/*}

# Build and push backend image
echo -e "${YELLOW}Building backend image...${NC}"
docker build -f infrastructure/docker/backend.Dockerfile -t roofing-platform-backend:${ENVIRONMENT} .
docker tag roofing-platform-backend:${ENVIRONMENT} ${BACKEND_ECR_URI}:${ENVIRONMENT}
docker push ${BACKEND_ECR_URI}:${ENVIRONMENT}

# Build and push frontend image
echo -e "${YELLOW}Building frontend image...${NC}"
docker build -f infrastructure/docker/frontend.Dockerfile -t roofing-platform-frontend:${ENVIRONMENT} .
docker tag roofing-platform-frontend:${ENVIRONMENT} ${FRONTEND_ECR_URI}:${ENVIRONMENT}
docker push ${FRONTEND_ECR_URI}:${ENVIRONMENT}

echo -e "${GREEN}✅ Docker images built and pushed${NC}"

# Update ECS service with new images
echo -e "${YELLOW}Updating ECS service...${NC}"

# Update task definition with new image URIs
TASK_DEF_ARN=$(aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${REGION} --query 'services[0].taskDefinition' --output text)
TASK_DEF_FAMILY=$(aws ecs describe-task-definition --task-definition ${TASK_DEF_ARN} --region ${REGION} --query 'taskDefinition.family' --output text)

# Create new task definition
aws ecs register-task-definition \
    --family ${TASK_DEF_FAMILY} \
    --container-definitions "[
        {
            \"name\": \"backend\",
            \"image\": \"${BACKEND_ECR_URI}:${ENVIRONMENT}\",
            \"essential\": true,
            \"portMappings\": [
                {
                    \"containerPort\": 8000,
                    \"hostPort\": 8000,
                    \"protocol\": \"tcp\"
                }
            ],
            \"environment\": [
                {\"name\": \"ENVIRONMENT\", \"value\": \"${ENVIRONMENT}\"},
                {\"name\": \"DB_HOST\", \"value\": \"${DB_HOST}\"},
                {\"name\": \"DB_NAME\", \"value\": \"${DB_NAME}\"}
            ],
            \"logConfiguration\": {
                \"logDriver\": \"awslogs\",
                \"options\": {
                    \"awslogs-group\": \"/ecs/roofing-platform-${ENVIRONMENT}\",
                    \"awslogs-region\": \"${REGION}\",
                    \"awslogs-stream-prefix\": \"ecs\"
                }
            }
        },
        {
            \"name\": \"frontend\",
            \"image\": \"${FRONTEND_ECR_URI}:${ENVIRONMENT}\",
            \"essential\": true,
            \"portMappings\": [
                {
                    \"containerPort\": 3000,
                    \"hostPort\": 3000,
                    \"protocol\": \"tcp\"
                }
            ],
            \"logConfiguration\": {
                \"logDriver\": \"awslogs\",
                \"options\": {
                    \"awslogs-group\": \"/ecs/roofing-platform-${ENVIRONMENT}\",
                    \"awslogs-region\": \"${REGION}\",
                    \"awslogs-stream-prefix\": \"ecs\"
                }
            }
        }
    ]" \
    --region ${REGION}

# Update service to use new task definition
aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${ECS_SERVICE} \
    --task-definition ${TASK_DEF_FAMILY} \
    --region ${REGION}

echo -e "${GREEN}✅ ECS service updated${NC}"

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"

# This would typically be done via a separate migration task or manual execution
echo -e "${YELLOW}⚠️  Database migrations need to be run manually on the staging instance${NC}"
echo -e "${YELLOW}   SSH into the EC2 instance and run:${NC}"
echo -e "${YELLOW}   cd /app && python manage.py migrate${NC}"

# Set up SSL certificate
echo -e "${YELLOW}Setting up SSL certificate...${NC}"

# Request SSL certificate from ACM
CERT_ARN=$(aws acm request-certificate \
    --domain-name ${DOMAIN_NAME} \
    --validation-method DNS \
    --region ${REGION} \
    --query 'CertificateArn' \
    --output text)

echo -e "${GREEN}✅ SSL certificate requested: ${CERT_ARN}${NC}"

# Update Route 53 with validation records
echo -e "${YELLOW}⚠️  DNS validation required. Check AWS ACM console for validation records.${NC}"

# Configure CloudFront distribution
echo -e "${YELLOW}Setting up CloudFront distribution...${NC}"

# Create CloudFront distribution for static files
DISTRIBUTION_ID=$(aws cloudfront create-distribution \
    --distribution-config "{
        \"CallerReference\": \"${STACK_NAME}-$(date +%s)\",
        \"Comment\": \"Roofing Platform ${ENVIRONMENT} Static Files\",
        \"Enabled\": true,
        \"Origins\": {
            \"Quantity\": 1,
            \"Items\": [
                {
                    \"Id\": \"S3-${STATIC_BUCKET}\",
                    \"DomainName\": \"${STATIC_BUCKET}.s3.amazonaws.com\",
                    \"S3OriginConfig\": {
                        \"OriginAccessIdentity\": \"\"
                    }
                }
            ]
        },
        \"DefaultCacheBehavior\": {
            \"TargetOriginId\": \"S3-${STATIC_BUCKET}\",
            \"ViewerProtocolPolicy\": \"redirect-to-https\",
            \"MinTTL\": 0,
            \"ForwardedValues\": {
                \"QueryString\": false,
                \"Cookies\": {
                    \"Forward\": \"none\"
                }
            }
        }
    }" \
    --query 'Distribution.Id' \
    --output text)

echo -e "${GREEN}✅ CloudFront distribution created: ${DISTRIBUTION_ID}${NC}"

# Deployment summary
echo ""
echo -e "${GREEN}🎉 Deployment Summary${NC}"
echo "======================"
echo -e "Environment: ${ENVIRONMENT}"
echo -e "Domain: https://${DOMAIN_NAME}"
echo -e "Load Balancer: http://${ALB_DNS}"
echo -e "Static Files: https://${DISTRIBUTION_ID}.cloudfront.net"
echo -e "Database Host: ${DB_HOST}"
echo -e "ECS Cluster: ${ECS_CLUSTER}"
echo -e "ECS Service: ${ECS_SERVICE}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Complete DNS validation for SSL certificate"
echo "2. Update your DNS records to point to the load balancer"
echo "3. Run database migrations on the EC2 instance"
echo "4. Load default notification templates: python manage.py load_default_templates"
echo "5. Create initial admin user: python manage.py createsuperuser"
echo "6. Configure notification service settings (Twilio, SendGrid)"
echo ""
echo -e "${GREEN}🚀 MVP Staging Deployment Complete!${NC}"
