# BeHAZEL'd Admin CMS Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-featured admin back-office with dashboard, products, collections, orders, and customer management — all inside the existing Next.js 15 frontend, replacing the minimal `/admin/upload` page.

**Architecture:** Four new FastAPI admin endpoints (orders + customers) extend the existing backend. The Next.js frontend gains an `(admin)` route group with a shared top-nav layout, a server-side `admin-api.ts` helper, and five management pages. Browser interactions route through Next.js API proxy routes that hold the server-side `ADMIN_API_KEY`.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Pydantic v2 (backend) · Next.js 15 · TypeScript · Tailwind CSS v4 (frontend) · pytest + httpx (backend tests)

---

## File Map

### Backend — new files
| File | Responsibility |
|------|---------------|
| `backend/app/schemas/admin_orders.py` | Pydantic read/write schemas for order admin endpoints |
| `backend/app/schemas/admin_customers.py` | Pydantic read schemas for customer admin endpoints |
| `backend/app/routers/admin/orders.py` | `GET /admin/orders/` · `PATCH /admin/orders/{id}/status` |
| `backend/app/routers/admin/customers.py` | `GET /admin/customers/` · `GET /admin/customers/{id}/orders` |
| `backend/tests/conftest.py` | Pytest fixtures: in-memory SQLite DB + TestClient |
| `backend/tests/test_admin_orders.py` | Tests for admin order endpoints |
| `backend/tests/test_admin_customers.py` | Tests for admin customer endpoints |

### Backend — modified files
| File | Change |
|------|--------|
| `backend/app/main.py` | Register `admin_orders` and `admin_customers` routers |

### Frontend — new files
| File | Responsibility |
|------|---------------|
| `frontend/lib/admin-api.ts` | Server-side helper: `getAdminToken()` + `adminFetch()` |
| `frontend/components/admin/AdminNav.tsx` | Top nav with active-tab highlighting |
| `frontend/components/admin/StatusBadge.tsx` | Coloured status pill (Pending/Shipped/etc.) |
| `frontend/components/admin/ConfirmModal.tsx` | Reusable delete-confirmation dialog |
| `frontend/components/admin/Toast.tsx` | Toast context provider + `useToast` hook |
| `frontend/app/(admin)/layout.tsx` | Route-group layout: auth gate + `<AdminNav>` |
| `frontend/app/(admin)/admin/dashboard/page.tsx` | Stat cards + recent orders |
| `frontend/app/(admin)/admin/products/page.tsx` | Products list with client-side search |
| `frontend/app/(admin)/admin/products/new/page.tsx` | Create-product shell |
| `frontend/app/(admin)/admin/products/[id]/page.tsx` | Edit-product shell |
| `frontend/components/admin/ProductForm.tsx` | Shared create/edit form (variants + images) |
| `frontend/app/(admin)/admin/collections/page.tsx` | Collections CRUD with inline edit |
| `frontend/app/(admin)/admin/orders/page.tsx` | Orders list: filter, status update, CSV export |
| `frontend/app/(admin)/admin/customers/page.tsx` | Customers list with expandable order history |
| `frontend/app/api/admin/orders/route.ts` | Proxy: `GET /admin/orders/` |
| `frontend/app/api/admin/orders/[id]/status/route.ts` | Proxy: `PATCH /admin/orders/{id}/status` |
| `frontend/app/api/admin/customers/route.ts` | Proxy: `GET /admin/customers/` |
| `frontend/app/api/admin/customers/[id]/orders/route.ts` | Proxy: customer order history |

### Frontend — modified files
| File | Change |
|------|--------|
| `frontend/app/admin/upload/page.tsx` | Replace with redirect to `/admin/products/new` |

---

## Task 1: Backend test fixtures

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Install pytest + httpx**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
pip install pytest httpx pytest-anyio
```

- [ ] **Step 2: Create `backend/tests/__init__.py`**

Empty file — makes `tests/` a package.

```python
```

- [ ] **Step 3: Create `backend/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(client):
    """Return headers with a valid admin JWT."""
    import os
    api_key = os.getenv("ADMIN_API_KEY", "change-me-before-production")
    res = client.post("/admin/auth/token", json={"api_key": api_key})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 4: Verify fixtures load**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
python -m pytest tests/conftest.py --collect-only
```

Expected output: `no tests ran` (fixtures collected, no errors)

- [ ] **Step 5: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add backend/tests/
git commit -m "feat: add pytest fixtures for admin endpoint tests"
```

---

## Task 2: Backend — Admin orders schemas + router

**Files:**
- Create: `backend/app/schemas/admin_orders.py`
- Create: `backend/app/routers/admin/orders.py`
- Create: `backend/tests/test_admin_orders.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_admin_orders.py`:

```python
from decimal import Decimal
from app.models.order import Order, OrderItem


def _seed_order(db, status: str = "pending") -> Order:
    order = Order(
        customer_email="test@example.com",
        customer_name="Test User",
        shipping_address="123 Main St",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
        country="India",
        status=status,
        subtotal=Decimal("4200.00"),
        shipping_total=Decimal("0.00"),
        total=Decimal("4200.00"),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        product_id=1,
        product_name="Ivory Wrap Kurta",
        product_slug="ivory-wrap-kurta",
        color="Ivory",
        size="36",
        unit_price=Decimal("4200.00"),
        quantity=1,
        line_total=Decimal("4200.00"),
    )
    db.add(item)
    db.commit()
    return order


def test_list_orders_returns_all(client, admin_headers, db):
    _seed_order(db, "pending")
    _seed_order(db, "shipped")
    res = client.get("/admin/orders/", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_orders_filter_by_status(client, admin_headers, db):
    _seed_order(db, "pending")
    _seed_order(db, "shipped")
    res = client.get("/admin/orders/?status=pending", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"


def test_update_order_status(client, admin_headers, db):
    order = _seed_order(db, "pending")
    res = client.patch(
        f"/admin/orders/{order.id}/status",
        json={"status": "confirmed"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"


def test_update_order_status_invalid(client, admin_headers, db):
    order = _seed_order(db, "pending")
    res = client.patch(
        f"/admin/orders/{order.id}/status",
        json={"status": "flying"},
        headers=admin_headers,
    )
    assert res.status_code == 422


def test_update_order_status_404(client, admin_headers):
    res = client.patch(
        "/admin/orders/99999/status",
        json={"status": "confirmed"},
        headers=admin_headers,
    )
    assert res.status_code == 404


def test_list_orders_unauthenticated(client):
    res = client.get("/admin/orders/")
    assert res.status_code == 401
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
python -m pytest tests/test_admin_orders.py -v
```

