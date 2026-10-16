cd "C:\Users\aliqa\OneDrive\Desktop\dq-command-center-v2"
Write-Host "=== Stopping containers ===" -ForegroundColor Green
docker-compose down
Write-Host "=== Rebuilding backend ===" -ForegroundColor Green
docker-compose build backend
Write-Host "=== Starting all services ===" -ForegroundColor Green
docker-compose up -d
Write-Host "=== Waiting for services to be healthy ===" -ForegroundColor Green
Start-Sleep -Seconds 50
Write-Host "=== Checking service status ===" -ForegroundColor Green
docker-compose ps
Write-Host "=== Done! ===" -ForegroundColor Green
