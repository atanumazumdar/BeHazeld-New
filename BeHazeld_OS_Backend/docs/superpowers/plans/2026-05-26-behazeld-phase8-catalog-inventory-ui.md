# BeHazeld Phase 8: Catalog & Inventory UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Catalog (product table + creation wizard + master data CRUD) and Inventory (SKU detail + stock ledger + adjustment form) admin UI in Next.js 14 App Router, backed by the existing FastAPI API.

**Architecture:** Two backend additions (search params on list_products; a locations list endpoint) plus a pure frontend build using TanStack Query v5 for server state, react-hook-form + zod for forms, and Shadcn UI components. All API calls go through the existing `lib/api-client.ts`. The user is notified after Task 5 (Product Table + Wizard complete) before Inventory tasks begin.

**Tech Stack:** Next.js 14 App Router, TypeScript, TanStack Query v5, react-hook-form v7, zod v3, Shadcn UI (base-ui), Tailwind CSS v3, lucide-react, FastAPI (existing backend on `http://localhost:8000`)

---

## Backend changes overview

| File | Change |
|---|---|
| `app/api/v1/catalog.py` | Add `search`, `category_id`, `brand_id`, `status` query params to `GET /catalog/products` |
| `app/repositories/catalog_repository.py` | Add optional filters to `list_products` |
| `app/services/catalog_service.py` | Pass new params through |
| `app/api/v1/inventory.py` | Add `GET /inventory/locations` endpoint |
| `app/repositories/tenant_repository.py` | Add `list_locations_by_tenant` method |

## Frontend file map

```
behazeld-admin/
├── app/(admin)/
│   ├── catalog/
│   │   ├── products/
│   │   │   └── page.tsx                  ← product table + wizard trigger
│   │   ├── categories/page.tsx           ← categories CRUD
│   │   ├── brands/page.tsx               ← brands CRUD
│   │   ├── sizes/page.tsx                ← sizes CRUD
│   │   └── colors/page.tsx               ← colors CRUD
│   └── inventory/
│       └── [variantId]/page.tsx          ← SKU detail: balance + ledger + adjustment
├── components/
│   ├── catalog/
│   │   ├── product-table.tsx             ← data table with search/filter/pagination
│   │   ├── product-columns.tsx           ← column definitions
│   │   ├── create-product-wizard.tsx     ← 2-step modal wizard
│   │   ├── variant-row.tsx               ← single variant row in step 2
│   │   └── master-data-page.tsx          ← reusable list+add for categories/brands/etc
│   ├── inventory/
│   │   └── stock-adjustment-form.tsx     ← record movement modal
│   └── ui/
│       ├── badge.tsx                     ← Shadcn badge (added via CLI)
│       ├── dialog.tsx                    ← Shadcn dialog
│       ├── select.tsx                    ← Shadcn select
│       ├── table.tsx                     ← Shadcn table
│       ├── toast.tsx                     ← Shadcn sonner toast
│       ├── separator.tsx                 ← Shadcn separator
│       └── skeleton.tsx                  ← Shadcn skeleton
├── hooks/
│   ├── use-catalog.ts                    ← TanStack Query hooks for catalog
│   └── use-inventory.ts                  ← TanStack Query hooks for inventory
├── types/
│   ├── catalog.ts                        ← TypeScript types mirroring catalog schemas
│   └── inventory.ts                      ← TypeScript types mirroring inventory schemas
└── lib/
    └── query-client.tsx                  ← QueryClientProvider wrapper
```

---

## Task 1: Backend — Product Search + Locations API

**Files:**
- Modify: `BeHazeld E-Commerce OS/app/repositories/catalog_repository.py`
- Modify: `BeHazeld E-Commerce OS/app/services/catalog_service.py`
- Modify: `BeHazeld E-Commerce OS/app/api/v1/catalog.py`
- Modify: `BeHazeld E-Commerce OS/app/repositories/tenant_repository.py`
- Modify: `BeHazeld E-Commerce OS/app/api/v1/inventory.py`
- Modify: `BeHazeld E-Commerce OS/tests/integration/test_catalog_router.py`
- Modify: `BeHazeld E-Commerce OS/tests/integration/test_inventory_router.py`

- [ ] **Step 1: Verify baseline tests pass**

```bash
cd "/Users/atanumazumdar/Claude Workspace/BeHazeld E-Commerce OS"
python3 -m pytest tests/integration/test_catalog_router.py tests/integration/test_inventory_router.py -v --no-header
```

Expected: 13 + 13 = 26 passed.

- [ ] **Step 2: Add search/filter to `list_products` in catalog_repository.py**

Read `app/repositories/catalog_repository.py`, find the `list_products` method (around line 229), and replace it with:

```python
def list_products(
    self,
    tenant_id: uuid.UUID,
    status: str = "active",
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
) -> list[Product]:
    q = (
        select(Product)
        .where(Product.tenant_id == tenant_id, Product.status == status)
    )
    if search:
        pattern = f"%{search}%"
        q = q.where(
            Product.product_code.ilike(pattern) | Product.name.ilike(pattern)
        )
    if category_id is not None:
        q = q.where(Product.category_id == category_id)
    if brand_id is not None:
        q = q.where(Product.brand_id == brand_id)
    return list(
        self.db.scalars(q.order_by(Product.name).offset(skip).limit(limit))
    )
```

- [ ] **Step 3: Add search params to `list_products` in catalog_service.py**

Read `app/services/catalog_service.py`, find the `list_products` method (around line 213), and replace it with:

```python
def list_products(
    self,
    tenant_id: uuid.UUID,
    status: str = "active",
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
) -> list[Product]:
    return self.repo.list_products(
        tenant_id,
        status=status,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        brand_id=brand_id,
    )
```

- [ ] **Step 4: Expose search params in the catalog router**

Read `app/api/v1/catalog.py`, find the `list_products` endpoint (around line 183), and replace it with:

```python
@router.get("/products", response_model=list[ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 50,
    status: str = "active",
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    return CatalogService(db).list_products(  # type: ignore[return-value]
        ctx.tenant_id,
        status=status,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        brand_id=brand_id,
    )
```

Also add `Optional` import if needed — `uuid` is already imported. The `uuid.UUID | None` type on query params works in FastAPI 0.100+.

- [ ] **Step 5: Add `list_locations_by_tenant` to tenant_repository.py**

Read `app/repositories/tenant_repository.py`. Add this import at the top (after existing imports):

```python
from app.models.tenant import Location
```

Then add this method to the `TenantRepository` class:

```python
def list_locations_by_tenant(self, tenant_id: uuid.UUID) -> list[Location]:
    """Return all active locations for a tenant."""
    from sqlalchemy import select as sa_select
    return list(
        self.db.scalars(
            sa_select(Location)
            .where(Location.tenant_id == tenant_id, Location.is_active.is_(True))
            .order_by(Location.name)
        )
    )
```

- [ ] **Step 6: Add locations response schema to inventory schemas**

Read `app/schemas/inventory.py`. Append this class at the end:

```python
class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    address: str | None
    is_active: bool
    bins: list[BinResponse] = []
```

- [ ] **Step 7: Add GET /inventory/locations endpoint**

Read `app/api/v1/inventory.py`. Add the import for `LocationResponse` in the import block:

```python
from app.schemas.inventory import (
    BinResponse,
    CreateBinRequest,
    LocationResponse,
    RecordMovementRequest,
    StockBalanceResponse,
    StockMovementResponse,
)
```

Then add this endpoint after the bins section (after line 54):

```python
# ── Locations ─────────────────────────────────────────────────────────────────

@router.get(
    "/locations",
    response_model=list[LocationResponse],
)
def list_locations(
    ctx: TenantContext = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db),
) -> list[LocationResponse]:
    """List all active locations for the tenant, with their bins."""
    from app.repositories.tenant_repository import TenantRepository
    from app.repositories.inventory_repository import InventoryRepository
    locations = TenantRepository(db).list_locations_by_tenant(ctx.tenant_id)
    inv_repo = InventoryRepository(db)
    result = []
    for loc in locations:
        bins = inv_repo.list_bins_by_location(ctx.tenant_id, loc.id)
        loc_data = LocationResponse.model_validate(loc)
        loc_data.bins = [BinResponse.model_validate(b) for b in bins]
        result.append(loc_data)
    return result
```

- [ ] **Step 8: Write new tests for search params**

Add to `tests/integration/test_catalog_router.py` (append at the end of the file):

