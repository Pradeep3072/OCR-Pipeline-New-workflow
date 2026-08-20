# Ensure we are in the script's directory
Set-Location $PSScriptRoot

$useK8s = $false

# Check if .env file exists and parse it
if (Test-Path ".env") {
    $envContent = Get-Content ".env"
    foreach ($line in $envContent) {
        if ($line -match "^USE_K8S=(true|1|yes)$") {
            $useK8s = $true
        }
    }
}

if ($useK8s) {
    Write-Host "USE_K8S is set to true in .env" -ForegroundColor Cyan
    Write-Host "Deploying to Kubernetes..." -ForegroundColor Green
    
    # Check if kubectl is installed
    if (Get-Command kubectl -ErrorAction SilentlyContinue) {
        kubectl apply -f k8s/
    } else {
        Write-Host "Error: kubectl is not installed or not in PATH." -ForegroundColor Red
    }
} else {
    Write-Host "USE_K8S is false (or not set) in .env" -ForegroundColor Cyan
    Write-Host "Deploying using Docker Compose..." -ForegroundColor Green
    
    docker-compose up --build -d
}
