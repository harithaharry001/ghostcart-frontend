# GhostCart Infrastructure

AWS deployment infrastructure for GhostCart using ECS Fargate and Application Load Balancer.

## Quick Start

### 1. Setup Infrastructure
```bash
chmod +x infrastructure/ecs-setup.sh
./infrastructure/ecs-setup.sh
```

Creates: ECS cluster, ALB, security groups, target groups, IAM roles

### 2. Deploy Application
```bash
chmod +x deploy-ecs.sh
./deploy-ecs.sh
```

Builds Docker image, pushes to ECR, updates ECS service

### 3. Configure HTTPS (Optional)
```bash
chmod +x infrastructure/configure-https-route53.sh
./infrastructure/configure-https-route53.sh
```

## Architecture

```
Internet → Route 53 (optional) → ALB → ECS Fargate → CloudWatch
```

## Components

- **ECS Fargate**: Serverless container hosting (1 vCPU, 2GB RAM)
- **Application Load Balancer**: HTTP/HTTPS routing with health checks
- **ECR**: Docker image registry
- **CloudWatch**: Logging and monitoring
- **Route 53**: DNS management (optional)
- **ACM**: SSL certificates (optional)

## Configuration

After setup, config saved to `infrastructure/config.sh`:
- AWS_REGION, AWS_ACCOUNT_ID
- VPC_ID, SUBNET_1, SUBNET_2
- ALB_SG_ID, ECS_SG_ID
- CLUSTER_NAME, SERVICE_NAME
- ALB_ARN, ALB_DNS, TG_ARN

## Monitoring

```bash
# View logs
aws logs tail /ecs/ghostcart-backend --follow

# Check service
aws ecs describe-services --cluster ghostcart-cluster --services ghostcart-backend-service

# Check health
aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

## Scaling

```bash
# Manual scaling
aws ecs update-service --cluster ghostcart-cluster --service ghostcart-backend-service --desired-count 2
```

## Cost Estimate

~$65-70/month:
- ECS Fargate: ~$30
- ALB: ~$20
- Data Transfer: ~$10
- CloudWatch: ~$5
- ECR: ~$1

## Troubleshooting

**Task fails to start**: Check CloudWatch logs, verify IAM permissions
**Health check fails**: Verify /api/health endpoint, check security groups
**Cannot access**: Check ALB DNS, security groups, Route 53 records

## Cleanup

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
```

## Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [ALB Guide](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)

---

For application docs, see [README.md](../README.md)
