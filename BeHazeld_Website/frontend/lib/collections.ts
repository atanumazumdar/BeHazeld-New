import type { Collection, CollectionWithProducts } from "@/types/collection";
import {
  adaptCategory,
  adaptProduct,
  fetchAllPublicProducts,
  fetchPublicCategories,
  fetchPublicProductGroups,
  slugify,
} from "@/lib/os-catalog";

export class CollectionLoadError extends Error {
  constructor(message = "Unable to load collection") {
    super(message);
    this.name = "CollectionLoadError";
  }
}

type StorefrontCollectionDefinition = {
  name: string;
};

const STOREFRONT_COLLECTIONS: Record<string, StorefrontCollectionDefinition> = {
  "campus-muse": { name: "Campus Muse" },
  "power-edit": { name: "Power Edit" },
  "afterglow-evenings": { name: "Afterglow Evenings" },
  "ultra-luxe": { name: "Ultra Luxe" },
  accessories: { name: "Accessories" },
  "pre-loved": { name: "Pre Loved" },
};

function storefrontCollection(slug: string): Collection {
  const definition = STOREFRONT_COLLECTIONS[slug];
  const name =
    definition?.name ??
    slug
      .split("-")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");

  return {
    id: slug,
    name,
    slug,
    description: "",
    hero_image_url: null,
    display_order: 0,
    is_active: true,
    created_at: "",
  };
}

function isStockedProduct(product: ReturnType<typeof adaptProduct>): boolean {
  return product.total_stock > 0 && product.variants.some((variant) => variant.is_available);
}

function productMatchesCollection(product: ReturnType<typeof adaptProduct>, slug: string): boolean {
  const definition = STOREFRONT_COLLECTIONS[slug];
  if (!definition) return false;
  const targetSlug = slugify(definition.name);
  return [product.collection_name, product.product_group_name]
    .filter((value): value is string => Boolean(value))
    .some((value) => slugify(value) === targetSlug);
}

export async function getCollections(): Promise<Collection[]> {
  try {
    const [categories, productGroups] = await Promise.all([
      fetchPublicCategories(),
      fetchPublicProductGroups(),
    ]);
    const osCategories = categories.map(adaptCategory);
    const osProductGroups = productGroups.map((group) => ({
      id: group.id,
      name: group.name,
      slug: slugify(group.name),
      description: group.description ?? "",
      hero_image_url: null,
      display_order: 0,
      is_active: true,
      created_at: "",
    }));
    const storefrontSections = Object.keys(STOREFRONT_COLLECTIONS).map(storefrontCollection);

    const bySlug = new Map<string, Collection>();
    for (const collection of [...storefrontSections, ...osCategories, ...osProductGroups]) {
      bySlug.set(collection.slug, collection);
    }

    return Array.from(bySlug.values()).sort((a, b) => a.display_order - b.display_order);
  } catch {
    return Object.keys(STOREFRONT_COLLECTIONS).map(storefrontCollection);
  }
}

export async function getCollection(
  slug: string,
): Promise<CollectionWithProducts | null> {
  try {
    const categories = await fetchPublicCategories();
    const category = categories.find((item) => slugify(item.name) === slug);

    if (category) {
      const products = await fetchAllPublicProducts({ categoryId: category.id, pageSize: 100 });
      return {
        ...adaptCategory(category),
        products: products.map(adaptProduct).filter(isStockedProduct),
      };
    }

    const products = await fetchAllPublicProducts({ pageSize: 100 });
    const matchedProducts = products
      .map(adaptProduct)
      .filter((product) => isStockedProduct(product) && productMatchesCollection(product, slug));

    if (!STOREFRONT_COLLECTIONS[slug] && matchedProducts.length === 0) return null;

    return {
      ...storefrontCollection(slug),
      products: matchedProducts,
    };
  } catch {
    return null;
  }
}
