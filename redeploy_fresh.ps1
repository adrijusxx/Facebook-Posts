Write-Host "Completely Redeploying Service from Scratch..." -ForegroundColor Blue
Write-Host ""

# Confirm the action
Write-Host "This will:" -ForegroundColor Yellow
Write-Host "1. Delete the current service" -ForegroundColor Red
Write-Host "2. Build a fresh container" -ForegroundColor Yellow
Write-Host "3. Deploy with correct configuration" -ForegroundColor Yellow
Write-Host ""
$continue = Read-Host "Continue? This will cause downtime (y/N)"
if ($continue -ne "y" -and $continue -ne "Y") {
    Write-Host "Redeployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Delete the current service
Write-Host "Deleting current service..." -ForegroundColor Red
gcloud run services delete trucking-news-bot --region=us-central1 --quiet

Write-Host "Waiting for deletion to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Generate a new secret key
$randomBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
$rng.GetBytes($randomBytes)
$secretKey = -join ($randomBytes | ForEach-Object { "{0:x2}" -f $_ })

Write-Host "Generated new SECRET_KEY: $secretKey" -ForegroundColor Green

# Deploy fresh service
Write-Host "Deploying fresh service..." -ForegroundColor Blue

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
  --set-env-vars "SECRET_KEY=$secretKey,DATABASE_URL=sqlite:///trucking_news.db,FLASK_ENV=production,HOST=0.0.0.0" `
  --quiet

Write-Host ""
Write-Host "Fresh deployment complete! Getting service URL..." -ForegroundColor Green

# Get the service URL
$serviceUrl = gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.url)" 2>&1

Write-Host "Service URL: $serviceUrl" -ForegroundColor Blue
Write-Host ""
Write-Host "Opening service in browser to test..." -ForegroundColor Yellow

# Open in browser
Start-Process $serviceUrl

Write-Host ""
Write-Host "Fresh deployment complete! The service should now work properly." -ForegroundColor Green
Write-Host "If you still see issues, there may be a problem with the application code itself." -ForegroundColor Yellow
