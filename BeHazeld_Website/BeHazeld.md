# BeHAZEL'd — Project Overview

**Full-stack luxury ethnic couture e-commerce platform**
GitHub: `https://github.com/atanumazumdar/BeHazeld.git`
Version: 2.0.0

---

## What It Is

BeHAZEL'd is an end-to-end e-commerce store for a luxury Indian ethnic couture brand. It includes a public-facing storefront, an admin portal for managing products and collections, and a production deployment stack for Windows Server + IIS + MS SQL Server.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 · TypeScript · Tailwind CSS v4 · Framer Motion · Zustand |
| Backend | FastAPI · Python 3.11 · SQLAlchemy 2.0 · Alembic · Pydantic v2 |
| Auth | JWT (`python-jose`) · HMAC-SHA256 HttpOnly session cookie |
| Database | SQLite (dev) · MS SQL Server (prod) |
| Images | Cloudinary SDK 2 |
| Server | Uvicorn · IIS + ARR · NSSM · pm2 |

---

## Project Structure

```
BeHazel'd Website/
├── frontend/          Next.js 15 storefront
├── backend/           FastAPI API + SQLAlchemy models + Alembic migrations
├── deploy/windows/    PowerShell + SQL Server production deployment scripts
└── brand-site/        Original Vite/React brand editorial (legacy)
```

---

## Collections

| # | Name | Tagline |
|---|---|---|
| 1 | Campus Muse | Effortless. Expressive. Unapologetically You. |
| 2 | Power Edit | Tailored for ambition. Styled for impact. |
| 3 | Afterglow Evenings | Turn moments into statements. |
| 4 | Ultra Luxe | Couture craftsmanship without compromise. |
| 5 | Accessories | The finishing touch that defines the look. |
| 6 | Pre Loved | Sustainably yours. Uniquely Hazel. |

12 seeded products across the first three collections. Each product has 9 size variants (32–48) and labelled placeholder images (Pic 1 … Pic N) until real photos are uploaded via the admin portal.

---

## Key Pages

| Route | Description |
|---|---|
| `/` | Brand homepage |
| `/atelier` | All-collections landing |
| `/collections/[slug]` | 4-column product grid with split hero |
| `/products/[slug]` | Product detail with size/colour picker |
| `/cart` | Cart view |
| `/checkout` | Checkout form |
| `/admin/login` | Admin login |
| `/admin/upload` | Add new product (JWT-protected) |

---

## API Endpoints

### Public
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness + DB connectivity (200 / 503) |
| `GET` | `/collections/` | All active collections |
| `GET` | `/collections/{slug}` | Collection + products |
| `GET` | `/products/{slug}` | Product + variants + images |
| `POST` | `/checkout/` | Place an order |
| `POST` | `/customers/register` | Register a customer |

### Admin (Bearer JWT)
| Method | Path | Description |
|---|---|---|
| `POST` | `/admin/auth/token` | Exchange API key for JWT |
| `POST/PATCH/DELETE` | `/admin/collections/` | Manage collections |
| `POST/PATCH/DELETE` | `/admin/products/` | Manage products |
| `POST/PATCH` | `/admin/products/{id}/variants/` | Manage variants |
| `POST` | `/admin/products/{id}/variants/{vid}/stock` | Adjust stock |
| `POST/DELETE` | `/admin/products/{id}/images/` | Manage images |

---

## Local Development

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload
# → http://localhost:8000

# Frontend (new terminal)
cd frontend
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
# → http://localhost:3000
```

---

## Environment Variables

### `backend/.env`
```env
DATABASE_URL=sqlite:///./store.db
ADMIN_API_KEY=<32+ chars>
JWT_SECRET_KEY=<32+ chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALLOWED_ORIGINS=http://localhost:3000
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
ENVIRONMENT=development
```

### `frontend/.env.local`
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ADMIN_SESSION_SECRET=<32+ chars>
```

---

## Production Deployment (Windows Server + IIS)

```powershell
# Run as Administrator, in order:
.\deploy\windows\01-prerequisites.ps1        # IIS, Python, Node, NSSM, ODBC Driver 18
# In SSMS: run 02-sql-server-setup.sql       # Create DB + app login
.\deploy\windows\03-deploy-and-services.ps1  # Deploy + IIS sites + services
# In SSMS: run 04-post-go-live.sql           # Harden DB permissions
```

**Production topology:**
```
Internet → IIS (HTTPS 443, ARR)
               ├── behazeld.com      → pm2  Next.js   :3000
               └── api.behazeld.com  → NSSM Uvicorn   :8000
                                              │
                                       MS SQL Server  :1433
```

---

## Design Tokens

| Token | Value | Usage |
|---|---|---|
| Hero background | `#1C0D06` | Collection hero (espresso) |
| Page background | `#E4DBCE` | Product grid (warm cream) |
| Gold accent | `#C09330` | Labels, borders, highlights |
| Muted | `rgba(177,152,112,0.6)` | Secondary text, nav links |
| Display font | Playfair Display (italic) | Headings |

---

## Admin Portal Flow

1. Log in at `/admin/login` with `ADMIN_API_KEY`
2. Session stored as HMAC-SHA256 `HttpOnly` cookie
3. Add product at `/admin/upload` — name, slug, price, collection, variants, Cloudinary images
4. Product goes live within 60 seconds (ISR revalidation)

**SKU format:** `COLLECTION-COLOR-SIZE` — uppercase, digits, hyphens only
Example: `CM-IVO-36`, `PE-AGA-40`, `AE-HKS-38`

---

## Image Uploads

Cloudinary presets:

| Preset | Size | Use |
|---|---|---|
| `card` | 400 × 533 | Product grid thumbnail |
| `detail` | 800 × 1066 | Product detail page |
| `hero` | 1600 × 900 | Collection hero |
| `original` | — | Full resolution |

Placeholders: `placehold.co/400x533/D8CEBC/7A5C14` labelled Pic 1 … Pic N

---

## Paths

| | Path |
|---|---|
| Project root | `/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/` |
| Frontend | `/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend/` |
| Backend | `/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend/` |
| Deploy scripts | `/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/deploy/windows/` |
| GitHub | `https://github.com/atanumazumdar/BeHazeld.git` |

---

*BeHAZEL'd · Dynamic Luxury Couture Store · v2.0.0*
