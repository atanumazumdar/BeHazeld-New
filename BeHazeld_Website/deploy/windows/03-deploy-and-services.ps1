#Requires -RunAsAdministrator
<#
.SYNOPSIS
    BeHAZEL'd — Step 3: Deploy app files, run migrations, and register Windows Services.

.DESCRIPTION
    Run this script after:
      1. 01-prerequisites.ps1 has completed successfully.
      2. 02-sql-server-setup.sql has been executed in SSMS.
      3. You have copied the app source to this server (git pull or robocopy).

    The script:
      • Creates IIS application pools and sites
      • Builds Next.js
      • Runs Alembic migrations against SQL Server
      • Seeds the database
      • Registers FastAPI (uvicorn) as a Windows Service via NSSM
      • Registers Next.js (next start) via pm2
      • Configures Windows Firewall

.PARAMETER SourceRoot
    Root folder of the cloned repository on this server.
    Default: C:\deploy\BeHazeld

.PARAMETER ApiHostname
    Public hostname for the API site (must match your DNS A record + SSL cert).
    Default: api.behazeld.com

.PARAMETER WebHostname
    Public hostname for the frontend site.
    Default: www.behazeld.com

.NOTES
    Run from: PowerShell (Administrator)
    Command : .\03-deploy-and-services.ps1 -SourceRoot "C:\deploy\BeHazeld"
#>