Expected: all 6 tests FAIL with `404 Not Found` (endpoint doesn't exist yet)

- [ ] **Step 3: Create `backend/app/schemas/admin_orders.py`**

```python
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

ORDER_STATUSES = Literal[
    "pending", "confirmed", "shipped", "delivered", "cancelled"
]


class OrderItemAdminRead(BaseModel):
    id: int
    product_name: str
    product_slug: str
    color: str
    size: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderAdminRead(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    shipping_address: str
    city: str
    state: str
    postal_code: str
    country: str
    status: str
    subtotal: Decimal
    shipping_total: Decimal
    total: Decimal
    created_at: datetime
    items: list[OrderItemAdminRead]

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: ORDER_STATUSES
```

- [ ] **Step 4: Create `backend/app/routers/admin/orders.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.order import Order
from app.routers.admin.dependencies import require_admin
from app.schemas.admin_orders import OrderAdminRead, OrderStatusUpdate

router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


@router.get("/", response_model=list[OrderAdminRead], dependencies=[Depends(require_admin)])
def list_orders(
    status: str | None = Query(default=None, description="Filter by status, e.g. pending"),
    db: Session = Depends(get_db),
):
    q = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status:
        q = q.where(Order.status == status)
    return db.scalars(q).all()


@router.patch("/{order_id}/status", response_model=OrderAdminRead, dependencies=[Depends(require_admin)])
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = body.status
    db.commit()
    db.refresh(order)
    return order
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

Add to the imports at line 22:
```python
from app.routers.admin import orders as admin_orders
```

Add after line 65 (after `admin_products` include):
```python
app.include_router(admin_orders.router)     # GET+PATCH /admin/orders/
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
python -m pytest tests/test_admin_orders.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 7: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add backend/app/schemas/admin_orders.py backend/app/routers/admin/orders.py backend/app/main.py backend/tests/test_admin_orders.py
git commit -m "feat: add admin orders list and status-update endpoints"
```

---

## Task 3: Backend — Admin customers schemas + router

**Files:**
- Create: `backend/app/schemas/admin_customers.py`
- Create: `backend/app/routers/admin/customers.py`
- Create: `backend/tests/test_admin_customers.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_admin_customers.py`:

```python
from decimal import Decimal
from app.models.customer import CustomerProfile
from app.models.order import Order, OrderItem
from datetime import date


def _seed_customer(db, email: str = "priya@example.com") -> CustomerProfile:
    c = CustomerProfile(
        full_name="Priya Sharma",
        email=email,
        phone_number="9876543210",
        birth_day=date(1990, 1, 1),
        address="123 Main St",
        city="Mumbai",
        pin_code="400001",
        style_notes="Casual",
        consent_given=True,
    )
    db.add(c)
    db.commit()
    return c


def _seed_order_for_email(db, email: str, total: str = "4200.00") -> Order:
    from decimal import Decimal as D
    order = Order(
        customer_email=email,
        customer_name="Priya Sharma",
        shipping_address="123 Main St",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
        country="India",
        status="delivered",
        subtotal=D(total),
        shipping_total=D("0.00"),
        total=D(total),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        product_id=1,
        product_name="Ivory Wrap Kurta",
        product_slug="ivory-wrap-kurta",
        color="Ivory",
        size="36",
        unit_price=D(total),
        quantity=1,
        line_total=D(total),
    )
    db.add(item)
    db.commit()
    return order


def test_list_customers(client, admin_headers, db):
    _seed_customer(db, "a@example.com")
    _seed_customer(db, "b@example.com")
    res = client.get("/admin/customers/", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_customer_has_order_stats(client, admin_headers, db):
    c = _seed_customer(db)
    _seed_order_for_email(db, c.email, "4200.00")
    _seed_order_for_email(db, c.email, "6800.00")
    res = client.get("/admin/customers/", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data[0]["order_count"] == 2
    assert float(data[0]["total_spend"]) == 11000.00


def test_customer_order_history(client, admin_headers, db):
    c = _seed_customer(db)
    o = _seed_order_for_email(db, c.email)
    res = client.get(f"/admin/customers/{c.id}/orders", headers=admin_headers)
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) == 1
    assert orders[0]["id"] == o.id


def test_customer_order_history_404(client, admin_headers):
    res = client.get("/admin/customers/99999/orders", headers=admin_headers)
    assert res.status_code == 404


def test_list_customers_unauthenticated(client):
    res = client.get("/admin/customers/")
    assert res.status_code == 401
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
python -m pytest tests/test_admin_customers.py -v
```

Expected: all 5 tests FAIL with `404 Not Found`

- [ ] **Step 3: Create `backend/app/schemas/admin_customers.py`**

```python
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.admin_orders import OrderAdminRead


class CustomerAdminRead(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: str
    city: str
    created_at: datetime
    order_count: int
    total_spend: Decimal

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Create `backend/app/routers/admin/customers.py`**

```python
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.customer import CustomerProfile
from app.models.order import Order
from app.routers.admin.dependencies import require_admin
from app.schemas.admin_customers import CustomerAdminRead
from app.schemas.admin_orders import OrderAdminRead

router = APIRouter(prefix="/admin/customers", tags=["admin-customers"])


@router.get("/", response_model=list[CustomerAdminRead], dependencies=[Depends(require_admin)])
def list_customers(db: Session = Depends(get_db)):
    customers = db.scalars(
        select(CustomerProfile).order_by(CustomerProfile.created_at.desc())
    ).all()

    result = []
    for c in customers:
        order_agg = db.execute(
            select(
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total), 0).label("total_spend"),
            ).where(Order.customer_email == c.email)
        ).one()
        result.append(
            CustomerAdminRead(
                id=c.id,
                full_name=c.full_name,
                email=c.email,
                phone_number=c.phone_number,
                city=c.city,
                created_at=c.created_at,
                order_count=order_agg.order_count,
                total_spend=Decimal(str(order_agg.total_spend)),
            )
        )
    return result


@router.get("/{customer_id}/orders", response_model=list[OrderAdminRead], dependencies=[Depends(require_admin)])
def get_customer_orders(customer_id: int, db: Session = Depends(get_db)):
    customer = db.scalar(select(CustomerProfile).where(CustomerProfile.id == customer_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.customer_email == customer.email)
        .order_by(Order.created_at.desc())
    ).all()
    return orders
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

Add to the imports (after the admin_orders import added in Task 2):
```python
from app.routers.admin import customers as admin_customers
```

Add the router include after the admin_orders line:
```python
app.include_router(admin_customers.router)  # GET /admin/customers/ + /{id}/orders
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
python -m pytest tests/test_admin_customers.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 7: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all 11 tests PASS

- [ ] **Step 8: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add backend/app/schemas/admin_customers.py backend/app/routers/admin/customers.py backend/app/main.py backend/tests/test_admin_customers.py
git commit -m "feat: add admin customers list and order-history endpoints"
```

---

## Task 4: Frontend — `lib/admin-api.ts` server-side helper

**Files:**
- Create: `frontend/lib/admin-api.ts`

- [ ] **Step 1: Create `frontend/lib/admin-api.ts`**

```typescript
/**
 * Server-side helper for calling FastAPI admin endpoints.
 * Only use from server components or Next.js API route handlers —
 * ADMIN_API_KEY must never reach the browser.
 */

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const ADMIN_KEY = process.env.ADMIN_API_KEY ?? "change-me-before-production";

export async function getAdminToken(): Promise<string> {
  const res = await fetch(`${API}/admin/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: ADMIN_KEY }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("FastAPI admin auth failed");
  const data = await res.json();
  return data.access_token as string;
}

export async function adminFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAdminToken();
  return fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers as Record<string, string> | undefined),
    },
    cache: "no-store",
  });
}
```

- [ ] **Step 2: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors in `lib/admin-api.ts`

- [ ] **Step 3: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add frontend/lib/admin-api.ts
git commit -m "feat: add server-side admin API helper"
```

---

## Task 5: Frontend — Shared UI components

**Files:**
- Create: `frontend/components/admin/StatusBadge.tsx`
- Create: `frontend/components/admin/ConfirmModal.tsx`
- Create: `frontend/components/admin/Toast.tsx`

- [ ] **Step 1: Create `frontend/components/admin/StatusBadge.tsx`**

```typescript
type Status =
  | "pending"
  | "pending_payment"
  | "confirmed"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "active"
  | "inactive";

const STYLES: Record<Status, string> = {
  pending:         "bg-[#FFF8EC] text-[#C09330] border border-[#F0D88A]",
  pending_payment: "bg-[#FFF8EC] text-[#C09330] border border-[#F0D88A]",
  confirmed:       "bg-[#EEF4FF] text-[#3366CC] border border-[#B3CCFF]",
  shipped:         "bg-[#EDFBF2] text-[#2D8A4E] border border-[#9FD9B4]",
  delivered:       "bg-[#EDFBF2] text-[#2D8A4E] border border-[#9FD9B4]",
  cancelled:       "bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA]",
  active:          "bg-[#EDFBF2] text-[#2D8A4E] border border-[#9FD9B4]",
  inactive:        "bg-[#F8F5F0] text-[#9C8B7A] border border-[#E2D9CC]",
};

const LABELS: Record<Status, string> = {
  pending:         "Pending",
  pending_payment: "Pending Payment",
  confirmed:       "Confirmed",
  shipped:         "Shipped",
  delivered:       "Delivered",
  cancelled:       "Cancelled",
  active:          "Active",
  inactive:        "Inactive",
};

export function StatusBadge({ status }: { status: string }) {
  const key = status as Status;
  const cls = STYLES[key] ?? "bg-[#F8F5F0] text-[#9C8B7A] border border-[#E2D9CC]";
  const label = LABELS[key] ?? status;
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded-sm font-medium ${cls}`}>
      {label}
    </span>
  );
}
```

- [ ] **Step 2: Create `frontend/components/admin/ConfirmModal.tsx`**

```typescript
"use client";

interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm mx-4">
        <h3 className="text-[#3D2B1F] font-semibold text-base mb-2">{title}</h3>
        <p className="text-[#9C8B7A] text-sm mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-[#3D2B1F] border border-[#E2D9CC] rounded-md hover:bg-[#F8F5F0] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/admin/Toast.tsx`**

```typescript
"use client";

import { createContext, useCallback, useContext, useState } from "react";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const TYPE_STYLES: Record<ToastType, string> = {
    success: "bg-[#EDFBF2] text-[#2D8A4E] border-[#9FD9B4]",
    error:   "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]",
    info:    "bg-white text-[#3D2B1F] border-[#E2D9CC]",
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`px-4 py-3 rounded-md border text-sm shadow-md animate-in fade-in slide-in-from-right-4 ${TYPE_STYLES[t.type]}`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
```

- [ ] **Step 4: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors in the three new component files

- [ ] **Step 5: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add frontend/components/admin/StatusBadge.tsx frontend/components/admin/ConfirmModal.tsx frontend/components/admin/Toast.tsx
git commit -m "feat: add shared admin UI components (StatusBadge, ConfirmModal, Toast)"
```

---

## Task 6: Frontend — Admin route group layout + nav

**Files:**
- Create: `frontend/components/admin/AdminNav.tsx`
- Create: `frontend/app/(admin)/layout.tsx`
- Modify: `frontend/app/admin/upload/page.tsx`

- [ ] **Step 1: Create `frontend/components/admin/AdminNav.tsx`**

```typescript
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const NAV_LINKS = [
  { label: "Dashboard",   href: "/admin/dashboard" },
  { label: "Products",    href: "/admin/products" },
  { label: "Collections", href: "/admin/collections" },
  { label: "Orders",      href: "/admin/orders" },
  { label: "Customers",   href: "/admin/customers" },
];

export function AdminNav() {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/admin/logout", { method: "POST" });
    router.push("/admin/login");
  }

  return (
    <nav className="bg-white border-b border-[#E2D9CC] px-6 py-0 flex items-center gap-0 sticky top-0 z-40">
      <span className="text-[#3D2B1F] font-semibold text-sm mr-8 py-4 shrink-0">
        BeHAZEL&apos;d
      </span>
      <div className="flex items-center gap-1 flex-1">
        {NAV_LINKS.map(({ label, href }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`px-4 py-4 text-sm transition-colors border-b-2 ${
                active
                  ? "text-[#C09330] border-[#C09330] font-medium"
                  : "text-[#9C8B7A] border-transparent hover:text-[#3D2B1F]"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>
      <button
        onClick={handleLogout}
        className="text-xs text-[#9C8B7A] hover:text-[#3D2B1F] transition-colors py-4"
      >
        Sign out
      </button>
    </nav>
  );
}
```

- [ ] **Step 2: Create `frontend/app/(admin)/layout.tsx`**

```typescript
import { redirect } from "next/navigation";
import { getSessionToken, verifySessionToken } from "@/lib/admin-session";
import { AdminNav } from "@/components/admin/AdminNav";
import { ToastProvider } from "@/components/admin/Toast";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const token = await getSessionToken();
  const valid = token ? await verifySessionToken(token) : false;
  if (!valid) redirect("/admin/login");

  return (
    <ToastProvider>
      <div className="min-h-screen bg-[#F8F5F0]">
        <AdminNav />
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </div>
    </ToastProvider>
  );
}
```

- [ ] **Step 3: Modify `frontend/app/admin/upload/page.tsx`** to redirect to the new product creation page

Replace the entire file content with:

```typescript
import { redirect } from "next/navigation";

export default function AdminUploadPage() {
  redirect("/admin/products/new");
}
```

- [ ] **Step 4: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors

- [ ] **Step 5: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add frontend/components/admin/AdminNav.tsx "frontend/app/(admin)/layout.tsx" frontend/app/admin/upload/page.tsx
git commit -m "feat: add admin route group layout with top nav and auth gate"
```

---

## Task 7: Frontend — Dashboard page

**Files:**
- Create: `frontend/app/(admin)/admin/dashboard/page.tsx`

- [ ] **Step 1: Create `frontend/app/(admin)/admin/dashboard/page.tsx`**

```typescript
import type { Metadata } from "next";
import { adminFetch } from "@/lib/admin-api";
import { StatusBadge } from "@/components/admin/StatusBadge";

export const metadata: Metadata = {
  title: "Dashboard | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

async function getDashboardData() {
  const [collectionsRes, productsRes, ordersRes, customersRes] =
    await Promise.all([
      fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}/collections/`,
        { cache: "no-store" }
      ),
      fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}/products/`,
        { cache: "no-store" }
      ),
      adminFetch("/admin/orders/"),
      adminFetch("/admin/customers/"),
    ]);

  const [collections, products, orders, customers] = await Promise.all([
    collectionsRes.json(),
    productsRes.json(),
    ordersRes.json(),
    customersRes.json(),
  ]);

  return { collections, products, orders, customers };
}

export default async function DashboardPage() {
  const { collections, products, orders, customers } =
    await getDashboardData();

  const pendingOrders = (orders as { status: string }[]).filter(
    (o) => o.status === "pending" || o.status === "pending_payment"
  );
  const recentOrders = (
    orders as {
      id: number;
      customer_name: string;
      total: string;
      status: string;
      created_at: string;
    }[]
  ).slice(0, 10);

  const stats = [
    { label: "Products",   value: (products as unknown[]).length,    highlight: false },
    { label: "Collections", value: (collections as unknown[]).length, highlight: false },
    { label: "Pending Orders", value: pendingOrders.length,          highlight: true  },
    { label: "Customers",  value: (customers as unknown[]).length,   highlight: false },
  ];

  return (
    <div>
      <h1 className="text-xl font-semibold text-[#3D2B1F] mb-6">Dashboard</h1>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, highlight }) => (
          <div
            key={label}
            className={`bg-white rounded-lg border p-5 ${
              highlight ? "border-[#F0D88A] bg-[#FFF8EC]" : "border-[#E2D9CC]"
            }`}
          >
            <div
              className={`text-2xl font-bold mb-1 ${
                highlight ? "text-[#C09330]" : "text-[#3D2B1F]"
              }`}
            >
              {value}
            </div>
            <div className="text-xs text-[#9C8B7A]">{label}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-[#E2D9CC] overflow-hidden">
        <div className="px-5 py-3 border-b border-[#E2D9CC] bg-[#FDFAF7]">
          <h2 className="text-sm font-semibold text-[#3D2B1F]">Recent Orders</h2>
        </div>
        <div className="divide-y divide-[#F0EAE1]">
          {recentOrders.length === 0 && (
            <p className="px-5 py-4 text-sm text-[#9C8B7A]">No orders yet.</p>
          )}
          {recentOrders.map((order) => (
            <div
              key={order.id}
              className="px-5 py-3 grid grid-cols-4 items-center text-sm"
            >
              <span className="text-[#9C8B7A] text-xs">#{order.id}</span>
              <span className="text-[#3D2B1F]">{order.customer_name}</span>
              <span className="text-[#3D2B1F]">
                ₹{parseFloat(order.total).toLocaleString("en-IN")}
              </span>
              <StatusBadge status={order.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Start the dev server and verify**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npm run dev
```

Navigate to `http://localhost:3000/admin/dashboard` (after logging in at `/admin/login`). Verify: stat cards render, recent orders table appears.

- [ ] **Step 3: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add "frontend/app/(admin)/admin/dashboard/page.tsx"
git commit -m "feat: add admin dashboard with stat cards and recent orders"
```

---

## Task 8: Frontend — Products list page + Next.js API proxy routes

**Files:**
- Create: `frontend/app/(admin)/admin/products/page.tsx`
- Create: `frontend/app/api/admin/collections/route.ts` (needed by product form for collection dropdown)

- [ ] **Step 1: Create `frontend/app/api/admin/collections/route.ts`**

This proxies the collection list for client components that need it (product form dropdown).

```typescript
import { NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function GET() {
  const res = await adminFetch("/admin/collections/");
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 2: Create `frontend/app/(admin)/admin/products/page.tsx`**

```typescript
import type { Metadata } from "next";
import Link from "next/link";
import { adminFetch } from "@/lib/admin-api";
import { ProductsTable } from "@/components/admin/ProductsTable";

export const metadata: Metadata = {
  title: "Products | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

export default async function ProductsPage() {
  const res = await adminFetch("/admin/products/");
  const products = await res.json();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-[#3D2B1F]">Products</h1>
        <Link
          href="/admin/products/new"
          className="bg-[#C09330] text-white text-sm px-4 py-2 rounded-md hover:bg-[#A07A28] transition-colors"
        >
          + Add Product
        </Link>
      </div>
      <ProductsTable initialProducts={products} />
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/admin/ProductsTable.tsx`**

This is a client component so search/delete interactions work without page reload.

```typescript
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ConfirmModal } from "@/components/admin/ConfirmModal";
import { useToast } from "@/components/admin/Toast";

interface Variant {
  stock_count: number;
  is_available: boolean;
}

interface Product {
  id: number;
  name: string;
  slug: string;
  base_price: string;
  is_active: boolean;
  collection_id: number | null;
  variants: Variant[];
}

export function ProductsTable({ initialProducts }: { initialProducts: Product[] }) {
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);
  const router = useRouter();
  const { toast } = useToast();

  const filtered = initialProducts.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.slug.includes(search.toLowerCase())
  );

  async function handleDelete(product: Product) {
    const res = await fetch(`/api/admin/products/${product.id}`, {
      method: "DELETE",
    });
    if (res.ok) {
      toast(`"${product.name}" deleted`, "success");
      router.refresh();
    } else {
      toast("Failed to delete product", "error");
    }
    setDeleteTarget(null);
  }

  return (
    <>
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by name or slug…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 px-3 py-2 text-sm border border-[#E2D9CC] rounded-md bg-white text-[#3D2B1F] placeholder-[#9C8B7A] focus:outline-none focus:ring-1 focus:ring-[#C09330]"
        />
      </div>

      <div className="bg-white rounded-lg border border-[#E2D9CC] overflow-hidden">
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_100px] bg-[#FDFAF7] border-b border-[#E2D9CC] px-4 py-2 text-xs text-[#9C8B7A] uppercase tracking-wide">
          <span>Product</span>
          <span>Price</span>
          <span>Stock</span>
          <span>Status</span>
          <span>Actions</span>
        </div>

        {filtered.length === 0 && (
          <p className="px-4 py-6 text-sm text-[#9C8B7A]">No products found.</p>
        )}

        {filtered.map((product) => {
          const totalStock = product.variants.reduce(
            (sum, v) => sum + v.stock_count,
            0
          );
          const lowStock = totalStock <= 5;
          return (
            <div
              key={product.id}
              className="grid grid-cols-[2fr_1fr_1fr_1fr_100px] px-4 py-3 border-b border-[#F0EAE1] last:border-0 items-center text-sm"
            >
              <span className="text-[#3D2B1F] font-medium">{product.name}</span>
              <span className="text-[#3D2B1F]">
                ₹{parseFloat(product.base_price).toLocaleString("en-IN")}
              </span>
              <span className={lowStock ? "text-[#C09330] font-medium" : "text-[#3D2B1F]"}>
                {totalStock} {lowStock && "⚠ Low"}
              </span>
              <span className={`text-xs ${product.is_active ? "text-[#2D8A4E]" : "text-[#9C8B7A]"}`}>
                {product.is_active ? "Active" : "Inactive"}
              </span>
              <div className="flex gap-3">
                <Link
                  href={`/admin/products/${product.id}`}
                  className="text-[#C09330] hover:underline text-xs"
                >
                  Edit
                </Link>
                <button
                  onClick={() => setDeleteTarget(product)}
                  className="text-red-400 hover:text-red-600 text-xs"
                >
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <ConfirmModal
        open={deleteTarget !== null}
        title={`Delete "${deleteTarget?.name}"?`}
        message="This permanently removes the product, all its variants, and images. This cannot be undone."
        onConfirm={() => deleteTarget && handleDelete(deleteTarget)}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
```

- [ ] **Step 4: Add the `DELETE /api/admin/products/[id]` proxy route**

Create `frontend/app/api/admin/products/[id]/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const res = await adminFetch(`/admin/products/${id}`, { method: "DELETE" });
  return NextResponse.json({}, { status: res.status });
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.json();
  const res = await adminFetch(`/admin/products/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 5: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add "frontend/app/(admin)/admin/products/page.tsx" frontend/components/admin/ProductsTable.tsx "frontend/app/api/admin/products/[id]/route.ts" frontend/app/api/admin/collections/route.ts
git commit -m "feat: add admin products list page with search and delete"
```

---

## Task 9: Frontend — Product create/edit pages

**Files:**
- Create: `frontend/components/admin/ProductForm.tsx`
- Create: `frontend/app/(admin)/admin/products/new/page.tsx`
- Create: `frontend/app/(admin)/admin/products/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/components/admin/ProductForm.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/admin/Toast";

interface Collection { id: number; name: string; slug: string }
interface Variant { id?: number; sku: string; color: string; size: string; stock_count: number; price_adjustment: string }
interface ProductImage { id: number; url: string; alt_text: string; display_order: number; is_primary: boolean }

interface ProductFormProps {
  mode: "create" | "edit";
  productId?: number;
  collections: Collection[];
  initialData?: {
    name: string;
    slug: string;
    description: string;
    base_price: string;
    collection_id: number | null;
    is_active: boolean;
    variants: Variant[];
    images: ProductImage[];
  };
}

const SIZES = ["32", "34", "36", "38", "40", "42", "44", "46", "48"];

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function ProductForm({ mode, productId, collections, initialData }: ProductFormProps) {
  const router = useRouter();
  const { toast } = useToast();

  const [name, setName]           = useState(initialData?.name ?? "");
  const [slug, setSlug]           = useState(initialData?.slug ?? "");
  const [description, setDescription] = useState(initialData?.description ?? "");
  const [basePrice, setBasePrice] = useState(initialData?.base_price ?? "");
  const [collectionId, setCollectionId] = useState<number | null>(initialData?.collection_id ?? null);
  const [isActive, setIsActive]   = useState(initialData?.is_active ?? true);
  const [variants, setVariants]   = useState<Variant[]>(
    initialData?.variants ?? []
  );
  const [saving, setSaving]       = useState(false);
  const [deleting, setDeleting]   = useState(false);

  function handleNameChange(val: string) {
    setName(val);
    if (mode === "create") setSlug(slugify(val));
  }

  function addVariant() {
    setVariants((prev) => [
      ...prev,
      { sku: "", color: "", size: SIZES[0], stock_count: 20, price_adjustment: "0.00" },
    ]);
  }

  function updateVariant(index: number, field: keyof Variant, value: string | number) {
    setVariants((prev) =>
      prev.map((v, i) => (i === index ? { ...v, [field]: value } : v))
    );
  }

  function removeVariant(index: number) {
    setVariants((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!collectionId) { toast("Select a collection", "error"); return; }
    setSaving(true);

    try {
      const payload = {
        name,
        slug,
        description,
        base_price: parseFloat(basePrice).toFixed(2),
        collection_id: collectionId,
        is_active: isActive,
      };

      let res: Response;
      if (mode === "create") {
        res = await fetch("/api/admin/products", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...payload, sizes: variants.map((v) => v.size), colors: variants.map((v) => v.color) }),
        });
      } else {
        res = await fetch(`/api/admin/products/${productId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) {
        const err = await res.json();
        toast(err.error ?? "Save failed", "error");
        return;
      }

      toast(mode === "create" ? "Product created" : "Product updated", "success");
      router.push("/admin/products");
      router.refresh();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!productId) return;
    setDeleting(true);
    const res = await fetch(`/api/admin/products/${productId}`, { method: "DELETE" });
    if (res.ok) {
      toast("Product deleted", "success");
      router.push("/admin/products");
    } else {
      toast("Delete failed", "error");
    }
    setDeleting(false);
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
      {/* Core fields */}
      <div className="bg-white rounded-lg border border-[#E2D9CC] p-6 space-y-4">
        <h2 className="text-sm font-semibold text-[#3D2B1F]">Product Details</h2>

        <div>
          <label className="block text-xs text-[#9C8B7A] mb-1">Name</label>
          <input
            required
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded-md focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
          />
        </div>

        <div>
          <label className="block text-xs text-[#9C8B7A] mb-1">Slug</label>
          <input
            required
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            pattern="^[a-z0-9-]+$"
            title="Lowercase letters, numbers, and hyphens only"
            className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded-md focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F] font-mono"
          />
        </div>

        <div>
          <label className="block text-xs text-[#9C8B7A] mb-1">Description</label>
          <textarea
            required
            minLength={10}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded-md focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F] resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-[#9C8B7A] mb-1">Base Price (₹)</label>
            <input
              required
              type="number"
              min="1"
              step="0.01"
              value={basePrice}
              onChange={(e) => setBasePrice(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded-md focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
            />
          </div>

          <div>
            <label className="block text-xs text-[#9C8B7A] mb-1">Collection</label>
            <select
              value={collectionId ?? ""}
              onChange={(e) => setCollectionId(Number(e.target.value) || null)}
              className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded-md focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F] bg-white"
            >
              <option value="">Select collection…</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_active"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="accent-[#C09330]"
          />
          <label htmlFor="is_active" className="text-sm text-[#3D2B1F]">Active (visible on storefront)</label>
        </div>
      </div>

      {/* Variants */}
      <div className="bg-white rounded-lg border border-[#E2D9CC] p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[#3D2B1F]">Variants</h2>
          <button
            type="button"
            onClick={addVariant}
            className="text-xs text-[#C09330] hover:underline"
          >
            + Add variant
          </button>
        </div>

        {variants.length === 0 && (
          <p className="text-sm text-[#9C8B7A]">No variants yet. Add at least one.</p>
        )}

        <div className="space-y-2">
          {variants.map((v, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_80px_80px_32px] gap-2 items-center">
              <input
                placeholder="Color"
                value={v.color}
                onChange={(e) => updateVariant(i, "color", e.target.value)}
                className="px-2 py-1.5 text-xs border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
              />
              <select
                value={v.size}
                onChange={(e) => updateVariant(i, "size", e.target.value)}
                className="px-2 py-1.5 text-xs border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F] bg-white"
              >
                {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <input
                type="number"
                placeholder="Stock"
                min="0"
                value={v.stock_count}
                onChange={(e) => updateVariant(i, "stock_count", parseInt(e.target.value) || 0)}
                className="px-2 py-1.5 text-xs border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
              />
              <input
                placeholder="SKU"
                value={v.sku}
                onChange={(e) => updateVariant(i, "sku", e.target.value.toUpperCase())}
                className="px-2 py-1.5 text-xs border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F] font-mono"
              />
              <button
                type="button"
                onClick={() => removeVariant(i)}
                className="text-red-400 hover:text-red-600 text-xs"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={saving}
          className="bg-[#C09330] text-white text-sm px-6 py-2 rounded-md hover:bg-[#A07A28] disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving…" : mode === "create" ? "Create Product" : "Save Changes"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/admin/products")}
          className="text-sm text-[#9C8B7A] hover:text-[#3D2B1F] transition-colors"
        >
          Cancel
        </button>
        {mode === "edit" && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="ml-auto text-sm text-red-500 hover:text-red-700 disabled:opacity-50 transition-colors"
          >
            {deleting ? "Deleting…" : "Delete product"}
          </button>
        )}
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Create `frontend/app/(admin)/admin/products/new/page.tsx`**

```typescript
import type { Metadata } from "next";
import { adminFetch } from "@/lib/admin-api";
import { ProductForm } from "@/components/admin/ProductForm";

export const metadata: Metadata = {
  title: "Add Product | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

export default async function NewProductPage() {
  const res = await adminFetch("/admin/collections/");
  const collections = await res.json();

  return (
    <div>
      <h1 className="text-xl font-semibold text-[#3D2B1F] mb-6">Add Product</h1>
      <ProductForm mode="create" collections={collections} />
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/app/(admin)/admin/products/[id]/page.tsx`**

```typescript
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { adminFetch } from "@/lib/admin-api";
import { ProductForm } from "@/components/admin/ProductForm";

export const metadata: Metadata = {
  title: "Edit Product | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

export default async function EditProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [productRes, collectionsRes] = await Promise.all([
    adminFetch(`/admin/products/${id}`),
    adminFetch("/admin/collections/"),
  ]);

  if (!productRes.ok) notFound();

  const product = await productRes.json();
  const collections = await collectionsRes.json();

  return (
    <div>
      <h1 className="text-xl font-semibold text-[#3D2B1F] mb-6">
        Edit — {product.name}
      </h1>
      <ProductForm
        mode="edit"
        productId={product.id}
        collections={collections}
        initialData={{
          name:          product.name,
          slug:          product.slug,
          description:   product.description,
          base_price:    product.base_price,
          collection_id: product.collection_id,
          is_active:     product.is_active,
          variants:      product.variants ?? [],
          images:        product.images ?? [],
        }}
      />
    </div>
  );
}
```

- [ ] **Step 4: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add frontend/components/admin/ProductForm.tsx "frontend/app/(admin)/admin/products/new/page.tsx" "frontend/app/(admin)/admin/products/[id]/page.tsx"
git commit -m "feat: add product create/edit pages with variant management"
```

---

## Task 10: Frontend — Collections page

**Files:**
- Create: `frontend/app/(admin)/admin/collections/page.tsx`

- [ ] **Step 1: Create `frontend/app/(admin)/admin/collections/page.tsx`**

```typescript
import type { Metadata } from "next";
import { adminFetch } from "@/lib/admin-api";
import { CollectionsManager } from "@/components/admin/CollectionsManager";

export const metadata: Metadata = {
  title: "Collections | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

export default async function CollectionsPage() {
  const res = await adminFetch("/admin/collections/");
  const collections = await res.json();

  return (
    <div>
      <h1 className="text-xl font-semibold text-[#3D2B1F] mb-6">Collections</h1>
      <CollectionsManager initialCollections={collections} />
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/admin/CollectionsManager.tsx`**

```typescript
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { ConfirmModal } from "@/components/admin/ConfirmModal";
import { useToast } from "@/components/admin/Toast";

interface Collection {
  id: number;
  name: string;
  slug: string;
  description: string;
  display_order: number;
  is_active: boolean;
}

export function CollectionsManager({ initialCollections }: { initialCollections: Collection[] }) {
  const [collections, setCollections] = useState(
    [...initialCollections].sort((a, b) => a.display_order - b.display_order)
  );
  const [editId, setEditId]           = useState<number | null>(null);
  const [editName, setEditName]       = useState("");
  const [editDesc, setEditDesc]       = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Collection | null>(null);
  const [creating, setCreating]       = useState(false);
  const [newName, setNewName]         = useState("");
  const [newSlug, setNewSlug]         = useState("");
  const [newDesc, setNewDesc]         = useState("");
  const router = useRouter();
  const { toast } = useToast();

  async function patchCollection(id: number, body: Record<string, unknown>) {
    const res = await fetch(`/api/admin/collections/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) { toast("Update failed", "error"); return false; }
    return true;
  }

  async function saveEdit(id: number) {
    const ok = await patchCollection(id, { name: editName, description: editDesc });
    if (ok) {
      setCollections((prev) =>
        prev.map((c) => (c.id === id ? { ...c, name: editName, description: editDesc } : c))
      );
      setEditId(null);
      toast("Collection updated", "success");
    }
  }

  async function toggleActive(c: Collection) {
    const ok = await patchCollection(c.id, { is_active: !c.is_active });
    if (ok) {
      setCollections((prev) =>
        prev.map((col) => (col.id === c.id ? { ...col, is_active: !col.is_active } : col))
      );
    }
  }

  async function moveOrder(index: number, direction: -1 | 1) {
    const next = [...collections];
    const swap = index + direction;
    if (swap < 0 || swap >= next.length) return;
    [next[index], next[swap]] = [next[swap], next[index]];
    const updated = next.map((c, i) => ({ ...c, display_order: i }));
    setCollections(updated);
    await Promise.all(
      updated.map((c) => patchCollection(c.id, { display_order: c.display_order }))
    );
  }

  async function handleDelete(c: Collection) {
    const res = await fetch(`/api/admin/collections/${c.id}`, { method: "DELETE" });
    if (res.ok) {
      setCollections((prev) => prev.filter((col) => col.id !== c.id));
      toast(`"${c.name}" deleted`, "success");
    } else {
      const err = await res.json();
      toast(err.error ?? "Cannot delete collection", "error");
    }
    setDeleteTarget(null);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/admin/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName, slug: newSlug, description: newDesc }),
    });
    if (res.ok) {
      toast("Collection created", "success");
      setCreating(false);
      setNewName(""); setNewSlug(""); setNewDesc("");
      router.refresh();
    } else {
      const err = await res.json();
      toast(err.error ?? "Create failed", "error");
    }
  }

  return (
    <>
      <div className="bg-white rounded-lg border border-[#E2D9CC] overflow-hidden mb-6">
        {collections.map((c, i) => (
          <div key={c.id} className="border-b border-[#F0EAE1] last:border-0 px-5 py-4">
            {editId === c.id ? (
              <div className="flex items-center gap-3">
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
                />
                <input
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="Tagline"
                  className="flex-1 px-3 py-1.5 text-sm border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
                />
                <button onClick={() => saveEdit(c.id)} className="text-xs text-[#C09330] font-medium hover:underline">Save</button>
                <button onClick={() => setEditId(null)} className="text-xs text-[#9C8B7A] hover:underline">Cancel</button>
              </div>
            ) : (
              <div className="flex items-center gap-4">
                <div className="flex gap-1">
                  <button onClick={() => moveOrder(i, -1)} disabled={i === 0} className="text-[#9C8B7A] hover:text-[#3D2B1F] disabled:opacity-30 text-xs px-1">↑</button>
                  <button onClick={() => moveOrder(i, 1)} disabled={i === collections.length - 1} className="text-[#9C8B7A] hover:text-[#3D2B1F] disabled:opacity-30 text-xs px-1">↓</button>
                </div>
                <div className="flex-1">
                  <span className="text-sm font-medium text-[#3D2B1F]">{c.name}</span>
                  {c.description && (
                    <span className="text-xs text-[#9C8B7A] ml-3">{c.description}</span>
                  )}
                </div>
                <StatusBadge status={c.is_active ? "active" : "inactive"} />
                <button onClick={() => { setEditId(c.id); setEditName(c.name); setEditDesc(c.description); }} className="text-xs text-[#C09330] hover:underline">Edit</button>
                <button onClick={() => toggleActive(c)} className="text-xs text-[#9C8B7A] hover:text-[#3D2B1F]">{c.is_active ? "Deactivate" : "Activate"}</button>
                <button onClick={() => setDeleteTarget(c)} className="text-xs text-red-400 hover:text-red-600">Delete</button>
              </div>
            )}
          </div>
        ))}
      </div>

      {creating ? (
        <form onSubmit={handleCreate} className="bg-white rounded-lg border border-[#E2D9CC] p-5 space-y-3">
          <h3 className="text-sm font-semibold text-[#3D2B1F]">New Collection</h3>
          <input required value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Name" className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]" />
          <input required value={newSlug} onChange={(e) => setNewSlug(e.target.value)} placeholder="slug (lowercase-hyphen)" pattern="^[a-z0-9-]+$" className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F] font-mono" />
          <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Tagline (optional)" className="w-full px-3 py-2 text-sm border border-[#E2D9CC] rounded focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]" />
          <div className="flex gap-3">
            <button type="submit" className="bg-[#C09330] text-white text-sm px-4 py-2 rounded-md hover:bg-[#A07A28]">Create</button>
            <button type="button" onClick={() => setCreating(false)} className="text-sm text-[#9C8B7A] hover:text-[#3D2B1F]">Cancel</button>
          </div>
        </form>
      ) : (
        <button onClick={() => setCreating(true)} className="text-sm text-[#C09330] hover:underline">+ New collection</button>
      )}

      <ConfirmModal
        open={deleteTarget !== null}
        title={`Delete "${deleteTarget?.name}"?`}
        message="This will fail if the collection has products. Remove or reassign products first."
        confirmLabel="Delete collection"
        onConfirm={() => deleteTarget && handleDelete(deleteTarget)}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
```

- [ ] **Step 3: Add `/api/admin/collections/[id]` proxy route**

Create `frontend/app/api/admin/collections/[id]/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.json();
  const res = await adminFetch(`/admin/collections/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const res = await adminFetch(`/admin/collections/${id}`, { method: "DELETE" });
  if (res.status === 204) return NextResponse.json({}, { status: 204 });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 4: Add `POST /api/admin/collections` proxy**

Add POST handler to `frontend/app/api/admin/collections/route.ts` (file created in Task 8). Replace the file content:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function GET() {
  const res = await adminFetch("/admin/collections/");
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await adminFetch("/admin/collections/", {
    method: "POST",
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 5: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add "frontend/app/(admin)/admin/collections/page.tsx" frontend/components/admin/CollectionsManager.tsx "frontend/app/api/admin/collections/[id]/route.ts" frontend/app/api/admin/collections/route.ts
git commit -m "feat: add collections management page with inline edit and reorder"
```

---

## Task 11: Frontend — Orders page + API proxy routes

**Files:**
- Create: `frontend/app/(admin)/admin/orders/page.tsx`
- Create: `frontend/components/admin/OrdersManager.tsx`
- Create: `frontend/app/api/admin/orders/route.ts`
- Create: `frontend/app/api/admin/orders/[id]/status/route.ts`

- [ ] **Step 1: Create `frontend/app/api/admin/orders/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function GET(req: NextRequest) {
  const status = req.nextUrl.searchParams.get("status");
  const path = status ? `/admin/orders/?status=${status}` : "/admin/orders/";
  const res = await adminFetch(path);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 2: Create `frontend/app/api/admin/orders/[id]/status/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.json();
  const res = await adminFetch(`/admin/orders/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 3: Create `frontend/app/(admin)/admin/orders/page.tsx`**

```typescript
import type { Metadata } from "next";
import { adminFetch } from "@/lib/admin-api";
import { OrdersManager } from "@/components/admin/OrdersManager";

export const metadata: Metadata = {
  title: "Orders | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

export default async function OrdersPage() {
  const res = await adminFetch("/admin/orders/");
  const orders = await res.json();

  return (
    <div>
      <h1 className="text-xl font-semibold text-[#3D2B1F] mb-6">Orders</h1>
      <OrdersManager initialOrders={orders} />
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/components/admin/OrdersManager.tsx`**

```typescript
"use client";

import React, { useState } from "react";
import { StatusBadge } from "@/components/admin/StatusBadge";
import { useToast } from "@/components/admin/Toast";

type OrderStatus = "pending" | "pending_payment" | "confirmed" | "shipped" | "delivered" | "cancelled";

interface OrderItem {
  id: number;
  product_name: string;
  color: string;
  size: string;
  quantity: number;
  unit_price: string;
  line_total: string;
}

interface Order {
  id: number;
  customer_name: string;
  customer_email: string;
  shipping_address: string;
  city: string;
  state: string;
  postal_code: string;
  total: string;
  status: OrderStatus;
  created_at: string;
  items: OrderItem[];
}

const STATUS_TABS: { label: string; value: string | null }[] = [
  { label: "All",       value: null },
  { label: "Pending",   value: "pending" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Shipped",   value: "shipped" },
  { label: "Delivered", value: "delivered" },
  { label: "Cancelled", value: "cancelled" },
];

const NEXT_STATUS: Record<string, OrderStatus[]> = {
  pending:         ["confirmed", "cancelled"],
  pending_payment: ["confirmed", "cancelled"],
  confirmed:       ["shipped",   "cancelled"],
  shipped:         ["delivered", "cancelled"],
  delivered:       [],
  cancelled:       [],
};

function exportCsv(orders: Order[]) {
  const headers = ["Order ID","Customer","Email","City","Items","Total","Status","Date"];
  const rows = orders.map((o) => [
    o.id,
    o.customer_name,
    o.customer_email,
    o.city,
    o.items.map((i) => `${i.product_name} (${i.color}/${i.size} ×${i.quantity})`).join("; "),
    parseFloat(o.total).toFixed(2),
    o.status,
    new Date(o.created_at).toLocaleDateString("en-IN"),
  ]);
  const csv = [headers, ...rows].map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "behazeld-orders.csv"; a.click();
  URL.revokeObjectURL(url);
}

export function OrdersManager({ initialOrders }: { initialOrders: Order[] }) {
  const [orders, setOrders]     = useState<Order[]>(initialOrders);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [search, setSearch]     = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { toast } = useToast();

  const filtered = orders
    .filter((o) => activeTab === null || o.status === activeTab || (activeTab === "pending" && o.status === "pending_payment"))
    .filter((o) =>
      search === "" ||
      o.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      String(o.id).includes(search)
    );

  const countForTab = (val: string | null) =>
    val === null
      ? orders.length
      : orders.filter((o) => o.status === val || (val === "pending" && o.status === "pending_payment")).length;

  async function updateStatus(order: Order, newStatus: OrderStatus) {
    setOrders((prev) =>
      prev.map((o) => (o.id === order.id ? { ...o, status: newStatus } : o))
    );
    const res = await fetch(`/api/admin/orders/${order.id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    if (!res.ok) {
      setOrders((prev) =>
        prev.map((o) => (o.id === order.id ? { ...o, status: order.status } : o))
      );
      toast("Status update failed", "error");
    } else {
      toast(`Order #${order.id} → ${newStatus}`, "success");
    }
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4 items-center">
        {STATUS_TABS.map(({ label, value }) => (
          <button
            key={label}
            onClick={() => setActiveTab(value)}
            className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${
              activeTab === value
                ? "bg-[#FFF8EC] text-[#C09330] border-[#F0D88A] font-medium"
                : "bg-white text-[#9C8B7A] border-[#E2D9CC] hover:text-[#3D2B1F]"
            }`}
          >
            {label} ({countForTab(value)})
          </button>
        ))}
        <input
          type="text"
          placeholder="Search name or order ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto w-48 px-3 py-1.5 text-xs border border-[#E2D9CC] rounded-full focus:outline-none focus:ring-1 focus:ring-[#C09330] text-[#3D2B1F]"
        />
        <button
          onClick={() => exportCsv(filtered)}
          className="px-3 py-1.5 text-xs border border-[#E2D9CC] rounded-md text-[#3D2B1F] bg-white hover:bg-[#F8F5F0] transition-colors"
        >
          ↓ Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-[#E2D9CC] overflow-hidden">
        <div className="grid grid-cols-[60px_2fr_1fr_1fr_1fr_120px] bg-[#FDFAF7] border-b border-[#E2D9CC] px-4 py-2 text-xs text-[#9C8B7A] uppercase tracking-wide">
          <span>#</span>
          <span>Customer</span>
          <span>Amount</span>
          <span>Status</span>
          <span>Date</span>
          <span>Update</span>
        </div>

        {filtered.length === 0 && (
          <p className="px-4 py-6 text-sm text-[#9C8B7A]">No orders found.</p>
        )}

        {filtered.map((order) => (
          <React.Fragment key={order.id}>
            <div
              onClick={() => setExpandedId(expandedId === order.id ? null : order.id)}
              className="grid grid-cols-[60px_2fr_1fr_1fr_1fr_120px] px-4 py-3 border-b border-[#F0EAE1] last:border-0 items-center text-sm cursor-pointer hover:bg-[#FDFAF7] transition-colors"
            >
              <span className="text-[#9C8B7A] text-xs">#{order.id}</span>
              <div>
                <div className="text-[#3D2B1F]">{order.customer_name}</div>
                <div className="text-[#9C8B7A] text-xs">{order.customer_email}</div>
              </div>
              <span className="text-[#3D2B1F]">₹{parseFloat(order.total).toLocaleString("en-IN")}</span>
              <StatusBadge status={order.status} />
              <span className="text-[#9C8B7A] text-xs">
                {new Date(order.created_at).toLocaleDateString("en-IN")}
              </span>
              <div onClick={(e) => e.stopPropagation()}>
                {NEXT_STATUS[order.status]?.length > 0 ? (
                  <select
                    value=""
                    onChange={(e) => updateStatus(order, e.target.value as OrderStatus)}
                    className="text-xs border border-[#E2D9CC] rounded px-2 py-1 bg-white text-[#3D2B1F] focus:outline-none focus:ring-1 focus:ring-[#C09330]"
                  >
                    <option value="" disabled>Move to…</option>
                    {NEXT_STATUS[order.status].map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                ) : (
                  <span className="text-xs text-[#9C8B7A]">—</span>
                )}
              </div>
            </div>

            {expandedId === order.id && (
              <div className="px-6 py-4 bg-[#FDFAF7] border-b border-[#F0EAE1] text-sm">
                <div className="text-xs text-[#9C8B7A] mb-2">
                  {order.shipping_address}, {order.city}, {order.state} {order.postal_code}
                </div>
                <div className="space-y-1">
                  {order.items.map((item) => (
                    <div key={item.id} className="flex justify-between text-[#3D2B1F]">
                      <span>{item.product_name} — {item.color}, size {item.size} × {item.quantity}</span>
                      <span>₹{parseFloat(item.line_total).toLocaleString("en-IN")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add "frontend/app/(admin)/admin/orders/page.tsx" frontend/components/admin/OrdersManager.tsx frontend/app/api/admin/orders/route.ts "frontend/app/api/admin/orders/[id]/status/route.ts"
git commit -m "feat: add orders management page with status updates and CSV export"
```

---

## Task 12: Frontend — Customers page + API proxy routes

**Files:**
- Create: `frontend/app/(admin)/admin/customers/page.tsx`
- Create: `frontend/components/admin/CustomersTable.tsx`
- Create: `frontend/app/api/admin/customers/route.ts`
- Create: `frontend/app/api/admin/customers/[id]/orders/route.ts`

- [ ] **Step 1: Create `frontend/app/api/admin/customers/route.ts`**

```typescript
import { NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function GET() {
  const res = await adminFetch("/admin/customers/");
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 2: Create `frontend/app/api/admin/customers/[id]/orders/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { adminFetch } from "@/lib/admin-api";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const res = await adminFetch(`/admin/customers/${id}/orders`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

- [ ] **Step 3: Create `frontend/app/(admin)/admin/customers/page.tsx`**

```typescript
import type { Metadata } from "next";
import { adminFetch } from "@/lib/admin-api";
import { CustomersTable } from "@/components/admin/CustomersTable";

export const metadata: Metadata = {
  title: "Customers | BeHAZEL'd Admin",
  robots: "noindex, nofollow",
};

export default async function CustomersPage() {
  const res = await adminFetch("/admin/customers/");
  const customers = await res.json();

  return (
    <div>
      <h1 className="text-xl font-semibold text-[#3D2B1F] mb-6">Customers</h1>
      <CustomersTable initialCustomers={customers} />
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/components/admin/CustomersTable.tsx`**

```typescript
"use client";

import React, { useState } from "react";
import { StatusBadge } from "@/components/admin/StatusBadge";

interface Customer {
  id: number;
  full_name: string;
  email: string;
  phone_number: string;
  city: string;
  created_at: string;
  order_count: number;
  total_spend: string;
}

interface OrderItem {
  product_name: string;
  color: string;
  size: string;
  quantity: number;
  line_total: string;
}

interface Order {
  id: number;
  total: string;
  status: string;
  created_at: string;
  items: OrderItem[];
}

export function CustomersTable({ initialCustomers }: { initialCustomers: Customer[] }) {
  const [search, setSearch]           = useState("");
  const [expandedId, setExpandedId]   = useState<number | null>(null);
  const [orderHistory, setOrderHistory] = useState<Record<number, Order[]>>({});
  const [loading, setLoading]         = useState<number | null>(null);

  const filtered = initialCustomers.filter(
    (c) =>
      c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.email.toLowerCase().includes(search.toLowerCase())
  );

  async function handleExpand(customerId: number) {
    if (expandedId === customerId) { setExpandedId(null); return; }
    setExpandedId(customerId);
    if (orderHistory[customerId]) return;
    setLoading(customerId);
    const res = await fetch(`/api/admin/customers/${customerId}/orders`);
    if (res.ok) {
      const orders = await res.json();
      setOrderHistory((prev) => ({ ...prev, [customerId]: orders }));
    }
    setLoading(null);
  }

  return (
    <div>
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 px-3 py-2 text-sm border border-[#E2D9CC] rounded-md bg-white text-[#3D2B1F] placeholder-[#9C8B7A] focus:outline-none focus:ring-1 focus:ring-[#C09330]"
        />
      </div>

      <div className="bg-white rounded-lg border border-[#E2D9CC] overflow-hidden">
        <div className="grid grid-cols-[2fr_2fr_1fr_1fr_1fr] bg-[#FDFAF7] border-b border-[#E2D9CC] px-4 py-2 text-xs text-[#9C8B7A] uppercase tracking-wide">
          <span>Name</span>
          <span>Email</span>
          <span>City</span>
          <span>Orders</span>
          <span>Total Spend</span>
        </div>

        {filtered.length === 0 && (
          <p className="px-4 py-6 text-sm text-[#9C8B7A]">No customers found.</p>
        )}

        {filtered.map((c) => (
          <React.Fragment key={c.id}>
            <div
              onClick={() => handleExpand(c.id)}
              className="grid grid-cols-[2fr_2fr_1fr_1fr_1fr] px-4 py-3 border-b border-[#F0EAE1] last:border-0 items-center text-sm cursor-pointer hover:bg-[#FDFAF7] transition-colors"
            >
              <div>
                <div className="text-[#3D2B1F] font-medium">{c.full_name}</div>
                <div className="text-[#9C8B7A] text-xs">{c.phone_number}</div>
              </div>
              <span className="text-[#9C8B7A] text-xs">{c.email}</span>
              <span className="text-[#3D2B1F] text-xs">{c.city}</span>
              <span className="text-[#3D2B1F]">{c.order_count}</span>
              <span className="text-[#C09330] font-medium">
                ₹{parseFloat(c.total_spend).toLocaleString("en-IN")}
              </span>
            </div>

            {expandedId === c.id && (
              <div className="px-6 py-4 bg-[#FDFAF7] border-b border-[#F0EAE1] text-sm">
                {loading === c.id && (
                  <p className="text-xs text-[#9C8B7A]">Loading order history…</p>
                )}
                {!loading && orderHistory[c.id]?.length === 0 && (
                  <p className="text-xs text-[#9C8B7A]">No orders yet.</p>
                )}
                <div className="space-y-3">
                  {(orderHistory[c.id] ?? []).map((order) => (
                    <div key={order.id} className="border border-[#E2D9CC] rounded-md p-3 bg-white">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-[#9C8B7A]">#{order.id} · {new Date(order.created_at).toLocaleDateString("en-IN")}</span>
                        <div className="flex items-center gap-3">
                          <StatusBadge status={order.status} />
                          <span className="text-sm font-medium text-[#3D2B1F]">₹{parseFloat(order.total).toLocaleString("en-IN")}</span>
                        </div>
                      </div>
                      {order.items.map((item, idx) => (
                        <div key={idx} className="text-xs text-[#9C8B7A]">
                          {item.product_name} — {item.color}, size {item.size} × {item.quantity} (₹{parseFloat(item.line_total).toLocaleString("en-IN")})
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Type-check**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add "frontend/app/(admin)/admin/customers/page.tsx" frontend/components/admin/CustomersTable.tsx frontend/app/api/admin/customers/route.ts "frontend/app/api/admin/customers/[id]/orders/route.ts"
git commit -m "feat: add customers page with expandable order history"
```

---

## Task 13: End-to-end smoke test

- [ ] **Step 1: Start backend**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/backend"
source .venv/bin/activate
uvicorn app.main:app --reload
```

- [ ] **Step 2: Start frontend (new terminal)**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website/frontend"
npm run dev
```

- [ ] **Step 3: Verify each page loads**

Open `http://localhost:3000/admin/login`, log in with `ADMIN_API_KEY`.

Verify each of these loads without error:
- `/admin/dashboard` — stat cards visible, recent orders table renders
- `/admin/products` — product list visible, search filters results
- `/admin/products/new` — create form renders with collection dropdown populated
- `/admin/collections` — 6 collections listed with active/inactive badges
- `/admin/orders` — orders list, status filter tabs, CSV export button visible
- `/admin/customers` — customers list, click row expands order history

- [ ] **Step 4: Verify order status update**

On `/admin/orders`, find a pending order. Use the "Move to…" dropdown to mark it Confirmed. Verify:
- The badge updates immediately (optimistic)
- A success toast appears top-right
- Refreshing the page still shows Confirmed

- [ ] **Step 5: Verify `/admin/upload` redirect**

Navigate to `http://localhost:3000/admin/upload`. Verify it redirects to `/admin/products/new`.

- [ ] **Step 6: Final commit**

```bash
cd "/Users/atanumazumdar/Codex Workspace/BeHazel'd Website"
git add .
git commit -m "chore: complete CMS admin dashboard implementation"
```