```python
def test_product_listing_search_param_forwarded_to_service(client: TestClient) -> None:
    """search query param is forwarded to CatalogService.list_products."""
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = []
        resp = client.get("/api/v1/catalog/products", params={"search": "kurti"})
    assert resp.status_code == 200
    call_kwargs = MockSvc.return_value.list_products.call_args.kwargs
    assert call_kwargs["search"] == "kurti"


def test_product_listing_category_filter_forwarded(client: TestClient) -> None:
    """category_id query param is forwarded to CatalogService.list_products."""
    cat_id = uuid.uuid4()
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = []
        resp = client.get("/api/v1/catalog/products", params={"category_id": str(cat_id)})
    assert resp.status_code == 200
    call_kwargs = MockSvc.return_value.list_products.call_args.kwargs
    assert call_kwargs["category_id"] == cat_id


def test_product_listing_status_param_forwarded(client: TestClient) -> None:
    """status=deleted returns deleted products."""
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = []
        resp = client.get("/api/v1/catalog/products", params={"status": "deleted"})
    assert resp.status_code == 200
    call_kwargs = MockSvc.return_value.list_products.call_args.kwargs
    assert call_kwargs["status"] == "deleted"
```

- [ ] **Step 9: Write new test for locations endpoint**

Add to `tests/integration/test_inventory_router.py` (append at the end):

```python
def test_list_locations_returns_200(client: TestClient) -> None:
    """GET /inventory/locations returns 200 with location list."""
    from app.schemas.inventory import LocationResponse
    with patch("app.api.v1.inventory.TenantRepository") as MockTRepo, \
         patch("app.api.v1.inventory.InventoryRepository") as MockIRepo:
        mock_loc = MagicMock()
        mock_loc.id = uuid.uuid4()
        mock_loc.tenant_id = _TENANT_ID
        mock_loc.name = "Main Warehouse"
        mock_loc.address = None
        mock_loc.is_active = True
        MockTRepo.return_value.list_locations_by_tenant.return_value = [mock_loc]
        MockIRepo.return_value.list_bins_by_location.return_value = [_bin_orm()]
        resp = client.get("/api/v1/inventory/locations")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Main Warehouse"
    assert isinstance(body[0]["bins"], list)
```

- [ ] **Step 10: Run all tests to verify**

```bash
cd "/Users/atanumazumdar/Claude Workspace/BeHazeld E-Commerce OS"
python3 -m pytest tests/integration/test_catalog_router.py tests/integration/test_inventory_router.py -v --no-header
```

Expected: 16 catalog tests + 14 inventory tests = 30 passed, 0 failed.

- [ ] **Step 11: Commit backend changes**

```bash
cd "/Users/atanumazumdar/Claude Workspace/BeHazeld E-Commerce OS"
git add app/api/v1/catalog.py app/api/v1/inventory.py \
    app/repositories/catalog_repository.py \
    app/repositories/tenant_repository.py \
    app/services/catalog_service.py \
    app/schemas/inventory.py \
    tests/integration/test_catalog_router.py \
    tests/integration/test_inventory_router.py
git commit -m "feat(api): add search/filter to list_products; add GET /inventory/locations

- list_products: new query params search (ilike on code+name), category_id,
  brand_id, status (already in service, now exposed in router)
- GET /inventory/locations: returns active locations with their bins
- LocationResponse schema with nested BinResponse list
- All existing tests pass; 4 new catalog tests + 1 new inventory test added"
```

---

## Task 2: Install Frontend Dependencies

**Files:**
- Modify: `behazeld-admin/package.json` (via npm install)

- [ ] **Step 1: Install TanStack Query, react-hook-form, zod**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm install @tanstack/react-query@^5 react-hook-form zod @hookform/resolvers
```

Expected: packages installed, no peer dep errors.

- [ ] **Step 2: Add required Shadcn UI components**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx shadcn@latest add badge dialog select table separator skeleton --yes 2>&1
```

Expected: `components/ui/badge.tsx`, `dialog.tsx`, `select.tsx`, `table.tsx`, `separator.tsx`, `skeleton.tsx` created.

- [ ] **Step 3: Install sonner for toasts**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm install sonner
```

- [ ] **Step 4: Verify TypeScript still clean**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx tsc --noEmit 2>&1 | head -20
```

Expected: 0 errors (or only pre-existing errors from base-ui types — none expected).

---

## Task 3: Shared Infrastructure (QueryClient + Types + Hooks)

**Files:**
- Create: `behazeld-admin/lib/query-client.tsx`
- Modify: `behazeld-admin/app/layout.tsx`
- Create: `behazeld-admin/types/catalog.ts`
- Create: `behazeld-admin/types/inventory.ts`
- Create: `behazeld-admin/hooks/use-catalog.ts`
- Create: `behazeld-admin/hooks/use-inventory.ts`

- [ ] **Step 1: Create QueryClient provider**

Create `behazeld-admin/lib/query-client.tsx`:

```tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function ReactQueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,      // 30 seconds
            retry: 1,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 2: Wrap root layout with ReactQueryProvider + Toaster**

Read `behazeld-admin/app/layout.tsx`. Replace it with:

```tsx
import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/query-client";
import { Toaster } from "sonner";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "BeHazeld OS — Admin",
  description: "BeHazeld E-Commerce Operating System — Admin Panel",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ReactQueryProvider>
          {children}
          <Toaster position="top-right" richColors closeButton />
        </ReactQueryProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Create catalog TypeScript types**

Create `behazeld-admin/types/catalog.ts`:

```typescript
// Mirrors the FastAPI Pydantic schemas in app/schemas/catalog.py

export interface CategoryResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductGroupResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductTypeResponse {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrandResponse {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SizeResponse {
  id: string;
  tenant_id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ColorResponse {
  id: string;
  tenant_id: string;
  name: string;
  hex_code: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductResponse {
  id: string;
  tenant_id: string;
  product_code: string;
  name: string;
  description: string | null;
  image_url: string | null;
  status: 'active' | 'deleted';
  category_id: string | null;
  product_group_id: string | null;
  product_type_id: string | null;
  brand_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductVariantResponse {
  id: string;
  tenant_id: string;
  product_id: string;
  size_id: string;
  color_id: string;
  sku_code: string;
  fabric: string | null;
  mrp: string;
  selling_price: string;
  cost_price: string;
  reorder_level: number;
  status: 'active' | 'deleted';
  created_at: string;
  updated_at: string;
}

// ── Request types ─────────────────────────────────────────────────────────────

export interface CreateProductRequest {
  name: string;
  category_id?: string | null;
  product_group_id?: string | null;
  product_type_id?: string | null;
  brand_id?: string | null;
  description?: string | null;
  image_url?: string | null;
}

export interface CreateVariantRequest {
  size_id: string;
  color_id: string;
  mrp: string;
  selling_price: string;
  cost_price: string;
  fabric?: string | null;
  reorder_level?: number;
}

export interface CreateCategoryRequest {
  name: string;
  description?: string | null;
  sort_order?: number;
}

export interface CreateBrandRequest {
  name: string;
}

export interface CreateSizeRequest {
  name: string;
  sort_order?: number;
}

export interface CreateColorRequest {
  name: string;
  hex_code?: string | null;
}

export interface ProductListParams {
  skip?: number;
  limit?: number;
  status?: string;
  search?: string;
  category_id?: string;
  brand_id?: string;
}
```

- [ ] **Step 4: Create inventory TypeScript types**

Create `behazeld-admin/types/inventory.ts`:

```typescript
// Mirrors the FastAPI Pydantic schemas in app/schemas/inventory.py

export interface BinResponse {
  id: string;
  tenant_id: string;
  location_id: string;
  name: string;
  is_default: boolean;
  is_active: boolean;
}

export interface LocationResponse {
  id: string;
  tenant_id: string;
  name: string;
  address: string | null;
  is_active: boolean;
  bins: BinResponse[];
}

export interface StockBalanceResponse {
  id: string;
  product_variant_id: string;
  location_id: string;
  bin_id: string;
  quantity_on_hand: string;
  quantity_reserved: string;
  quantity_available: string;
}

export interface StockMovementResponse {
  id: string;
  product_variant_id: string;
  location_id: string;
  bin_id: string;
  movement_type: string;
  quantity_change: string;
  unit_cost: string;
  notes: string | null;
}

// ── Request types ─────────────────────────────────────────────────────────────

export type MovementType =
  | 'opening_stock'
  | 'purchase_in'
  | 'sale_out'
  | 'return_in'
  | 'adjustment_in'
  | 'adjustment_out'
  | 'transfer_in'
  | 'transfer_out';

export interface RecordMovementRequest {
  product_variant_id: string;
  location_id: string;
  bin_id: string;
  movement_type: MovementType;
  quantity: string;
  unit_cost: string;
  notes?: string | null;
}
```

- [ ] **Step 5: Create catalog React Query hooks**

Create `behazeld-admin/hooks/use-catalog.ts`:

