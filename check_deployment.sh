#!/bin/bash

# 🔍 Deployment Status Checker for Trucking News Bot
# This script helps verify if your deployment was successful

set -e

echo "🔍 Checking Trucking News Bot Deployment Status"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
echo -e "${BLUE}📋 Current Project: $PROJECT_ID${NC}"

# Check if service exists
echo -e "\n${BLUE}🔍 Checking for service in us-central1...${NC}"
SERVICE_EXISTS=$(gcloud run services list --region=us-central1 --filter="metadata.name=trucking-news-bot" --format="value(metadata.name)")

if [ -z "$SERVICE_EXISTS" ]; then
    echo -e "${RED}❌ Service 'trucking-news-bot' NOT FOUND in us-central1${NC}"
    echo -e "${YELLOW}🔍 Let's check other regions...${NC}"
    
    # Check all regions
    ALL_REGIONS=$(gcloud run services list --filter="metadata.name=trucking-news-bot" --format="value(metadata.region)")
    if [ -z "$ALL_REGIONS" ]; then
        echo -e "${RED}❌ Service not found in ANY region${NC}"
        echo -e "${YELLOW}💡 Possible issues:${NC}"
        echo "   - Deployment failed"
        echo "   - Wrong service name"
        echo "   - Wrong project"
        echo "   - Build error"
    else
        echo -e "${YELLOW}📍 Found service in regions: $ALL_REGIONS${NC}"
        echo "   Update your deploy script to use the correct region"
    fi
else
    echo -e "${GREEN}✅ Service 'trucking-news-bot' FOUND in us-central1${NC}"
    
    # Get service details
    echo -e "\n${BLUE}📊 Service Details:${NC}"
    gcloud run services describe trucking-news-bot --region=us-central1 --format="table(
        metadata.name,
        status.url,
        status.conditions[0].status,
        status.conditions[0].type,
        spec.template.spec.containers[0].image
    )"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.url)")
    echo -e "\n${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
    
    # Test if service is responding
    echo -e "\n${BLUE}🧪 Testing service response...${NC}"
    if curl -s --max-time 10 "$SERVICE_URL" > /dev/null; then
        echo -e "${GREEN}✅ Service is responding!${NC}"
    else
        echo -e "${YELLOW}⚠️  Service might be starting up or having issues${NC}"
    fi
fi

# Check recent builds
echo -e "\n${BLUE}🔨 Recent Builds:${NC}"
gcloud builds list --limit=3 --format="table(
    id,
    status,
    createTime,
    source.repoSource.branchName
)"

# Check if you're authenticated
echo -e "\n${BLUE}🔐 Authentication Status:${NC}"
CURRENT_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)")
if [ ! -z "$CURRENT_ACCOUNT" ]; then
    echo -e "${GREEN}✅ Authenticated as: $CURRENT_ACCOUNT${NC}"
else
    echo -e "${RED}❌ Not authenticated${NC}"
    echo "Run: gcloud auth login"
fi

# Check project access
echo -e "\n${BLUE}📋 Project Access:${NC}"
if gcloud projects describe $PROJECT_ID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Have access to project: $PROJECT_ID${NC}"
else
    echo -e "${RED}❌ No access to project: $PROJECT_ID${NC}"
    echo "Check your permissions or switch projects with: gcloud config set project PROJECT_ID"
fi

echo -e "\n${BLUE}💡 Next Steps:${NC}"
if [ -z "$SERVICE_EXISTS" ]; then
    echo "1. Run the deployment script again: ./deploy_gcp.sh"
    echo "2. Check for error messages during deployment"
    echo "3. Verify you're in the correct project and region"
else
    echo "1. Open the service URL in your browser"
    echo "2. Check the Google Console: https://console.cloud.google.com/run"
    echo "3. Monitor logs: gcloud logs tail --service=trucking-news-bot --region=us-central1"
fi

echo -e "\n${GREEN}🔍 Deployment check complete!${NC}"