param(
    [string]$SourceRoot = "C:\deploy\BeHazeld",
    [string]$ApiHostname = "api.behazeld.com",
    [string]$WebHostname = "www.behazeld.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "    WARN: $msg" -ForegroundColor Yellow }

$apicmd   = "$env:SystemRoot\system32\inetsrv\appcmd.exe"
$apiDest  = "C:\inetpub\wwwroot\behazeld-api"
$webDest  = "C:\inetpub\wwwroot\behazeld-web"
$apiLog   = "C:\logs\behazeld-api"
$webLog   = "C:\logs\behazeld-web"

# ══════════════════════════════════════════════════════════════════════
# A. Read secrets from environment (must be set before running this script)
# ══════════════════════════════════════════════════════════════════════
Write-Step "Reading secrets from environment"

$dbPassword   = $env:DB_PASSWORD
$adminKey     = $env:ADMIN_API_KEY
$jwtSecret    = $env:ADMIN_JWT_SECRET
$sessionSecret = $env:ADMIN_SESSION_SECRET
$cloudName    = $env:CLOUDINARY_CLOUD_NAME
$cloudKey     = $env:CLOUDINARY_API_KEY
$cloudSecret  = $env:CLOUDINARY_API_SECRET

if (-not $dbPassword)   { throw "DB_PASSWORD environment variable is not set." }
if (-not $adminKey)     { throw "ADMIN_API_KEY environment variable is not set." }
if (-not $jwtSecret)    { throw "ADMIN_JWT_SECRET environment variable is not set." }
if (-not $sessionSecret){ throw "ADMIN_SESSION_SECRET environment variable is not set." }

$DATABASE_URL = "mssql+pyodbc://behazeld_app:$dbPassword@localhost/BeHAZELD?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
Write-OK "All secrets present"

# ══════════════════════════════════════════════════════════════════════
# B. Copy application files
# ══════════════════════════════════════════════════════════════════════
Write-Step "Copying backend source to $apiDest"
robocopy "$SourceRoot\backend" $apiDest /MIR /XD ".venv" "venv" "__pycache__" ".mypy_cache" ".ruff_cache" /NFL /NDL /NJH | Out-Null
Write-OK "Backend files copied"

Write-Step "Copying frontend source to $webDest"
robocopy "$SourceRoot\frontend" $webDest /MIR /XD "node_modules" ".next" /NFL /NDL /NJH | Out-Null
Write-OK "Frontend files copied"

# ══════════════════════════════════════════════════════════════════════
# C. Backend: virtualenv + pip install
# ══════════════════════════════════════════════════════════════════════
Write-Step "Setting up Python virtualenv"
python -m venv "$apiDest\.venv"
& "$apiDest\.venv\Scripts\pip.exe" install --upgrade pip --quiet
& "$apiDest\.venv\Scripts\pip.exe" install -r "$apiDest\requirements.txt" --quiet
Write-OK "Python dependencies installed"

# ══════════════════════════════════════════════════════════════════════
# D. Write backend .env
# ══════════════════════════════════════════════════════════════════════
Write-Step "Writing backend .env"
$backendEnv = @"
DATABASE_URL=$DATABASE_URL
ENVIRONMENT=production
ADMIN_API_KEY=$adminKey
ADMIN_JWT_SECRET=$jwtSecret
ADMIN_JWT_EXPIRY=86400
ALLOWED_ORIGINS=https://$WebHostname,https://behazeld.com
CLOUDINARY_CLOUD_NAME=$cloudName
CLOUDINARY_API_KEY=$cloudKey
CLOUDINARY_API_SECRET=$cloudSecret
"@
Set-Content -Path "$apiDest\.env" -Value $backendEnv -Encoding UTF8
# Restrict .env to SYSTEM + Administrators only
$acl = Get-Acl "$apiDest\.env"
$acl.SetAccessRuleProtection($true, $false)
$acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM","FullControl","Allow")))
$acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators","FullControl","Allow")))
Set-Acl "$apiDest\.env" $acl
Write-OK "Backend .env written and secured"

# ══════════════════════════════════════════════════════════════════════
# E. Run Alembic migrations + seed
# ══════════════════════════════════════════════════════════════════════
Write-Step "Running Alembic migrations"
Push-Location $apiDest
$env:DATABASE_URL = $DATABASE_URL
& "$apiDest\.venv\Scripts\alembic.exe" upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic migration failed." }
Write-OK "Migrations applied"

Write-Step "Seeding database"
& "$apiDest\.venv\Scripts\python.exe" -m app.seed
Write-OK "Database seeded"
Pop-Location

# ══════════════════════════════════════════════════════════════════════
# F. Frontend: npm install + build + .env.local
# ══════════════════════════════════════════════════════════════════════
Write-Step "Writing frontend .env.local"
$frontendEnv = @"
NODE_ENV=production
NEXT_PUBLIC_API_BASE_URL=https://$ApiHostname
ADMIN_API_KEY=$adminKey
ADMIN_SESSION_SECRET=$sessionSecret
"@
Set-Content -Path "$webDest\.env.local" -Value $frontendEnv -Encoding UTF8
Write-OK "Frontend .env.local written"

Write-Step "Installing Node.js dependencies"
Push-Location $webDest
npm ci --silent 2>&1 | Out-Null
Write-OK "npm ci complete"

Write-Step "Building Next.js"
npm run build 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Next.js build failed." }
Write-OK "Next.js built successfully"
Pop-Location

# ══════════════════════════════════════════════════════════════════════
# G. IIS: application pools + sites
# ══════════════════════════════════════════════════════════════════════
Write-Step "Configuring IIS application pools"

foreach ($pool in @("BeHAZELD-API", "BeHAZELD-Web")) {
    $existing = & $apicmd list apppool $pool 2>&1
    if ($existing -notlike "*$pool*") {
        & $apicmd add apppool /name:$pool /managedRuntimeVersion:"" | Out-Null
        Write-OK "Created app pool $pool"
    } else {
        Write-Warn "App pool $pool already exists"
    }
}

Write-Step "Configuring IIS sites"

# API site
$apiSiteExists = & $apicmd list site "BeHAZELD-API" 2>&1
if ($apiSiteExists -notlike "*BeHAZELD-API*") {
    & $apicmd add site /name:"BeHAZELD-API" `
        /physicalPath:$apiDest `
        /bindings:"http/*:80:$ApiHostname" | Out-Null
    & $apicmd set app "BeHAZELD-API/" /applicationPool:"BeHAZELD-API" | Out-Null
    Write-OK "IIS site BeHAZELD-API created"
} else {
    Write-Warn "IIS site BeHAZELD-API already exists"
}

# Web site
$webSiteExists = & $apicmd list site "BeHAZELD-Web" 2>&1
if ($webSiteExists -notlike "*BeHAZELD-Web*") {
    & $apicmd add site /name:"BeHAZELD-Web" `
        /physicalPath:$webDest `
        /bindings:"http/*:80:$WebHostname" | Out-Null
    & $apicmd set app "BeHAZELD-Web/" /applicationPool:"BeHAZELD-Web" | Out-Null
    Write-OK "IIS site BeHAZELD-Web created"
} else {
    Write-Warn "IIS site BeHAZELD-Web already exists"
}

Write-Warn "Remember to add HTTPS bindings with your SSL certificate via IIS Manager."

# ══════════════════════════════════════════════════════════════════════
# H. NSSM: FastAPI Windows Service
# ══════════════════════════════════════════════════════════════════════
Write-Step "Registering BeHAZELD-API Windows Service via NSSM"

$uvicorn  = "$apiDest\.venv\Scripts\uvicorn.exe"
$svcName  = "BeHAZELD-API"

# Remove existing service if present
$existing = nssm status $svcName 2>&1
if ($existing -notlike "*can't open service*") {
    nssm stop  $svcName 2>&1 | Out-Null
    nssm remove $svcName confirm 2>&1 | Out-Null
    Write-Warn "Removed existing $svcName service"
}

nssm install $svcName $uvicorn
nssm set $svcName AppParameters "app.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers"
nssm set $svcName AppDirectory  $apiDest
nssm set $svcName AppStdout     "$apiLog\stdout.log"
nssm set $svcName AppStderr     "$apiLog\stderr.log"
nssm set $svcName AppRotateFiles 1
nssm set $svcName AppRotateSeconds 86400
nssm set $svcName AppRestartDelay 5000
nssm set $svcName Start SERVICE_AUTO_START
nssm set $svcName DisplayName "BeHAZELD FastAPI Backend"
nssm set $svcName Description "BeHAZEL'd e-commerce API powered by FastAPI + uvicorn"

# Inject environment variables into the service
nssm set $svcName AppEnvironmentExtra `
    "DATABASE_URL=$DATABASE_URL" `
    "ENVIRONMENT=production" `
    "ADMIN_API_KEY=$adminKey" `
    "ADMIN_JWT_SECRET=$jwtSecret" `
    "ADMIN_JWT_EXPIRY=86400" `
    "ALLOWED_ORIGINS=https://$WebHostname,https://behazeld.com" `
    "CLOUDINARY_CLOUD_NAME=$cloudName" `
    "CLOUDINARY_API_KEY=$cloudKey" `
    "CLOUDINARY_API_SECRET=$cloudSecret"

nssm start $svcName
Start-Sleep -Seconds 4

$status = nssm status $svcName 2>&1
Write-OK "Service $svcName status: $status"

# ══════════════════════════════════════════════════════════════════════
# I. pm2: Next.js Windows Service
# ══════════════════════════════════════════════════════════════════════
Write-Step "Registering BeHAZELD-Web via pm2"

Push-Location $webDest

# Register pm2 as a Windows startup service (only needs to run once)
pm2-startup install 2>&1 | Out-Null

# Delete old pm2 process if it exists
pm2 delete behazeld-web 2>&1 | Out-Null

# Start Next.js
pm2 start npm --name behazeld-web -- start -- --port 3000

# Save process list so it survives reboots
pm2 save

Start-Sleep -Seconds 3
pm2 status behazeld-web
Pop-Location
Write-OK "Next.js service registered with pm2"

# ══════════════════════════════════════════════════════════════════════
# J. Windows Firewall rules
# ══════════════════════════════════════════════════════════════════════
Write-Step "Configuring Windows Firewall"

# Block direct external access to internal service ports
foreach ($port in @(8000, 3000, 1433)) {
    $ruleName = "BeHAZELD Block External Port $port"
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Protocol TCP -LocalPort $port `
        -RemoteAddress Internet -Action Block | Out-Null
    Write-OK "Blocked external access to port $port"
}

