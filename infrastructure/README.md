# Strands AP2 Payment Agent Infrastructure

AWS deployment infrastructure for Strands AP2 Payment Agent using ECS Fargate, Application Load Balancer, and AWS Amplify.

## Quick Start

### Backend Deployment (ECS)

#### 1. Setup Infrastructure
```bash
chmod +x infrastructure/ecs-setup.sh
./infrastructure/ecs-setup.sh
```

Creates: ECS cluster, ALB, security groups, target groups, IAM roles

#### 2. Deploy Backend
```bash
chmod +x deploy-ecs.sh
./deploy-ecs.sh
```

Builds Docker image, pushes to ECR, updates ECS service

#### 3. Configure HTTPS with CloudFront
```bash
chmod +x infrastructure/configure-cloudfront.sh
./infrastructure/configure-cloudfront.sh
```

### Frontend Deployment (Amplify)

#### 4. Deploy Frontend to AWS Amplify
```bash
chmod +x deploy-amplify.sh
./deploy-amplify.sh
```

**What it does:**
- Creates/updates AWS Amplify app
- Connects to GitHub repository
- Sets backend API URL as environment variable
- Triggers build and deployment
- Provides HTTPS URL automatically

**Requirements:**
- Backend must be deployed first (needs ALB URL)
- GitHub repository access configured

**First-time setup:**
```bash
# 1. Ensure backend is deployed
./infrastructure/ecs-setup.sh
./deploy-ecs.sh

# 2. Deploy frontend
./deploy-amplify.sh
```

**Subsequent deployments:**
```bash
# Just run deploy script - it auto-detects existing app
./deploy-amplify.sh
```

**Check deployment status:**
```bash
aws amplify list-jobs \
    --app-id <APP_ID> \
    --branch-name main \
    --max-results 5
```

## Architecture

### Complete Stack
```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                            │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             │ Frontend                       │ API Calls
             ▼                                ▼
    ┌─────────────────┐            ┌──────────────────┐
    │  AWS Amplify    │            │   CloudFront     │
    │  (React SPA)    │            │                  │
    │  - Auto HTTPS   │            └────────┬─────────┘
    │  - CDN          │                     │
    │  - CI/CD        │                     ▼
    └─────────────────┘            ┌──────────────────┐
                                   │       ALB        │
                                   │  (Load Balancer) │
                                   └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │   ECS Fargate    │
                                   │  (Backend API)   │
                                   │  - Python/FastAPI│
                                   │  - AWS Bedrock   |
                                   │  - Strands SDK   |
                                   └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │   CloudWatch     │
                                   │  (Logs/Metrics)  │
                                   └──────────────────┘
```

### Backend Only
```
Internet → CloudFront → ALB → ECS Fargate → CloudWatch
```

## Components

### Backend (ECS)
- **ECS Fargate**: Serverless container hosting (1 vCPU, 2GB RAM)
- **Application Load Balancer**: HTTP routing with health checks
- **CloudFront**: CDN and HTTPS termination (optional)
- **ECR**: Docker image registry
- **CloudWatch**: Logging and monitoring
- **IAM Roles**: Task execution and Bedrock access

### Frontend (Amplify)
- **AWS Amplify**: Managed hosting for React SPA
- **Built-in CDN**: Global content delivery
- **Auto HTTPS**: SSL certificates managed automatically
- **CI/CD**: Automatic builds on git push
- **Environment Variables**: Backend API URL configuration

## Configuration

### Backend Config
After ECS setup, config saved to `infrastructure/config.sh`:
- AWS_REGION, AWS_ACCOUNT_ID
- VPC_ID, SUBNET_1, SUBNET_2
- ALB_SG_ID, ECS_SG_ID
- CLUSTER_NAME, SERVICE_NAME
- ALB_ARN, ALB_DNS, TG_ARN
- TASK_ROLE_ARN

### Frontend Config
Amplify configuration in `frontend/amplify.yml`:
- Build commands
- Output directory
- Node version
- Environment variables (VITE_API_BASE_URL)

## Monitoring

### Backend (ECS)
```bash
# View logs
aws logs tail /ecs/ghostcart-backend --follow

# Check service
aws ecs describe-services --cluster ghostcart-cluster --services ghostcart-backend-service

# Check health
aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

### Frontend (Amplify)
```bash
# List apps
aws amplify list-apps

# Get app details
aws amplify get-app --app-id <APP_ID>
```

## Scaling

```bash
# Manual scaling
aws ecs update-service --cluster ghostcart-cluster --service ghostcart-backend-service --desired-count 2
```

## Troubleshooting

### Backend Issues
**Task fails to start**: Check CloudWatch logs, verify IAM permissions for Bedrock
**Health check fails**: Verify /api/health endpoint, check security groups
**Cannot access**: Check ALB DNS, security groups, CloudFront distribution (if configured)
**Bedrock errors**: Verify task role has bedrock:InvokeModel permissions

### Frontend Issues
**Build fails**: Check amplify.yml syntax, verify Node version compatibility
**API calls fail**: Verify VITE_API_BASE_URL is set correctly, check CORS settings
**Cannot access**: Check Amplify app status, verify branch is connected
**Environment variables not working**: Redeploy after updating variables


## Cleanup

### Frontend (Amplify)
```bash
# Get app ID
APP_ID=$(aws amplify list-apps --query "apps[?name=='strands-ap2-payment-agent'].appId" --output text)

# Delete app
aws amplify delete-app --app-id $APP_ID
```

### Backend (ECS)
```bash
# Delete service
aws ecs update-service --cluster ghostcart-cluster --service ghostcart-backend-service --desired-count 0
aws ecs delete-service --cluster ghostcart-cluster --service ghostcart-backend-service

# Delete cluster
aws ecs delete-cluster --cluster ghostcart-cluster

# Delete ALB and target group
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# Delete security groups
aws ec2 delete-security-group --group-id $ALB_SG_ID
aws ec2 delete-security-group --group-id $ECS_SG_ID

# Delete ECR repository
aws ecr delete-repository --repository-name ghostcart-backend --force
```

## Resources

### AWS Documentation
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Amplify Documentation](https://docs.aws.amazon.com/amplify/)
- [Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Amplify Pricing](https://aws.amazon.com/amplify/pricing/)
- [ALB Guide](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)

### Deployment Scripts
- `infrastructure/ecs-setup.sh` - Backend infrastructure setup
- `deploy-ecs.sh` - Backend deployment
- `deploy-amplify.sh` - Frontend deployment
- `infrastructure/configure-cloudfront.sh` - Optional HTTPS setup

---

For application docs, see [README.md](../README.md)
