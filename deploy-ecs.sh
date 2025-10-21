#!/bin/bash

# GhostCart ECS Fargate Deployment Script
# Deploys backend to ECS with Application Load Balancer

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 GhostCart ECS Fargate Deployment${NC}"
echo "===================================="

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="ghostcart-backend"
CLUSTER_NAME="ghostcart-cluster"
SERVICE_NAME="ghostcart-backend-service"
TASK_FAMILY="ghostcart-backend"

# Get AWS Account ID
echo -e "\n${YELLOW}Getting AWS account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# Create ECR repository if it doesn't exist
echo -e "\n${YELLOW}Checking ECR repository...${NC}"
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION &> /dev/null; then
    echo "Creating ECR repository..."
    aws ecr create-repository \
        --repository-name $ECR_REPOSITORY \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true
    echo -e "${GREEN}✓ ECR repository created${NC}"
else
    echo -e "${GREEN}✓ ECR repository exists${NC}"
fi

# Login to ECR
echo -e "\n${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo -e "${GREEN}✓ Logged in to ECR${NC}"

# Build Docker image
echo -e "\n${YELLOW}Building backend Docker image...${NC}"
docker build -f backend-only.Dockerfile -t $ECR_REPOSITORY:latest .
echo -e "${GREEN}✓ Docker image built${NC}"

# Tag and push image
echo -e "\n${YELLOW}Pushing image to ECR...${NC}"
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
echo -e "${GREEN}✓ Image pushed to ECR${NC}"

# Create CloudWatch log group
echo -e "\n${YELLOW}Creating CloudWatch log group...${NC}"
aws logs create-log-group --log-group-name /ecs/ghostcart-backend --region $AWS_REGION 2>/dev/null || echo "Log group already exists"
echo -e "${GREEN}✓ Log group ready${NC}"

# Update task definition with account ID
echo -e "\n${YELLOW}Preparing task definition...${NC}"
sed "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" ecs-task-definition.json > ecs-task-definition-updated.json

# Register task definition
echo -e "\n${YELLOW}Registering ECS task definition...${NC}"
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition-updated.json \
    --region $AWS_REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)
echo -e "${GREEN}✓ Task definition registered: $TASK_DEFINITION_ARN${NC}"

# Clean up temp file
rm ecs-task-definition-updated.json

# Check if cluster exists
echo -e "\n${YELLOW}Checking ECS cluster...${NC}"
if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text | grep -q ACTIVE; then
    echo -e "${RED}❌ ECS cluster '$CLUSTER_NAME' not found${NC}"
    echo -e "${YELLOW}Please run the infrastructure setup script first:${NC}"
    echo -e "  ./infrastructure/ecs-setup.sh"
    exit 1
fi
echo -e "${GREEN}✓ ECS cluster exists${NC}"

# Update or create service
echo -e "\n${YELLOW}Checking ECS service...${NC}"
if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text | grep -q ACTIVE; then
    echo "Updating existing service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_DEFINITION_ARN \
        --force-new-deployment \
        --region $AWS_REGION \
        --query 'service.serviceName' \
        --output text
    echo -e "${GREEN}✓ Service updated${NC}"
else
    echo -e "${YELLOW}Service not found. Please create it using the infrastructure setup script.${NC}"
    echo -e "  ./infrastructure/ecs-setup.sh"
    exit 1
fi

# Get ALB DNS name
echo -e "\n${YELLOW}Getting ALB endpoint...${NC}"
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names ghostcart-alb \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text 2>/dev/null || echo "")

if [ -n "$ALB_DNS" ]; then
    echo -e "\n${GREEN}✅ Deployment complete!${NC}"
    echo -e "${GREEN}🌐 Backend API: http://$ALB_DNS${NC}"
    echo -e "${GREEN}🏥 Health check: http://$ALB_DNS/api/health${NC}"
    echo -e "\n${YELLOW}Note: It may take 2-3 minutes for the service to become healthy${NC}"
else
    echo -e "\n${GREEN}✅ Deployment complete!${NC}"
    echo -e "${YELLOW}Run 'aws elbv2 describe-load-balancers --names ghostcart-alb' to get the ALB endpoint${NC}"
fi

echo -e "\n${GREEN}✨ Deployment script completed!${NC}"
