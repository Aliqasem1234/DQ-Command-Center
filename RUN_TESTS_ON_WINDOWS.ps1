# ============================================================================
# DQ COMMAND CENTER V2 - COMPREHENSIVE DOCKER & UI/UX TESTING SCRIPT
# ============================================================================
# Run this on Windows (PowerShell Admin) with Docker Desktop running
# ============================================================================

param(
    [string]$TestMode = "full"  # Options: "full", "docker-only", "manual"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
$success = "Green"
$error = "Red"
$warning = "Yellow"
$info = "Cyan"

function Write-Step {
    param([string]$Message, [string]$Status = "")
    if ($Status -eq "OK") {
        Write-Host "✅ $Message" -ForegroundColor $success
    } elseif ($Status -eq "ERROR") {
        Write-Host "❌ $Message" -ForegroundColor $error
    } elseif ($Status -eq "WARN") {
        Write-Host "⚠️  $Message" -ForegroundColor $warning
    } else {
        Write-Host "➜  $Message" -ForegroundColor $info
    }
}

function Check-Docker {
    Write-Step "Checking Docker installation..."
    try {
        $dockerVersion = docker --version
        Write-Step "Docker found: $dockerVersion" "OK"
        
        $composeVersion = docker compose version
        Write-Step "Docker Compose found: $composeVersion" "OK"
        
        return $true
    } catch {
        Write-Step "Docker not found or not running" "ERROR"
        Write-Host "Please ensure Docker Desktop is running and accessible" -ForegroundColor $error
        return $false
    }
}

function Extract-Project {
    Write-Step "Extracting project ZIP..."
    
    $zipPath = Get-ChildItem -Filter "*dq-command-center-production.zip" -Recurse | Select-Object -First 1
    if (-not $zipPath) {
        Write-Step "ZIP file not found. Place dq-command-center-production.zip in current directory" "ERROR"
        return $false
    }
    
    $extractPath = Join-Path $PSScriptRoot "dq-command-center-v2"
    
    if (Test-Path $extractPath) {
        Write-Step "Project directory already exists, skipping extraction" "WARN"
    } else {
        Expand-Archive -Path $zipPath.FullName -DestinationPath $PSScriptRoot
        Write-Step "Project extracted to $extractPath" "OK"
    }
    
    return $extractPath
}

function Setup-Environment {
    param([string]$ProjectPath)
    
    Write-Step "Setting up environment..."
    
    $envFile = Join-Path $ProjectPath ".env"
    if (-not (Test-Path $envFile)) {
        $exampleFile = Join-Path $ProjectPath ".env.example"
        Copy-Item $exampleFile $envFile
        Write-Step ".env file created from template" "OK"
    } else {
        Write-Step ".env file already exists" "WARN"
    }
}

function Build-Docker {
    param([string]$ProjectPath)
    
    Write-Step ""
    Write-Step "================================"
    Write-Step "BUILDING DOCKER IMAGES"
    Write-Step "================================"
    Write-Step ""
    
    Push-Location $ProjectPath
    
    try {
        Write-Step "Building Docker images (this may take 2-5 minutes)..."
        docker compose build --no-cache 2>&1 | Tee-Object -Variable buildOutput
        
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Docker build completed successfully" "OK"
            return $true
        } else {
            Write-Step "Docker build failed. Check output above" "ERROR"
            return $false
        }
    } catch {
        Write-Step "Error during Docker build: $_" "ERROR"
        return $false
    } finally {
        Pop-Location
    }
}

function Start-Services {
    param([string]$ProjectPath)
    
    Write-Step ""
    Write-Step "================================"
    Write-Step "STARTING DOCKER SERVICES"
    Write-Step "================================"
    Write-Step ""
    
    Push-Location $ProjectPath
    
    try {
        Write-Step "Starting containers..."
        docker compose up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Containers started" "OK"
            
            Write-Step "Waiting for services to be ready (30 seconds)..."
            Start-Sleep -Seconds 30
            
            Write-Step "Checking service status..."
            $status = docker compose ps --format "json" | ConvertFrom-Json
            
            foreach ($service in $status) {
                if ($service.State -like "*Up*") {
                    Write-Step "$($service.Service) is UP" "OK"
                } else {
                    Write-Step "$($service.Service) is $($service.State)" "WARN"
                }
            }
            
            return $true
        } else {
            Write-Step "Failed to start containers" "ERROR"
            return $false
        }
    } catch {
        Write-Step "Error starting services: $_" "ERROR"
        return $false
    } finally {
        Pop-Location
    }
}

