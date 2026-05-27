# BeHAZEL'd — Windows Server Deployment Guide

**Stack:** Windows Server 2019/2022 · IIS (reverse proxy) · MS SQL Server · FastAPI · Next.js

---

## Architecture

```
Internet (HTTPS 443)
        │
       IIS  ──  ARR Reverse Proxy  ──  URL Rewrite
      /    \
     /      \
Port 3000   Port 8000     ← both BLOCKED externally by Windows Firewall
Next.js     FastAPI
(pm2)       (NSSM service)
                │
         SQL Server (localhost:1433, BLOCKED externally)
                │
         Cloudinary CDN  (images)
```

---

## Pre-Requisites (one-time, on the server)

| Software | Version | Purpose |
|---|---|---|
| Windows Server | 2019 or 2022 | Host OS |
| IIS + URL Rewrite + ARR | Latest | Reverse proxy + HTTPS |
| MS SQL Server | 2019 or 2022 | Production database |
| Python | 3.11+ (x64) | FastAPI runtime |
| Node.js | LTS | Next.js runtime |
| NSSM | 2.24 | FastAPI as Windows Service |
| pm2 | Latest | Next.js as Windows Service |
| ODBC Driver 18 | Latest | Python ↔ SQL Server |

---

## Deployment Steps

### Step 1 — Install prerequisites (run once)

```powershell
# Run as Administrator
.\01-prerequisites.ps1
```

Creates IIS, installs URL Rewrite + ARR, Python, Node, NSSM, ODBC Driver 18.

### Step 2 — Set up SQL Server database (run once in SSMS)

Open **SQL Server Management Studio (SSMS)**, connect as SA, and run:

```
02-sql-server-setup.sql
```

⚠ Replace `<YourStrongPassword>` with a real password before running.

### Step 3 — Set environment secrets, then deploy

Set these environment variables in your Administrator PowerShell session **before** running the deploy script:

```powershell
$env:DB_PASSWORD          = "YourSQLPassword"
$env:ADMIN_API_KEY        = "your-admin-api-key"
$env:ADMIN_JWT_SECRET     = "your-jwt-secret-min-32-chars"
$env:ADMIN_SESSION_SECRET = "your-hmac-secret-min-32-chars"
$env:CLOUDINARY_CLOUD_NAME = "your-cloud-name"
$env:CLOUDINARY_API_KEY   = "your-api-key"
$env:CLOUDINARY_API_SECRET = "your-api-secret"
```

Clone the repo to the server, then run:

```powershell
.\03-deploy-and-services.ps1 `
    -SourceRoot   "C:\deploy\BeHazeld" `
    -ApiHostname  "api.behazeld.com" `
    -WebHostname  "www.behazeld.com"
```

This script will:
- Copy files to `C:\inetpub\wwwroot\`
- Create Python virtualenv + `pip install`
- Write `.env` files (permissions-restricted)
- Run `alembic upgrade head` against SQL Server
- Seed the database
- `npm ci` + `next build`
- Create IIS app pools + sites
- Register FastAPI as a Windows Service via NSSM
- Register Next.js via pm2
- Configure Windows Firewall rules

### Step 4 — Add SSL certificate (IIS Manager)

1. Open **IIS Manager** → select the server node → **Server Certificates**
2. Click **Import** → browse to your `.pfx` file → enter export password
3. For each site (`BeHAZELD-API`, `BeHAZELD-Web`):
   - Click the site → **Bindings** → **Add**
   - Type: HTTPS · Port: 443 · Hostname: `api.behazeld.com` (or `www.behazeld.com`)
   - SSL certificate: select your imported cert

### Step 5 — DNS

Point your domain's A records to this server's public IP:

```
A  api.behazeld.com    →  <server IP>
A  www.behazeld.com    →  <server IP>
A  behazeld.com        →  <server IP>
```

### Step 6 — Post-go-live hardening

After confirming the live site works end-to-end, run in SSMS:

```
04-post-go-live.sql
```

This revokes the DDL permissions (CREATE TABLE, ALTER) that Alembic needed during migration — the application only needs read/write from this point.

---

## Day-to-Day Operations

### Manage the FastAPI service

```powershell
nssm status  BeHAZELD-API
nssm start   BeHAZELD-API
nssm stop    BeHAZELD-API
nssm restart BeHAZELD-API

# View live logs
Get-Content C:\logs\behazeld-api\stderr.log -Tail 50 -Wait
```

### Manage the Next.js service

```powershell
pm2 status
pm2 restart behazeld-web
pm2 logs behazeld-web --lines 50
```

### Deploy a code update

```powershell
# Pull latest code
cd C:\deploy\BeHazeld
git pull

# Re-run the deploy script (idempotent)
cd deploy\windows
.\03-deploy-and-services.ps1
```

### Run database migrations manually

```powershell
cd C:\inetpub\wwwroot\behazeld-api
$env:DATABASE_URL = "mssql+pyodbc://behazeld_app:Password@localhost/BeHAZELD?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
.\.venv\Scripts\alembic upgrade head
```

---

## File Locations

| Item | Path |
|---|---|
| FastAPI app | `C:\inetpub\wwwroot\behazeld-api\` |
| FastAPI `.env` | `C:\inetpub\wwwroot\behazeld-api\.env` |
| FastAPI logs | `C:\logs\behazeld-api\` |
| FastAPI IIS config | `C:\inetpub\wwwroot\behazeld-api\web.config` |
| Next.js app | `C:\inetpub\wwwroot\behazeld-web\` |
| Next.js `.env.local` | `C:\inetpub\wwwroot\behazeld-web\.env.local` |
| Next.js logs | `pm2 logs behazeld-web` |
| Next.js IIS config | `C:\inetpub\wwwroot\behazeld-web\web.config` |
| IIS access logs | `C:\inetpub\logs\LogFiles\` |
| IIS server config | `%SystemRoot%\System32\inetsrv\config\applicationHost.config` |

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `500 Bad Gateway` from IIS | FastAPI not running — `nssm status BeHAZELD-API` |
| FastAPI won't start | `Get-Content C:\logs\behazeld-api\stderr.log -Tail 50` |
| DB connection error | Check `DATABASE_URL` in NSSM env; verify SQL Server TCP on 1433 |
| ODBC error `[IM002]` | ODBC Driver 18 not installed — re-run `01-prerequisites.ps1` |
| Next.js 502 | pm2 not running — `pm2 restart behazeld-web` |
| Images not uploading | Check Cloudinary credentials in `.env` |
| Alembic fails | Verify `behazeld_app` has CREATE TABLE + ALTER SCHEMA permissions |
