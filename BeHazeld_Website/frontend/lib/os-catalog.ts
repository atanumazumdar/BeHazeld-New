import type { Collection } from "@/types/collection";
import type { Product, ProductDetail, ProductImage, ProductVariant } from "@/types/product";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/$/, "").replace(/\/api$/, "");

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID;
const IS_LOCAL_DEV = process.env.NODE_ENV !== "production";
const DEFAULT_PRODUCT_LIMIT = IS_LOCAL_DEV ? 24 : 100;
const PRODUCT_LIMIT = Math.min(
  200,
  Math.max(
    1,
    Number(process.env.NEXT_PUBLIC_CATALOG_PRODUCT_LIMIT ?? DEFAULT_PRODUCT_LIMIT),
  ),
);

const UUID_PATTERN =
  /[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i;

type OsVariant = {
  id: string;
  sku_code: string;
  size_id?: string;
  size_name?: string;
  color_id?: string;
  color_name?: string;
  color_hex_code?: string | null;
  fabric?: string | null;
  image_url: string | null;
  mrp: string;
  selling_price: string;
  stock_count?: string | number;
  is_available?: boolean;
  status: string;
};

type OsProduct = {
  id: string;
  category_id?: string | null;
  product_group_id?: string | null;
  product_type_id?: string | null;
  brand_id?: string | null;
  product_code: string;
  name: string;
  description: string | null;
  image_url: string | null;
  status: string;
  variants: OsVariant[];
};

type OsProductsResponse = {
  total: number;
  skip: number;
  limit: number;
  items: OsProduct[];
};

type OsCategory = {
  id: string;
  name: string;
  description: string | null;
  sort_order: number;
};

function publicUrl(path: string): string | null {
  if (!TENANT_ID) return null;
  return `${API_BASE_URL}/api/v1/public/${TENANT_ID}${path}`;
}

export function storefrontCatalogConfigured(): boolean {
  return Boolean(TENANT_ID);
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function productIdFromSlug(slug: string): string | null {
  const match = slug.match(UUID_PATTERN);
  return match?.[0] ?? null;
}

function productSlug(product: Pick<OsProduct, "id" | "name" | "product_code">): string {
  const base = slugify(product.name || product.product_code || "product");
  return `${base}-${product.id}`;
}

function imageFromUrl(
  id: string,
  url: string | null,
  altText: string,
  displayOrder = 0,
): ProductImage | null {
  if (!url) return null;
  return {
    id,
    url,
    alt_text: altText,
    display_order: displayOrder,
    is_primary: displayOrder === 0,
    transform_urls: {
      card: url,
      detail: url,
      hero: url,
      original: url,
    },
  };
}

const COLOR_NAMES: Record<string, string> = {
  BLK: "Black",
  BLU: "Blue",
  GLD: "Gold",
  GLDN: "Gold",
  GRN: "Green",
  IVR: "Ivory",
  NVY: "Navy",
  PCH: "Peach",
  PNK: "Pink",
  PST: "Pistachio",
  RED: "Red",
  SLV: "Silver",
  SLVR: "Silver",
  WHT: "White",
};

function parseVariantMeta(skuCode: string): { color: string; size: string } {
  const parts = skuCode.split("-").filter(Boolean);
  const size = parts.at(-1) ?? "One Size";
  const colorCode = parts.at(-2) ?? "";
  const colorName = COLOR_NAMES[colorCode.toUpperCase()] ?? colorCode;
  return {
    color: colorName || "Default",
    size,
  };
}

function adaptVariant(variant: OsVariant, basePrice: number): ProductVariant {
  const fallback = parseVariantMeta(variant.sku_code);
  const sellingPrice = Number(variant.selling_price || 0);
  const stockCount = Math.max(0, Math.floor(Number(variant.stock_count ?? 0)));
  return {
    id: variant.id,
    sku: variant.sku_code,
    color: variant.color_name || fallback.color,
    color_hex_code: variant.color_hex_code ?? null,
    size: variant.size_name || fallback.size,
    fabric: variant.fabric ?? null,
    image_url: variant.image_url,
    mrp: String(variant.mrp ?? sellingPrice.toFixed(2)),
    selling_price: sellingPrice.toFixed(2),
    price_adjustment: (sellingPrice - basePrice).toFixed(2),
    stock_count: stockCount,
    is_available: variant.status === "active" && Boolean(variant.is_available) && stockCount > 0,
  };
}

export function adaptProduct(product: OsProduct): Product {
  const activeVariants = product.variants.filter((variant) => variant.status === "active");
  const variantPrices = activeVariants.map((variant) => Number(variant.selling_price || 0));
  const basePrice = variantPrices.length > 0 ? Math.min(...variantPrices) : 0;
  const primaryImage =
    imageFromUrl(`${product.id}:product`, product.image_url, product.name) ??
    imageFromUrl(
      `${product.id}:variant`,
      activeVariants.find((variant) => variant.image_url)?.image_url ?? null,
      product.name,
    );

  const variants = activeVariants.map((variant) => adaptVariant(variant, basePrice));

  return {
    id: product.id,
    product_code: product.product_code,
    name: product.name,
    slug: productSlug(product),
    description: product.description ?? "",
    base_price: basePrice.toFixed(2),
    is_active: product.status === "active",
    created_at: "",
    collection_id: product.category_id ?? null,
    product_group_id: product.product_group_id ?? null,
    product_type_id: product.product_type_id ?? null,
    brand_id: product.brand_id ?? null,
    primary_image: primaryImage,
    secondary_image: null,
    variants,
    min_price: basePrice.toFixed(2),
    total_stock: variants.reduce((total, variant) => total + variant.stock_count, 0),
  };
}

export function adaptProductDetail(product: OsProduct): ProductDetail {
  const adapted = adaptProduct(product);
  const images = [
    adapted.primary_image,
    ...product.variants.map((variant, index) =>
      imageFromUrl(variant.id, variant.image_url, product.name, index + 1),
    ),
  ].filter((image): image is ProductImage => Boolean(image));

  const uniqueImages = Array.from(
    new Map(images.map((image) => [image.url, image])).values(),
  );

  return {
    ...adapted,
    images: uniqueImages,
  };
}

export function adaptCategory(category: OsCategory): Collection {
  return {
    id: category.id,
    name: category.name,
    slug: slugify(category.name),
    description: category.description ?? "",
    hero_image_url: null,
    display_order: category.sort_order,
    is_active: true,
    created_at: "",
  };
}

export async function fetchPublicProducts(
  options: { categoryId?: string; search?: string; limit?: number } = {},
): Promise<OsProduct[]> {
  const url = publicUrl("/products");
  if (!url) return [];

  const limit = Math.min(200, Math.max(1, options.limit ?? PRODUCT_LIMIT));
  const params = new URLSearchParams({ limit: String(limit) });
  if (options.categoryId) params.set("category_id", options.categoryId);
  if (options.search) params.set("search", options.search);

  const res = await fetch(`${url}?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Public products API returned ${res.status}`);

  const data = (await res.json()) as OsProductsResponse;
  return data.items ?? [];
}

export async function fetchPublicProduct(productId: string): Promise<OsProduct | null> {
  const url = publicUrl(`/products/${productId}`);
  if (!url) return null;

  const res = await fetch(url, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Public product API returned ${res.status}`);
  return res.json();
}

export async function fetchPublicCategories(): Promise<OsCategory[]> {
  const url = publicUrl("/categories");
  if (!url) return [];

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}
