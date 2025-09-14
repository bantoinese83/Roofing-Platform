# Infrastructure Setup Guide

This guide provides detailed instructions for setting up the AWS infrastructure for the Roofing Platform using CloudFormation templates and automated deployment scripts.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CloudFront    │────│   Application   │────│   RDS Postgres  │
│   (CDN)         │    │   Load Balancer │    │   Database       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   S3 Static     │    │   EC2 Auto      │    │   Redis (Elasti │
│   Assets        │    │   Scaling Group │    │   Cache)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

### AWS Account Setup
1. Create an AWS account or use an existing one
2. Set up AWS CLI with appropriate credentials:
   ```bash
   aws configure
   ```

3. Install required tools:
   ```bash
   # AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # AWS SAM CLI (for local testing)
   pip install aws-sam-cli
   ```

### Domain Setup
1. Register a domain (e.g., roofingplatform.com) or use Route 53
2. Update the domain name in the CloudFormation parameters

## Infrastructure Components

### 1. VPC and Networking (`vpc.yaml`)
- **VPC**: Isolated network environment
- **Subnets**: Public and private subnets across multiple AZs
- **Internet Gateway**: For public internet access
- **NAT Gateway**: For private subnet outbound traffic
- **Security Groups**: Firewall rules for EC2, ALB, and RDS

### 2. RDS PostgreSQL (`rds.yaml`)
- **PostgreSQL 15**: Managed database service
- **Multi-AZ**: High availability (disabled for dev/staging)
- **Automated Backups**: 7-day retention
- **CloudWatch Monitoring**: CPU and storage alarms

### 3. EC2 and ALB (`ec2-alb.yaml`)
- **EC2 Auto Scaling Group**: Automatic scaling based on CPU utilization
- **Application Load Balancer**: Distributes traffic across instances
- **Launch Template**: Defines instance configuration
- **IAM Roles**: Least-privilege access for EC2 instances

### 4. S3 and CloudFront (`s3-cloudfront.yaml`)
- **S3 Buckets**: Static assets and media files storage
- **CloudFront CDN**: Global content delivery
- **Origin Access Identity**: Secure S3 access
- **WAF**: Web application firewall

### 5. Route 53 (`route53.yaml`)
- **DNS Management**: Domain routing
- **Health Checks**: Endpoint monitoring
- **SSL Certificates**: HTTPS support

## Deployment Instructions

### Step 1: Deploy VPC Infrastructure

```bash
# Deploy VPC stack
aws cloudformation create-stack \
  --stack-name roofing-platform-vpc \
  --template-body file://infrastructure/aws/vpc.yaml \
  --parameters ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
  --region us-east-1

# Wait for completion
aws cloudformation wait stack-create-complete --stack-name roofing-platform-vpc
```

### Step 2: Deploy RDS Database

```bash
# Get VPC outputs
VPC_ID=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`VPCId`].OutputValue' --output text)
PRIVATE_SUBNET_1=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnet1Id`].OutputValue' --output text)
PRIVATE_SUBNET_2=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnet2Id`].OutputValue' --output text)
RDS_SG=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`RDSSecurityGroupId`].OutputValue' --output text)

# Deploy RDS stack
aws cloudformation create-stack \
  --stack-name roofing-platform-rds \
  --template-body file://infrastructure/aws/rds.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=DBPassword,ParameterValue=YOUR_SECURE_PASSWORD \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=PrivateSubnet1Id,ParameterValue=$PRIVATE_SUBNET_1 \
    ParameterKey=PrivateSubnet2Id,ParameterValue=$PRIVATE_SUBNET_2 \
    ParameterKey=RDSSecurityGroupId,ParameterValue=$RDS_SG \
  --region us-east-1
```

### Step 3: Deploy EC2 and ALB

```bash
# Get VPC outputs
PUBLIC_SUBNET_1=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnet1Id`].OutputValue' --output text)
PUBLIC_SUBNET_2=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnet2Id`].OutputValue' --output text)
ALB_SG=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`ALBSecurityGroupId`].OutputValue' --output text)
EC2_SG=$(aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs[?OutputKey==`EC2SecurityGroupId`].OutputValue' --output text)

# Create key pair (if not exists)
aws ec2 create-key-pair --key-name roofing-platform-key --query 'KeyMaterial' --output text > roofing-platform-key.pem
chmod 400 roofing-platform-key.pem

# Deploy EC2/ALB stack
aws cloudformation create-stack \
  --stack-name roofing-platform-ec2-alb \
  --template-body file://infrastructure/aws/ec2-alb.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=KeyName,ParameterValue=roofing-platform-key \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=PublicSubnet1Id,ParameterValue=$PUBLIC_SUBNET_1 \
    ParameterKey=PublicSubnet2Id,ParameterValue=$PUBLIC_SUBNET_2 \
    ParameterKey=ALBSecurityGroupId,ParameterValue=$ALB_SG \
    ParameterKey=EC2SecurityGroupId,ParameterValue=$EC2_SG \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Step 4: Deploy S3 and CloudFront

```bash
# Deploy S3/CloudFront stack
aws cloudformation create-stack \
  --stack-name roofing-platform-s3-cloudfront \
  --template-body file://infrastructure/aws/s3-cloudfront.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=DomainName,ParameterValue=roofingplatform.com \
  --region us-east-1
