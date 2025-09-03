Write-Host "Checking Service Logs..." -ForegroundColor Blue
Write-Host ""

Write-Host "Service Status:" -ForegroundColor Yellow
$status = gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.conditions[0].status,status.conditions[0].type,status.conditions[0].message)" 2>&1
Write-Host $status -ForegroundColor Green

Write-Host ""
Write-Host "Recent Logs:" -ForegroundColor Yellow
$logs = gcloud logs tail --service=trucking-news-bot --region=us-central1 --limit=10 2>&1
Write-Host $logs -ForegroundColor Green

Write-Host ""
Write-Host "Service Configuration:" -ForegroundColor Yellow
$config = gcloud run services describe trucking-news-bot --region=us-central1 --format="value(spec.template.spec.containers[0].env[0].name,spec.template.spec.containers[0].env[0].value)" 2>&1
Write-Host $config -ForegroundColor Green

Write-Host ""
Write-Host "Press any key to continue..."
Read-Host
