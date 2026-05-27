/**
 * Catalog domain types — mirrors FastAPI Pydantic schemas.
 */

export interface CategoryResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  sort_order: number;
}

export interface ProductGroupResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
}

export interface ProductTypeResponse {
  id: string;
  tenant_id: string;
  name: string;
}

export interface BrandResponse {
  id: string;
  tenant_id: string;
  name: string;
}

export interface SizeResponse {
  id: string;
  tenant_id: string;
  name: string;
  sort_order: number;
}

export interface ColorResponse {
  id: string;
  tenant_id: string;
  name: string;
  hex_code: string | null;
}

export interface ProductVariantResponse {
  id: string;
  tenant_id: string;
  product_id: string;
  sku_code: string;
  size_id: string;
  color_id: string;
  mrp: string;            // Decimal serialised as string
  selling_price: string;
  cost_price: string | null;
  fabric: string | null;
  reorder_level: string;
  status: string;
}

export interface ProductResponse {
  id: string;
  tenant_id: string;
  product_code: string;
  name: string;
  status: string;
  description: string | null;
  image_url: string | null;
  category_id: string | null;
  product_group_id: string | null;
  product_type_id: string | null;
  brand_id: string | null;
  variants?: ProductVariantResponse[];
}

// ── Request payloads ──────────────────────────────────────────────────────────

export interface CreateProductPayload {
  name: string;
  category_id: string | null;
  product_group_id: string | null;
  product_type_id: string | null;
  brand_id: string | null;
  description: string | null;
  image_url: string | null;
}

export interface CreateVariantPayload {
  size_id: string;
  color_id: string;
  mrp: string;
  selling_price: string;
  cost_price: string;
  fabric: string | null;
  reorder_level: string;
}

export interface CreateMasterPayload {
  name: string;
}

export interface CreateCategoryPayload {
  name: string;
  description: string | null;
  sort_order: number;
}

export interface CreateColorPayload {
  name: string;
  hex_code: string | null;
}

export interface CreateSizePayload {
  name: string;
  sort_order: number;
}
