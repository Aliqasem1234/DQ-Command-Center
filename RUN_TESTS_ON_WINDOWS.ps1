#requires -Version 5.1
<#
.SYNOPSIS
    DQ Command Center v2 - Docker build/start/health test script for Windows PowerShell.
.DESCRIPTION
    Validates prerequisites, builds and starts the Docker Compose stack for this
    project, waits for services to become healthy, and smoke-tests the HTTP
    endpoints. Never deletes files and never touches other projects/containers.
.PARAMETER TestMode
    "full"         - build, start, health-check (default)
    "docker-only"  - build and start only, skip HTTP smoke tests
    "manual"       - only print manual testing instructions, no Docker actions
#>
param(
    [ValidateSet("full", "docker-only", "manual")]
    [string]$TestMode = "full"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ColorOk   = "Green"
$ColorErr  = "Red"
$ColorWarn = "Yellow"
$ColorInfo = "Cyan"

$ProjectRoot = $PSScriptRoot
$script:FailureCount = 0

function Write-Step {
    param([string]$Message, [string]$Status = "")
    switch ($Status) {
        "OK"    { Write-Host "[OK]    $Message" -ForegroundColor $ColorOk }
        "ERROR" { Write-Host "[ERROR] $Message" -ForegroundColor $ColorErr; $script:FailureCount++ }
        "WARN"  { Write-Host "[WARN]  $Message" -ForegroundColor $ColorWarn }
        default { Write-Host "[..]    $Message" -ForegroundColor $ColorInfo }
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor $ColorInfo
    Write-Host " $Title" -ForegroundColor $ColorInfo
    Write-Host "================================================================" -ForegroundColor $ColorInfo
}

function Test-Prerequisites {
    Write-Section "STEP 1: PREREQUISITES"
    $ok = $true

    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $dockerVersion) { throw "docker CLI not found" }
        Write-Step "Docker found: $dockerVersion" "OK"
    } catch {
        Write-Step "Docker CLI not found. Install/start Docker Desktop." "ERROR"
        return $false
    }

    try {
        docker info *>$null
        if ($LASTEXITCODE -ne 0) { throw "daemon not responding" }
        Write-Step "Docker daemon is running" "OK"
    } catch {
        Write-Step "Docker daemon is not running. Start Docker Desktop and retry." "ERROR"
        return $false
    }

    try {
        $composeVersion = docker compose version 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $composeVersion) { throw "compose plugin not found" }
        Write-Step "Docker Compose found: $composeVersion" "OK"
    } catch {
        Write-Step "Docker Compose plugin not found (need Docker Desktop >= 3.x)." "ERROR"
        $ok = $false
    }

    $requiredPaths = @(
        "docker-compose.yml",
        "backend\Dockerfile",
        "backend\requirements.txt",
        "frontend\Dockerfile",
        "frontend\package.json",
        "nginx\nginx.conf",
        ".env.example"
    )
    foreach ($rel in $requiredPaths) {
        $full = Join-Path $ProjectRoot $rel
        if (Test-Path $full) {
            Write-Step "Found $rel" "OK"
        } else {
            Write-Step "Missing required file: $rel" "ERROR"
            $ok = $false
        }
    }

    return $ok
}

function Initialize-Environment {
    Write-Section "STEP 2: ENVIRONMENT CONFIGURATION"

    $envFile = Join-Path $ProjectRoot ".env"
    $exampleFile = Join-Path $ProjectRoot ".env.example"

    if (-not (Test-Path $envFile)) {
        Copy-Item $exampleFile $envFile
        Write-Step ".env created from .env.example - EDIT IT before using in production" "WARN"
    } else {
        Write-Step ".env already exists, leaving it untouched" "OK"
    }

    $envContent = Get-Content $envFile -Raw
    $placeholders = @("ChangeMe_Database_Password_Min_12_Chars", "change-this-to-a-random-secret-key-at-least-32-chars")
    foreach ($placeholder in $placeholders) {
        if ($envContent -like "*$placeholder*") {
            Write-Step "Default placeholder secret still present in .env: '$placeholder'" "WARN"
        }
    }
}

function Invoke-DockerBuild {
    Write-Section "STEP 3: BUILDING DOCKER IMAGES"
    Push-Location $ProjectRoot
    try {
        Write-Step "Running: docker compose build (this can take a few minutes)..."
        docker compose build
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Docker build completed successfully" "OK"
            return $true
        }
        Write-Step "Docker build failed (exit code $LASTEXITCODE). See output above." "ERROR"
        return $false
    } finally {
        Pop-Location
    }
}

