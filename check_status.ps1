Write-Host "Checking Google Cloud Status..." -ForegroundColor Blue
Write-Host ""

Write-Host "Current Project:" -ForegroundColor Yellow
$project = gcloud config get-value project 2>&1
Write-Host $project -ForegroundColor Green

Write-Host ""
Write-Host "Current Account:" -ForegroundColor Yellow
$account = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>&1
Write-Host $account -ForegroundColor Green

Write-Host ""
Write-Host "Cloud Run Services in us-central1:" -ForegroundColor Yellow
$services = gcloud run services list --region=us-central1 2>&1
Write-Host $services -ForegroundColor Green

Write-Host ""
Write-Host "Recent Builds:" -ForegroundColor Yellow
$builds = gcloud builds list --limit=5 2>&1
Write-Host $builds -ForegroundColor Green

Write-Host ""
Write-Host "Service Details (if exists):" -ForegroundColor Yellow
$serviceUrl = gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.url)" 2>&1
Write-Host $serviceUrl -ForegroundColor Green

Write-Host ""
Write-Host "Press any key to continue..."
Read-Host