```

### Step 5: Deploy Route 53 (Optional)

```bash
# Get ALB DNS name
ALB_DNS=$(aws cloudformation describe-stacks --stack-name roofing-platform-ec2-alb --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSName`].OutputValue' --output text)

# Get CloudFront domain
CF_DOMAIN=$(aws cloudformation describe-stacks --stack-name roofing-platform-s3-cloudfront --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomain`].OutputValue' --output text)

# Deploy Route 53 stack
aws cloudformation create-stack \
  --stack-name roofing-platform-route53 \
  --template-body file://infrastructure/aws/route53.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=DomainName,ParameterValue=roofingplatform.com \
    ParameterKey=LoadBalancerDNS,ParameterValue=$ALB_DNS \
    ParameterKey=CloudFrontDomain,ParameterValue=$CF_DOMAIN \
  --region us-east-1
```

## Container Setup

### Build and Push Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repositories
aws ecr create-repository --repository-name roofing-platform-backend --region us-east-1
aws ecr create-repository --repository-name roofing-platform-frontend --region us-east-1

# Build and push backend
docker build -f infrastructure/docker/backend.Dockerfile -t roofing-platform-backend .
docker tag roofing-platform-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/roofing-platform-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/roofing-platform-backend:latest

# Build and push frontend
docker build -f infrastructure/docker/frontend.Dockerfile -t roofing-platform-frontend .
docker tag roofing-platform-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/roofing-platform-frontend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/roofing-platform-frontend:latest
```

## Environment Configuration

### Application Environment Variables

Create environment files for each environment:

```bash
# .env.staging
DEBUG=False
SECRET_KEY=your-staging-secret-key
DB_NAME=roof_platform
DB_USER=admin
DB_PASSWORD=your-db-password
DB_HOST=your-rds-endpoint
DB_PORT=5432
REDIS_URL=redis://your-elasticache-endpoint:6379/0
ALLOWED_HOSTS=.roofingplatform.com
CORS_ALLOWED_ORIGINS=https://roofingplatform.com,https://staging.roofingplatform.com

# .env.production (similar structure)
```

## Monitoring and Logging

### CloudWatch Setup

```bash
# Create CloudWatch log groups
aws logs create-log-group --log-group-name roofing-platform-backend
aws logs create-log-group --log-group-name roofing-platform-frontend
aws logs create-log-group --log-group-name roofing-platform-nginx
```

### Monitoring Dashboard

The CloudFormation templates include CloudWatch alarms for:
- RDS CPU utilization (>80%)
- RDS free storage space (<2GB)
- EC2 auto scaling based on CPU

## Security Considerations

### Network Security
- All resources deployed in private subnets where possible
- Security groups follow least-privilege principle
- No SSH access from public internet (use AWS Systems Manager)

### Data Protection
- RDS encryption at rest
- S3 server-side encryption
- SSL/TLS for all communications

### Access Control
- IAM roles with minimal required permissions
- No hardcoded credentials
- Regular rotation of access keys

## Cost Optimization

### Reserved Instances
Consider purchasing Reserved Instances for production workloads to reduce EC2 costs by up to 75%.

### Auto Scaling
The auto scaling group automatically adjusts capacity based on demand, optimizing costs during low-traffic periods.

### S3 Lifecycle Policies
Automated lifecycle policies move infrequently accessed data to cheaper storage classes.

## Troubleshooting

### Common Issues

1. **Stack Creation Fails**
   - Check CloudTrail logs for detailed error messages
   - Verify parameter values and resource limits
   - Ensure dependencies are created in correct order

2. **Application Won't Start**
   - Check ECS service events and task logs
   - Verify environment variables are set correctly
   - Check security group rules allow necessary traffic

3. **Database Connection Issues**
   - Verify RDS endpoint and port are correct
   - Check security group allows traffic from EC2 instances
   - Ensure database credentials are correct

### Useful Commands

```bash
# Check stack status
aws cloudformation describe-stack-events --stack-name roofing-platform-vpc

# View stack outputs
aws cloudformation describe-stacks --stack-name roofing-platform-vpc --query 'Stacks[0].Outputs'

# Check ECS service status
aws ecs describe-services --cluster roofing-platform-production --services roofing-platform-backend-production

# View application logs
aws logs tail roofing-platform-backend --follow
```

## Maintenance

### Regular Tasks
- Monitor CloudWatch alarms and dashboards
- Review and rotate access keys quarterly
- Update AMIs and Docker images regularly
- Monitor costs and usage patterns

### Backup and Recovery
- RDS automated backups (7-day retention)
- S3 versioning for static assets
- Regular AMI backups for EC2 instances

### Scaling
- Monitor application performance metrics
- Adjust auto scaling policies as needed
- Consider upgrading instance types for better performance

## Support

For infrastructure-related issues:
1. Check AWS documentation and support forums
2. Review CloudWatch logs and metrics
3. Contact AWS support for account-specific issues
4. Consult the application logs for runtime errors
