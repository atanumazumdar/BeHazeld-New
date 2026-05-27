# BeHAZEL'd Project Overview

BeHAZEL'd is a full-stack luxury ethnic couture ecommerce project. It combines a branded editorial storefront with a minimal working commerce flow: product discovery, product detail pages, cart, checkout, and backend order creation.

## Current Stack

### Frontend

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Framer Motion
- Zustand for cart state

### Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic migrations
- SQLite for local development
- Designed to support MS SQL Server in production

## Project Structure

```txt
BeHazel'd Website/
├── frontend/              # Next.js ecommerce storefront
├── backend/               # FastAPI API and database layer
├── brand-site/            # Original branded couture prototype
├── deploy/windows/        # Windows Server / IIS deployment assets
├── README.md              # Full technical README
└── PROJECT_OVERVIEW.md    # Quick project summary
```

## Core User Flow

```txt
Home / Atelier
  → Collection browsing
  → Product detail
  → Add to bag
  → Cart review
  → Checkout form
  → Backend order creation
```

## Key Features

- Branded couture homepage and product presentation
- Product listing and product detail pages
- Persistent cart using Zustand
- Quantity update, remove item, and clear cart behavior
- Checkout page with contact and shipping details
- FastAPI checkout endpoint that creates orders
- Database-backed products and orders
- Seed data for couture products and collections

## Important Local Commands

### Backend

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Backend URL:

```txt
http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```txt
http://localhost:3000
```

## Verification Commands

```bash
cd frontend
npm run typecheck
npm run build
```

```bash
cd backend
python -m compileall app
```

## API Endpoints

```txt
GET  /health
GET  /products/
GET  /products/{slug}
POST /checkout/
```

## Current Status

The MVP ecommerce flow is functional. The branded couture prototype has been integrated into the Next.js storefront styling and user experience while preserving the working FastAPI backend and Zustand cart architecture.

## Suggested Next Steps

- Add Stripe or another payment provider
- Add customer accounts and order history
- Add admin-facing product management polish
- Replace placeholder/demo images with final product photography
- Add automated tests for checkout and cart behavior
