@echo off
echo Checking Google Cloud Status...
echo.

echo Current Project:
gcloud config get-value project

echo.
echo Current Account:
gcloud auth list --filter="status:ACTIVE" --format="value(account)"

echo.
echo Cloud Run Services in us-central1:
gcloud run services list --region=us-central1

echo.
echo Recent Builds:
gcloud builds list --limit=5

echo.
echo Service Details (if exists):
gcloud run services describe trucking-news-bot --region=us-central1 --format="value(status.url)" 2>nul

echo.
pause
