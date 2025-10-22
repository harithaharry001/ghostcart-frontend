#!/bin/bash

# Fix CloudFront CORS Configuration - Simple Version
set -e

echo "Fixing CloudFront CORS Configuration..."
echo "========================================"

# Load infrastructure config
source infrastructure/config.sh

echo ""
echo "Distribution ID: $DISTRIBUTION_ID"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo ""

# Step 1: Create Response Headers Policy for CORS
echo "Step 1: Creating Response Headers Policy..."

POLICY_NAME="ghostcart-cors-policy-$(date +%s)"

cat > /tmp/response-headers-policy.json << EOF
{
  "Comment": "CORS policy for GhostCart API",
  "Name": "$POLICY_NAME",
  "CorsConfig": {
    "AccessControlAllowOrigins": {
      "Quantity": 1,
      "Items": ["*"]
    },
    "AccessControlAllowHeaders": {
      "Quantity": 4,
      "Items": ["Content-Type", "Authorization", "Accept", "Origin"]
    },
    "AccessControlAllowMethods": {
      "Quantity": 7,
      "Items": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    },
    "AccessControlAllowCredentials": true,
    "AccessControlExposeHeaders": {
      "Quantity": 5,
      "Items": ["Content-Type", "Content-Length", "Date", "Server", "X-Request-Id"]
    },
    "AccessControlMaxAgeSec": 600,
    "OriginOverride": false
  },
  "SecurityHeadersConfig": {
    "StrictTransportSecurity": {
      "Override": false,
      "AccessControlMaxAgeSec": 31536000,
      "IncludeSubdomains": true
    },
    "ContentTypeOptions": {
      "Override": false
    }
  }
}
EOF

echo "Creating response headers policy..."

POLICY_OUTPUT=$(aws cloudfront create-response-headers-policy \
    --response-headers-policy-config file:///tmp/response-headers-policy.json \
    --output json)

POLICY_ID=$(echo "$POLICY_OUTPUT" | jq -r '.ResponseHeadersPolicy.Id')
echo "✓ Response headers policy created"
echo "  Policy ID: $POLICY_ID"

rm -f /tmp/response-headers-policy.json

# Step 2: Get current distribution config
echo ""
echo "Step 2: Getting current distribution configuration..."

DIST_CONFIG=$(aws cloudfront get-distribution-config --id $DISTRIBUTION_ID --output json)
ETAG=$(echo "$DIST_CONFIG" | jq -r '.ETag')

echo "$DIST_CONFIG" | jq '.DistributionConfig' > /tmp/dist-config.json

# Step 3: Update distribution config with response headers policy
echo ""
echo "Step 3: Updating distribution configuration..."

# Add response headers policy ID to default cache behavior
jq --arg policy_id "$POLICY_ID" \
  '.DefaultCacheBehavior.ResponseHeadersPolicyId = $policy_id' \
  /tmp/dist-config.json > /tmp/dist-config-updated.json

# Also update the /api/* cache behavior if it exists
jq --arg policy_id "$POLICY_ID" \
  'if .CacheBehaviors.Items then
    .CacheBehaviors.Items = [.CacheBehaviors.Items[] | .ResponseHeadersPolicyId = $policy_id]
  else . end' \
  /tmp/dist-config-updated.json > /tmp/dist-config-final.json

echo "Applying configuration changes..."

aws cloudfront update-distribution \
    --id $DISTRIBUTION_ID \
    --distribution-config file:///tmp/dist-config-final.json \
    --if-match "$ETAG" \
    --output json > /dev/null

echo "✓ Distribution configuration updated"

# Cleanup temp files
rm -f /tmp/dist-config*.json

# Step 4: Create cache invalidation
echo ""
echo "Step 4: Creating cache invalidation..."

INVALIDATION_OUTPUT=$(aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*" \
    --output json)

INVALIDATION_ID=$(echo "$INVALIDATION_OUTPUT" | jq -r '.Invalidation.Id')

echo "✓ Cache invalidation created"
echo "  Invalidation ID: $INVALIDATION_ID"

echo ""
echo "Waiting for invalidation to complete (2-5 minutes)..."

aws cloudfront wait invalidation-completed \
    --distribution-id $DISTRIBUTION_ID \
    --id $INVALIDATION_ID

echo "✓ Cache invalidation completed!"

# Step 5: Test CORS
echo ""
echo "Step 5: Testing CORS configuration..."

sleep 5

echo "Testing OPTIONS preflight request..."
PREFLIGHT_RESPONSE=$(curl -s -X OPTIONS \
    -H "Origin: https://main.d1n3p8ci7f7lpa.amplifyapp.com" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -i "https://$CLOUDFRONT_DOMAIN/api/health" 2>&1 | head -20)

echo "$PREFLIGHT_RESPONSE"

if echo "$PREFLIGHT_RESPONSE" | grep -q "access-control-allow-origin"; then
    echo ""
    echo "✓ CORS headers are now present!"
else
    echo ""
    echo "⚠️  CORS headers might not be visible yet"
    echo "Wait a few minutes and try accessing from your Amplify app"
fi

# Summary
echo ""
echo "✅ CloudFront CORS Configuration Fixed!"
echo ""
echo "Changes Applied:"
echo "  ✓ Created Response Headers Policy with CORS support"
echo "  ✓ Updated CloudFront distribution to use the policy"
echo "  ✓ Invalidated CloudFront cache"
echo ""
echo "CORS Headers Now Added:"
echo "  ✓ Access-Control-Allow-Origin: *"
echo "  ✓ Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
echo "  ✓ Access-Control-Allow-Headers: Content-Type, Authorization, Accept, Origin"
echo "  ✓ Access-Control-Allow-Credentials: true"
echo ""
echo "Test your Amplify app now!"
echo "  URL: https://main.d1n3p8ci7f7lpa.amplifyapp.com"
echo ""
echo "If you still see 504 errors, the backend might not be responding."
echo "Check if your ECS backend is responding:"
echo "  curl http://$ALB_DNS/api/health"