function Start-Stack {
    Write-Section "STEP 4: STARTING SERVICES"
    Push-Location $ProjectRoot
    try {
        Write-Step "Running: docker compose up -d ..."
        docker compose up -d
        if ($LASTEXITCODE -ne 0) {
            Write-Step "Failed to start containers (exit code $LASTEXITCODE)" "ERROR"
            return $false
        }
        Write-Step "Containers started, waiting for health checks..." "OK"

        $maxWaitSeconds = 90
        $elapsed = 0
        $allHealthy = $false
        while ($elapsed -lt $maxWaitSeconds) {
            Start-Sleep -Seconds 5
            $elapsed += 5
            $psJson = docker compose ps --format json 2>$null
            if (-not $psJson) { continue }

            $states = @()
            foreach ($line in ($psJson -split "`n" | Where-Object { $_.Trim() })) {
                try { $states += ($line | ConvertFrom-Json) } catch { }
            }
            if ($states.Count -eq 0) { continue }

            $notReady = $states | Where-Object {
                $_.State -notlike "*running*" -or ($_.Health -and $_.Health -notlike "*healthy*" -and $_.Health -ne "")
            }
            if (-not $notReady) { $allHealthy = $true; break }
        }

        $finalStatus = docker compose ps --format json 2>$null
        foreach ($line in ($finalStatus -split "`n" | Where-Object { $_.Trim() })) {
            try {
                $svc = $line | ConvertFrom-Json
                $label = "$($svc.Service): $($svc.State)"
                if ($svc.Health) { $label += " ($($svc.Health))" }
                if ($svc.State -like "*running*") { Write-Step $label "OK" } else { Write-Step $label "WARN" }
            } catch { }
        }

        if (-not $allHealthy) {
            Write-Step "Not all services reached a healthy state within $maxWaitSeconds seconds" "WARN"
        }
        return $true
    } finally {
        Pop-Location
    }
}

function Test-Endpoints {
    Write-Section "STEP 5: SMOKE-TESTING ENDPOINTS"

    $targets = @(
        @{ Name = "Nginx (frontend proxy)"; Url = "http://localhost/" },
        @{ Name = "Backend API docs";       Url = "http://localhost:8000/docs" },
        @{ Name = "Backend health";         Url = "http://localhost:8000/health" }
    )

    foreach ($t in $targets) {
        try {
            $response = Invoke-WebRequest -Uri $t.Url -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Step "$($t.Name) responded $($response.StatusCode) at $($t.Url)" "OK"
            } else {
                Write-Step "$($t.Name) responded $($response.StatusCode) at $($t.Url)" "WARN"
            }
        } catch {
            Write-Step "$($t.Name) not reachable at $($t.Url): $($_.Exception.Message)" "ERROR"
        }
    }
}

function Show-ManualTestingInstructions {
    Write-Section "MANUAL BROWSER TESTING CHECKLIST"

    Write-Host @"
Open a browser and verify the following. Check DevTools (F12) Console and
Network tabs throughout - there should be no red errors and no failed (4xx/5xx)
requests other than ones you intentionally trigger.

1. FRONTEND
   - Open http://localhost -> should show the login page, styled with Tailwind.

2. LOGIN
   - Sign in with the admin account created via the secure init process
     (see ADMIN_SETUP_GUIDE.md - do NOT use hardcoded credentials in prod).
   - Confirm redirect to dashboard and no console errors.

3. NAVIGATION
   - Dashboard, Data Quality > Rules, Data Quality > Monitoring, Departments,
     Users, Roles, Audit Log, Profile, Logout - every link should load real data
     or an explicit empty state, never a blank/broken page.

4. LANGUAGE
   - Switch between English and Swedish. No missing translation keys, no
     leftover Arabic text or RTL layout anywhere.

5. RBAC
   - Log in as a non-admin user and confirm admin-only routes are blocked
     both in the UI (hidden/disabled) and by the API (403/401).

6. RESPONSIVE / THEME
   - Resize to mobile width, confirm the mobile nav works.
   - Toggle dark mode.

7. API DOCS
   - Open http://localhost:8000/docs, try a few endpoints with "Try it out".

8. LOGS
   - docker compose logs backend
   - docker compose logs frontend
   - docker compose logs postgres
   Look for stack traces, unhandled exceptions, or secrets being printed.

STOP THE STACK WHEN DONE:
   docker compose down

FOLLOW LOGS LIVE:
   docker compose logs -f
"@ -ForegroundColor $ColorInfo
}

function Main {
    Write-Host "================================================================" -ForegroundColor $ColorInfo
    Write-Host " DQ COMMAND CENTER V2 - DOCKER & UX TEST RUNNER (Windows)" -ForegroundColor $ColorInfo
    Write-Host "================================================================" -ForegroundColor $ColorInfo

    if ($TestMode -eq "manual") {
        Show-ManualTestingInstructions
        return
    }

    if (-not (Test-Prerequisites)) {
        Write-Step "Prerequisite checks failed. Fix the issues above and re-run." "ERROR"
        exit 1
    }

    Initialize-Environment

    if (-not (Invoke-DockerBuild)) {
        exit 1
    }

    if (-not (Start-Stack)) {
        exit 1
    }

    if ($TestMode -eq "full") {
        Test-Endpoints
        Show-ManualTestingInstructions
    }

    Write-Host ""
    if ($script:FailureCount -gt 0) {
        Write-Step "Completed with $($script:FailureCount) error(s) - see [ERROR] lines above." "ERROR"
        exit 1
    } else {
        Write-Step "Completed with no fatal errors." "OK"
    }
}

Main
