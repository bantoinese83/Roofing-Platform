# Deployment Guide

This guide covers the complete deployment process for the Roofing Platform, including infrastructure setup, application deployment, and maintenance procedures.

## Prerequisites

### AWS Account Setup
1. Create AWS account with appropriate permissions
2. Configure AWS CLI:
   ```bash
   aws configure
   ```

3. Install required tools:
   - AWS CLI v2
   - Docker
   - Git
   - Node.js 18+
   - Python 3.11+

### Domain and SSL
1. Register domain (roofingplatform.com)
2. Request SSL certificates in AWS Certificate Manager
3. Configure DNS in Route 53

## Infrastructure Deployment

### 1. Deploy Core Infrastructure

```bash
# Deploy VPC
aws cloudformation create-stack \
  --stack-name roofing-platform-vpc \
  --template-body file://infrastructure/aws/vpc.yaml \
  --parameters ParameterKey=EnvironmentName,ParameterValue=roofing-platform

# Deploy RDS
aws cloudformation create-stack \
  --stack-name roofing-platform-rds \
  --template-body file://infrastructure/aws/rds.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=DBPassword,ParameterValue=$(openssl rand -base64 32)

# Deploy EC2 and ALB
aws cloudformation create-stack \
  --stack-name roofing-platform-ec2-alb \
  --template-body file://infrastructure/aws/ec2-alb.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=KeyName,ParameterValue=roofing-platform-key \
  --capabilities CAPABILITY_IAM

# Deploy S3 and CloudFront
aws cloudformation create-stack \
  --stack-name roofing-platform-s3-cloudfront \
  --template-body file://infrastructure/aws/s3-cloudfront.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=DomainName,ParameterValue=roofingplatform.com
```

### 2. Configure DNS (Optional)

```bash
# Deploy Route 53 configuration
aws cloudformation create-stack \
  --stack-name roofing-platform-route53 \
  --template-body file://infrastructure/aws/route53.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=roofing-platform \
    ParameterKey=DomainName,ParameterValue=roofingplatform.com
```

## Application Deployment

### Container Registry Setup

```bash
# Create ECR repositories
aws ecr create-repository --repository-name roofing-platform-backend
aws ecr create-repository --repository-name roofing-platform-frontend

# Login to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com
```

### Build and Push Images

```bash
# Build backend image
docker build -f infrastructure/docker/backend.Dockerfile -t roofing-platform-backend .
docker tag roofing-platform-backend:latest ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/roofing-platform-backend:latest
docker push ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/roofing-platform-backend:latest

# Build frontend image
docker build -f infrastructure/docker/frontend.Dockerfile -t roofing-platform-frontend .
docker tag roofing-platform-frontend:latest ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/roofing-platform-frontend:latest
docker push ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/roofing-platform-frontend:latest
```

### ECS Cluster Setup

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name roofing-platform-production

# Register task definitions
aws ecs register-task-definition --cli-input-json file://infrastructure/aws/ecs-task-definition.json

# Create services
aws ecs create-service \
  --cluster roofing-platform-production \
  --service-name roofing-platform-backend \
  --task-definition roofing-platform-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-123,subnet-456],securityGroups=[sg-abc]}"
```

## Environment Configuration

### Production Environment Variables

Create `.env.production` file:

```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=.roofingplatform.com,api.roofingplatform.com

# Database
DB_NAME=roof_platform
DB_USER=admin
DB_PASSWORD=your-secure-db-password
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432

# Redis/Celery
REDIS_URL=redis://your-elasticache-cluster:6379/0
CELERY_BROKER_URL=redis://your-elasticache-cluster:6379/0
CELERY_RESULT_BACKEND=redis://your-elasticache-cluster:6379/0

# CORS
CORS_ALLOWED_ORIGINS=https://roofingplatform.com,https://www.roofingplatform.com

# Third-party Services
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890
GOOGLE_MAPS_API_KEY=your-maps-api-key

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

## CI/CD Pipeline Setup

### GitHub Actions Configuration

1. **Repository Secrets Setup:**
   ```bash
   # AWS Credentials
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1

   # Slack Notifications
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

   # Production Configuration
   PRIVATE_SUBNET_1=subnet-12345
   PRIVATE_SUBNET_2=subnet-67890
   ECS_SECURITY_GROUP=sg-abcdef
   ```

2. **Branch Protection Rules:**
   - Require PR reviews
   - Require status checks
   - Include administrators

### Manual Deployment (Alternative)

```bash
# Use deployment script
chmod +x scripts/deploy/deploy.sh
./scripts/deploy/deploy.sh production
```

## Database Setup

### Initial Migration

```bash
# Run migrations on production
aws ecs run-task \
  --cluster roofing-platform-production \
  --task-definition roofing-platform-migration \
  --overrides "containerOverrides=[{name=backend,command=[\"python\",\"manage.py\",\"migrate\"]}]"
```

### Create Superuser

