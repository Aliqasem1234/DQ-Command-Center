# Run every automated check that needs no browser:
#   backend tests (inside the running dev backend container), frontend type
#   check, unit tests and production build, and Docker Compose validation.
# Requires the development stack to be up (docker compose up -d).
# Read-only for your data: tests use an in-memory database.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -Path $root
$failed = @()

function Invoke-Check([string]$name, [scriptblock]$cmd) {
    Write-Host "=== $name ===" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) { $script:failed += $name; Write-Host "FAILED: $name" -ForegroundColor Red }
}

Invoke-Check "Backend tests" { docker exec dq-backend python -m pytest -q -p no:logging }
Invoke-Check "Compose config (development)" { docker compose config --quiet }
Invoke-Check "Compose config (production)" { docker compose -f docker-compose.prod.yml config --quiet }

Set-Location -Path (Join-Path $root "frontend")
Invoke-Check "Frontend type check" { npx tsc -b }
Invoke-Check "Frontend unit tests" { npx vitest run }
Invoke-Check "Frontend production build" { npm run build }
Set-Location -Path $root

if ($failed.Count -gt 0) {
    Write-Host "`nFailed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "`nAll checks passed." -ForegroundColor Green
