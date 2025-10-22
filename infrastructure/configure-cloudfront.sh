#!/bin/bash

# Configure CloudFront with HTTPS for ALB
# Provides free HTTPS without requiring a custom domain

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}☁️  Configuring CloudFront with HTTPS${NC}"
echo "========================================"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"

# Load infrastructure config
if [ ! -f "infrastructure/config.sh" ]; then
    echo -e "${RED}❌ infrastructure/config.sh not found${NC}"
    echo -e "${YELLOW}Please run ./infrastructure/ecs-setup.sh first${NC}"
    exit 1
fi

source infrastructure/config.sh

echo -e "\n${YELLOW}Current Configuration:${NC}"
echo -e "  ALB DNS: $ALB_DNS"
echo -e "  Region: $AWS_REGION"

# Step 1: Create CloudFront distribution
echo -e "\n${YELLOW}Step 1: Creating CloudFront distribution...${NC}"
echo -e "${YELLOW}This will provide free HTTPS with AWS-managed certificate${NC}"

# Create CloudFront distribution config
cat > /tmp/cloudfront-config.json << EOF
{
  "CallerReference": "ghostcart-$(date +%s)",
  "Comment": "GhostCart API - HTTPS via CloudFront",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "alb-origin",
        "DomainName": "$ALB_DNS",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          },
          "OriginReadTimeout": 60,
          "OriginKeepaliveTimeout": 5
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "alb-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {
        "Forward": "all"
      },
      "Headers": {
        "Quantity": 4,
        "Items": ["Authorization", "Content-Type", "Accept", "Origin"]
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0,
    "Compress": true,
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    }
  },
  "CacheBehaviors": {
    "Quantity": 1,
    "Items": [
      {
        "PathPattern": "/api/*",
        "TargetOriginId": "alb-origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
          "Quantity": 7,
          "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
          "CachedMethods": {
            "Quantity": 2,
            "Items": ["GET", "HEAD"]
          }
        },
        "ForwardedValues": {
          "QueryString": true,
          "Cookies": {
            "Forward": "all"
          },
          "Headers": {
            "Quantity": 4,
            "Items": ["Authorization", "Content-Type", "Accept", "Origin"]
          }
        },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0,
        "Compress": true,
        "TrustedSigners": {
          "Enabled": false,
          "Quantity": 0
        }
      }
    ]
  },
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true,
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "PriceClass": "PriceClass_100"
}
EOF

echo -e "${YELLOW}Creating distribution (this takes 5-10 minutes)...${NC}"

DISTRIBUTION_OUTPUT=$(aws cloudfront create-distribution \
    --distribution-config file:///tmp/cloudfront-config.json \
    --output json)

DISTRIBUTION_ID=$(echo $DISTRIBUTION_OUTPUT | jq -r '.Distribution.Id')
CLOUDFRONT_DOMAIN=$(echo $DISTRIBUTION_OUTPUT | jq -r '.Distribution.DomainName')

rm /tmp/cloudfront-config.json

echo -e "${GREEN}✓ CloudFront distribution created${NC}"
echo -e "  Distribution ID: $DISTRIBUTION_ID"
echo -e "  Domain: $CLOUDFRONT_DOMAIN"

# Save CloudFront config
cat >> infrastructure/config.sh << EOF

# CloudFront Configuration
export DISTRIBUTION_ID="$DISTRIBUTION_ID"
export CLOUDFRONT_DOMAIN="$CLOUDFRONT_DOMAIN"
EOF

# Step 2: Wait for distribution to deploy
echo -e "\n${YELLOW}Step 2: Waiting for CloudFront distribution to deploy...${NC}"
echo -e "${YELLOW}This typically takes 5-10 minutes${NC}"
echo -e "${YELLOW}You can check status at: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/$DISTRIBUTION_ID${NC}"

aws cloudfront wait distribution-deployed --id $DISTRIBUTION_ID

echo -e "${GREEN}✓ CloudFront distribution deployed!${NC}"

# Step 3: Create initial cache invalidation
echo -e "\n${YELLOW}Step 3: Creating initial cache invalidation...${NC}"
echo -e "${YELLOW}This ensures CloudFront starts with fresh content${NC}"

INVALIDATION_OUTPUT=$(aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*" \
    --output json)

INVALIDATION_ID=$(echo $INVALIDATION_OUTPUT | jq -r '.Invalidation.Id')

echo -e "${GREEN}✓ Cache invalidation created${NC}"
echo -e "  Invalidation ID: $INVALIDATION_ID"
echo -e "${YELLOW}Waiting for invalidation to complete (2-3 minutes)...${NC}"

aws cloudfront wait invalidation-completed \
    --distribution-id $DISTRIBUTION_ID \
    --id $INVALIDATION_ID

echo -e "${GREEN}✓ Cache invalidation completed!${NC}"

# Step 4: Test the endpoint
echo -e "\n${YELLOW}Step 4: Testing HTTPS endpoint...${NC}"

sleep 5

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$CLOUDFRONT_DOMAIN/api/health || echo "000")

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ HTTPS endpoint is working!${NC}"
else
    echo -e "${YELLOW}⚠️  Endpoint returned HTTP $HTTP_CODE${NC}"
    echo -e "${YELLOW}This is normal if your backend isn't running yet${NC}"
    echo -e "${YELLOW}Try again in a few minutes or check your backend logs${NC}"
fi

# Summary
echo -e "\n${GREEN}✅ CloudFront HTTPS Configuration Complete!${NC}"
echo -e "\n${GREEN}🌐 Your backend is now available at:${NC}"
echo -e "  ${GREEN}https://$CLOUDFRONT_DOMAIN/api/health${NC}"
echo -e "\n${YELLOW}Update your Amplify environment variable:${NC}"
echo -e "  Key: ${GREEN}VITE_API_BASE_URL${NC}"
echo -e "  Value: ${GREEN}https://$CLOUDFRONT_DOMAIN/api${NC}"
echo -e "\n${BLUE}Benefits:${NC}"
echo -e "  ✓ Free HTTPS with AWS-managed certificate"
echo -e "  ✓ Global CDN for better performance"
echo -e "  ✓ DDoS protection"
echo -e "  ✓ No domain registration required"
echo -e "\n${YELLOW}Test with:${NC}"
echo -e "  curl https://$CLOUDFRONT_DOMAIN/api/health"
echo -e "\n${GREEN}✨ Setup completed!${NC}"
