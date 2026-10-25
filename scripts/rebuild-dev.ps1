# Rebuild and restart the development stack. Data is kept: this never removes
# volumes (no "down -v"). Run from anywhere.
$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

Write-Host "=== Stopping containers (volumes are kept) ===" -ForegroundColor Green
docker compose down
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Rebuilding and starting ===" -ForegroundColor Green
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Waiting for the backend to become healthy ===" -ForegroundColor Green
for ($i = 0; $i -lt 60; $i++) {
    $state = docker inspect -f "{{.State.Health.Status}}" dq-backend 2>$null
    if ($state -eq "healthy") { break }
    Start-Sleep -Seconds 2
}
docker compose ps
if ($state -ne "healthy") {
    Write-Host "Backend is not healthy yet - check: docker compose logs backend" -ForegroundColor Yellow
    exit 1
}
Write-Host "=== Done ===" -ForegroundColor Green
