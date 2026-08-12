"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { CartItem } from "@/types/cart";
import type { Product, ProductVariant } from "@/types/product";
import { cardImageUrl, variantPrice } from "@/types/product";

type CartState = {
  items: CartItem[];
  addItem:        (product: Product, variant: ProductVariant | null) => void;
  removeItem:     (productId: string, variantId: string | null) => void;
  updateQuantity: (productId: string, variantId: string | null, quantity: number) => void;
  clearCart:      () => void;
  getItemCount:   () => number;
  getSubtotal:    () => number;
};

/** Unique key per cart line: productId + variantId */
function lineKey(productId: string, variantId: string | null): string {
  return `${productId}:${variantId ?? "no-variant"}`;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],

      addItem(product, variant) {
        set((state) => {
          const key        = lineKey(product.id, variant?.id ?? null);
          const existingIdx = state.items.findIndex(
            (i) => lineKey(i.productId, i.variantId) === key,
          );

          if (existingIdx >= 0) {
            const refreshedImage = variant ? variant.image_url ?? "" : cardImageUrl(product);
            return {
              items: state.items.map((item, idx) =>
                idx === existingIdx
                  ? {
                      ...item,
                      sku: variant?.sku ?? item.sku,
                      imageUrl: refreshedImage,
                      color: variant?.color ?? item.color,
                      size: variant?.size ?? item.size,
                      quantity: item.quantity + 1,
                    }
                  : item,
              ),
            };
          }

          const effectivePrice = variant
            ? variantPrice(product, variant).toFixed(2)
            : Number(product.base_price).toFixed(2);

          const newItem: CartItem = {
            productId: product.id,
            variantId: variant?.id ?? null,
            sku:       variant?.sku ?? "",
            slug:      product.slug,
            name:      product.name,
            imageUrl:  variant ? variant.image_url ?? "" : cardImageUrl(product),
            price:     effectivePrice,
            color:     variant?.color ?? "—",
            size:      variant?.size  ?? "—",
            quantity:  1,
          };

          return { items: [...state.items, newItem] };
        });
      },

      removeItem(productId, variantId) {
        const key = lineKey(productId, variantId);
        set((state) => ({
          items: state.items.filter(
            (i) => lineKey(i.productId, i.variantId) !== key,
          ),
        }));
      },

      updateQuantity(productId, variantId, quantity) {
        const next = Math.max(0, Math.floor(quantity));
        if (next === 0) {
          get().removeItem(productId, variantId);
          return;
        }
        const key = lineKey(productId, variantId);
        set((state) => ({
          items: state.items.map((i) =>
            lineKey(i.productId, i.variantId) === key
              ? { ...i, quantity: next }
              : i,
          ),
        }));
      },

      clearCart: () => set({ items: [] }),

      getItemCount: () =>
        get().items.reduce((total, i) => total + i.quantity, 0),

      getSubtotal: () =>
        get().items.reduce(
          (total, i) => total + Number(i.price) * i.quantity,
          0,
        ),
    }),
    {
      name: "behazeld-cart",
      partialize: (state) => ({ items: state.items }),
    },
  ),
);
