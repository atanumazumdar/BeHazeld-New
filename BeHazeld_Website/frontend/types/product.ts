// ── Image ──────────────────────────────────────────────────────────
export type TransformUrls = {
  card:     string;   // 400×533  — product grid card
  detail:   string;   // 900×1200 — product detail hero
  hero:     string;   // 1440×600 — collection banner
  original: string;   // full quality
};

export type ProductImage = {
  id:             string;
  url:            string;
  alt_text:       string;
  display_order:  number;
  is_primary:     boolean;
  transform_urls: TransformUrls;
};

// ── Variant ────────────────────────────────────────────────────────
export type ProductVariant = {
  id:               string;
  sku:              string;
  color:            string;
  color_hex_code:   string | null;
  size:             string;
  fabric:           string | null;
  image_url:        string | null;
  mrp:              string;
  selling_price:    string;
  price_adjustment: string;   // Decimal serialised as string
  stock_count:      number;
  is_available:     boolean;
};

// ── Product (listing view — includes primary_image + variants) ─────
export type Product = {
  id:            string;
  product_code:  string;
  name:          string;
  slug:          string;
  description:   string;
  base_price:    string;    // Decimal as string
  is_active:     boolean;
  created_at:    string;
  collection_id: string | null;
  collection_name: string | null;
  product_group_id: string | null;
  product_group_name: string | null;
  product_type_id: string | null;
  brand_id: string | null;

  primary_image:   ProductImage | null;
  secondary_image: ProductImage | null;
  variants:        ProductVariant[];

  // Computed by the backend @property helpers
  min_price:   string;
  total_stock: number;
};

// ── Product (detail view — adds the full image gallery) ────────────
export type ProductDetail = Product & {
  images: ProductImage[];
};

// ── Pure helper functions (no React imports needed) ────────────────

/** Return the first available variant, or null. */
export function firstAvailableVariant(
  product: Pick<Product, "variants">,
): ProductVariant | null {
  return product.variants.find((v) => v.is_available && v.stock_count > 0) ?? null;
}

/** Final price for a variant: base_price + price_adjustment */
export function variantPrice(
  product: Pick<Product, "base_price">,
  variant: Pick<ProductVariant, "price_adjustment">,
): number {
  return Number(product.base_price) + Number(variant.price_adjustment);
}

/** Best card image URL: Cloudinary card transform → url → empty string */
export function cardImageUrl(product: Pick<Product, "primary_image">): string {
  if (!product.primary_image) return "";
  return product.primary_image.transform_urls?.card || product.primary_image.url;
}
