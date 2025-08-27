#!/bin/bash

# 🚛 Google Cloud Deployment Script for Trucking News Bot
# This script deploys your Facebook automation to Google Cloud Run

set -e

echo "🚛 Facebook Trucking News Automation - Google Cloud Deployment"
echo "=============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud SDK not found.${NC}"
    echo "📥 Install from: https://cloud.google.com/sdk"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}🔐 Please authenticate with Google Cloud:${NC}"
    gcloud auth login
fi

# Get or set project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}📋 No project set. Please enter your Google Cloud Project ID:${NC}"
    read -p "Project ID: " PROJECT_ID
    gcloud config set project $PROJECT_ID
fi

echo -e "${BLUE}📋 Using project: $PROJECT_ID${NC}"

# Confirm deployment
echo -e "${YELLOW}🚀 Ready to deploy to Google Cloud Run?${NC}"
echo "This will:"
echo "  ✅ Enable required APIs"
echo "  🐳 Build Docker container"
echo "  🌐 Deploy to Cloud Run"
echo "  📱 Make accessible on mobile"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Enable required APIs
echo -e "${BLUE}🔧 Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and deploy
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy trucking-news-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 3600 \
  --set-env-vars "SECRET_KEY=$(openssl rand -hex 32)" \
  --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe trucking-news-bot --region us-central1 --format="value(status.url)")

echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo "=============================================="
echo -e "${GREEN}🌐 Your app is live at:${NC}"
echo -e "${BLUE}$SERVICE_URL${NC}"
echo ""
echo -e "${YELLOW}📱 Mobile Setup:${NC}"
echo "1. Open the URL on your phone"
echo "2. Add to Home Screen (looks like a native app!)"
echo "3. Configure your API keys in Settings"
echo ""
echo -e "${YELLOW}🔑 Next Steps:${NC}"
echo "1. Go to: $SERVICE_URL/settings"
echo "2. Add your Facebook Page ID and Access Token"
echo "3. Add your OpenAI API Key"
echo "4. Enable auto-posting"
echo "5. Start managing your trucking news empire! 🚛"
echo ""
echo -e "${BLUE}💰 Cost: Pay-per-use (likely $0-5/month)${NC}"
echo -e "${BLUE}📊 Monitor: https://console.cloud.google.com/run${NC}"

# Optional: Set up custom domain
echo ""
read -p "🌐 Do you want to set up a custom domain? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📋 To set up a custom domain:"
    echo "1. Go to: https://console.cloud.google.com/run"
    echo "2. Click on your service: trucking-news-bot"
    echo "3. Go to 'Custom Domains' tab"
    echo "4. Click 'Add Mapping'"
    echo "5. Follow the instructions to verify your domain"
fi

echo ""
echo -e "${GREEN}🎉 Happy trucking news automation! 🚛📱${NC}"