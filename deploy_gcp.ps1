Write-Host "Facebook Trucking News Automation - Google Cloud Deployment" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""

# Check if gcloud is available
try {
    $gcloudVersion = gcloud --version 2>&1
    Write-Host "Google Cloud SDK found" -ForegroundColor Green
} catch {
    Write-Host "Google Cloud SDK not found. Install from: https://cloud.google.com/sdk" -ForegroundColor Red
    exit 1
}

# Check if user is authenticated
$authStatus = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>&1
if (-not $authStatus) {
    Write-Host "Please authenticate with Google Cloud:" -ForegroundColor Yellow
    gcloud auth login
} else {
    Write-Host "Authenticated as: $authStatus" -ForegroundColor Green
}

# Get or set project ID
$projectId = gcloud config get-value project 2>&1
if (-not $projectId) {
    Write-Host "No project set. Please enter your Google Cloud Project ID:" -ForegroundColor Yellow
    $projectId = Read-Host "Project ID"
    gcloud config set project $projectId
}

Write-Host "Using project: $projectId" -ForegroundColor Blue

# Check for environment file
if (Test-Path ".env") {
    Write-Host "Found .env file - will use existing configuration" -ForegroundColor Green
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^=]+)=(.*)$") {
            Set-Variable -Name $matches[1] -Value $matches[2]
        }
    }
} else {
    Write-Host "No .env file found. You'll need to configure settings after deployment." -ForegroundColor Yellow
}

# Confirm deployment
Write-Host ""
Write-Host "Ready to deploy to Google Cloud Run?" -ForegroundColor Yellow
Write-Host "This will:"
Write-Host "  Enable required APIs"
Write-Host "  Build Docker container"
Write-Host "  Deploy to Cloud Run"
Write-Host "  Configure environment variables"
Write-Host ""
$continue = Read-Host "Continue? (y/N)"
if ($continue -ne "y" -and $continue -ne "Y") {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Enable required APIs
Write-Host "Enabling required APIs..." -ForegroundColor Blue
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and deploy with comprehensive configuration
Write-Host "Deploying to Cloud Run..." -ForegroundColor Blue

# Prepare environment variables - generate random key using PowerShell
$randomBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
$rng.GetBytes($randomBytes)
$secretKey = -join ($randomBytes | ForEach-Object { "{0:x2}" -f $_ })

$envVars = "SECRET_KEY=$secretKey"
$envVars = "$envVars,DATABASE_URL=sqlite:///trucking_news.db"

# Add optional environment variables if they exist
if ($FACEBOOK_PAGE_ID) {
    $envVars = "$envVars,FACEBOOK_PAGE_ID=$FACEBOOK_PAGE_ID"
}

if ($FACEBOOK_ACCESS_TOKEN) {
    $envVars = "$envVars,FACEBOOK_ACCESS_TOKEN=$FACEBOOK_ACCESS_TOKEN"
}

if ($OPENAI_API_KEY) {
    $envVars = "$envVars,OPENAI_API_KEY=$OPENAI_API_KEY"
}

# Deploy with enhanced configuration
Write-Host "Deploying with environment variables: $envVars" -ForegroundColor Blue
gcloud run deploy trucking-news-bot `
  --source . `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --port 5000 `
  --memory 1Gi `
  --cpu 1 `
  --min-instances 0 `
  --max-instances 10 `
  --timeout 3600 `
  --set-env-vars "$envVars" `
  --set-env-vars "FLASK_ENV=production" `
  --set-env-vars "HOST=0.0.0.0" `
  --quiet

# Get the service URL
$serviceUrl = gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.url)" 2>&1

Write-Host ""
Write-Host "Deployment successful!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "Your app is live at:" -ForegroundColor Green
Write-Host "$serviceUrl" -ForegroundColor Blue
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Go to: $serviceUrl/settings"
Write-Host "2. Add your Facebook Page ID and Access Token"
Write-Host "3. Add your OpenAI API Key"
Write-Host "4. Enable auto-posting"
Write-Host ""
Write-Host "Monitor: https://console.cloud.google.com/run" -ForegroundColor Blue

Write-Host ""
Write-Host "Happy trucking news automation!" -ForegroundColor Green
