#!/bin/bash

# GhostCart ECS Infrastructure Setup
# Creates ECS cluster, ALB, security groups, and IAM roles

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🏗️  GhostCart ECS Infrastructure Setup${NC}"
echo "========================================"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="ghostcart-cluster"
SERVICE_NAME="ghostcart-backend-service"
ALB_NAME="ghostcart-alb"
TARGET_GROUP_NAME="ghostcart-tg"

# Get AWS Account ID
echo -e "\n${YELLOW}Getting AWS account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# Get default VPC
echo -e "\n${YELLOW}Getting default VPC...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region $AWS_REGION --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo -e "${RED}❌ No default VPC found. Please create a VPC first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Using VPC: $VPC_ID${NC}"

# Get subnets
echo -e "\n${YELLOW}Getting subnets...${NC}"
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --region $AWS_REGION --query 'Subnets[*].SubnetId' --output text)
SUBNET_1=$(echo $SUBNETS | awk '{print $1}')
SUBNET_2=$(echo $SUBNETS | awk '{print $2}')

if [ -z "$SUBNET_1" ] || [ -z "$SUBNET_2" ]; then
    echo -e "${RED}❌ Need at least 2 subnets. Found: $SUBNETS${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Using subnets: $SUBNET_1, $SUBNET_2${NC}"

# Create security group for ALB
echo -e "\n${YELLOW}Creating ALB security group...${NC}"
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name ghostcart-alb-sg \
    --description "Security group for GhostCart ALB" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=ghostcart-alb-sg" "Name=vpc-id,Values=$VPC_ID" \
        --region $AWS_REGION \
        --query 'SecurityGroups[0].GroupId' \
        --output text)

# Allow HTTP traffic to ALB
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "Ingress rule already exists"

echo -e "${GREEN}✓ ALB Security Group: $ALB_SG_ID${NC}"

# Create security group for ECS tasks
echo -e "\n${YELLOW}Creating ECS task security group...${NC}"
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name ghostcart-ecs-sg \
    --description "Security group for GhostCart ECS tasks" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=ghostcart-ecs-sg" "Name=vpc-id,Values=$VPC_ID" \
        --region $AWS_REGION \
        --query 'SecurityGroups[0].GroupId' \
        --output text)

# Allow traffic from ALB to ECS tasks
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG_ID \
    --region $AWS_REGION 2>/dev/null || echo "Ingress rule already exists"

echo -e "${GREEN}✓ ECS Security Group: $ECS_SG_ID${NC}"

# Create ECS cluster
echo -e "\n${YELLOW}Creating ECS cluster...${NC}"
aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --region $AWS_REGION 2>/dev/null || echo "Cluster already exists"
echo -e "${GREEN}✓ ECS Cluster: $CLUSTER_NAME${NC}"

# Create Application Load Balancer
echo -e "\n${YELLOW}Creating Application Load Balancer...${NC}"
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name $ALB_NAME \
    --subnets $SUBNET_1 $SUBNET_2 \
    --security-groups $ALB_SG_ID \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null || \
    aws elbv2 describe-load-balancers \
        --names $ALB_NAME \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text)

echo -e "${GREEN}✓ ALB ARN: $ALB_ARN${NC}"

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text)
echo -e "${GREEN}✓ ALB DNS: $ALB_DNS${NC}"

# Create target group
echo -e "\n${YELLOW}Creating target group...${NC}"
TG_ARN=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_NAME \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /api/health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || \
    aws elbv2 describe-target-groups \
        --names $TARGET_GROUP_NAME \
        --region $AWS_REGION \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)

echo -e "${GREEN}✓ Target Group ARN: $TG_ARN${NC}"

# Create ALB listener
echo -e "\n${YELLOW}Creating ALB listener...${NC}"
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --region $AWS_REGION 2>/dev/null || echo "Listener already exists"
echo -e "${GREEN}✓ ALB Listener created${NC}"

# Create ECS Task Execution Role if it doesn't exist
echo -e "\n${YELLOW}Checking ECS Task Execution Role...${NC}"
if ! aws iam get-role --role-name ecsTaskExecutionRole &>/dev/null; then
    echo "Creating ecsTaskExecutionRole..."
    aws iam create-role \
        --role-name ecsTaskExecutionRole \
        --assume-role-policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        }'
    
    aws iam attach-role-policy \
        --role-name ecsTaskExecutionRole \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    
    echo -e "${GREEN}✓ ecsTaskExecutionRole created${NC}"
else
    echo -e "${GREEN}✓ ecsTaskExecutionRole exists${NC}"
fi

# Create ECS Task Role with Bedrock permissions
echo -e "\n${YELLOW}Setting up ECS Task Role with Bedrock permissions...${NC}"

