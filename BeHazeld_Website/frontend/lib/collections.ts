import type { Collection, CollectionWithProducts } from "@/types/collection";
import {
  adaptCategory,
  adaptProduct,
  fetchPublicCategories,
  fetchPublicProducts,
  slugify,
} from "@/lib/os-catalog";

export class CollectionLoadError extends Error {
  constructor(message = "Unable to load collection") {
    super(message);
    this.name = "CollectionLoadError";
  }
}

/**
 * Fetch all active collections (used for nav + generateStaticParams).
 * Returns an empty array if the backend is unreachable — safe for build time.
 */
export async function getCollections(): Promise<Collection[]> {
  try {
    const categories = await fetchPublicCategories();
    return categories.map(adaptCategory);
  } catch {
    return [];
  }
}

/**
 * Fetch a single collection with all its active products (images + variants).
 * Returns null if not found or backend is unreachable.
 *
 * Adding a product to the DB with this collection's id is the *only*
 * step needed to make it appear on the page — no TSX changes required.
 */
export async function getCollection(
  slug: string,
): Promise<CollectionWithProducts | null> {
  try {
    const categories = await fetchPublicCategories();
    const category = categories.find((item) => slugify(item.name) === slug);
    if (!category) return null;

    const products = await fetchPublicProducts({ categoryId: category.id });
    return {
      ...adaptCategory(category),
      products: products.map(adaptProduct),
    };
  } catch {
    return null;
  }
}