```bash
# Create admin user
aws ecs run-task \
  --cluster roofing-platform-production \
  --task-definition roofing-platform-migration \
  --overrides "containerOverrides=[{name=backend,command=[\"python\",\"manage.py\",\"createsuperuser\",\"--noinput\",\"--username\",\"admin\",\"--email\",\"admin@roofingplatform.com\"]}]"
```

## Monitoring Setup

### CloudWatch Configuration

```bash
# Create log groups
aws logs create-log-group --log-group-name roofing-platform-backend
aws logs create-log-group --log-group-name roofing-platform-frontend

# Set up alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "RoofingPlatform-HighCPU" \
  --alarm-description "CPU utilization above 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

### Application Monitoring

1. **Health Checks:** Configure ALB health checks
2. **Logging:** Enable CloudWatch logging for ECS tasks
3. **Metrics:** Monitor key application metrics
4. **Alerts:** Set up SNS notifications for critical alerts

## Security Configuration

### SSL/TLS Setup

1. **Certificate Manager:** Request certificates for domain
2. **ALB Configuration:** Configure HTTPS listeners
3. **CloudFront:** Set up SSL for CDN distribution

### Network Security

1. **Security Groups:** Configure least-privilege rules
2. **WAF:** Set up Web Application Firewall rules
3. **Shield:** Enable AWS Shield for DDoS protection

### Access Control

1. **IAM Roles:** Create least-privilege roles
2. **Secrets Manager:** Store sensitive configuration
3. **Parameter Store:** Store non-sensitive configuration

## Backup and Recovery

### Database Backups

```bash
# Configure automated backups
aws rds modify-db-instance \
  --db-instance-identifier roofing-platform-db \
  --backup-retention-period 7 \
  --preferred-backup-window 03:00-04:00
```

### Application Backups

1. **AMI Backups:** Regular EC2 instance backups
2. **S3 Versioning:** Enable versioning for critical buckets
3. **Container Images:** Backup ECR repositories

## Performance Optimization

### Auto Scaling

```bash
# Configure auto scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/roofing-platform-production/roofing-platform-backend \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --policy-name cpu-scaling \
  --service-namespace ecs \
  --resource-id service/roofing-platform-production/roofing-platform-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration "TargetValue=70.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization}"
```

### CDN Optimization

1. **Cache Behaviors:** Configure appropriate cache policies
2. **Compression:** Enable gzip compression
3. **Edge Locations:** Utilize global CloudFront distribution

## Maintenance Procedures

### Regular Tasks

1. **Security Updates:** Apply security patches monthly
2. **Dependency Updates:** Update dependencies quarterly
3. **Performance Monitoring:** Review metrics weekly
4. **Backup Verification:** Test backups monthly

### Emergency Procedures

1. **Service Restart:** Force deployment for stuck services
2. **Rollback:** Quick rollback to previous version
3. **Scale Up:** Emergency scaling for traffic spikes
4. **Database Recovery:** Restore from backup if needed

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check ECS service events
aws ecs describe-services --cluster roofing-platform-production --services roofing-platform-backend

# View container logs
aws logs tail /ecs/roofing-platform-backend --follow
```

#### Database Connection Issues
```bash
# Check RDS status
aws rds describe-db-instances --db-instance-identifier roofing-platform-db

# Verify security groups
aws ec2 describe-security-groups --group-ids sg-12345
```

#### Load Balancer Issues
```bash
# Check ALB health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/tg-name/id
```

## Cost Optimization

### Reserved Instances
```bash
# Purchase RI for production workloads
aws ec2 purchase-reserved-instances-offering \
  --reserved-instances-offering-id offering-id \
  --instance-count 2
```

### Storage Optimization
```bash
# Configure S3 lifecycle policies
aws s3api put-bucket-lifecycle-configuration \
  --bucket roofing-platform-media \
  --lifecycle-configuration file://lifecycle-policy.json
```

## Support and Documentation

### Useful Commands

```bash
# Check service status
aws ecs describe-services --cluster roofing-platform-production

# View logs
aws logs tail roofing-platform-backend --follow

# Check CloudWatch alarms
aws cloudwatch describe-alarms --alarm-names-prefix "RoofingPlatform"

# Monitor costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost
```

### Support Contacts

- **AWS Support:** For infrastructure issues
- **DevOps Team:** For deployment and monitoring issues
- **Development Team:** For application-specific issues

### Documentation Links

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Application Documentation](./README.md)

## Checklist

### Pre-Deployment
- [ ] Domain registered and DNS configured
- [ ] SSL certificates issued
- [ ] AWS account permissions verified
- [ ] Environment variables prepared
- [ ] Database backups configured

### Post-Deployment
- [ ] Application accessible via domain
- [ ] SSL certificates working
- [ ] Monitoring and alerts configured
- [ ] Backup procedures tested
- [ ] Documentation updated

### Maintenance
- [ ] Regular security updates
- [ ] Performance monitoring
- [ ] Cost optimization
- [ ] Backup verification
