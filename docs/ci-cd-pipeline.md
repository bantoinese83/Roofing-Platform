# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Roofing Platform, implemented using GitHub Actions.

## Pipeline Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Push/PR   │───▶│   Testing   │───▶│   Build     │───▶│ Deployment  │
│             │    │   Backend   │    │   Images    │    │             │
└─────────────┘    │   Frontend  │    └─────────────┘    └─────────────┘
                   └─────────────┘
```

## Workflow Structure

### 1. CI/CD Main Pipeline (`.github/workflows/ci-cd.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

#### `backend-test`
- **Environment:** Ubuntu latest with PostgreSQL and Redis services
- **Steps:**
  - Checkout code
  - Set up Python 3.11
  - Cache pip dependencies
  - Install dependencies
  - Run database migrations
  - Execute backend tests
  - Upload coverage reports to Codecov

#### `frontend-test`
- **Environment:** Ubuntu latest with Node.js 18
- **Steps:**
  - Checkout code
  - Set up Node.js with npm caching
  - Install dependencies
  - Run ESLint
  - Run TypeScript type checking
  - Execute frontend tests
  - Upload coverage reports

#### `build-and-push`
- **Dependencies:** `backend-test` and `frontend-test`
- **Condition:** Runs on `main` or `develop` branches
- **Steps:**
  - Set up Docker Buildx
  - Login to GitHub Container Registry
  - Build and push backend Docker image
  - Build and push frontend Docker image
  - Generate appropriate tags (branch, PR, SHA)

#### `deploy-staging`
- **Dependencies:** `build-and-push`
- **Condition:** Runs on `develop` branch push
- **Environment:** `staging`
- **Steps:**
  - Configure AWS credentials
  - Deploy to ECS staging environment

#### `deploy-production`
- **Dependencies:** `build-and-push`
- **Condition:** Runs on `main` branch push
- **Environment:** `production`
- **Steps:**
  - Configure AWS credentials
  - Run database migrations
  - Deploy backend to production
  - Deploy frontend to production
  - Run health checks
  - Send Slack notifications

### 2. Security Pipeline (`.github/workflows/security.yml`)

**Triggers:**
- Push/PR to main/develop branches
- Weekly schedule (Sundays at midnight)

**Jobs:**

#### `backend-security`
- Bandit security scanning
- Safety dependency vulnerability check

#### `frontend-security`
- NPM audit for vulnerabilities
- Trivy container vulnerability scanning
- SARIF report generation

#### `container-security`
- Build images for scanning
- Trivy image vulnerability scanning
- Upload security reports

#### `dependency-updates`
- Automated dependency updates (weekly)
- Separate PRs for backend and frontend

#### `sast` (Static Application Security Testing)
- CodeQL analysis for Python and JavaScript
- Automated security vulnerability detection

#### `secret-scan`
- TruffleHog secret detection
- Git history scanning for exposed secrets

## Environment Configuration

### GitHub Secrets Required

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION

# Container Registry
GITHUB_TOKEN (automatically provided)

# Notification
SLACK_WEBHOOK_URL

