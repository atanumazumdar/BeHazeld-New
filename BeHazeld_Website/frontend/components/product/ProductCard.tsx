"use client";

import { useState } from "react";
import { AddToCartButton } from "@/components/cart/AddToCartButton";
import { formatCurrency } from "@/lib/format";
import type { Product, ProductVariant } from "@/types/product";
import { firstAvailableVariant, variantPrice } from "@/types/product";

type ProductCardProps = {
  product: Product;
  /** Grid position (0-based) — used to label the placeholder "Pic 1", "Pic 2" … */
  index?: number;
};

function cardImg(img: Product["primary_image"]): string {
  if (!img) return "";
  return img.transform_urls?.card || img.url;
}

export function ProductCard({ product, index = 0 }: ProductCardProps) {
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | null>(
    () => firstAvailableVariant(product),
  );

  const isSoldOut    = product.total_stock === 0;
  const imgUrl       = selectedVariant
    ? selectedVariant.image_url ?? ""
    : cardImg(product.primary_image);
  const displayPrice = selectedVariant
    ? variantPrice(product, selectedVariant)
    : Number(product.min_price);

  const availableVariants = product.variants.filter((variant) => variant.is_available);
  const colors = [...new Set(availableVariants.map((v) => v.color))];
  const sizesForColor = (color: string) =>
    availableVariants.filter((v) => v.color === color);
  const activeColor = selectedVariant?.color ?? colors[0] ?? "";

  const picLabel = `Pic ${index + 1}`;
  const productHref = `/products/${encodeURIComponent(product.slug)}`;

  return (
    <article style={{ display: "flex", flexDirection: "column", width: 350 }}>

      {/* ── Single portrait image ──────────────────────────────── */}
      <a
        href={productHref}
        aria-label={`View ${product.name}`}
        className="block group"
      >
        <div
          className="relative overflow-hidden"
          style={{
            width: 350,
            height: 450,
            background: "linear-gradient(145deg, #D8CEBC 0%, #C8BCA8 100%)",
            border: "1px solid rgba(140,100,30,0.2)",
            borderBottom: "none",
          }}
        >
          {imgUrl ? (
            <img
              src={imgUrl}
              alt={product.primary_image?.alt_text ?? product.name}
              className="h-full w-full object-cover object-top transition duration-700 group-hover:scale-[1.04]"
              style={{ filter: "brightness(0.97)" }}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            /* Numbered placeholder — "Pic 1", "Pic 2", … */
            <div
              className="flex flex-col h-full w-full items-center justify-center gap-2"
              style={{ background: "linear-gradient(145deg, #E4DBCE 0%, #D4C8B4 100%)" }}
            >
              {/* Large label */}
              <span
                className="font-sans font-light select-none"
                style={{
                  fontSize: "clamp(18px, 2.5vw, 28px)",
                  color: "rgba(100,70,20,0.45)",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                }}
              >
                {picLabel}
              </span>
              {/* Upload hint */}
              <span
                className="font-sans font-light select-none"
                style={{
                  fontSize: "clamp(7px, 0.8vw, 9px)",
                  color: "rgba(100,70,20,0.3)",
                  letterSpacing: "0.24em",
                  textTransform: "uppercase",
                }}
              >
                Upload photo
              </span>
            </div>
          )}

          {/* Sold-out badge */}
          {isSoldOut && (
            <div
              className="absolute top-2 left-2 font-sans font-light uppercase"
              style={{
                fontSize: 7, letterSpacing: "0.22em",
                background: "rgba(255,252,248,0.88)", color: "#92400e",
                padding: "2px 7px", border: "1px solid rgba(146,64,14,0.35)",
              }}
            >
              Sold out
            </div>
          )}
        </div>
      </a>

      {/* ── Product details ───────────────────────────────────── */}
      <div
        style={{
          border: "1px solid rgba(140,100,30,0.18)",
          borderTop: "none",
          padding: "10px 10px 12px",
          background: "rgba(255,252,248,0.6)",
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        {/* Name + price */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 6 }}>
          <a href={productHref} style={{ flex: 1, minWidth: 0 }}>
            <h2
              className="font-serif font-normal leading-snug hover:text-[#8B6914] transition-colors"
              style={{
                fontSize: "clamp(11px, 1.1vw, 13px)",
                color: "#3A2810",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {product.name}
            </h2>
          </a>
          <span
            className="font-sans font-normal shrink-0"
            style={{ fontSize: "clamp(10px, 1vw, 12px)", color: "#8B6914" }}
          >
            {formatCurrency(displayPrice)}
          </span>
        </div>

        {/* Color tabs */}
        {colors.length > 1 && (
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {colors.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => {
                  const first = sizesForColor(color)[0];
                  if (first) setSelectedVariant(first);
                }}
                className="cursor-pointer transition-colors"
                style={{
                  fontSize: 7, fontWeight: 300, letterSpacing: "0.22em",
                  textTransform: "uppercase", padding: "2px 5px",
                  border: `1px solid ${color === activeColor ? "#8B6914" : "rgba(140,100,30,0.3)"}`,
                  color:  color === activeColor ? "#8B6914" : "rgba(90,60,20,0.6)",
                  background: color === activeColor ? "rgba(139,105,20,0.08)" : "transparent",
                }}
              >
                {color}
              </button>
            ))}
          </div>
        )}

        {/* Size pills */}
        {!isSoldOut && sizesForColor(activeColor).length > 0 && (
          <div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
            {sizesForColor(activeColor).map((variant) => {
              const isSel = selectedVariant?.id === variant.id;
              return (
                <button
                  key={variant.id}
                  type="button"
                  onClick={() => setSelectedVariant(variant)}
                  className="cursor-pointer transition-colors"
                  style={{
                    fontSize: 7, fontWeight: 300, letterSpacing: "0.16em",
                    textTransform: "uppercase", padding: "2px 4px",
                    border:     `1px solid ${isSel ? "#8B6914" : "rgba(140,100,30,0.22)"}`,
                    background: isSel ? "rgba(139,105,20,0.1)" : "transparent",
                    color:      isSel ? "#8B6914" : "rgba(90,60,20,0.55)",
                  }}
                >
                  {variant.size}
                </button>
              );
            })}
          </div>
        )}

        {/* Low stock */}
        {!isSoldOut && selectedVariant && selectedVariant.stock_count <= 5 && (
          <p style={{ fontSize: 7, letterSpacing: "0.18em", color: "#92400e", textTransform: "uppercase", fontWeight: 300 }}>
            Only {selectedVariant.stock_count} left
          </p>
        )}

        <AddToCartButton product={product} selectedVariant={selectedVariant} compact />
      </div>
    </article>
  );
}
