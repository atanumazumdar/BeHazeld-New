import { ProductCard } from "@/components/product/ProductCard";
import type { Product } from "@/types/product";

type ProductGridProps = {
  products: Product[];
  error?: string;
};

export function ProductGrid({ products, error }: ProductGridProps) {
  if (error) {
    return (
      <div
        style={{
          border: "1px solid rgba(140,100,30,0.25)",
          background: "rgba(255,252,248,0.5)",
          padding: "48px 20px",
          textAlign: "center",
        }}
      >
        <h2 className="font-serif font-light italic" style={{ fontSize: 22, color: "#3A2810" }}>
          Unable to load products
        </h2>
        <p style={{ marginTop: 8, fontSize: 13, color: "rgba(90,60,20,0.65)", lineHeight: 1.7 }}>
          {error}
        </p>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div
        style={{
          border: "1px solid rgba(140,100,30,0.2)",
          background: "rgba(255,252,248,0.4)",
          padding: "48px 20px",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: 13, color: "rgba(90,60,20,0.6)" }}>No products available yet.</p>
      </div>
    );
  }

  return (
    /* Fixed 4-column grid — each product image box is 350 × 450 px. */
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 350px)",
        gap: 0,
        border: "1px solid rgba(140,100,30,0.2)",
        overflowX: "auto",
        width: 1400,
        maxWidth: "none",
      }}
    >
      {products.map((product, index) => (
        <div
          key={product.id}
          style={{ width: 350, borderRight: "1px solid rgba(140,100,30,0.2)" }}
        >
          {/* index passed so placeholder shows "Pic 1", "Pic 2" … */}
          <ProductCard product={product} index={index} />
        </div>
      ))}
    </div>
  );
}
