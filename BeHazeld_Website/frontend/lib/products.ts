import type { Product, ProductDetail } from "@/types/product";
import {
  adaptProduct,
  adaptProductDetail,
  fetchPublicCategories,
  fetchPublicProduct,
  fetchPublicProducts,
  productIdFromSlug,
  slugify,
} from "@/lib/os-catalog";

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
    let categoryId: string | undefined;
    if (collection) {
      const categories = await fetchPublicCategories();
      const category = categories.find((item) => slugify(item.name) === collection);
      if (!category) return [];
      categoryId = category.id;
    }

    const products = await fetchPublicProducts({ categoryId });
    return products.map(adaptProduct);
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
    const productId = productIdFromSlug(slug);
    if (!productId) return null;

    const product = await fetchPublicProduct(productId);
    return product ? adaptProductDetail(product) : null;
  } catch {
    return null;
  }
}
