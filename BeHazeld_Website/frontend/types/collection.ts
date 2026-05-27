import type { Product } from "@/types/product";

// ── Collection (summary — for nav and listing) ─────────────────────
export type Collection = {
  id:            number;
  name:          string;
  slug:          string;
  description:   string;
  hero_image_url: string | null;
  display_order: number;
  is_active:     boolean;
  created_at:    string;
};

// ── Collection with its active products ────────────────────────────
// Returned by GET /collections/{slug}.
// This is the data shape the frontend collection page consumes:
// adding a Product row with this collection_id in the DB is the only
// step needed to make it appear here — no TSX changes required.
export type CollectionWithProducts = Collection & {
  products: Product[];
};