# Allow IIS (HTTP + HTTPS)
foreach ($port in @(80, 443)) {
    $ruleName = "BeHAZELD Allow IIS Port $port"
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Protocol TCP -LocalPort $port `
        -Action Allow | Out-Null
    Write-OK "Allowed inbound port $port"
}

# ══════════════════════════════════════════════════════════════════════
# K. Smoke test
# ══════════════════════════════════════════════════════════════════════
Write-Step "Running smoke tests"

Start-Sleep -Seconds 5

try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-OK "FastAPI /health → 200 OK"
    } else {
        Write-Warn "FastAPI /health returned $($resp.StatusCode)"
    }
} catch {
    Write-Warn "FastAPI /health check failed: $_"
    Write-Warn "Check logs at $apiLog\stderr.log"
}

try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-OK "Next.js / → 200 OK"
    } else {
        Write-Warn "Next.js / returned $($resp.StatusCode)"
    }
} catch {
    Write-Warn "Next.js check failed: $_"
    Write-Warn "Check pm2 logs: pm2 logs behazeld-web"
}

Write-Host @"

╔════════════════════════════════════════════════════════════════╗
║              🎉  Deployment complete!                          ║
╠════════════════════════════════════════════════════════════════╣
║  Next steps:                                                   ║
║  1. Import SSL certificate in IIS Manager                      ║
║  2. Add HTTPS bindings (port 443) for both IIS sites           ║
║  3. Update DNS A records to point to this server's IP          ║
║  4. Revoke DDL permissions from behazeld_app in SSMS           ║
║     (run: 04-post-go-live.sql)                                 ║
║                                                                ║
║  Useful commands:                                              ║
║    nssm status BeHAZELD-API                                    ║
║    nssm restart BeHAZELD-API                                   ║
║    pm2 status                                                   ║
║    pm2 logs behazeld-web                                        ║
║    Get-Content C:\logs\behazeld-api\stderr.log -Tail 50        ║
╚════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
