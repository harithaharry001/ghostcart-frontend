#!/bin/bash

# Strands AP2 Payment Agent Amplify Deployment Script
# Deploys frontend to AWS Amplify

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 GhostCart Amplify Deployment${NC}"
echo "===================================="

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
APP_NAME="strands-ap2-payment-agent"
BRANCH_NAME="main"
REPO_URL="git@github.com:harithaharry001/ghostcart-frontend.git"

# Get backend URL from infrastructure config
if [ -f "infrastructure/config.sh" ]; then
    source infrastructure/config.sh
    BACKEND_URL="http://${ALB_DNS}/api"
    echo -e "${GREEN}✓ Backend URL: $BACKEND_URL${NC}"
else
    echo -e "${YELLOW}⚠️  infrastructure/config.sh not found${NC}"
    echo -e "${YELLOW}Please enter your backend ALB URL:${NC}"
    read -p "Backend URL (e.g., http://ghostcart-alb-xxx.us-east-1.elb.amazonaws.com/api): " BACKEND_URL
fi

# Check if app already exists
echo -e "\n${YELLOW}Checking if Amplify app exists...${NC}"
APP_ID=$(aws amplify list-apps --region $AWS_REGION --query "apps[?name=='$APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -n "$APP_ID" ]; then
    echo -e "${GREEN}✓ Amplify app exists: $APP_ID${NC}"
    
    # Update environment variables
    echo -e "\n${YELLOW}Updating environment variables...${NC}"
    aws amplify update-app \
        --app-id $APP_ID \
        --environment-variables "VITE_API_BASE_URL=$BACKEND_URL" \
        --region $AWS_REGION \
        --query 'app.name' \
        --output text
    
    echo -e "${GREEN}✓ Environment variables updated${NC}"
    
    # Trigger new build
    echo -e "\n${YELLOW}Triggering new deployment...${NC}"
    JOB_ID=$(aws amplify start-job \
        --app-id $APP_ID \
        --branch-name $BRANCH_NAME \
        --job-type RELEASE \
        --region $AWS_REGION \
        --query 'jobSummary.jobId' \
        --output text)
    
    echo -e "${GREEN}✓ Deployment triggered: Job ID $JOB_ID${NC}"
    
else
    echo -e "${YELLOW}Creating new Amplify app...${NC}"
    
    # Create app
    APP_ID=$(aws amplify create-app \
        --name $APP_NAME \
        --repository $REPO_URL \
        --platform WEB \
        --environment-variables "VITE_API_BASE_URL=$BACKEND_URL" \
        --build-spec "$(cat frontend/amplify.yml)" \
        --region $AWS_REGION \
        --query 'app.appId' \
        --output text)
    
    echo -e "${GREEN}✓ Amplify app created: $APP_ID${NC}"
    
    # Create branch
    echo -e "\n${YELLOW}Connecting branch...${NC}"
    aws amplify create-branch \
        --app-id $APP_ID \
        --branch-name $BRANCH_NAME \
        --region $AWS_REGION \
        --query 'branch.branchName' \
        --output text
    
    echo -e "${GREEN}✓ Branch connected${NC}"
    
    # Start deployment
    echo -e "\n${YELLOW}Starting initial deployment...${NC}"
    JOB_ID=$(aws amplify start-job \
        --app-id $APP_ID \
        --branch-name $BRANCH_NAME \
        --job-type RELEASE \
        --region $AWS_REGION \
        --query 'jobSummary.jobId' \
        --output text)
    
    echo -e "${GREEN}✓ Deployment started: Job ID $JOB_ID${NC}"
fi

# Get app URL
APP_URL=$(aws amplify get-app \
    --app-id $APP_ID \
    --region $AWS_REGION \
    --query 'app.defaultDomain' \
    --output text)

FULL_URL="https://$BRANCH_NAME.$APP_URL"

echo -e "\n${GREEN}✅ Deployment initiated!${NC}"
echo -e "\n${YELLOW}Deployment Details:${NC}"
echo -e "  App ID: $APP_ID"
echo -e "  Job ID: $JOB_ID"
echo -e "  Branch: $BRANCH_NAME"
echo -e "\n${GREEN}🌐 Your frontend will be available at:${NC}"
echo -e "  ${GREEN}$FULL_URL${NC}"
echo -e "\n${YELLOW}Note: Build takes 3-5 minutes. Check status:${NC}"
echo -e "  aws amplify get-job --app-id $APP_ID --branch-name $BRANCH_NAME --job-id $JOB_ID --region $AWS_REGION"
echo -e "\n${GREEN}✨ Deployment script completed!${NC}"
