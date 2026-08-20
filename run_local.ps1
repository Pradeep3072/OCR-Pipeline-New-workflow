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

# Set PYTHONPATH for local backend
$env:PYTHONPATH = ".\backend"

# Start FastAPI API
Write-Host "Starting FastAPI..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "backend.api:app", "--host", "0.0.0.0", "--port", "8000"

# Start Celery Worker
Write-Host "Starting Celery worker..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "celery" -ArgumentList "-A", "backend.worker.celery_app", "worker", "--loglevel=info"

# Start Streamlit Dashboard
Write-Host "Starting Streamlit UI..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "streamlit" -ArgumentList "run", "frontend/app.py"

Write-Host "All services started!" -ForegroundColor Green
