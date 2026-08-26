param(
    [string]$ContainerName = "dq-postgres",
    [string]$DbName = "dq_command_center",
    [string]$DbUser = "dqadmin"
)

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  DQ Command Center - Development Reset " -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Check if container is running
$container = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
if (-not $container) {
    Write-Host "Error: Container $ContainerName is not running." -ForegroundColor Red
    Write-Host "Start the containers first with: docker compose up -d" -ForegroundColor Cyan
    exit 1
}

Write-Host "This will delete all data in the database and reseed it." -ForegroundColor Red
Write-Host "Are you sure you want to continue? (y/N): " -ForegroundColor Yellow -NoNewline
$confirmation = Read-Host

if ($confirmation -ne "y" -and $confirmation -ne "Y") {
    Write-Host "Reset cancelled." -ForegroundColor Cyan
    exit 0
}

Write-Host ""
Write-Host "Dropping and recreating database..." -ForegroundColor Cyan

# Drop all tables by dropping and recreating the database
docker exec -e PGPASSWORD=[REDACTED-DEV-CREDENTIAL] $ContainerName psql -U $DbUser -d postgres -c "DROP DATABASE IF EXISTS $DbName;"
docker exec -e PGPASSWORD=[REDACTED-DEV-CREDENTIAL] $ContainerName psql -U $DbUser -d postgres -c "CREATE DATABASE $DbName;"

Write-Host "Running migrations..." -ForegroundColor Cyan
docker exec dq-backend alembic upgrade head

Write-Host "Seeding super admin..." -ForegroundColor Cyan
docker exec dq-backend python -c "from app.core.seed import seed_super_admin; import asyncio; asyncio.run(seed_super_admin())"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Database reset complete!               " -ForegroundColor Green
Write-Host "  Super Admin:                           " -ForegroundColor Green
Write-Host "    Email:    admin@dqcommandcenter.com   " -ForegroundColor Green
Write-Host "    Password: [REDACTED-DEV-CREDENTIAL]              " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
