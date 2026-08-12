# BeHazeld Windows Self-Hosting Steps

This guide moves the full BeHazeld stack to the Windows AWS server at `54.224.2.26`.

## Target Setup

- `https://www.behazeld.com` -> Storefront Next.js app on `127.0.0.1:3000`
- `https://admin.behazeld.com` -> Admin Next.js app on `127.0.0.1:3001`
- `https://api.behazeld.com` -> FastAPI backend on `127.0.0.1:8000`
- PostgreSQL runs locally on Windows.
- Product images are stored locally at `C:\BeHazeld\data\uploads`.

## Phase 1: Install PostgreSQL

1. Download PostgreSQL for Windows from `https://www.postgresql.org/download/windows/`.
2. Install PostgreSQL 16 or newer.
3. Remember the password for the `postgres` superuser.
4. Open SQL Shell or pgAdmin.
5. Create the database and app user:

```sql
CREATE DATABASE behazeld_os;
CREATE USER behazeld_app WITH PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE behazeld_os TO behazeld_app;
```

Connect to `behazeld_os`, then run:

```sql
GRANT CREATE ON SCHEMA public TO behazeld_app;
```

## Phase 2: Prepare Folders

Open PowerShell as Administrator:

```powershell
mkdir C:\BeHazeld\data
mkdir C:\BeHazeld\data\uploads
mkdir C:\BeHazeld\data\invoices
mkdir C:\BeHazeld\logs
```

## Phase 3: Backend Environment

Create:

`C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Backend\.env`

Use the backend template from `windows-self-hosting.env.guide`.

Important:

- Replace `CHANGE_THIS_PASSWORD` with the PostgreSQL password.
- Replace `JWT_SECRET_KEY` with a long private secret.

## Phase 4: Install Backend Dependencies

Open PowerShell:

```powershell
cd "C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Backend"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `py -3.11` is not found, install Python 3.11 from `https://www.python.org/downloads/windows/`.

## Phase 5: Create Database Tables

With the backend virtual environment activated:

```powershell
cd "C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Backend"
alembic upgrade head
```

## Phase 6: Migrate Existing Neon Data

This requires the Neon database connection string.

On a machine with PostgreSQL tools installed, export from Neon:

```powershell
pg_dump "NEON_DATABASE_URL_HERE" -Fc -f C:\BeHazeld\backup\behazeld_neon.dump
```

Restore into local PostgreSQL:

```powershell
pg_restore -d "postgresql://behazeld_app:CHANGE_THIS_PASSWORD@127.0.0.1:5432/behazeld_os" --clean --if-exists C:\BeHazeld\backup\behazeld_neon.dump
```

If this step is confusing, stop and ask before running destructive restore commands.

## Phase 7: Start Backend

```powershell
cd "C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Test:

```text
http://127.0.0.1:8000/health
```

Expected: JSON with database and uploads checks as `ok`.

## Phase 8: Run Backend Permanently

Create:

`C:\BeHazeld\start-behazeld-backend.bat`

```bat
@echo off
cd /d C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Backend
call .venv\Scripts\activate.bat
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use Windows Task Scheduler:

- Name: `BeHazeld Backend`
- Trigger: At startup
- Action: `C:\BeHazeld\start-behazeld-backend.bat`
- Run whether user is logged on or not
- Run with highest privileges
- Restart on failure

## Phase 9: Admin Environment

Create:

`C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Admin\.env.local`

```env
NEXT_PUBLIC_API_URL=https://api.behazeld.com
```

## Phase 10: Build And Run Admin

```powershell
cd "C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Admin"
npm install
npm run build
npm run start
```

Test:

```text
http://127.0.0.1:3001
```

For permanent startup, create:

`C:\BeHazeld\start-behazeld-admin.bat`

```bat
@echo off
cd /d C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Admin
npm run start
```

Add it to Task Scheduler as `BeHazeld Admin`.

## Phase 11: Update Storefront Environment

Update:

`C:\BeHazeld\The-Complete-Story\BeHazeld_Website\frontend\.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=https://api.behazeld.com
NEXT_PUBLIC_TENANT_ID=b86e1ba8-2d77-4eed-a069-4041504d3717
ADMIN_SESSION_SECRET=CHANGE_THIS_TO_A_LONG_RANDOM_STOREFRONT_SECRET
ADMIN_API_KEY=Gappu@2023
```

Then rebuild and restart storefront:

```powershell
cd "C:\BeHazeld\The-Complete-Story\BeHazeld_Website\frontend"
npm install
npm run build
npm run start
```

## Phase 12: IIS Sites

Create three IIS websites:

### Storefront

- Site name: `BeHazeld Storefront`
- Path: `C:\BeHazeld\The-Complete-Story\BeHazeld_Website\frontend`
- Host: `www.behazeld.com`
- Port: `80`

### Admin

- Site name: `BeHazeld Admin`
- Path: `C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Admin`
- Host: `admin.behazeld.com`
- Port: `80`

### API

- Site name: `BeHazeld API`
- Path: `C:\BeHazeld\The-Complete-Story\BeHazeld_OS_Backend`
- Host: `api.behazeld.com`
- Port: `80`

Each folder has its own `web.config`.

Enable ARR proxy in IIS server settings.

## Phase 13: DNS

Create DNS records:

```text
www   A   54.224.2.26
admin A   54.224.2.26
api   A   54.224.2.26
```

## Phase 14: HTTPS

Install Win-ACME and create certificates for:

- `www.behazeld.com`
- `admin.behazeld.com`
- `api.behazeld.com`

## Phase 15: Final Checks

Open:

```text
https://api.behazeld.com/health
https://admin.behazeld.com/login
https://www.behazeld.com
```

Then test:

1. Login to admin.
2. Upload product image.
3. Confirm image URL begins with `https://api.behazeld.com/uploads/`.
4. Confirm website shows the product/image.
5. Place a test order.

