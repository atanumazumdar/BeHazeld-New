import type { Collection, CollectionWithProducts } from "@/types/collection";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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
    const res = await fetch(`${API_BASE_URL}/collections/`, {
      next: { revalidate: 60 },   // ISR — re-fetch at most once per minute
    });
    if (!res.ok) return [];
    return res.json();
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
    const res = await fetch(`${API_BASE_URL}/collections/${slug}`, {
      next: { revalidate: 60 },
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new CollectionLoadError(`API returned ${res.status}`);
    return res.json();
  } catch {
    return null;
  }
}
