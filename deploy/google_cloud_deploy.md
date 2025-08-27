# ☁️ Google Cloud Deployment Guide

## 🚀 Deploy Facebook Trucking News Automation to Google Cloud

### **Prerequisites**
- Google Cloud account with billing enabled
- Google Cloud SDK installed (or use Cloud Shell)

## **Option 1: Cloud Run (Recommended - Serverless)**

### 1. **Prepare for Cloud Run**

Create `cloudbuild.yaml`:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/trucking-news-bot', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/trucking-news-bot']
```

### 2. **Quick Deploy Commands**
```bash
# Set your project ID
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Build and deploy
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
  --set-env-vars "SECRET_KEY=your-secret-key-here" \
  --timeout 3600
```

### 3. **Set Environment Variables**
```bash
gcloud run services update trucking-news-bot \
  --region us-central1 \
  --set-env-vars \
  "FACEBOOK_PAGE_ID=your-page-id,FACEBOOK_ACCESS_TOKEN=your-token,OPENAI_API_KEY=your-openai-key"
```

**Cost:** ~$0-5/month (pay per use)
**URL:** https://trucking-news-bot-xxx-uc.a.run.app

---

## **Option 2: App Engine (Platform as a Service)**

### 1. **Create app.yaml**
```yaml
runtime: python313
service: default

env_variables:
  SECRET_KEY: "your-secret-key-here"
  FACEBOOK_PAGE_ID: "your-page-id"
  FACEBOOK_ACCESS_TOKEN: "your-token"
  OPENAI_API_KEY: "your-openai-key"

automatic_scaling:
  min_instances: 0
  max_instances: 10
  target_cpu_utilization: 0.6
  
resources:
  cpu: 1
  memory_gb: 1
  disk_size_gb: 10
```

### 2. **Deploy Commands**
```bash
# Enable App Engine
gcloud app create --region=us-central

# Deploy
gcloud app deploy
```

**Cost:** ~$5-20/month
**URL:** https://your-project-id.uc.r.appspot.com

---

## **Option 3: Compute Engine (Virtual Machine)**

### 1. **Create VM Instance**
```bash
gcloud compute instances create trucking-news-vm \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud \
  --machine-type e2-micro \
  --zone us-central1-a \
  --tags http-server,https-server
```

### 2. **Setup Firewall**
```bash
gcloud compute firewall-rules create allow-flask \
  --allow tcp:5000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow Flask app"
```

### 3. **SSH and Setup**
```bash
# SSH to instance
gcloud compute ssh trucking-news-vm --zone us-central1-a

# Install dependencies
sudo apt update
sudo apt install python3-pip git nginx -y

# Clone and setup app
git clone [your-repo-url]
cd facebook-trucking-automation
pip3 install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/trucking-bot.service
```

**Cost:** ~$5-10/month
**IP:** External IP assigned by GCP

---

## **🎯 Recommended: Cloud Run Setup**

I'll create the necessary files for Cloud Run deployment:

### **Dockerfile**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]
```

### **Quick Start Script**
```bash
#!/bin/bash
echo "🚛 Deploying to Google Cloud Run..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK not found. Install from: https://cloud.google.com/sdk"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo "📋 Using project: $PROJECT_ID"

# Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy trucking-news-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5000 \
  --memory 1Gi \
  --cpu 1

echo "✅ Deployment complete!"
echo "🌐 Your app will be available at the URL shown above"
echo "📱 Perfect for mobile access!"
```

## **💰 Cost Estimates**

| Service | Monthly Cost | Best For |
|---------|-------------|----------|
| **Cloud Run** | $0-5 | Low traffic, pay-per-use |
| **App Engine** | $5-20 | Medium traffic, managed |
| **Compute Engine** | $5-15 | Full control, always-on |

## **📱 Mobile Optimization for Google Cloud**

### **Cloud Run Benefits:**
- ✅ **Auto-scaling** - Scales to zero when not used
- ✅ **Global CDN** - Fast loading worldwide
- ✅ **HTTPS** - Secure by default
- ✅ **Custom domains** - Use your own domain
- ✅ **Mobile-optimized** - Perfect for phone access

### **Performance Tuning:**
```bash
# Configure for better mobile performance
gcloud run services update trucking-news-bot \
  --region us-central1 \
  --cpu-boost \
  --session-affinity \
  --set-env-vars "FLASK_ENV=production"
```

## **🔐 Security Setup**

### **Environment Variables (Secure)**
```bash
# Store secrets in Secret Manager
gcloud secrets create facebook-token --data-file=- <<< "your-facebook-token"
gcloud secrets create openai-key --data-file=- <<< "your-openai-key"

# Update Cloud Run to use secrets
gcloud run services update trucking-news-bot \
  --region us-central1 \
  --set-secrets "FACEBOOK_ACCESS_TOKEN=facebook-token:latest,OPENAI_API_KEY=openai-key:latest"
```

## **📊 Monitoring & Logging**

### **Enable Monitoring:**
```bash
# View logs
gcloud run services logs read trucking-news-bot --region us-central1

# Monitor performance
gcloud run services describe trucking-news-bot --region us-central1
```

## **🚀 One-Click Deploy**

Ready to deploy? I'll create all the necessary files!