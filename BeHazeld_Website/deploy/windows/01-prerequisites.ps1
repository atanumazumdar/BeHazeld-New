#Requires -RunAsAdministrator
<#
.SYNOPSIS
    BeHAZEL'd — Step 1: Install all Windows Server prerequisites.

.DESCRIPTION
    Run this script once on a fresh Windows Server 2019/2022 instance.
    It installs IIS, URL Rewrite, ARR, Python, Node.js, NSSM, and the
    ODBC Driver 18 for SQL Server.

    Prerequisites: Windows Server 2019 or 2022, Administrator PowerShell.

.NOTES
    Run from: PowerShell (Administrator)
    Command : .\01-prerequisites.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "    OK: $msg" -ForegroundColor Green }

# ── 1. IIS + management tools ─────────────────────────────────────────
Write-Step "Installing IIS and management tools"
$features = @(
    "Web-Server",
    "Web-Common-Http",
    "Web-Static-Content",
    "Web-Default-Doc",
    "Web-Http-Errors",
    "Web-Http-Redirect",
    "Web-Health",
    "Web-Http-Logging",
    "Web-Performance",
    "Web-Stat-Compression",
    "Web-Security",
    "Web-Filtering",
    "Web-Mgmt-Tools",
    "Web-Mgmt-Console",
    "Web-Scripting-Tools"
)
Install-WindowsFeature -Name $features -IncludeManagementTools | Out-Null
Write-OK "IIS installed"

# ── 2. URL Rewrite module ─────────────────────────────────────────────
Write-Step "Downloading and installing URL Rewrite 2.1"
$urlRewriteMsi = "$env:TEMP\rewrite_amd64.msi"
Invoke-WebRequest -Uri "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi" `
    -OutFile $urlRewriteMsi -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$urlRewriteMsi`" /quiet /norestart" -Wait
Write-OK "URL Rewrite installed"

# ── 3. Application Request Routing (ARR) 3.0 ─────────────────────────
Write-Step "Downloading and installing ARR 3.0"
$arrExe = "$env:TEMP\ARRv3_setup_amd64.exe"
Invoke-WebRequest -Uri "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47C4-B631-0DA35ADDB496/ARRv3_setup_amd64_en-US.exe" `
    -OutFile $arrExe -UseBasicParsing
Start-Process $arrExe -ArgumentList "/quiet /norestart" -Wait
Write-OK "ARR installed"

# Enable ARR proxy at the server level
Start-Sleep -Seconds 3
$appcmd = "$env:SystemRoot\system32\inetsrv\appcmd.exe"
if (Test-Path $appcmd) {
    & $appcmd set config -section:system.webServer/proxy /enabled:"True" /commit:apphost 2>&1 | Out-Null
    Write-OK "ARR proxy enabled"
}

# ── 4. Python 3.11 ───────────────────────────────────────────────────
Write-Step "Installing Python 3.11 (x64)"
winget install --id Python.Python.3.11 --source winget --silent --accept-source-agreements --accept-package-agreements
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
Write-OK "Python installed: $(python --version 2>&1)"

# ── 5. Node.js LTS ───────────────────────────────────────────────────
Write-Step "Installing Node.js LTS"
winget install --id OpenJS.NodeJS.LTS --source winget --silent --accept-source-agreements --accept-package-agreements
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
Write-OK "Node.js installed: $(node --version 2>&1)"

# Install pm2 and pm2-windows-startup globally
npm install -g pm2 pm2-windows-startup 2>&1 | Out-Null
Write-OK "pm2 installed: $(pm2 --version 2>&1)"

# ── 6. NSSM (Non-Sucking Service Manager) ────────────────────────────
Write-Step "Installing NSSM"
$nssmZip  = "$env:TEMP\nssm.zip"
$nssmDir  = "C:\tools\nssm"
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $nssmZip -UseBasicParsing
Expand-Archive -Path $nssmZip -DestinationPath "$env:TEMP\nssm_extract" -Force
New-Item -ItemType Directory -Path $nssmDir -Force | Out-Null
Copy-Item "$env:TEMP\nssm_extract\nssm-2.24\win64\nssm.exe" "$nssmDir\nssm.exe" -Force

# Add NSSM to system PATH
$machinePath = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($machinePath -notlike "*$nssmDir*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$machinePath;$nssmDir", "Machine")
}
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
Write-OK "NSSM installed at $nssmDir"

# ── 7. ODBC Driver 18 for SQL Server ─────────────────────────────────
Write-Step "Installing ODBC Driver 18 for SQL Server"
$odbcMsi = "$env:TEMP\msodbcsql18.msi"
Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/?linkid=2249006" -OutFile $odbcMsi -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$odbcMsi`" /quiet /norestart IACCEPTMSODBCSQLLICENSETERMS=YES" -Wait
Write-OK "ODBC Driver 18 installed"

# ── 8. Create directory structure ────────────────────────────────────
Write-Step "Creating application directories"
@(
    "C:\inetpub\wwwroot\behazeld-api",
    "C:\inetpub\wwwroot\behazeld-web",
    "C:\logs\behazeld-api",
    "C:\logs\behazeld-web"
) | ForEach-Object {
    New-Item -ItemType Directory -Path $_ -Force | Out-Null
    Write-OK "Created $_"
}

Write-Host "`n✅  All prerequisites installed successfully." -ForegroundColor Green
Write-Host "   Next: run 02-sql-server-setup.sql in SSMS, then 03-deploy-and-services.ps1" -ForegroundColor Yellow
