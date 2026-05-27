import type { Product, ProductDetail } from "@/types/product";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ProductLoadError extends Error {
  constructor(message = "Unable to load products") {
    super(message);
    this.name = "ProductLoadError";
  }
}

/**
 * Fetch all active products (with primary_image + variants).
 * Pass `collection` slug to filter by collection.
 */
export async function getProducts(
  collection?: string,
): Promise<Product[]> {
  try {
    const url = collection
      ? `${API_BASE_URL}/products/?collection=${encodeURIComponent(collection)}`
      : `${API_BASE_URL}/products/`;

    const res = await fetch(url, { next: { revalidate: 60 } });

    if (!res.ok) {
      throw new ProductLoadError(
        `Unable to load products: API returned ${res.status}`,
      );
    }

    return res.json();
  } catch (err) {
    if (err instanceof ProductLoadError) throw err;
    throw new ProductLoadError("Backend offline: unable to load products");
  }
}

/**
 * Fetch a single product by slug — full detail with images[] + variants[].
 */
export async function getProduct(slug: string): Promise<ProductDetail | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/products/${slug}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
