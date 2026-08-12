"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useCartStore } from "@/store/cartStore";
import type { Product, ProductVariant } from "@/types/product";

type Props = {
  product:         Product;
  selectedVariant: ProductVariant | null;
  compact?: boolean;
};

export function AddToCartButton({ product, selectedVariant, compact = false }: Props) {
  const addItem   = useCartStore((s) => s.addItem);
  const itemCount = useCartStore((s) => s.getItemCount());
  const [justAdded, setJustAdded] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);
  const isSoldOut = product.total_stock === 0;

  // Require a variant choice when multiple exist
  const needsSelection = product.variants.length > 1 && selectedVariant === null;
  const isDisabled     = isSoldOut || needsSelection;

  const label = isSoldOut
    ? "Sold out"
    : needsSelection
    ? "Select a size"
    : justAdded
    ? "Added to bag"
    : "Add to bag";

  function handleAdd() {
    if (isDisabled) return;
    addItem(product, selectedVariant);
    setJustAdded(true);
    window.setTimeout(() => setJustAdded(false), 1800);
  }

  useEffect(() => {
    setHasMounted(true);
  }, []);

  return (
    <div className={compact ? "mt-2 space-y-2" : "mt-4 space-y-3"}>
      <button
        type="button"
        disabled={isDisabled}
        onClick={handleAdd}
        className="btn-couture flex h-11 w-full items-center justify-center px-3 disabled:cursor-not-allowed disabled:border-[rgba(192,147,48,0.2)] disabled:bg-[rgba(248,244,236,0.06)] disabled:text-muted-foreground"
        aria-live="polite"
      >
        {label}
      </button>

      {hasMounted && itemCount > 0 && (
        <Link
          href="/cart"
          className="flex h-9 w-full items-center justify-center border text-[9px] font-light uppercase tracking-[0.28em] transition-colors hover:text-[#8B6914]"
          style={{
            borderColor: "rgba(140,100,30,0.28)",
            color: "rgba(90,60,20,0.7)",
            background: "rgba(255,252,248,0.45)",
          }}
        >
          View bag ({itemCount})
        </Link>
      )}
    </div>
  );
}
