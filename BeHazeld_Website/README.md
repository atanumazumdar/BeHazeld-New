# BeHAZEL'd — Luxury Ethnic Couture Storefront

A full-stack e-commerce platform for **BeHAZEL'd**, a luxury Indian ethnic couture brand. Built with Next.js 15 on the frontend and FastAPI on the backend, designed for production deployment on Windows Server with IIS and MS SQL Server.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Collections & Products](#collections--products)
- [Design System](#design-system)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [API Reference](#api-reference)
- [Admin Portal](#admin-portal)
- [Image Uploads (Cloudinary)](#image-uploads-cloudinary)
- [Production Deployment — Windows Server + IIS](#production-deployment--windows-server--iis)
- [Quality Checks](#quality-checks)

---

## Overview

BeHAZEL'd is a dynamic luxury couture store selling handcrafted Indian ethnic wear across six curated collections. The platform supports:

- **Public storefront** — collection browsing, product detail pages, cart, and checkout
- **Admin portal** — JWT-protected product and collection management with Cloudinary image uploads
- **SSG + ISR** — pages are statically generated and revalidated every 60 seconds for performance
- **PWA** — Progressive Web App manifest for installability
- **Production-ready** — IIS reverse proxy, NSSM Windows Service, MS SQL Server connection pooling

---

## Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 + inline styles |
| Animations | Framer Motion 12 |
| State management | Zustand 5 (persist middleware) |
| Runtime | React 19 |

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115+ |
| Language | Python 3.11+ |
| ORM | SQLAlchemy 2.0 (async-compatible) |
| Migrations | Alembic (batch mode for SQLite, standard for MSSQL) |
| Validation | Pydantic v2 |
| Auth | JWT via `python-jose` + `passlib[bcrypt]` |
| Image CDN | Cloudinary SDK 2 |
| Dev DB | SQLite |
| Prod DB | MS SQL Server (via `pyodbc` + ODBC Driver 18) |
| Server | Uvicorn behind IIS ARR (Windows) |

---

## Architecture

```
Internet (HTTPS 443)
    │
    ▼
IIS + ARR (Reverse Proxy)
    ├── /api/* → Uvicorn on 127.0.0.1:8000   (FastAPI)
    └── /*     → pm2 on 127.0.0.1:3000        (Next.js)
                        │
                        ▼
                MS SQL Server on localhost:1433
                        │
                        ▼
                Cloudinary CDN (product images)
```

**Key design decisions:**
- `ProxyHeadersMiddleware` trusts IIS as the single upstream proxy so `request.client.host` and `request.url.scheme` reflect the real client.
- CORS origins are driven by the `ALLOWED_ORIGINS` env var (comma-separated) — no code changes needed per environment.
- Docs (`/docs`, `/redoc`) are hidden when `ENVIRONMENT=production`.
- Cart state is persisted in `localStorage` via Zustand `persist` middleware using `productId:variantId` as the line key.
- All critical layout properties use inline `style={{}}` to avoid Tailwind v4 JIT purging issues with dynamic class names.

---

## Project Structure

```
BeHazel'd Website/
├── frontend/                       # Next.js 15 storefront
│   ├── app/
│   │   ├── page.tsx                # Homepage (brand hero)
│   │   ├── atelier/                # All-collections landing
│   │   ├── collections/[slug]/     # Dynamic collection pages (SSG + ISR)
│   │   ├── products/[slug]/        # Product detail page
│   │   ├── cart/                   # Cart view
│   │   ├── checkout/               # Checkout form
│   │   ├── story/                  # Brand story
│   │   ├── register/               # Customer registration
│   │   ├── admin/
│   │   │   ├── login/              # Admin login
│   │   │   └── upload/             # Add new product (JWT-protected)
│   │   └── api/admin/              # Next.js route handlers (proxy to FastAPI)
│   │       ├── login/
│   │       ├── logout/
│   │       ├── products/
│   │       └── images/
│   ├── components/
│   │   ├── layout/Header.tsx
│   │   ├── collection/ProductListingPage.tsx   # Hero + 4-col product grid
│   │   ├── product/
│   │   │   ├── ProductCard.tsx                 # Single-image card with size picker
│   │   │   ├── ProductGrid.tsx                 # 4-column borderless grid
│   │   │   └── ProductDetailPage.tsx
│   │   ├── cart/
│   │   ├── checkout/
│   │   ├── admin/
│   │   │   ├── AdminUploadShell.tsx
│   │   │   └── ProductUploadForm.tsx
│   │   └── pwa/PWARegister.tsx
│   └── web.config                              # IIS ARR config for Next.js
│
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── main.py                 # App factory, middleware, router registration
│   │   ├── database.py             # Dialect-aware engine (SQLite / MSSQL)
│   │   ├── seed.py                 # Idempotent seed: 3 collections × 4 products
│   │   ├── models/
│   │   │   ├── collection.py
│   │   │   ├── product.py
│   │   │   ├── product_image.py
│   │   │   ├── product_variant.py
│   │   │   ├── customer.py
│   │   │   └── order.py
│   │   ├── schemas/
│   │   │   ├── admin.py            # Write schemas (create / update / patch)
│   │   │   ├── collection.py
│   │   │   ├── product.py
│   │   │   ├── customer.py
│   │   │   └── order.py
│   │   ├── routers/
│   │   │   ├── collections.py      # GET /collections/, /collections/{slug}
│   │   │   ├── products.py         # GET /products/, /products/{slug}
│   │   │   ├── checkout.py         # POST /checkout/
│   │   │   ├── customers.py        # POST /customers/register
│   │   │   └── admin/
│   │   │       ├── auth.py         # POST /admin/auth/token
│   │   │       ├── collections.py  # CRUD /admin/collections/
│   │   │       ├── products.py     # CRUD /admin/products/ + variants + images
│   │   │       └── dependencies.py # JWT Bearer guard
│   │   └── services/
│   │       └── cloudinary_service.py
│   ├── alembic/                    # Alembic migration env
│   ├── requirements.txt
│   └── web.config                  # IIS ARR config for FastAPI
│
├── deploy/windows/                 # Production deployment scripts
│   ├── 01-prerequisites.ps1        # IIS, Python, Node, NSSM, ODBC Driver 18
│   ├── 02-sql-server-setup.sql     # CREATE DATABASE, LOGIN, least-privilege grants
│   ├── 03-deploy-and-services.ps1  # Full deploy: venv, build, IIS sites, services
│   ├── 04-post-go-live.sql         # Revoke CREATE TABLE / ALTER from app login
│   └── README.md                   # Operations runbook
│
└── brand-site/                     # Original Vite/React brand editorial (legacy)
```

---

## Collections & Products

Six curated collections are seeded into the database:

| # | Collection | Description |
|---|---|---|
| 1 | **Campus Muse** | Effortless. Expressive. Unapologetically You. |
| 2 | **Power Edit** | Tailored for ambition. Styled for impact. |
| 3 | **Afterglow Evenings** | Turn moments into statements. |
| 4 | **Ultra Luxe** | Couture craftsmanship without compromise. |
| 5 | **Accessories** | The finishing touch that defines the look. |
| 6 | **Pre Loved** | Sustainably yours. Uniquely Hazel. |

**Seeded products (12 total):**

- Campus Muse — Ivory Bloom Chikankari Kurta · Sage Green Kurta Set · Dusty Rose Anarkali · Indigo Block Print Suit
- Power Edit — Antique Gold Anarkali · Navy Blazer Lehenga · Burgundy Silk Pant Suit · Emerald Indo-Western Co-ord
- Afterglow Evenings — Heritage Kanjivaram Saree · Champagne Zari Set · Midnight Blue Tissue Saree · Rose Gold Sharara Set

Each product ships with **9 size variants** (32 · 34 · 36 · 38 · 40 · 42 · 44 · 46 · 48) and a labelled placeholder image (`Pic 1` … `Pic N`) until real Cloudinary photos are uploaded via the admin portal.

---

## Design System

| Token | Value | Usage |
|---|---|---|
| `HERO_BG` | `#1C0D06` | Collection hero panel (espresso) |
| `BODY_BG` | `#E4DBCE` | Product grid background (warm cream) |
| `GOLD` | `#C09330` | Accent, labels, borders |
| `MUTED` | `rgba(177,152,112,0.6)` | Secondary text, nav links |
| Hero font | Playfair Display (italic, light) | Display headings |
| Body font | system sans | Labels, caps |

Product grid: 4-column, zero-gap, border-separated cells. Each card shows a single product image, the name, base price, colour tabs, and a size picker (32–48).

---

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- npm

### 1. Clone

```bash
git clone https://github.com/atanumazumdar/BeHazeld.git
cd BeHazeld
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit as needed
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
# → http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
# create .env.local if the API URL differs from the default
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
# → http://localhost:3000
```

---

## Environment Variables

### Backend — `backend/.env`

```env
# Database
DATABASE_URL=sqlite:///./store.db
# Production MS SQL Server:
# DATABASE_URL=mssql+pyodbc://behazeld_app:<PASSWORD>@localhost/BeHAZELD?driver=ODBC+Driver+18+for+SQL+Server

# Auth
ADMIN_API_KEY=<minimum 32 chars>
JWT_SECRET_KEY=<minimum 32 chars — use: python3 -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
ALLOWED_ORIGINS=http://localhost:3000
# Production (comma-separated):
# ALLOWED_ORIGINS=https://www.behazeld.com,https://behazeld.com

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Environment
ENVIRONMENT=development   # set to "production" to hide /docs and /redoc
```

### Frontend — `frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# Production: https://api.behazeld.com (or the IIS backend URL)

ADMIN_SESSION_SECRET=<32+ char hex — must match the value used in route handlers>
```

---

## Database Setup

### SQLite (local dev — default)

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.seed
```

### MS SQL Server (production)

1. Run `deploy/windows/02-sql-server-setup.sql` in SSMS to create the database and least-privilege login.
2. Set `DATABASE_URL` in `.env` to the MSSQL connection string.
3. Run migrations and seed as above.
4. After go-live run `deploy/windows/04-post-go-live.sql` to revoke schema-altering permissions.

**Reset dev database:**

```bash
rm backend/store.db
alembic upgrade head
python -m app.seed
```

---

## API Reference

All endpoints return JSON. The backend runs on port **8000**.

### Public

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness + DB check (200 / 503) |
| `GET` | `/collections/` | List all active collections |
| `GET` | `/collections/{slug}` | Collection detail + products |
| `GET` | `/products/` | List all products |
| `GET` | `/products/{slug}` | Product detail + variants + images |
| `POST` | `/checkout/` | Place an order |
| `POST` | `/customers/register` | Register a new customer |

### Admin (Bearer JWT required)

Obtain a token first:

```bash
curl -X POST http://localhost:8000/admin/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "<ADMIN_API_KEY>"}'
```

| Method | Path | Description |
|---|---|---|
| `POST` | `/admin/auth/token` | Exchange API key for JWT |
| `GET` | `/admin/collections/` | List collections |
| `POST` | `/admin/collections/` | Create collection |
| `PATCH` | `/admin/collections/{id}` | Update collection |
| `DELETE` | `/admin/collections/{id}` | Delete collection |
| `GET` | `/admin/products/` | List products |
| `POST` | `/admin/products/` | Create product |
| `PATCH` | `/admin/products/{id}` | Update product |
| `DELETE` | `/admin/products/{id}` | Delete product |
| `POST` | `/admin/products/{id}/variants/` | Add variant |
| `PATCH` | `/admin/products/{id}/variants/{vid}` | Update variant |
| `POST` | `/admin/products/{id}/variants/{vid}/stock` | Adjust stock |
| `POST` | `/admin/products/{id}/images/` | Add image by URL |
| `DELETE` | `/admin/products/{id}/images/{iid}` | Remove image |

Interactive docs (dev only): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Admin Portal

The admin portal lives at `/admin`. It is protected by an HMAC-SHA256 `HttpOnly` session cookie set via the Next.js route handler at `/api/admin/login`.

**Login flow:**
1. `POST /api/admin/login` → Next.js route handler → `POST /admin/auth/token` (FastAPI) → sets `admin_token` cookie.
2. All subsequent admin API calls read the cookie server-side and forward the Bearer token to FastAPI.

**Add a product** (`/admin/upload`):
1. Log in at `/admin/login`.
2. Fill in name, slug, description, base price, collection, and size/colour variants.
3. Upload images via Cloudinary (drag-and-drop). Each image is tagged with its product ID.
4. Submit — the product is live immediately (ISR revalidates within 60 seconds).

**SKU format:** `COLLECTION-COLOR-SIZE`, e.g. `CM-IVO-36` (uppercase, digits, hyphens only).

---

## Image Uploads (Cloudinary)

Images are uploaded from the admin portal directly to Cloudinary. The backend stores only the resulting CDN URL.

**Transform presets used:**

| Preset | Dimensions | Use |
|---|---|---|
| `card` | 400 × 533 (crop: fill) | Product grid thumbnail |
| `detail` | 800 × 1066 (crop: fill) | Product detail page |
| `hero` | 1600 × 900 (crop: fill) | Collection hero |
| `original` | — | Full-resolution download |

**Placeholder images** (pre-upload): `placehold.co/400x533/D8CEBC/7A5C14` labelled `Pic 1` … `Pic N` in the brand cream/amber palette.

---

## Production Deployment — Windows Server + IIS

Full automation scripts live in `deploy/windows/`. Run them in order on the server:

### Step 1 — Prerequisites (PowerShell as Administrator)

```powershell
.\deploy\windows\01-prerequisites.ps1
```

Installs: IIS + URL Rewrite + ARR, Python 3.11, Node LTS, NSSM, ODBC Driver 18 for SQL Server.

### Step 2 — SQL Server setup (SSMS)

```sql
-- Run as sa or sysadmin:
-- deploy/windows/02-sql-server-setup.sql
```

Creates `BeHAZELD` database and `behazeld_app` login with least-privilege grants.

### Step 3 — Deploy & configure services (PowerShell as Administrator)

```powershell
.\deploy\windows\03-deploy-and-services.ps1
```

Does everything in one pass:
- Copies files with `robocopy`
- Creates Python venv, installs requirements
- Writes `.env` files
- Runs `alembic upgrade head` and `python -m app.seed`
- Runs `npm ci && npm run build`
- Creates IIS sites for frontend and backend with the correct `web.config`
- Registers the FastAPI backend as a Windows Service via NSSM
- Starts the Next.js frontend via pm2
- Opens firewall ports 80 and 443

### Step 4 — Post go-live hardening (SSMS)

```sql
-- Run after first successful deploy:
-- deploy/windows/04-post-go-live.sql
```

Revokes `CREATE TABLE` and `ALTER` from `behazeld_app` so the app login cannot modify the schema in production.

### Network topology

```
Internet → IIS (443 HTTPS, ARR)
               ├── behazeld.com/*     → pm2 Next.js   :3000
               └── api.behazeld.com/* → NSSM Uvicorn  :8000
                                              │
                                       MS SQL Server :1433
```

### Health check

```bash
curl https://api.behazeld.com/health
# {"status":"ok","version":"2.0.0","database":"connected"}
```

IIS ARR can poll `/health` to detect backend failures and route traffic accordingly.

---

## Quality Checks

### Frontend

```bash
cd frontend
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run build       # production build (catches missing env vars, type errors)
```

### Backend

```bash
cd backend
source .venv/bin/activate
python -m compileall app migrations   # syntax check all modules
```

---

## GitHub

```
https://github.com/atanumazumdar/BeHazeld.git
```

**Branch strategy:**
- `main` — production-ready code, deployed to Windows Server
- Feature branches — all development work, merged via PR

---

*BeHAZEL'd · Dynamic Luxury Couture Store · v2.0.0*
