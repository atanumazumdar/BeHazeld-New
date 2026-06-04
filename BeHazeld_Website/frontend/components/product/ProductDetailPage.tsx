"use client";

import { useState } from "react";
import { AddToCartButton } from "@/components/cart/AddToCartButton";
import { formatCurrency } from "@/lib/format";
import type { ProductDetail, ProductVariant } from "@/types/product";
import { firstAvailableVariant, variantPrice } from "@/types/product";

export function ProductDetailPage({ product }: { product: ProductDetail }) {
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(
    () => firstAvailableVariant(product),
  );

  const colors = [...new Set(product.variants.map((v) => v.color))];
  const activeColor = selectedVariant?.color ?? colors[0];
  const sizesForColor = (c: string) =>
    product.variants.filter((v) => v.color === c);

  const displayPrice = selectedVariant
    ? variantPrice(product, selectedVariant)
    : Number(product.min_price);
  const displayMrp = Number(selectedVariant?.mrp ?? displayPrice);
  const hasMarkdown = selectedVariant ? displayMrp > displayPrice : false;

  const heroImage = selectedVariant?.image_url
    ?? product.primary_image?.transform_urls?.detail
    ?? product.primary_image?.url
    ?? "";

  return (
    <main>
      <section
        className="mx-auto grid max-w-7xl gap-10 px-5 py-10 sm:px-6 lg:px-8"
        style={{ gridTemplateColumns: "minmax(0,1fr) 420px" }}
      >
        {/* ── Image gallery ──────────────────────────────────── */}
        <div className="relative overflow-hidden border border-border bg-[var(--hazel)]">
          {heroImage ? (
            <img
              src={heroImage}
              alt={product.primary_image?.alt_text ?? product.name}
              className="aspect-[3/4] h-full w-full object-cover object-top"
            />
          ) : (
            <div
              className="aspect-[3/4] flex items-center justify-center"
              style={{ background: "linear-gradient(145deg,#1A0E08,#3D2314)" }}
            >
              <span className="font-display font-light italic" style={{ fontSize: 80, color: "rgba(192,147,48,0.2)" }}>H</span>
            </div>
          )}
          <div className="absolute inset-4 border border-[rgba(192,147,48,0.2)]" />

          {/* Thumbnail strip for multiple images */}
          {product.images.length > 1 && (
            <div className="absolute bottom-4 left-4 right-4 flex gap-2">
              {product.images.map((img) => (
                <div
                  key={img.id}
                  className="h-16 w-12 overflow-hidden border border-[rgba(192,147,48,0.4)] cursor-pointer"
                >
                  <img
                    src={img.transform_urls?.card ?? img.url}
                    alt={img.alt_text}
                    className="h-full w-full object-cover object-top"
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Product info aside ────────────────────────────── */}
        <aside className="glass-panel h-fit p-6 lg:sticky lg:top-24">
          <p className="text-[10px] font-light uppercase tracking-[0.42em]" style={{ color: "#C09330" }}>
            {product.product_code}
          </p>
          <h1 className="font-serif mt-3 text-4xl font-light italic leading-tight" style={{ color: "rgba(248,240,232,0.92)" }}>
            {product.name}
          </h1>
          <div className="mt-4 flex items-baseline gap-3">
            <p className="font-display text-3xl font-normal" style={{ color: "#C09330" }}>
              {formatCurrency(displayPrice)}
            </p>
            {hasMarkdown && (
              <p className="font-display text-lg font-light line-through" style={{ color: "rgba(177,152,112,0.58)" }}>
                {formatCurrency(displayMrp)}
              </p>
            )}
          </div>

          <div className="my-6 flex w-40 items-center gap-3">
            <span className="h-px flex-1" style={{ background: "linear-gradient(to right, #C09330, rgba(192,147,48,0.2))" }} />
            <span className="h-1.5 w-1.5 rotate-45 bg-[#C09330]" />
          </div>

          <p className="text-sm font-light leading-7" style={{ color: "rgba(177,152,112,0.82)" }}>
            {product.description}
          </p>

          {/* ── Variant selection ──────────────────────────── */}
          {product.variants.length > 0 && (
            <div className="mt-6 space-y-4">
              {/* Colour */}
              {colors.length > 1 && (
                <div>
                  <p className="text-[9px] font-light uppercase tracking-[0.38em] mb-2" style={{ color: "rgba(177,152,112,0.7)" }}>
                    Colour — {activeColor}
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {colors.map((color) => (
                      <button
                        key={color}
                        type="button"
                        onClick={() => {
                          const first = sizesForColor(color)[0];
                          if (first) setSelectedVariant(first);
                        }}
                        className="text-[9px] font-light uppercase tracking-[0.28em] px-3 py-1.5 transition-colors cursor-pointer"
                        style={{
                          border:  `1px solid ${color === activeColor ? "#C09330" : "rgba(192,147,48,0.3)"}`,
                          color:   color === activeColor ? "#C09330" : "rgba(177,152,112,0.7)",
                          background: color === activeColor ? "rgba(192,147,48,0.1)" : "transparent",
                        }}
                      >
                        <span
                          aria-hidden="true"
                          className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                          style={{
                            background: product.variants.find((v) => v.color === color)?.color_hex_code ?? "transparent",
                            border: "1px solid rgba(192,147,48,0.4)",
                          }}
                        />
                        {color}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Size */}
              <div>
                <p className="text-[9px] font-light uppercase tracking-[0.38em] mb-2" style={{ color: "rgba(177,152,112,0.7)" }}>
                  Size{selectedVariant ? ` — ${selectedVariant.size}` : ""}
                </p>
                <div className="flex gap-2 flex-wrap">
                  {sizesForColor(activeColor).map((variant) => {
                    const isSel = selectedVariant?.id === variant.id;
                    return (
                      <button
                        key={variant.id}
                        type="button"
                        onClick={() => setSelectedVariant(variant)}
                        disabled={!variant.is_available}
                        className="text-[9px] font-light uppercase tracking-[0.22em] px-3 py-1.5 transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                        style={{
                          border:     `1px solid ${isSel ? "#C09330" : "rgba(192,147,48,0.25)"}`,
                          background: isSel ? "rgba(192,147,48,0.12)" : "transparent",
                          color:      isSel ? "#C09330" : "rgba(177,152,112,0.65)",
                        }}
                      >{variant.size}</button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── Metadata ──────────────────────────────────── */}
          <dl className="mt-6 space-y-3 py-5 text-sm" style={{ borderTop: "1px solid rgba(192,147,48,0.2)", borderBottom: "1px solid rgba(192,147,48,0.2)" }}>
            {selectedVariant && (
              <div className="flex justify-between gap-6">
                <dt style={{ color: "rgba(177,152,112,0.7)" }}>SKU</dt>
                <dd className="font-light font-mono text-xs" style={{ color: "rgba(248,240,232,0.7)" }}>{selectedVariant.sku}</dd>
              </div>
            )}
            {selectedVariant && (
              <div className="flex justify-between gap-6">
                <dt style={{ color: "rgba(177,152,112,0.7)" }}>Colour</dt>
                <dd className="font-medium" style={{ color: "rgba(248,240,232,0.88)" }}>{selectedVariant.color}</dd>
              </div>
            )}
            {selectedVariant && (
              <div className="flex justify-between gap-6">
                <dt style={{ color: "rgba(177,152,112,0.7)" }}>Size</dt>
                <dd className="font-medium" style={{ color: "rgba(248,240,232,0.88)" }}>{selectedVariant.size}</dd>
              </div>
            )}
            {selectedVariant?.fabric && (
              <div className="flex justify-between gap-6">
                <dt style={{ color: "rgba(177,152,112,0.7)" }}>Fabric</dt>
                <dd className="font-medium text-right" style={{ color: "rgba(248,240,232,0.88)" }}>{selectedVariant.fabric}</dd>
              </div>
            )}
            {selectedVariant && (
              <div className="flex justify-between gap-6">
                <dt style={{ color: "rgba(177,152,112,0.7)" }}>MRP</dt>
                <dd className="font-medium" style={{ color: "rgba(248,240,232,0.88)" }}>{formatCurrency(selectedVariant.mrp)}</dd>
              </div>
            )}
            <div className="flex justify-between gap-6">
              <dt style={{ color: "rgba(177,152,112,0.7)" }}>Delivery</dt>
              <dd className="font-medium" style={{ color: "rgba(248,240,232,0.88)" }}>4–6 weeks</dd>
            </div>
            <div className="flex justify-between gap-6">
              <dt style={{ color: "rgba(177,152,112,0.7)" }}>Stock</dt>
              <dd className="font-medium" style={{ color: selectedVariant && selectedVariant.stock_count <= 5 ? "#f59e0b" : "#C09330" }}>
                {selectedVariant
                  ? selectedVariant.stock_count > 0
                    ? selectedVariant.stock_count <= 5
                      ? `Only ${selectedVariant.stock_count} left`
                      : "In stock"
                    : "Sold out"
                  : product.total_stock > 0 ? "In stock" : "Sold out"}
              </dd>
            </div>
          </dl>

          <AddToCartButton product={product} selectedVariant={selectedVariant} />

          <a
            href="/cart"
            className="mt-4 flex h-11 w-full items-center justify-center px-4 text-[10px] font-light uppercase tracking-[0.28em] transition-colors duration-300 hover:text-[#C09330]"
            style={{ border: "1px solid rgba(192,147,48,0.28)", color: "rgba(177,152,112,0.8)" }}
          >
            View bag
          </a>
        </aside>
      </section>
    </main>
  );
}