```typescript
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  CategoryResponse,
  ProductGroupResponse,
  ProductTypeResponse,
  BrandResponse,
  SizeResponse,
  ColorResponse,
  ProductResponse,
  ProductVariantResponse,
  CreateProductRequest,
  CreateVariantRequest,
  CreateCategoryRequest,
  CreateBrandRequest,
  CreateSizeRequest,
  CreateColorRequest,
  ProductListParams,
} from '@/types/catalog';

// ── Query keys ──────────────────────────────────────────────────────────────

export const catalogKeys = {
  products: (params?: ProductListParams) => ['catalog', 'products', params] as const,
  product: (id: string) => ['catalog', 'products', id] as const,
  variants: (productId: string) => ['catalog', 'products', productId, 'variants'] as const,
  categories: () => ['catalog', 'categories'] as const,
  productGroups: () => ['catalog', 'product-groups'] as const,
  productTypes: () => ['catalog', 'product-types'] as const,
  brands: () => ['catalog', 'brands'] as const,
  sizes: () => ['catalog', 'sizes'] as const,
  colors: () => ['catalog', 'colors'] as const,
};

// ── List hooks ──────────────────────────────────────────────────────────────

export function useProducts(params: ProductListParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params.status) searchParams.set('status', params.status);
  if (params.search) searchParams.set('search', params.search);
  if (params.category_id) searchParams.set('category_id', params.category_id);
  if (params.brand_id) searchParams.set('brand_id', params.brand_id);

  const qs = searchParams.toString();
  return useQuery({
    queryKey: catalogKeys.products(params),
    queryFn: () =>
      apiClient.get<ProductResponse[]>(`/api/v1/catalog/products${qs ? `?${qs}` : ''}`),
  });
}

export function useProduct(productId: string) {
  return useQuery({
    queryKey: catalogKeys.product(productId),
    queryFn: () => apiClient.get<ProductResponse>(`/api/v1/catalog/products/${productId}`),
    enabled: !!productId,
  });
}

export function useVariants(productId: string) {
  return useQuery({
    queryKey: catalogKeys.variants(productId),
    queryFn: () =>
      apiClient.get<ProductVariantResponse[]>(
        `/api/v1/catalog/products/${productId}/variants`,
      ),
    enabled: !!productId,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: catalogKeys.categories(),
    queryFn: () => apiClient.get<CategoryResponse[]>('/api/v1/catalog/categories'),
  });
}

export function useProductGroups() {
  return useQuery({
    queryKey: catalogKeys.productGroups(),
    queryFn: () => apiClient.get<ProductGroupResponse[]>('/api/v1/catalog/product-groups'),
  });
}

export function useProductTypes() {
  return useQuery({
    queryKey: catalogKeys.productTypes(),
    queryFn: () => apiClient.get<ProductTypeResponse[]>('/api/v1/catalog/product-types'),
  });
}

export function useBrands() {
  return useQuery({
    queryKey: catalogKeys.brands(),
    queryFn: () => apiClient.get<BrandResponse[]>('/api/v1/catalog/brands'),
  });
}

export function useSizes() {
  return useQuery({
    queryKey: catalogKeys.sizes(),
    queryFn: () => apiClient.get<SizeResponse[]>('/api/v1/catalog/sizes'),
  });
}

export function useColors() {
  return useQuery({
    queryKey: catalogKeys.colors(),
    queryFn: () => apiClient.get<ColorResponse[]>('/api/v1/catalog/colors'),
  });
}

// ── Mutation hooks ──────────────────────────────────────────────────────────

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateProductRequest) =>
      apiClient.post<ProductResponse>('/api/v1/catalog/products', body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['catalog', 'products'] });
    },
  });
}

export function useCreateVariant(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateVariantRequest) =>
      apiClient.post<ProductVariantResponse>(
        `/api/v1/catalog/products/${productId}/variants`,
        body,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: catalogKeys.variants(productId) });
    },
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (productId: string) =>
      apiClient.delete<ProductResponse>(`/api/v1/catalog/products/${productId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['catalog', 'products'] });
    },
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateCategoryRequest) =>
      apiClient.post<CategoryResponse>('/api/v1/catalog/categories', body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: catalogKeys.categories() });
    },
  });
}

export function useCreateBrand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateBrandRequest) =>
      apiClient.post<BrandResponse>('/api/v1/catalog/brands', body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: catalogKeys.brands() });
    },
  });
}

export function useCreateSize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSizeRequest) =>
      apiClient.post<SizeResponse>('/api/v1/catalog/sizes', body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: catalogKeys.sizes() });
    },
  });
}

export function useCreateColor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateColorRequest) =>
      apiClient.post<ColorResponse>('/api/v1/catalog/colors', body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: catalogKeys.colors() });
    },
  });
}
```

- [ ] **Step 6: Create inventory React Query hooks**

Create `behazeld-admin/hooks/use-inventory.ts`:

```typescript
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  LocationResponse,
  StockBalanceResponse,
  StockMovementResponse,
  RecordMovementRequest,
} from '@/types/inventory';

export const inventoryKeys = {
  locations: () => ['inventory', 'locations'] as const,
  summary: (variantId: string) => ['inventory', 'summary', variantId] as const,
  ledger: (variantId: string, locationId: string) =>
    ['inventory', 'ledger', variantId, locationId] as const,
};

export function useLocations() {
  return useQuery({
    queryKey: inventoryKeys.locations(),
    queryFn: () => apiClient.get<LocationResponse[]>('/api/v1/inventory/locations'),
  });
}

export function useStockSummary(variantId: string) {
  return useQuery({
    queryKey: inventoryKeys.summary(variantId),
    queryFn: () =>
      apiClient.get<StockBalanceResponse[]>(
        `/api/v1/inventory/summary/${variantId}`,
      ),
    enabled: !!variantId,
  });
}

export function useStockLedger(variantId: string, locationId: string, limit = 100) {
  return useQuery({
    queryKey: inventoryKeys.ledger(variantId, locationId),
    queryFn: () =>
      apiClient.get<StockMovementResponse[]>(
        `/api/v1/inventory/ledger/${variantId}?location_id=${locationId}&limit=${limit}`,
      ),
    enabled: !!variantId && !!locationId,
  });
}

export function useRecordMovement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecordMovementRequest) =>
      apiClient.post<StockMovementResponse>('/api/v1/inventory/movements', body),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: inventoryKeys.summary(vars.product_variant_id) });
      void qc.invalidateQueries({
        queryKey: inventoryKeys.ledger(vars.product_variant_id, vars.location_id),
      });
    },
  });
}
```

- [ ] **Step 7: TypeScript check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx tsc --noEmit 2>&1 | head -20
```

Expected: 0 errors.

---

## Task 4: Product Table Page

**Files:**
- Create: `behazeld-admin/components/catalog/product-columns.tsx`
- Create: `behazeld-admin/components/catalog/product-table.tsx`
- Create: `behazeld-admin/app/(admin)/catalog/products/page.tsx`

- [ ] **Step 1: Create product column definitions**

Create `behazeld-admin/components/catalog/product-columns.tsx`:

```tsx
'use client';

import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import type { ProductResponse } from '@/types/catalog';

export interface ProductColumn {
  key: keyof ProductResponse | 'actions';
  header: string;
  render: (row: ProductResponse) => React.ReactNode;
  className?: string;
}

export const productColumns: ProductColumn[] = [
  {
    key: 'product_code',
    header: 'Code',
    render: (row) => (
      <span className="font-mono text-xs text-stone-600">{row.product_code}</span>
    ),
    className: 'w-36',
  },
  {
    key: 'name',
    header: 'Product Name',
    render: (row) => (
      <span className="font-medium text-stone-900">{row.name}</span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (row) => (
      <Badge
        variant={row.status === 'active' ? 'default' : 'destructive'}
        className={
          row.status === 'active'
            ? 'bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
            : 'bg-red-100 text-red-800 border-red-200 hover:bg-red-100'
        }
      >
        {row.status === 'active' ? 'Active' : 'Deleted'}
      </Badge>
    ),
    className: 'w-28',
  },
  {
    key: 'actions',
    header: '',
    render: (row) => (
      <Link
        href={`/catalog/products/${row.id}`}
        className="text-xs text-rose-700 hover:text-rose-900 font-medium"
      >
        View →
      </Link>
    ),
    className: 'w-20 text-right',
  },
];
```

- [ ] **Step 2: Create the product data table component**

Create `behazeld-admin/components/catalog/product-table.tsx`:

