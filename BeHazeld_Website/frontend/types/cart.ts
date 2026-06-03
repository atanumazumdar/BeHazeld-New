import type { Product, ProductVariant } from "@/types/product";

// ── Cart item (persisted in localStorage via Zustand) ─────────────
export type CartItem = {
  productId: string;
  variantId: string | null;   // null for legacy items added without variant
  sku:       string;
  slug:      string;
  name:      string;
  imageUrl:  string;
  price:     string;          // effective unit price at time of add
  color:     string;
  size:      string;
  quantity:  number;
};

// ── What AddToCartButton needs to call addItem ─────────────────────
export type AddToCartInput = {
  product: Pick<Product, "id" | "slug" | "name" | "primary_image">;
  variant: Pick<ProductVariant, "id" | "sku" | "color" | "size" | "price_adjustment"> & {
    effectivePrice: string; // base_price + price_adjustment, formatted
  };
};
