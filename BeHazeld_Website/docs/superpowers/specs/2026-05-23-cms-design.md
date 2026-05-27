# BeHAZEL'd Admin CMS — Design Spec
**Date:** 2026-05-23  
**Status:** Approved

---

## Overview

A full store admin dashboard built inside the existing Next.js 15 frontend, under the `/admin/*` route group. Covers product catalog, collections, inventory, orders, and customer management. Replaces the minimal `/admin/upload` page with a complete back-office.

---

## Visual Design

- **Palette:** Warm Neutral Light — cream (`#F8F5F0`), white cards, warm borders (`#E2D9CC`), gold accents (`#C09330`), dark brown text (`#3D2B1F`), muted secondary (`#9C8B7A`)
- **Navigation:** Top horizontal nav bar with tabs: Dashboard · Products · Collections · Orders · Customers
- **Typography:** System font (`-apple-system`) for admin UI — Playfair Display is storefront-only
- **Status colours:** Pending = amber (`#FFF8EC`/`#C09330`), Shipped = green (`#EDFBF2`/`#2D8A4E`), Delivered = green, Cancelled = muted red, Inactive = grey

---

## Architecture

### Route Group

```
frontend/app/
├── (admin)/
│   ├── layout.tsx                  ← admin shell: top nav + auth gate
│   └── admin/
│       ├── dashboard/page.tsx
│       ├── products/
│       │   ├── page.tsx            list + search
│       │   ├── new/page.tsx        create product
│       │   └── [id]/page.tsx       edit: details, variants, images, stock
│       ├── collections/page.tsx    list + create + edit inline
│       ├── orders/page.tsx         list + filters + status updates + CSV export
│       └── customers/page.tsx      list + search + view order history
├── admin/login/page.tsx            ← unchanged (outside route group)
```

### Auth

- Existing `middleware.ts` already protects all `/admin/*` routes — no changes needed
- Existing `lib/admin-session.ts` handles JWT cookie validation — unchanged
- The `(admin)/layout.tsx` wraps all admin pages in the shared top nav and verifies session server-side; redirects to `/admin/login` if no valid session

### API Client

A new `lib/admin-api.ts` module wraps all FastAPI admin endpoint calls. All existing admin endpoints are already implemented in the backend. No new backend work required.

---

## Pages

### 1. Dashboard (`/admin/dashboard`)

**Purpose:** Landing page after login. At-a-glance store health.

**Content:**
- Stat cards: total products, total collections, pending order count, total customer count
- Recent orders table (last 10): customer name, amount, status badge, date
- Pending orders count highlighted in gold to draw attention

**Data sources:** `GET /collections/` count, `GET /products/` count, `GET /admin/orders/` filtered by pending

---

### 2. Products (`/admin/products`)

**Purpose:** Full catalog management.

**List view (`/admin/products`):**
- Search bar (client-side filter by name/slug)
- Table: product name, collection, price, total stock (sum across variants), Edit / Delete actions
- Low-stock warning (≤5 units) highlighted in gold
- "Add Product" button → `/admin/products/new`

**Create view (`/admin/products/new`):**
- Form: name, slug (auto-generated from name, editable), description, price, collection (dropdown), is_active toggle
- Variant section: add size variants (32–48), set stock per variant, set SKU (format: `COLLECTION-COLOR-SIZE`)
- Image upload: Cloudinary upload via existing `cloudinary_service`, supports multiple images, set display order

**Edit view (`/admin/products/[id]`):**
- Same form as create, pre-populated
- Inline variant editor: adjust stock per size, add/remove variants
- Image manager: reorder, delete, upload new images
- Delete product button (with confirmation modal)

**Backend endpoints used:**
- `GET/POST/PATCH/DELETE /admin/products/`
- `POST/PATCH /admin/products/{id}/variants/`
- `POST /admin/products/{id}/variants/{vid}/stock`
- `POST/DELETE /admin/products/{id}/images/`

---

### 3. Collections (`/admin/collections`)

**Purpose:** Manage the 6 brand collections.

**Features:**
- List all collections with name, slug, product count, active/inactive badge
- Inline edit: rename, update tagline, toggle active/inactive
- Create new collection (name, slug, tagline)
- Delete collection (blocked if it contains products — show error)
- Display order: up/down arrow buttons to reorder (no drag-and-drop — keeps implementation simple)

**Backend endpoints used:**
- `GET/POST/PATCH/DELETE /admin/collections/`

---

### 4. Orders (`/admin/orders`)

**Purpose:** Full order lifecycle management.

**Features:**
- Status filter tabs: All · Pending · Confirmed · Shipped · Delivered · Cancelled (with count badges)
- Search by customer name or order ID
- Date range filter
- Orders table: order ID, customer name, items summary, total amount, status badge, status update dropdown, date
- Status transitions: Pending → Confirmed → Shipped → Delivered; any → Cancelled
- "Export CSV" button: downloads filtered view as CSV (order ID, customer, email, phone, items, amount, status, date)
- Click row to expand inline: full item list, delivery address

**Backend endpoints used:**
- `GET /admin/orders/` (new endpoint — see Backend Note below)
- `PATCH /admin/orders/{id}/status` (new endpoint)

**Backend Note:** The orders router currently handles `POST /checkout/` (public). Two new admin endpoints are needed:
- `GET /admin/orders/` — list all orders with optional `status` filter
- `PATCH /admin/orders/{id}/status` — update order status

The `Order` model already exists. These are simple read/update operations.

---

### 5. Customers (`/admin/customers`)

**Purpose:** View registered customers and their order history.

**Features:**
- Search by name or email
- Table: name, email, phone, registration date, order count, total spend
- Click row to expand: full order history for that customer (order ID, items, amount, status, date)
- Read-only — no customer editing

**Backend endpoints used:**
- `GET /admin/customers/` (new endpoint)
- `GET /admin/customers/{id}/orders` (new endpoint)

**Backend Note:** Two new read-only admin endpoints needed:
- `GET /admin/customers/` — list all registered customers with order summary stats
- `GET /admin/customers/{id}/orders` — order history for a customer

---

## Data Flow

- **Server components** fetch initial data from FastAPI at render time (Next.js 15 server components)
- **Client components** handle interactive elements: search/filter, status dropdowns, form submissions, CSV export
- **Optimistic updates** for status changes (update UI immediately, revert on API error)
- **ISR not used** for admin pages — always fresh (`cache: 'no-store'`)

---

## Error Handling

- API errors surface as inline toast notifications (top-right, auto-dismiss 4s)
- Delete actions require a confirmation modal before proceeding
- Low-stock threshold: ≤5 units per variant triggers gold warning in products table
- Attempting to delete a collection with products shows a blocking error (not a confirmation)
- Form validation: slug uniqueness checked on blur against the API before submit

---

## New Backend Endpoints Required

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/orders/` | List orders, optional `?status=` filter |
| `PATCH` | `/admin/orders/{id}/status` | Update order status |
| `GET` | `/admin/customers/` | List customers with order count + total spend |
| `GET` | `/admin/customers/{id}/orders` | Order history for a customer |

All other admin endpoints already exist.

---

## Out of Scope

- Analytics / revenue charts (post-MVP)
- Bulk product import via CSV
- Email notifications to customers on status change
- Multi-admin user management (single API key owner)
- Storefront editorial content (banners, homepage copy)