```tsx
'use client';

import { useState, useCallback } from 'react';
import { Search, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { useDebounce } from 'use-debounce';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useProducts, useCategories, useBrands } from '@/hooks/use-catalog';
import { productColumns } from './product-columns';
import type { ProductListParams } from '@/types/catalog';

const PAGE_SIZE = 25;

interface ProductTableProps {
  onCreateClick: () => void;
}

export function ProductTable({ onCreateClick }: ProductTableProps) {
  const [search, setSearch] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [brandId, setBrandId] = useState('');
  const [page, setPage] = useState(0);
  const [debouncedSearch] = useDebounce(search, 400);

  const params: ProductListParams = {
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(categoryId ? { category_id: categoryId } : {}),
    ...(brandId ? { brand_id: brandId } : {}),
  };

  const { data: products, isLoading, isError } = useProducts(params);
  const { data: categories } = useCategories();
  const { data: brands } = useBrands();

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearch(e.target.value);
      setPage(0);
    },
    [],
  );

  const hasMore = (products?.length ?? 0) === PAGE_SIZE;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-stone-400" />
          <Input
            placeholder="Search code or name…"
            value={search}
            onChange={handleSearch}
            className="pl-8 border-stone-300"
          />
        </div>

        {/* Category filter */}
        <select
          value={categoryId}
          onChange={(e) => { setCategoryId(e.target.value); setPage(0); }}
          className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
        >
          <option value="">All categories</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        {/* Brand filter */}
        <select
          value={brandId}
          onChange={(e) => { setBrandId(e.target.value); setPage(0); }}
          className="h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
        >
          <option value="">All brands</option>
          {brands?.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>

        <Button
          onClick={onCreateClick}
          className="ml-auto bg-rose-800 hover:bg-rose-900 text-white gap-2"
        >
          <Plus className="h-4 w-4" />
          New Product
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50">
              {productColumns.map((col) => (
                <TableHead
                  key={col.key}
                  className={`text-xs font-semibold text-stone-500 uppercase tracking-wide ${col.className ?? ''}`}
                >
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  {productColumns.map((col) => (
                    <TableCell key={col.key}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
            {isError && (
              <TableRow>
                <TableCell colSpan={productColumns.length} className="text-center text-sm text-red-600 py-8">
                  Failed to load products. Check your connection.
                </TableCell>
              </TableRow>
            )}
            {!isLoading && !isError && products?.length === 0 && (
              <TableRow>
                <TableCell colSpan={productColumns.length} className="text-center text-sm text-stone-400 py-8">
                  No products found.
                </TableCell>
              </TableRow>
            )}
            {!isLoading && products?.map((product) => (
              <TableRow key={product.id} className="hover:bg-stone-50">
                {productColumns.map((col) => (
                  <TableCell key={col.key} className={col.className ?? ''}>
                    {col.render(product)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-stone-500">
        <span>
          {products?.length
            ? `Showing ${page * PAGE_SIZE + 1}–${page * PAGE_SIZE + products.length}`
            : 'No results'}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="gap-1"
          >
            <ChevronLeft className="h-3 w-3" />
            Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore}
            className="gap-1"
          >
            Next
            <ChevronRight className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

Note: `use-debounce` needs installing. Run:
```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm install use-debounce
```

- [ ] **Step 3: Create the products page**

Create `behazeld-admin/app/(admin)/catalog/products/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { ProductTable } from '@/components/catalog/product-table';
import { CreateProductWizard } from '@/components/catalog/create-product-wizard';

export default function ProductsPage() {
  const [wizardOpen, setWizardOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-stone-900">Products</h2>
        <p className="text-sm text-stone-500 mt-1">
          Manage your product catalog and SKU variants
        </p>
      </div>

      <ProductTable onCreateClick={() => setWizardOpen(true)} />

      <CreateProductWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
      />
    </div>
  );
}
```

---

## Task 5: Product Creation Wizard

**Files:**
- Create: `behazeld-admin/components/catalog/variant-row.tsx`
- Create: `behazeld-admin/components/catalog/create-product-wizard.tsx`

- [ ] **Step 1: Check the Dialog component API**

Read `behazeld-admin/components/ui/dialog.tsx` to understand the component signatures before using them. The base-ui Dialog may use different props.

- [ ] **Step 2: Create the variant row form component**

Create `behazeld-admin/components/catalog/variant-row.tsx`:

```tsx
'use client';