# Create Bedrock policy if it doesn't exist
BEDROCK_POLICY_NAME="GhostCartBedrockPolicy"
BEDROCK_POLICY_ARN=$(aws iam list-policies \
    --scope Local \
    --query "Policies[?PolicyName=='$BEDROCK_POLICY_NAME'].Arn" \
    --output text 2>/dev/null || echo "")

if [ -z "$BEDROCK_POLICY_ARN" ]; then
    echo "Creating Bedrock IAM policy..."
    cat > /tmp/bedrock-policy.json << 'POLICY_EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*:*:inference-profile/*"
      ]
    }
  ]
}
POLICY_EOF

    BEDROCK_POLICY_ARN=$(aws iam create-policy \
        --policy-name $BEDROCK_POLICY_NAME \
        --policy-document file:///tmp/bedrock-policy.json \
        --description "Allows ECS tasks to invoke AWS Bedrock models" \
        --query 'Policy.Arn' \
        --output text)
    
    rm /tmp/bedrock-policy.json
    echo -e "${GREEN}✓ Bedrock policy created: $BEDROCK_POLICY_ARN${NC}"
else
    echo -e "${GREEN}✓ Bedrock policy exists: $BEDROCK_POLICY_ARN${NC}"
fi

# Create task role if it doesn't exist
TASK_ROLE_NAME="ghostcart-ecs-task-role"
if ! aws iam get-role --role-name $TASK_ROLE_NAME &>/dev/null; then
    echo "Creating ECS task role..."
    aws iam create-role \
        --role-name $TASK_ROLE_NAME \
        --assume-role-policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        }' \
        --description "Task role for GhostCart ECS tasks to access AWS services"
    
    echo -e "${GREEN}✓ Task role created${NC}"
else
    echo -e "${GREEN}✓ Task role exists${NC}"
fi

# Attach Bedrock policy to task role
aws iam attach-role-policy \
    --role-name $TASK_ROLE_NAME \
    --policy-arn $BEDROCK_POLICY_ARN 2>/dev/null || echo "Policy already attached"

echo -e "${GREEN}✓ Bedrock permissions configured for ECS tasks${NC}"

TASK_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$TASK_ROLE_NAME"

# Create ECS Service
echo -e "\n${YELLOW}Creating ECS service...${NC}"
if ! aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
    echo "Creating ECS service..."
    
    # Get the latest task definition
    TASK_DEF=$(aws ecs list-task-definitions --family-prefix ghostcart-backend --region $AWS_REGION --query 'taskDefinitionArns[-1]' --output text)
    
    if [ -z "$TASK_DEF" ] || [ "$TASK_DEF" == "None" ]; then
        echo -e "${YELLOW}⚠️  No task definition found yet. Run ./deploy-ecs.sh to create and deploy.${NC}"
    else
        # Create the service
        aws ecs create-service \
            --cluster $CLUSTER_NAME \
            --service-name $SERVICE_NAME \
            --task-definition $TASK_DEF \
            --desired-count 1 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
            --load-balancers "targetGroupArn=$TG_ARN,containerName=ghostcart-backend,containerPort=8000" \
            --region $AWS_REGION \
            --query 'service.serviceName' \
            --output text
        
        echo -e "${GREEN}✓ ECS service created${NC}"
    fi
else
    echo -e "${GREEN}✓ ECS service already exists${NC}"
fi

# Save configuration
echo -e "\n${YELLOW}Saving configuration...${NC}"
cat > infrastructure/config.sh << EOF
# GhostCart Infrastructure Configuration
export AWS_REGION="$AWS_REGION"
export AWS_ACCOUNT_ID="$AWS_ACCOUNT_ID"
export VPC_ID="$VPC_ID"
export SUBNET_1="$SUBNET_1"
export SUBNET_2="$SUBNET_2"
export ALB_SG_ID="$ALB_SG_ID"
export ECS_SG_ID="$ECS_SG_ID"
export CLUSTER_NAME="$CLUSTER_NAME"
export SERVICE_NAME="$SERVICE_NAME"
export TASK_FAMILY="ghostcart-backend"
export ALB_ARN="$ALB_ARN"
export ALB_DNS="$ALB_DNS"
export TG_ARN="$TG_ARN"
export TASK_ROLE_ARN="$TASK_ROLE_ARN"
EOF

echo -e "${GREEN}✓ Configuration saved to infrastructure/config.sh${NC}"

echo -e "\n${GREEN}✅ Infrastructure setup complete!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Run: chmod +x deploy-ecs.sh"
echo -e "2. Run: ./deploy-ecs.sh"
echo -e "\n${GREEN}Your backend will be available at: http://$ALB_DNS${NC}"
