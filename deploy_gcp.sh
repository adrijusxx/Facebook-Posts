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

# Check for environment file
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ Found .env file - will use existing configuration${NC}"
    source .env
else
    echo -e "${YELLOW}⚠️  No .env file found. You'll need to configure settings after deployment.${NC}"
fi

# Confirm deployment
echo -e "${YELLOW}🚀 Ready to deploy to Google Cloud Run?${NC}"
echo "This will:"
echo "  ✅ Enable required APIs"
echo "  🐳 Build Docker container"
echo "  🌐 Deploy to Cloud Run"
echo "  📱 Make accessible on mobile"
echo "  🔧 Configure environment variables"
echo "  💾 Set up persistent storage"
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
gcloud services enable secretmanager.googleapis.com

# Create secrets if they don't exist (optional)
echo -e "${BLUE}🔐 Setting up secrets management...${NC}"
if [ ! -z "$SECRET_KEY" ]; then
    echo "$SECRET_KEY" | gcloud secrets create trucking-bot-secret-key --data-file=- --replication-policy="automatic" 2>/dev/null || echo "Secret already exists"
fi

# Build and deploy with comprehensive configuration
echo -e "${BLUE}🚀 Deploying to Cloud Run...${NC}"

# Prepare environment variables
ENV_VARS="SECRET_KEY=$(openssl rand -hex 32)"
ENV_VARS="$ENV_VARS,DATABASE_URL=sqlite:///trucking_news.db"

# Add optional environment variables if they exist
if [ ! -z "$FACEBOOK_PAGE_ID" ]; then
    ENV_VARS="$ENV_VARS,FACEBOOK_PAGE_ID=$FACEBOOK_PAGE_ID"
fi

if [ ! -z "$FACEBOOK_ACCESS_TOKEN" ]; then
    ENV_VARS="$ENV_VARS,FACEBOOK_ACCESS_TOKEN=$FACEBOOK_ACCESS_TOKEN"
fi

if [ ! -z "$OPENAI_API_KEY" ]; then
    ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"
fi

# Deploy with enhanced configuration
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
  --set-env-vars "$ENV_VARS" \
  --set-env-vars "FLASK_ENV=production" \
  --set-env-vars "HOST=0.0.0.0" \
  --set-env-vars "PORT=5000" \
  --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe trucking-news-bot --region us-central1 --format="value(status.url)")

# Set up custom domain if requested
echo ""
read -p "🌐 Do you want to set up a custom domain? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🔧 Setting up custom domain...${NC}"
    echo "📋 To set up a custom domain:"
    echo "1. Go to: https://console.cloud.google.com/run"
    echo "2. Click on your service: trucking-news-bot"
    echo "3. Go to 'Custom Domains' tab"
    echo "4. Click 'Add Mapping'"
    echo "5. Follow the instructions to verify your domain"
fi

# Set up monitoring and logging
echo -e "${BLUE}📊 Setting up monitoring...${NC}"
echo "📈 View logs: gcloud logs tail --service=trucking-news-bot --region=us-central1"
echo "📊 Monitor: https://console.cloud.google.com/run"

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
echo -e "${BLUE}🔐 Secrets: https://console.cloud.google.com/security/secrets${NC}"

echo ""
echo -e "${GREEN}🎉 Happy trucking news automation! 🚛📱${NC}"