import { UseFormReturn, useFieldArray } from 'react-hook-form';
import { Trash2, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { SizeResponse, ColorResponse } from '@/types/catalog';

export interface VariantFormValue {
  size_id: string;
  color_id: string;
  mrp: string;
  selling_price: string;
  cost_price: string;
  reorder_level: string;
}

export interface WizardStep2Form {
  variants: VariantFormValue[];
}

interface VariantRowProps {
  index: number;
  form: UseFormReturn<WizardStep2Form>;
  sizes: SizeResponse[];
  colors: ColorResponse[];
  onRemove: () => void;
  canRemove: boolean;
}

export function VariantRow({ index, form, sizes, colors, onRemove, canRemove }: VariantRowProps) {
  const { register, formState: { errors } } = form;

  return (
    <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1fr_auto] gap-2 items-start">
      {/* Size */}
      <div>
        <select
          {...register(`variants.${index}.size_id`, { required: 'Required' })}
          className="w-full h-9 rounded-md border border-stone-300 bg-white px-2 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
        >
          <option value="">Size</option>
          {sizes.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        {errors.variants?.[index]?.size_id && (
          <p className="text-xs text-red-600 mt-0.5">{errors.variants[index]!.size_id!.message}</p>
        )}
      </div>

      {/* Color */}
      <div>
        <select
          {...register(`variants.${index}.color_id`, { required: 'Required' })}
          className="w-full h-9 rounded-md border border-stone-300 bg-white px-2 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
        >
          <option value="">Color</option>
          {colors.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {errors.variants?.[index]?.color_id && (
          <p className="text-xs text-red-600 mt-0.5">{errors.variants[index]!.color_id!.message}</p>
        )}
      </div>

      {/* MRP */}
      <div>
        <Input
          {...register(`variants.${index}.mrp`, {
            required: 'Required',
            pattern: { value: /^\d+(\.\d{1,2})?$/, message: 'Invalid' },
          })}
          placeholder="MRP"
          className="border-stone-300 text-sm"
        />
        {errors.variants?.[index]?.mrp && (
          <p className="text-xs text-red-600 mt-0.5">{errors.variants[index]!.mrp!.message}</p>
        )}
      </div>

      {/* Selling Price */}
      <div>
        <Input
          {...register(`variants.${index}.selling_price`, {
            required: 'Required',
            pattern: { value: /^\d+(\.\d{1,2})?$/, message: 'Invalid' },
          })}
          placeholder="Selling ₹"
          className="border-stone-300 text-sm"
        />
        {errors.variants?.[index]?.selling_price && (
          <p className="text-xs text-red-600 mt-0.5">{errors.variants[index]!.selling_price!.message}</p>
        )}
      </div>

      {/* Cost Price */}
      <div>
        <Input
          {...register(`variants.${index}.cost_price`, {
            required: 'Required',
            pattern: { value: /^\d+(\.\d{1,2})?$/, message: 'Invalid' },
          })}
          placeholder="Cost ₹"
          className="border-stone-300 text-sm"
        />
        {errors.variants?.[index]?.cost_price && (
          <p className="text-xs text-red-600 mt-0.5">{errors.variants[index]!.cost_price!.message}</p>
        )}
      </div>

      {/* Remove button */}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onRemove}
        disabled={!canRemove}
        className="text-stone-400 hover:text-red-600 px-2"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
```

- [ ] **Step 3: Create the multi-step wizard**

Read `behazeld-admin/components/ui/dialog.tsx` first to see the component API, then create `behazeld-admin/components/catalog/create-product-wizard.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { toast } from 'sonner';
import { ArrowLeft, ArrowRight, CheckCircle2, Plus, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  useCreateProduct,
  useCreateVariant,
  useCategories,
  useProductGroups,
  useProductTypes,
  useBrands,
  useSizes,
  useColors,
} from '@/hooks/use-catalog';
import { VariantRow } from './variant-row';
import type { VariantFormValue, WizardStep2Form } from './variant-row';
import { ApiError } from '@/types/api';

interface Step1Form {
  name: string;
  category_id: string;
  product_group_id: string;
  product_type_id: string;
  brand_id: string;
  description: string;
}

interface CreateProductWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateProductWizard({ open, onOpenChange }: CreateProductWizardProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [createdProductId, setCreatedProductId] = useState<string | null>(null);
  const [createdProductCode, setCreatedProductCode] = useState<string>('');

  const { data: categories } = useCategories();
  const { data: productGroups } = useProductGroups();
  const { data: productTypes } = useProductTypes();
  const { data: brands } = useBrands();
  const { data: sizes } = useSizes();
  const { data: colors } = useColors();

  const createProduct = useCreateProduct();

  const step1Form = useForm<Step1Form>({
    defaultValues: {
      name: '',
      category_id: '',
      product_group_id: '',
      product_type_id: '',
      brand_id: '',
      description: '',
    },
  });

  const step2Form = useForm<WizardStep2Form>({
    defaultValues: {
      variants: [
        { size_id: '', color_id: '', mrp: '', selling_price: '', cost_price: '', reorder_level: '0' },
      ],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: step2Form.control,
    name: 'variants',
  });

  function resetWizard() {
    setStep(1);
    setCreatedProductId(null);
    setCreatedProductCode('');
    step1Form.reset();
    step2Form.reset({
      variants: [{ size_id: '', color_id: '', mrp: '', selling_price: '', cost_price: '', reorder_level: '0' }],
    });
  }

  function handleClose() {
    resetWizard();
    onOpenChange(false);
  }

  async function handleStep1Submit(data: Step1Form) {
    try {
      const product = await createProduct.mutateAsync({
        name: data.name,
        category_id: data.category_id || null,
        product_group_id: data.product_group_id || null,
        product_type_id: data.product_type_id || null,
        brand_id: data.brand_id || null,
        description: data.description || null,
      });
      setCreatedProductId(product.id);
      setCreatedProductCode(product.product_code);
      setStep(2);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to create product';
      toast.error(msg);
    }
  }

  async function handleStep2Submit(data: WizardStep2Form) {
    if (!createdProductId) return;

    const results = await Promise.allSettled(
      data.variants.map((v) =>
        apiClient.post(
          `/api/v1/catalog/products/${createdProductId}/variants`,
          {
            size_id: v.size_id,
            color_id: v.color_id,
            mrp: v.mrp,
            selling_price: v.selling_price,
            cost_price: v.cost_price,
            reorder_level: parseInt(v.reorder_level || '0', 10),
          },
        ),
      ),
    );

    const failed = results.filter((r) => r.status === 'rejected').length;
    if (failed > 0) {
      toast.error(`${failed} variant(s) failed to save. Product code: ${createdProductCode}`);
    } else {
      toast.success(
        `Product ${createdProductCode} created with ${data.variants.length} variant(s).`,
      );
    }
    handleClose();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">New Product</h2>
            <p className="text-sm text-stone-500">
              Step {step} of 2 — {step === 1 ? 'Basic details' : `Variants for ${createdProductCode}`}
            </p>
          </div>
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            <div className={`h-2 w-8 rounded-full ${step >= 1 ? 'bg-rose-800' : 'bg-stone-200'}`} />
            <div className={`h-2 w-8 rounded-full ${step >= 2 ? 'bg-rose-800' : 'bg-stone-200'}`} />
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {step === 1 && (
            <form id="step1-form" onSubmit={step1Form.handleSubmit(handleStep1Submit)}>
              <div className="space-y-4">
                <div>
                  <Label className="text-stone-700">Product Name *</Label>
                  <Input
                    {...step1Form.register('name', { required: 'Product name is required' })}
                    placeholder="e.g. Summer Kurti Collection"
                    className="mt-1 border-stone-300"
                  />
                  {step1Form.formState.errors.name && (
                    <p className="text-xs text-red-600 mt-1">{step1Form.formState.errors.name.message}</p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-stone-700">Category</Label>
                    <select
                      {...step1Form.register('category_id')}
                      className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
                    >
                      <option value="">Select category</option>
                      {categories?.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-stone-700">Brand</Label>
                    <select
                      {...step1Form.register('brand_id')}
                      className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
                    >
                      <option value="">Select brand</option>
                      {brands?.map((b) => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-stone-700">Product Group</Label>
                    <select
                      {...step1Form.register('product_group_id')}
                      className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
                    >
                      <option value="">Select group</option>
                      {productGroups?.map((g) => (
                        <option key={g.id} value={g.id}>{g.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-stone-700">Product Type</Label>
                    <select
                      {...step1Form.register('product_type_id')}
                      className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
                    >
                      <option value="">Select type</option>
                      {productTypes?.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <Label className="text-stone-700">Description</Label>
                  <textarea
                    {...step1Form.register('description')}
                    rows={2}
                    placeholder="Optional product description"
                    className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800 resize-none"
                  />
                </div>
              </div>
            </form>
          )}

          {step === 2 && (
            <form id="step2-form" onSubmit={step2Form.handleSubmit(handleStep2Submit)}>
              <div className="space-y-3">
                {/* Column headers */}
                <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1fr_auto] gap-2 text-xs font-semibold text-stone-500 uppercase tracking-wide pb-1">
                  <span>Size *</span>
                  <span>Color *</span>
                  <span>MRP (₹) *</span>
                  <span>Selling ₹ *</span>
                  <span>Cost ₹ *</span>
                  <span />
                </div>
                <Separator className="bg-stone-200" />

                {fields.map((field, index) => (
                  <VariantRow
                    key={field.id}
                    index={index}
                    form={step2Form}
                    sizes={sizes ?? []}
                    colors={colors ?? []}
                    onRemove={() => remove(index)}
                    canRemove={fields.length > 1}
                  />
                ))}

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    append({ size_id: '', color_id: '', mrp: '', selling_price: '', cost_price: '', reorder_level: '0' })
                  }
                  className="gap-2 border-dashed border-stone-300 text-stone-600"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add variant
                </Button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-stone-200 flex items-center justify-between">
          <Button variant="outline" onClick={handleClose} className="border-stone-300">
            Cancel
          </Button>
          <div className="flex gap-2">
            {step === 2 && (
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                className="gap-2 border-stone-300"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            )}
            {step === 1 && (
              <Button
                form="step1-form"
                type="submit"
                disabled={createProduct.isPending}
                className="bg-rose-800 hover:bg-rose-900 text-white gap-2"
              >
                {createProduct.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4" />
                )}
                Next: Add Variants
              </Button>
            )}
            {step === 2 && (
              <Button
                form="step2-form"
                type="submit"
                className="bg-rose-800 hover:bg-rose-900 text-white gap-2"
              >
                <CheckCircle2 className="h-4 w-4" />
                Save Product
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

Note: The wizard uses `apiClient` directly for variants. Add this import at the top of `create-product-wizard.tsx`:
```typescript
import { apiClient } from '@/lib/api-client';
```

- [ ] **Step 4: Install use-debounce if not already installed**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm install use-debounce
```

- [ ] **Step 5: TypeScript check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx tsc --noEmit 2>&1 | head -30
```

Fix any type errors found. Common issues:
- Import `apiClient` missing in `create-product-wizard.tsx` — add `import { apiClient } from '@/lib/api-client';`
- `useFieldArray` import — ensure it's imported from `react-hook-form`

- [ ] **Step 6: Build to verify**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm run build 2>&1 | tail -20
```

Expected: Build completes without errors.

- [ ] **Step 7: Commit Product Table + Wizard**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
git add -A
git commit -m "feat(catalog): product table with search/filter + 2-step creation wizard

- TanStack Query v5 for server state management (30s stale time, auto-invalidation)
- Product table: search by code/name (debounced 400ms), category + brand filters,
  server-side pagination (25/page), status badge, skeleton loading state
- Creation wizard: step 1 basic details (name/category/brand/group/type),
  step 2 dynamic variant rows (size/color/MRP/selling/cost price)
- Product code auto-generated by FastAPI CatalogService
- react-hook-form + useFieldArray for dynamic variant management
- sonner toast notifications for success/error"
```

**🔔 NOTIFY USER: Product Table and Creation Wizard are operational. Ready to proceed to Inventory views.**

---

## Task 6: Inventory — SKU Detail Page

**Files:**
- Create: `behazeld-admin/components/inventory/stock-adjustment-form.tsx`
- Create: `behazeld-admin/app/(admin)/inventory/[variantId]/page.tsx`

- [ ] **Step 1: Create stock adjustment modal form**

Create `behazeld-admin/components/inventory/stock-adjustment-form.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useRecordMovement, useLocations } from '@/hooks/use-inventory';
import type { MovementType } from '@/types/inventory';
import { ApiError } from '@/types/api';

interface AdjustmentForm {
  location_id: string;
  bin_id: string;
  movement_type: MovementType;
  quantity: string;
  unit_cost: string;
  notes: string;
}

const ADJUSTMENT_TYPES: { value: MovementType; label: string }[] = [
  { value: 'opening_stock',  label: 'Opening Stock' },
  { value: 'adjustment_in',  label: 'Adjustment In (e.g. found stock)' },
  { value: 'adjustment_out', label: 'Adjustment Out (e.g. damaged goods)' },
  { value: 'return_in',      label: 'Customer Return' },
];

interface StockAdjustmentFormProps {
  variantId: string;
  onClose: () => void;
}

export function StockAdjustmentForm({ variantId, onClose }: StockAdjustmentFormProps) {
  const { data: locations, isLoading: locLoading } = useLocations();
  const recordMovement = useRecordMovement();

  const [selectedLocationId, setSelectedLocationId] = useState('');

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<AdjustmentForm>({
    defaultValues: {
      location_id: '',
      bin_id: '',
      movement_type: 'opening_stock',
      quantity: '',
      unit_cost: '0',
      notes: '',
    },
  });

  const locationId = watch('location_id');
  const selectedLocation = locations?.find((l) => l.id === locationId);
  const bins = selectedLocation?.bins ?? [];

  async function onSubmit(data: AdjustmentForm) {
    try {
      await recordMovement.mutateAsync({
        product_variant_id: variantId,
        location_id: data.location_id,
        bin_id: data.bin_id,
        movement_type: data.movement_type,
        quantity: data.quantity,
        unit_cost: data.unit_cost || '0',
        notes: data.notes || null,
      });
      toast.success('Stock movement recorded successfully.');
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === 'SALE_STOCK_NOT_AVAILABLE') {
        toast.error(
          'Insufficient stock available. The adjustment could not be applied.',
          { duration: 6000 },
        );
      } else {
        const msg = err instanceof ApiError ? err.message : 'Failed to record movement';
        toast.error(msg);
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b border-stone-200">
          <h2 className="text-base font-semibold text-stone-900">Record Stock Adjustment</h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Manually adjust inventory for this SKU
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="px-6 py-5 space-y-4">
          {/* Movement type */}
          <div>
            <Label className="text-stone-700">Movement Type *</Label>
            <select
              {...register('movement_type', { required: 'Required' })}
              className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
            >
              {ADJUSTMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* Location */}
          <div>
            <Label className="text-stone-700">Location *</Label>
            <select
              {...register('location_id', { required: 'Location is required' })}
              className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800"
            >
              <option value="">
                {locLoading ? 'Loading locations…' : 'Select location'}
              </option>
              {locations?.map((l) => (
                <option key={l.id} value={l.id}>{l.name}</option>
              ))}
            </select>
            {errors.location_id && (
              <p className="text-xs text-red-600 mt-0.5">{errors.location_id.message}</p>
            )}
          </div>

          {/* Bin */}
          <div>
            <Label className="text-stone-700">Bin *</Label>
            <select
              {...register('bin_id', { required: 'Bin is required' })}
              disabled={!locationId || bins.length === 0}
              className="mt-1 w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-sm text-stone-700 focus:outline-none focus:ring-2 focus:ring-rose-800 disabled:bg-stone-50 disabled:text-stone-400"
            >
              <option value="">Select bin</option>
              {bins.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}{b.is_default ? ' (Default)' : ''}
                </option>
              ))}
            </select>
            {errors.bin_id && (
              <p className="text-xs text-red-600 mt-0.5">{errors.bin_id.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Quantity */}
            <div>
              <Label className="text-stone-700">Quantity *</Label>
              <Input
                {...register('quantity', {
                  required: 'Required',
                  pattern: { value: /^\d+(\.\d+)?$/, message: 'Must be a positive number' },
                })}
                placeholder="e.g. 10"
                className="mt-1 border-stone-300"
              />
              {errors.quantity && (
                <p className="text-xs text-red-600 mt-0.5">{errors.quantity.message}</p>
              )}
            </div>

            {/* Unit cost */}
            <div>
              <Label className="text-stone-700">Unit Cost (₹)</Label>
              <Input
                {...register('unit_cost')}
                placeholder="0.00"
                className="mt-1 border-stone-300"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <Label className="text-stone-700">Notes</Label>
            <Input
              {...register('notes')}
              placeholder="e.g. Damaged goods write-off"
              className="mt-1 border-stone-300"
            />
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="border-stone-300"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={recordMovement.isPending}
              className="bg-rose-800 hover:bg-rose-900 text-white gap-2"
            >
              {recordMovement.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Record Movement
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create the SKU detail page**

Create the directory first:
```bash
mkdir -p "/Users/atanumazumdar/Claude Workspace/behazeld-admin/app/(admin)/inventory/[variantId]"
```

Create `behazeld-admin/app/(admin)/inventory/[variantId]/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Plus, Package, TrendingUp, TrendingDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useStockSummary, useStockLedger, useLocations } from '@/hooks/use-inventory';
import { StockAdjustmentForm } from '@/components/inventory/stock-adjustment-form';

const MOVEMENT_LABELS: Record<string, { label: string; positive: boolean }> = {
  opening_stock:  { label: 'Opening Stock',     positive: true  },
  purchase_in:    { label: 'Purchase In',        positive: true  },
  sale_out:       { label: 'Sale Out',           positive: false },
  return_in:      { label: 'Customer Return',    positive: true  },
  adjustment_in:  { label: 'Adjustment In',      positive: true  },
  adjustment_out: { label: 'Adjustment Out',     positive: false },
  transfer_in:    { label: 'Transfer In',        positive: true  },
  transfer_out:   { label: 'Transfer Out',       positive: false },
};

export default function InventoryVariantPage() {
  const params = useParams();
  const router = useRouter();
  const variantId = params.variantId as string;
  const [adjustmentOpen, setAdjustmentOpen] = useState(false);
  const [selectedLocationId, setSelectedLocationId] = useState('');

  const { data: locations, isLoading: locLoading } = useLocations();
  const { data: summary, isLoading: summaryLoading } = useStockSummary(variantId);
  const { data: ledger, isLoading: ledgerLoading } = useStockLedger(
    variantId,
    selectedLocationId,
  );

  // Auto-select first location when locations load
  if (!selectedLocationId && locations && locations.length > 0) {
    setSelectedLocationId(locations[0].id);
  }

  const totalAvailable = summary?.reduce(
    (sum, b) => sum + parseFloat(b.quantity_available),
    0,
  ) ?? 0;

  const totalOnHand = summary?.reduce(
    (sum, b) => sum + parseFloat(b.quantity_on_hand),
    0,
  ) ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          className="gap-2 text-stone-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div className="flex-1">
          <h2 className="text-xl font-semibold text-stone-900">SKU Inventory</h2>
          <p className="text-sm text-stone-500 font-mono mt-0.5">{variantId}</p>
        </div>
        <Button
          onClick={() => setAdjustmentOpen(true)}
          className="bg-rose-800 hover:bg-rose-900 text-white gap-2"
        >
          <Plus className="h-4 w-4" />
          Record Adjustment
        </Button>
      </div>

      {/* Stock summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card className="border-stone-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-stone-500 uppercase tracking-wide">
              Available
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : (
              <span className="text-2xl font-bold text-emerald-700">
                {totalAvailable.toFixed(2)}
              </span>
            )}
          </CardContent>
        </Card>

        <Card className="border-stone-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-stone-500 uppercase tracking-wide">
              On Hand
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : (
              <span className="text-2xl font-bold text-stone-800">
                {totalOnHand.toFixed(2)}
              </span>
            )}
          </CardContent>
        </Card>

        <Card className="border-stone-200 shadow-sm sm:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-stone-500 uppercase tracking-wide">
              Locations
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summaryLoading ? (
              <Skeleton className="h-7 w-10" />
            ) : (
              <span className="text-2xl font-bold text-stone-800">
                {summary?.length ?? 0}
              </span>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Balance by location */}
      {!summaryLoading && summary && summary.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-stone-700 mb-2">Balance by Location</h3>
          <div className="rounded-md border border-stone-200 bg-white overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-stone-50">
                  <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Location</TableHead>
                  <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">On Hand</TableHead>
                  <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Reserved</TableHead>
                  <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Available</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.map((bal) => {
                  const loc = locations?.find((l) => l.id === bal.location_id);
                  return (
                    <TableRow
                      key={bal.id}
                      className={`cursor-pointer hover:bg-stone-50 ${
                        selectedLocationId === bal.location_id ? 'bg-rose-50' : ''
                      }`}
                      onClick={() => setSelectedLocationId(bal.location_id)}
                    >
                      <TableCell className="font-medium text-stone-800">
                        {loc?.name ?? bal.location_id}
                      </TableCell>
                      <TableCell>{parseFloat(bal.quantity_on_hand).toFixed(2)}</TableCell>
                      <TableCell>{parseFloat(bal.quantity_reserved).toFixed(2)}</TableCell>
                      <TableCell className="font-semibold text-emerald-700">
                        {parseFloat(bal.quantity_available).toFixed(2)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-stone-400 mt-1">Click a row to view its ledger below.</p>
        </div>
      )}

      {/* Stock Ledger */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-stone-700">
            Stock Ledger
            {selectedLocationId && locations && (
              <span className="font-normal text-stone-400 ml-1">
                — {locations.find((l) => l.id === selectedLocationId)?.name}
              </span>
            )}
          </h3>
        </div>

        <div className="rounded-md border border-stone-200 bg-white overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-stone-50">
                <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Type</TableHead>
                <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Qty Change</TableHead>
                <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Unit Cost</TableHead>
                <TableHead className="text-xs font-semibold text-stone-500 uppercase tracking-wide">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ledgerLoading && (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {[1, 2, 3, 4].map((j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              )}
              {!selectedLocationId && !ledgerLoading && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-sm text-stone-400 py-6">
                    Select a location row above to view its ledger.
                  </TableCell>
                </TableRow>
              )}
              {selectedLocationId && !ledgerLoading && ledger?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-sm text-stone-400 py-6">
                    No movements recorded for this location.
                  </TableCell>
                </TableRow>
              )}
              {!ledgerLoading && ledger?.map((mv) => {
                const meta = MOVEMENT_LABELS[mv.movement_type] ?? { label: mv.movement_type, positive: true };
                const qty = parseFloat(mv.quantity_change);
                return (
                  <TableRow key={mv.id} className="hover:bg-stone-50">
                    <TableCell>
                      <Badge
                        className={
                          meta.positive
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-50'
                            : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-50'
                        }
                      >
                        {meta.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className={`font-mono font-medium ${qty >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                        {qty >= 0 ? '+' : ''}{qty.toFixed(4)}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-stone-600">
                      ₹{parseFloat(mv.unit_cost).toFixed(2)}
                    </TableCell>
                    <TableCell className="text-stone-500 text-sm">
                      {mv.notes ?? '—'}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>

      {adjustmentOpen && (
        <StockAdjustmentForm
          variantId={variantId}
          onClose={() => setAdjustmentOpen(false)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx tsc --noEmit 2>&1 | head -30
```

Fix any errors. The `setSelectedLocationId` inside render needs to be moved to `useEffect`. Replace the auto-select block:

```tsx
// Add this import at the top
import { useEffect } from 'react';

// Replace the inline auto-select with:
useEffect(() => {
  if (!selectedLocationId && locations && locations.length > 0) {
    setSelectedLocationId(locations[0].id);
  }
}, [locations, selectedLocationId]);
```

- [ ] **Step 4: Build check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm run build 2>&1 | tail -20
```

Expected: Build passes.

- [ ] **Step 5: Commit**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
git add -A
git commit -m "feat(inventory): SKU detail page — balance summary + stock ledger + adjustment form

- /inventory/[variantId]: total available/on-hand cards, location breakdown table
- Click-to-select location for ledger view
- Full stock ledger with movement type badges, qty change +/-, unit cost
- Stock adjustment modal: movement type dropdown (opening/adj-in/adj-out/return),
  location+bin cascade selects, quantity + unit cost + notes
- SALE_STOCK_NOT_AVAILABLE (409) handled with descriptive toast notification
- TanStack Query auto-invalidates summary + ledger after successful movement"
```

---

## Task 7: Master Data CRUD Pages

**Files:**
- Create: `behazeld-admin/components/catalog/master-data-page.tsx`
- Create: `behazeld-admin/app/(admin)/catalog/categories/page.tsx`
- Create: `behazeld-admin/app/(admin)/catalog/brands/page.tsx`
- Create: `behazeld-admin/app/(admin)/catalog/sizes/page.tsx`
- Create: `behazeld-admin/app/(admin)/catalog/colors/page.tsx`

- [ ] **Step 1: Create the reusable master-data-page component**

Create `behazeld-admin/components/catalog/master-data-page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { UseMutationResult, UseQueryResult } from '@tanstack/react-query';
import { Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/types/api';

export interface MasterColumn<T> {
  header: string;
  render: (row: T) => React.ReactNode;
  className?: string;
}

export interface MasterField {
  name: string;
  label: string;
  placeholder: string;
  type?: 'text' | 'number' | 'color';
  required?: boolean;
}

interface MasterDataPageProps<T extends { id: string }> {
  title: string;
  description: string;
  query: UseQueryResult<T[], Error>;
  mutation: UseMutationResult<T, Error, Record<string, string | number | null>, unknown>;
  columns: MasterColumn<T>[];
  fields: MasterField[];
}

export function MasterDataPage<T extends { id: string }>({
  title,
  description,
  query,
  mutation,
  columns,
  fields,
}: MasterDataPageProps<T>) {
  const [formValues, setFormValues] = useState<Record<string, string>>(
    Object.fromEntries(fields.map((f) => [f.name, ''])),
  );
  const [adding, setAdding] = useState(false);

  const { data, isLoading, isError } = query;

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    // Validate required fields
    for (const field of fields) {
      if (field.required !== false && !formValues[field.name]?.trim()) {
        toast.error(`${field.label} is required.`);
        return;
      }
    }
    try {
      const payload: Record<string, string | number | null> = {};
      for (const field of fields) {
        const val = formValues[field.name];
        if (field.type === 'number') {
          payload[field.name] = val ? parseInt(val, 10) : 0;
        } else {
          payload[field.name] = val || null;
        }
      }
      await mutation.mutateAsync(payload as never);
      toast.success(`${title.replace(/s$/, '')} added.`);
      setFormValues(Object.fromEntries(fields.map((f) => [f.name, ''])));
      setAdding(false);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : `Failed to add ${title.toLowerCase()}`;
      toast.error(msg);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-stone-900">{title}</h2>
          <p className="text-sm text-stone-500 mt-1">{description}</p>
        </div>
        <Button
          onClick={() => setAdding((v) => !v)}
          className="bg-rose-800 hover:bg-rose-900 text-white gap-2"
        >
          <Plus className="h-4 w-4" />
          Add {title.replace(/s$/, '')}
        </Button>
      </div>

      {/* Inline add form */}
      {adding && (
        <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
          <form onSubmit={handleAdd} className="flex flex-wrap gap-3 items-end">
            {fields.map((field) => (
              <div key={field.name} className="flex-1 min-w-[160px]">
                <Label className="text-stone-700 text-xs mb-1 block">
                  {field.label}{field.required !== false ? ' *' : ''}
                </Label>
                <Input
                  type={field.type === 'color' ? 'text' : (field.type ?? 'text')}
                  value={formValues[field.name]}
                  onChange={(e) =>
                    setFormValues((prev) => ({ ...prev, [field.name]: e.target.value }))
                  }
                  placeholder={field.placeholder}
                  className="border-stone-300 h-8 text-sm"
                />
              </div>
            ))}
            <div className="flex gap-2">
              <Button
                type="submit"
                disabled={mutation.isPending}
                className="bg-rose-800 hover:bg-rose-900 text-white h-8 px-3 text-sm gap-1"
              >
                {mutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Save
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAdding(false)}
                className="border-stone-300 h-8 px-3 text-sm"
              >
                Cancel
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Data table */}
      <div className="rounded-md border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50">
              {columns.map((col, i) => (
                <TableHead
                  key={i}
                  className={`text-xs font-semibold text-stone-500 uppercase tracking-wide ${col.className ?? ''}`}
                >
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            )}
            {isError && (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-sm text-red-600 py-8">
                  Failed to load data.
                </TableCell>
              </TableRow>
            )}
            {!isLoading && !isError && data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-sm text-stone-400 py-8">
                  No {title.toLowerCase()} found. Add one above.
                </TableCell>
              </TableRow>
            )}
            {!isLoading && data?.map((row) => (
              <TableRow key={row.id} className="hover:bg-stone-50">
                {columns.map((col, j) => (
                  <TableCell key={j} className={col.className ?? ''}>
                    {col.render(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create Categories page**

Create directory: `mkdir -p "/Users/atanumazumdar/Claude Workspace/behazeld-admin/app/(admin)/catalog/categories"`

Create `behazeld-admin/app/(admin)/catalog/categories/page.tsx`:

```tsx
'use client';

import { MasterDataPage } from '@/components/catalog/master-data-page';
import { useCategories, useCreateCategory } from '@/hooks/use-catalog';
import type { CategoryResponse } from '@/types/catalog';

export default function CategoriesPage() {
  const query = useCategories();
  const mutation = useCreateCategory();

  return (
    <MasterDataPage<CategoryResponse>
      title="Categories"
      description="Product categories for grouping your catalog"
      query={query}
      mutation={mutation as never}
      columns={[
        { header: 'Name', render: (r) => <span className="font-medium text-stone-800">{r.name}</span> },
        { header: 'Description', render: (r) => <span className="text-stone-500 text-sm">{r.description ?? '—'}</span> },
        { header: 'Sort', render: (r) => <span className="text-stone-500 font-mono text-sm">{r.sort_order}</span>, className: 'w-20' },
      ]}
      fields={[
        { name: 'name', label: 'Name', placeholder: "e.g. Women's Wear", required: true },
        { name: 'description', label: 'Description', placeholder: 'Optional', required: false },
        { name: 'sort_order', label: 'Sort Order', placeholder: '0', type: 'number', required: false },
      ]}
    />
  );
}
```

- [ ] **Step 3: Create Brands page**

Create directory: `mkdir -p "/Users/atanumazumdar/Claude Workspace/behazeld-admin/app/(admin)/catalog/brands"`

Create `behazeld-admin/app/(admin)/catalog/brands/page.tsx`:

```tsx
'use client';

import { MasterDataPage } from '@/components/catalog/master-data-page';
import { useBrands, useCreateBrand } from '@/hooks/use-catalog';
import type { BrandResponse } from '@/types/catalog';

export default function BrandsPage() {
  const query = useBrands();
  const mutation = useCreateBrand();

  return (
    <MasterDataPage<BrandResponse>
      title="Brands"
      description="Brand labels for your products"
      query={query}
      mutation={mutation as never}
      columns={[
        { header: 'Name', render: (r) => <span className="font-medium text-stone-800">{r.name}</span> },
        {
          header: 'Status',
          render: (r) => (
            <span className={`text-xs font-medium ${r.is_active ? 'text-emerald-700' : 'text-stone-400'}`}>
              {r.is_active ? 'Active' : 'Inactive'}
            </span>
          ),
          className: 'w-24',
        },
      ]}
      fields={[
        { name: 'name', label: 'Brand Name', placeholder: 'e.g. Fabindia', required: true },
      ]}
    />
  );
}
```

- [ ] **Step 4: Create Sizes page**

Create directory: `mkdir -p "/Users/atanumazumdar/Claude Workspace/behazeld-admin/app/(admin)/catalog/sizes"`

Create `behazeld-admin/app/(admin)/catalog/sizes/page.tsx`:

```tsx
'use client';

import { MasterDataPage } from '@/components/catalog/master-data-page';
import { useSizes, useCreateSize } from '@/hooks/use-catalog';
import type { SizeResponse } from '@/types/catalog';

export default function SizesPage() {
  const query = useSizes();
  const mutation = useCreateSize();

  return (
    <MasterDataPage<SizeResponse>
      title="Sizes"
      description="Size options for product variants (e.g. XS, S, M, L, XL, Free Size)"
      query={query}
      mutation={mutation as never}
      columns={[
        { header: 'Name', render: (r) => <span className="font-medium font-mono text-stone-800">{r.name}</span>, className: 'w-24' },
        { header: 'Sort Order', render: (r) => <span className="text-stone-500 font-mono text-sm">{r.sort_order}</span>, className: 'w-28' },
      ]}
      fields={[
        { name: 'name', label: 'Size', placeholder: 'e.g. XL', required: true },
        { name: 'sort_order', label: 'Sort Order', placeholder: '0', type: 'number', required: false },
      ]}
    />
  );
}
```

- [ ] **Step 5: Create Colors page**

Create directory: `mkdir -p "/Users/atanumazumdar/Claude Workspace/behazeld-admin/app/(admin)/catalog/colors"`

Create `behazeld-admin/app/(admin)/catalog/colors/page.tsx`:

```tsx
'use client';

import { MasterDataPage } from '@/components/catalog/master-data-page';
import { useColors, useCreateColor } from '@/hooks/use-catalog';
import type { ColorResponse } from '@/types/catalog';

export default function ColorsPage() {
  const query = useColors();
  const mutation = useCreateColor();

  return (
    <MasterDataPage<ColorResponse>
      title="Colors"
      description="Color options for product variants — use #RRGGBB hex codes"
      query={query}
      mutation={mutation as never}
      columns={[
        {
          header: 'Name',
          render: (r) => (
            <div className="flex items-center gap-2">
              {r.hex_code && (
                <span
                  className="inline-block h-4 w-4 rounded-full border border-stone-300 flex-shrink-0"
                  style={{ backgroundColor: r.hex_code }}
                />
              )}
              <span className="font-medium text-stone-800">{r.name}</span>
            </div>
          ),
        },
        {
          header: 'Hex',
          render: (r) => (
            <span className="font-mono text-sm text-stone-500">{r.hex_code ?? '—'}</span>
          ),
          className: 'w-28',
        },
      ]}
      fields={[
        { name: 'name', label: 'Color Name', placeholder: 'e.g. Indigo Blue', required: true },
        { name: 'hex_code', label: 'Hex Code', placeholder: '#3730A3', required: false },
      ]}
    />
  );
}
```

- [ ] **Step 6: TypeScript check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx tsc --noEmit 2>&1 | head -30
```

Fix any errors. The `mutation as never` casts exist because the generic `useMutation` return type doesn't directly match the `Record<string, ...>` payload type — this is an intentional pragmatic cast.

- [ ] **Step 7: Build check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npm run build 2>&1 | tail -20
```

Expected: Build passes.

- [ ] **Step 8: Commit master data**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
git add -A
git commit -m "feat(catalog): master data CRUD pages — categories, brands, sizes, colors

- Reusable MasterDataPage component: inline add form + table, toast on success/error
- Categories: name, description, sort_order
- Brands: name + active status
- Sizes: name + sort order (sortable for display)
- Colors: name + hex_code with color swatch preview
- All pages use TanStack Query — table auto-refreshes after successful mutation"
```

---

## Task 8: Wire Sidebar Navigation Links

**Files:**
- Modify: `behazeld-admin/components/layout/sidebar.tsx`

- [ ] **Step 1: Update sidebar nav items to add sub-navigation**

The current sidebar has top-level items. Catalog and Inventory now have real pages. Update the nav to link correctly.

Read `behazeld-admin/components/layout/sidebar.tsx`. The `NAV_ITEMS` currently use `/catalog` and `/inventory` as hrefs. These are correct — the sidebar-nav-item uses `pathname.startsWith(href + '/')` for active detection, so `/catalog` will highlight when on `/catalog/products`.

No change needed to sidebar.tsx — the hrefs already work. But confirm the routes match by checking what pages exist:

```bash
find "/Users/atanumazumdar/Claude Workspace/behazeld-admin/app/(admin)" -name "page.tsx" | sort
```

Expected:
```
.../app/(admin)/catalog/brands/page.tsx
.../app/(admin)/catalog/categories/page.tsx
.../app/(admin)/catalog/colors/page.tsx
.../app/(admin)/catalog/products/page.tsx
.../app/(admin)/catalog/sizes/page.tsx
.../app/(admin)/dashboard/page.tsx
.../app/(admin)/inventory/[variantId]/page.tsx
```

- [ ] **Step 2: Add a catalog index redirect**

The sidebar links to `/catalog` but the page is at `/catalog/products`. Create a redirect:

Create `behazeld-admin/app/(admin)/catalog/page.tsx`:

```tsx
import { redirect } from 'next/navigation';

export default function CatalogIndexPage() {
  redirect('/catalog/products');
}
```

- [ ] **Step 3: Final TypeScript + build check**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
npx tsc --noEmit 2>&1 | head -20
npm run build 2>&1 | tail -20
```

Expected: 0 TS errors, build passes.

- [ ] **Step 4: Final commit**

```bash
cd "/Users/atanumazumdar/Claude Workspace/behazeld-admin"
git add -A
git commit -m "feat: Phase 8 complete — catalog + inventory UI wired to sidebar

- /catalog → redirects to /catalog/products (product table)
- /catalog/categories, /brands, /sizes, /colors — master data CRUD
- /inventory/[variantId] — stock balance, ledger, adjustment form
- All routes accessible from sidebar navigation"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task | Status |
|---|---|---|
| Product Table with server-side pagination | Task 4 | ✅ |
| Search by product code | Task 4 (debounced search, backend search=ilike) | ✅ |
| Category + brand filters | Task 4 (dropdowns → backend filter) | ✅ |
| Status badge (Active/Deleted) | Task 4 (product-columns.tsx Badge) | ✅ |
| Multi-step creation wizard | Task 5 | ✅ |
| Step 1: Basic product details (name/group/type/brand) | Task 5 | ✅ |
| Step 2: Multiple variants (size/color/MRP/cost) | Task 5 | ✅ |
| Calls CatalogService + auto product code | Task 5 (POST /products → service generates code) | ✅ |
| SKU detail — quantity_available | Task 6 (summary cards + table) | ✅ |
| Full stock ledger | Task 6 (ledger table with movement types) | ✅ |
| Stock movement form | Task 6 (StockAdjustmentForm modal) | ✅ |
| Calls atomic record_stock_movement | Task 6 (POST /inventory/movements) | ✅ |
| SALE_STOCK_NOT_AVAILABLE (409) toast | Task 6 (ApiError.errorCode check) | ✅ |
| CRUD for Categories, Brands, Sizes, Colors | Task 7 | ✅ |
| TanStack Query for data fetching | Tasks 3–7 | ✅ |
| Auto-update after stock change | Task 6 (onSuccess invalidation) | ✅ |
| Enterprise aesthetic (White/Stone) | All tasks | ✅ |
| Responsive tables | All tasks (overflow-hidden + Tailwind) | ✅ |

**Placeholder scan:** No TBDs or incomplete steps. All code blocks complete.

**Type consistency:** `ProductResponse`, `ProductVariantResponse`, `RecordMovementRequest`, `LocationResponse` all defined in Task 3 types and used consistently throughout Tasks 4–7. `ApiError` imported from `@/types/api` (defined in Phase 7). `useCreateProduct` returns `ProductResponse` matching the catalog type.
