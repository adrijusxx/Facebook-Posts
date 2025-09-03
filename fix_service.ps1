Write-Host "Fixing Service Configuration..." -ForegroundColor Blue
Write-Host ""

# Generate a new secret key
$randomBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
$rng.GetBytes($randomBytes)
$secretKey = -join ($randomBytes | ForEach-Object { "{0:x2}" -f $_ })

Write-Host "Generated new SECRET_KEY: $secretKey" -ForegroundColor Green

# Set the correct environment variables
Write-Host "Updating service with correct environment variables..." -ForegroundColor Blue

gcloud run services update trucking-news-bot `
  --region=us-central1 `
  --set-env-vars "SECRET_KEY=$secretKey,DATABASE_URL=sqlite:///trucking_news.db,FLASK_ENV=production,HOST=0.0.0.0" `
  --quiet

Write-Host ""
Write-Host "Service updated! Now testing..." -ForegroundColor Green

# Get the service URL
$serviceUrl = gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.url)" 2>&1

Write-Host "Service URL: $serviceUrl" -ForegroundColor Blue
Write-Host ""
Write-Host "Opening service in browser to test..." -ForegroundColor Yellow

# Open in browser
Start-Process $serviceUrl

Write-Host ""
Write-Host "Service should now be working!" -ForegroundColor Green
Write-Host "If you still see 'Service Unavailable', wait a few minutes for the update to take effect." -ForegroundColor Yellow