# Production Environment
PRIVATE_SUBNET_1
PRIVATE_SUBNET_2
ECS_SECURITY_GROUP
```

### Environment Variables

#### Staging Environment
```yaml
environment: staging
```

#### Production Environment
```yaml
environment: production
```

## Branch Strategy

### Development Workflow
1. **Feature Branch:** `feature/feature-name`
2. **Pull Request:** Merge to `develop`
3. **Staging Deployment:** Automatic on `develop` push
4. **Production Deployment:** Manual approval on `main` merge

### Branch Protection Rules

#### `main` Branch
- Require pull request reviews
- Require status checks to pass
- Require branches to be up to date
- Include administrators in restrictions

#### `develop` Branch
- Require pull request reviews
- Require status checks to pass

## Deployment Strategy

### Blue-Green Deployment
- Zero-downtime deployments using ECS
- Traffic shifting between old and new versions
- Automatic rollback on health check failures

### Database Migrations
- Automatic migration execution on production deployment
- Manual migration tasks for complex schema changes
- Backup verification before migrations

### Health Checks
- Application health endpoints (`/health/`)
- Database connectivity checks
- External service availability
- Response time monitoring

## Monitoring and Alerting

### Application Monitoring
- CloudWatch logs aggregation
- Application performance metrics
- Error tracking and alerting
- Custom dashboards

### Pipeline Monitoring
- GitHub Actions run history
- Success/failure notifications
- Performance metrics
- Security scan results

### Deployment Monitoring
- ECS service health
- Load balancer metrics
- Database performance
- CDN cache hit rates

## Troubleshooting

### Common Issues

#### Build Failures
```bash
# Check build logs in GitHub Actions
# Verify dependency versions
# Check for syntax errors
# Validate environment variables
```

#### Test Failures
```bash
# Run tests locally first
# Check database connectivity
# Verify test data setup
# Review error messages in detail
```

#### Deployment Failures
```bash
# Check ECS service events
# Review CloudWatch logs
# Verify environment variables
# Check security group rules
# Validate IAM permissions
```

### Debugging Commands

```bash
# Check pipeline status
gh run list --workflow=ci-cd.yml

# View pipeline logs
gh run view <run-id> --log

# Check deployment status
aws ecs describe-services --cluster roofing-platform-production --services roofing-platform-backend-production

# View application logs
aws logs tail roofing-platform-backend --follow
```

## Security Best Practices

### Pipeline Security
- No hardcoded secrets in code
- Least-privilege IAM roles
- Regular dependency updates
- Automated security scanning
- Secret detection in commits

### Code Security
- SAST (Static Application Security Testing)
- Dependency vulnerability scanning
- Container image scanning
- Secret leak detection

### Access Control
- Branch protection rules
- Required reviews for production changes
- Environment-specific secrets
- Audit logging

## Performance Optimization

### Build Optimization
- Docker layer caching
- Dependency caching (pip, npm)
- Parallel job execution
- Selective builds (only changed services)

### Deployment Optimization
- Blue-green deployments
- Health check-based rollouts
- Automated rollbacks
- CDN invalidation

### Monitoring Optimization
- Log aggregation
- Metric filtering
- Alert thresholds
- Dashboard customization

## Cost Optimization

### Pipeline Costs
- Scheduled jobs only when needed
- Efficient resource usage
- Cache utilization
- Parallel execution

### Infrastructure Costs
- Auto scaling based on demand
- Reserved instances for production
- Spot instances for CI/CD
- Storage lifecycle policies

## Maintenance

### Regular Tasks
- Update GitHub Actions versions
- Review and update security rules
- Clean up old container images
- Monitor pipeline performance
- Update dependencies

### Emergency Procedures
- Manual deployment override
- Pipeline pause/resume
- Emergency rollback procedures
- Incident response plan

## Integration with Other Tools

### Code Quality
- ESLint for JavaScript/TypeScript
- Black/Flake8 for Python
- Pre-commit hooks
- Code coverage reporting

### Documentation
- Automated API documentation
- Deployment runbooks
- Troubleshooting guides
- Change logs

### Communication
- Slack notifications
- Email alerts
- Dashboard sharing
- Status page updates

## Future Enhancements

### Planned Improvements
- Multi-region deployments
- Canary deployments
- Feature flags integration
- Advanced monitoring dashboards
- Automated performance testing
- Chaos engineering integration

### Tool Integration
- Jira for issue tracking
- SonarQube for code quality
- PagerDuty for incident response
- Datadog for advanced monitoring

## Support

For CI/CD pipeline issues:
1. Check GitHub Actions documentation
2. Review AWS ECS documentation
3. Check application logs in CloudWatch
4. Contact DevOps team for infrastructure issues

### Useful Links
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [ECS Deployment Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
