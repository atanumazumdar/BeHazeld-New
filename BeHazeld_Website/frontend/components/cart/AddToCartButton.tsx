"use client";

import { useCartStore } from "@/store/cartStore";
import type { Product, ProductVariant } from "@/types/product";

type Props = {
  product:         Product;
  selectedVariant: ProductVariant | null;
};

export function AddToCartButton({ product, selectedVariant }: Props) {
  const addItem   = useCartStore((s) => s.addItem);
  const isSoldOut = product.total_stock === 0;

  // Require a variant choice when multiple exist
  const needsSelection = product.variants.length > 1 && selectedVariant === null;
  const isDisabled     = isSoldOut || needsSelection;

  const label = isSoldOut
    ? "Sold out"
    : needsSelection
    ? "Select a size"
    : "Add to bag";

  return (
    <button
      type="button"
      disabled={isDisabled}
      onClick={() => !isDisabled && addItem(product, selectedVariant)}
      className="btn-couture mt-4 flex h-11 w-full items-center justify-center px-3 disabled:cursor-not-allowed disabled:border-[rgba(192,147,48,0.2)] disabled:bg-[rgba(248,244,236,0.06)] disabled:text-muted-foreground"
    >
      {label}
    </button>
  );
}
