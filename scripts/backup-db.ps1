param(
    [string]$BackupDir = "./backups",
    [string]$ContainerName = "dq-postgres",
    [string]$DbName = "dq_command_center",
    [string]$DbUser = "dqadmin"
)

# Create backup directory
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

# Generate filename with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "${DbName}_${timestamp}.sql"
$filepath = Join-Path -Path $BackupDir -ChildPath $filename

Write-Host "Starting backup of $DbName..." -ForegroundColor Cyan

# Check if container is running
$container = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
if (-not $container) {
    Write-Host "Error: Container $ContainerName is not running." -ForegroundColor Red
    exit 1
}

# Run pg_dump inside the container
docker exec $ContainerName pg_dump -U $DbUser -d $DbName -f "/tmp/$filename"
docker cp "${ContainerName}:/tmp/${filename}" $filepath
docker exec $ContainerName rm "/tmp/$filename"

if (Test-Path $filepath) {
    $filesize = (Get-Item $filepath).Length
    Write-Host "Backup completed: $filepath" -ForegroundColor Green
    Write-Host "Backup size: $([math]::Round($filesize / 1KB, 2)) KB" -ForegroundColor Green
} else {
    Write-Host "Backup failed!" -ForegroundColor Red
    exit 1
}
