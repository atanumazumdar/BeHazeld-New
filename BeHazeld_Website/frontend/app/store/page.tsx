import { ProductGrid } from "@/components/product/ProductGrid";
import { getProducts, ProductLoadError } from "@/lib/products";
import type { Product } from "@/types/product";

export default async function StorePage() {
  let products: Product[] = [];
  let error: string | undefined;

  try {
    products = await getProducts();
  } catch (caughtError) {
    error =
      caughtError instanceof ProductLoadError
        ? caughtError.message
        : "Backend offline: unable to load products";
  }

  return (
    <main>
      <section
        className="mx-auto max-w-7xl px-5 sm:px-6 lg:px-8"
        style={{ paddingTop: 80, paddingBottom: 80 }}
      >
        {/* Header */}
        <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p
              className="font-sans font-normal uppercase"
              style={{ fontSize: 9, letterSpacing: "0.5em", color: "#C09330", marginBottom: 14 }}
            >
              Handcrafted · Heirloom · Couture
            </p>
            <h1
              className="font-display font-light italic leading-tight"
              style={{ fontSize: "clamp(36px, 4.5vw, 64px)", color: "rgba(248,240,232,0.92)" }}
            >
              The Collection
            </h1>
          </div>

          <div className="flex flex-col gap-2 text-right">
            <p
              className="font-sans font-light"
              style={{ fontSize: 13, color: "rgba(177,152,112,0.75)", letterSpacing: "0.02em" }}
            >
              Each product Handpicked from the largest Chikankari market in the world · 4–6 weeks
            </p>
            <a
              href="/atelier"
              className="font-sans font-light uppercase self-start sm:self-end"
              style={{ fontSize: 9, letterSpacing: "0.36em", color: "#C09330" }}
            >
              ← The Atelier
            </a>
          </div>
        </div>

        {/* Gold divider */}
        <div className="flex items-center gap-3 mb-10">
          <div
            className="h-px flex-1"
            style={{ background: "linear-gradient(to right, #C09330, rgba(192,147,48,0.08))" }}
          />
          <svg width="5" height="5" viewBox="0 0 6 6">
            <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
          </svg>
        </div>

        <ProductGrid products={products} error={error} />
      </section>
    </main>
  );
}