function Test-Services {
    Write-Step ""
    Write-Step "================================"
    Write-Step "TESTING SERVICES"
    Write-Step "================================"
    Write-Step ""
    
    # Test frontend
    Write-Step "Testing frontend (http://localhost)..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Step "Frontend is accessible" "OK"
        } else {
            Write-Step "Frontend returned status $($response.StatusCode)" "WARN"
        }
    } catch {
        Write-Step "Frontend not accessible yet" "WARN"
    }
    
    # Test API
    Write-Step "Testing API (http://localhost:8000/docs)..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Step "API Swagger documentation is accessible" "OK"
        } else {
            Write-Step "API returned status $($response.StatusCode)" "WARN"
        }
    } catch {
        Write-Step "API not accessible yet" "WARN"
    }
}

function Show-Testing-Instructions {
    Write-Step ""
    Write-Step "================================"
    Write-Step "NEXT: MANUAL TESTING IN BROWSER"
    Write-Step "================================"
    Write-Step ""
    
    Write-Host @"
Services are running. Open your browser and perform the following tests:

FRONTEND ACCESS:
1. Open: http://localhost
   - Should see login page
   - Check browser console (F12) for errors
   - Verify Tailwind CSS styling is applied

LOGIN TEST:
2. Email: admin@dqcommandcenter.com
   Password: [REDACTED-DEV-CREDENTIAL]
   - Click "Sign In"
   - Wait for redirect to dashboard
   - Check that JWT token is created (look in Application/Storage)
   - Verify no console errors

NAVIGATION TEST:
3. Test all navigation items:
   - Dashboard
   - Data Quality → Rules
   - Data Quality → Monitoring
   - Departments
   - Users
   - Roles
   - Audit Log
   - Profile (top right)
   - Logout

LANGUAGE TESTING:
4. Change language in top navigation bar:
   a) English (default):
      - All text should be in English
      - No missing keys
      - Proper layout
   b) Svenska (Swedish):
      - All text should be in Swedish
      - No missing keys
      - Proper layout

VERIFY:
5. No Arabic anywhere in the application
6. Sidebar responsive on desktop (fixed)
7. Mobile menu works (if testing on mobile/tablet)
8. Dark mode toggle works

API DOCUMENTATION:
9. Open: http://localhost:8000/docs
   - Swagger UI should show all endpoints
   - Try "Try it out" on a few endpoints

DOCKER LOGS:
10. Check for any errors in logs:
    docker compose logs backend     # FastAPI logs
    docker compose logs frontend    # Node logs
    docker compose logs postgres    # Database logs

STOPPING SERVICES:
To stop when done:
docker compose down

To view logs in real-time:
docker compose logs -f

"@ -ForegroundColor $info
}

function Main {
    Clear-Host
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor $info
    Write-Host "║  DQ COMMAND CENTER V2 - DOCKER & UX TESTING SCRIPT             ║" -ForegroundColor $info
    Write-Host "║  Windows PowerShell Edition                                    ║" -ForegroundColor $info
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor $info
    Write-Host ""
    
    # Step 1: Check Docker
    if (-not (Check-Docker)) {
        exit 1
    }
    
    Write-Step ""
    
    # Step 2: Extract project
    $projectPath = Extract-Project
    if (-not $projectPath) {
        exit 1
    }
    
    Write-Step ""
    
    # Step 3: Setup environment
    Setup-Environment $projectPath
    
    Write-Step ""
    
    # Step 4: Build Docker
    if (-not (Build-Docker $projectPath)) {
        Write-Step "Docker build failed. Exiting." "ERROR"
        exit 1
    }
    
    Write-Step ""
    
    # Step 5: Start services
    if (-not (Start-Services $projectPath)) {
        Write-Step "Services failed to start. Exiting." "ERROR"
        exit 1
    }
    
    Write-Step ""
    
    # Step 6: Test services
    Test-Services
    
    Write-Step ""
    
    # Step 7: Show testing instructions
    Show-Testing-Instructions
    
    Write-Host "Keep this window open while testing. Press Ctrl+C to stop services." -ForegroundColor $warning
}

Main