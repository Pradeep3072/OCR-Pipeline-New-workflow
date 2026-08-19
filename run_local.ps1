# Ensure we are in the script's directory
Set-Location $PSScriptRoot

# Ensure Redis and MinIO are running (Requires Docker)
Write-Host "Starting infrastructure (Redis & MinIO)..." -ForegroundColor Cyan
docker-compose up redis minio -d

# Environment Variables
$env:CELERY_BROKER_URL="redis://localhost:6379/0"
$env:S3_ENDPOINT_URL="http://localhost:9000"
$env:AWS_ACCESS_KEY_ID="minioadmin"
$env:AWS_SECRET_ACCESS_KEY="minioadmin"
$env:S3_BUCKET_NAME="ocr-bucket"
$env:API_URL="http://localhost:8000/ocr"

# Ensure virtual environment is activated if it exists
if (Test-Path ".venv\Scripts\activate.ps1") {
    . ".venv\Scripts\activate.ps1"
}

Write-Host "Starting FastAPI Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "if (Test-Path '.venv\Scripts\activate.ps1') { . '.venv\Scripts\activate.ps1' }; `$env:CELERY_BROKER_URL='redis://localhost:6379/0'; `$env:S3_ENDPOINT_URL='http://localhost:9000'; `$env:AWS_ACCESS_KEY_ID='minioadmin'; `$env:AWS_SECRET_ACCESS_KEY='minioadmin'; `$env:S3_BUCKET_NAME='ocr-bucket'; uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting Celery Worker..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "if (Test-Path '.venv\Scripts\activate.ps1') { . '.venv\Scripts\activate.ps1' }; `$env:CELERY_BROKER_URL='redis://localhost:6379/0'; `$env:S3_ENDPOINT_URL='http://localhost:9000'; `$env:AWS_ACCESS_KEY_ID='minioadmin'; `$env:AWS_SECRET_ACCESS_KEY='minioadmin'; `$env:S3_BUCKET_NAME='ocr-bucket'; celery -A worker.celery_app worker --loglevel=info --pool=solo"

Write-Host "Starting Streamlit Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "if (Test-Path '.venv\Scripts\activate.ps1') { . '.venv\Scripts\activate.ps1' }; `$env:API_URL='http://localhost:8000/ocr'; streamlit run app.py"

Write-Host "All services started in separate windows!" -ForegroundColor Green
