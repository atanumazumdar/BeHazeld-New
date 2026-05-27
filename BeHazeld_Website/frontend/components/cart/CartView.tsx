"use client";

import Link from "next/link";

import { formatCurrency } from "@/lib/format";
import { useCartStore } from "@/store/cartStore";

const CREAM = "rgba(248,240,232,0.82)";
const MUTED = "rgba(177,152,112,0.8)";

function Diamond() {
  return (
    <div className="flex items-center gap-3 my-5">
      <div className="flex-1 h-px" style={{ background: "linear-gradient(to right, rgba(192,147,48,0.6), rgba(192,147,48,0.1))" }} />
      <span className="block h-1.5 w-1.5 rotate-45 bg-[#C09330]" />
    </div>
  );
}

export function CartView() {
  const items        = useCartStore((s) => s.items);
  const removeItem   = useCartStore((s) => s.removeItem);
  const updateQty    = useCartStore((s) => s.updateQuantity);
  const clearCart    = useCartStore((s) => s.clearCart);
  const subtotal     = useCartStore((s) => s.getSubtotal());

  if (items.length === 0) {
    return (
      <div className="glass-panel px-6 py-16 text-center max-w-lg mx-auto">
        <Diamond />
        <h1
          className="font-serif text-3xl font-light italic"
          style={{ color: CREAM }}
        >
          Your atelier bag is empty.
        </h1>
        <p className="mt-3 text-sm font-light" style={{ color: MUTED }}>
          Add a few pieces from the collection to begin.
        </p>
        <Diamond />
        <Link href="/" className="btn-couture inline-flex h-11 items-center justify-center px-7 mt-2">
          Continue shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_360px]">

      {/* ── Items ─────────────────────────────────────────── */}
      <section aria-label="Cart items" className="space-y-5">
        {items.map((item) => (
          <article
            key={item.productId}
            className="grid grid-cols-[96px_1fr] gap-5 pb-5"
            style={{ borderBottom: "1px solid rgba(192,147,48,0.15)" }}
          >
            <img
              src={item.imageUrl}
              alt={item.name}
              className="aspect-[3/4] object-cover object-top"
              style={{ filter: "brightness(0.92)" }}
            />
            <div className="min-w-0">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-serif text-xl font-normal" style={{ color: CREAM }}>
                    {item.name}
                  </h2>
                  <p className="mt-1 text-xs font-light" style={{ color: MUTED }}>
                    {item.color} · {item.size}
                  </p>
                </div>
                <p className="text-sm font-normal shrink-0" style={{ color: "#C09330" }}>
                  {formatCurrency(item.price)}
                </p>
              </div>

              <div className="mt-5 flex items-center justify-between gap-4">
                {/* Qty stepper */}
                <div
                  className="flex h-9 items-center"
                  style={{ border: "1px solid rgba(192,147,48,0.28)" }}
                >
                  <button
                    type="button"
                    aria-label={`Decrease ${item.name} quantity`}
                    onClick={() => updateQty(item.productId, item.variantId, item.quantity - 1)}
                    className="h-full w-9 text-lg leading-none transition-colors"
                    style={{ color: MUTED }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#C09330")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
                  >
                    −
                  </button>
                  <span
                    className="w-8 text-center text-sm font-light"
                    style={{ color: CREAM, borderLeft: "1px solid rgba(192,147,48,0.2)", borderRight: "1px solid rgba(192,147,48,0.2)" }}
                  >
                    {item.quantity}
                  </span>
                  <button
                    type="button"
                    aria-label={`Increase ${item.name} quantity`}
                    onClick={() => updateQty(item.productId, item.variantId, item.quantity + 1)}
                    className="h-full w-9 text-lg leading-none transition-colors"
                    style={{ color: MUTED }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#C09330")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
                  >
                    +
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => removeItem(item.productId, item.variantId)}
                  className="text-[10px] font-light uppercase tracking-[0.28em] transition-colors"
                  style={{ color: MUTED }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#C09330")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
                >
                  Remove
                </button>
              </div>
            </div>
          </article>
        ))}
      </section>

      {/* ── Sidebar ───────────────────────────────────────── */}
      <aside className="glass-panel h-fit p-6">
        <p className="text-[9px] font-normal uppercase tracking-[0.48em]" style={{ color: "#C09330" }}>
          Your Selection
        </p>
        <h2 className="font-serif mt-2 text-2xl font-light italic" style={{ color: CREAM }}>
          The Atelier Bag
        </h2>

        <div
          className="mt-5 space-y-3 text-sm pt-5"
          style={{ borderTop: "1px solid rgba(192,147,48,0.15)" }}
        >
          <div className="flex items-center justify-between">
            <span style={{ color: MUTED }}>Subtotal</span>
            <span className="font-medium" style={{ color: CREAM }}>{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ color: MUTED }}>Delivery</span>
            <span style={{ color: MUTED }}>4–6 weeks</span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ color: MUTED }}>Shipping</span>
            <span style={{ color: "#C09330" }}>Complimentary</span>
          </div>
        </div>

        <a href="/checkout" className="btn-couture mt-6 flex h-12 w-full items-center justify-center">
          Proceed to checkout
        </a>
        <button
          type="button"
          onClick={clearCart}
          className="mt-4 flex h-10 w-full items-center justify-center text-[10px] font-light uppercase tracking-[0.28em] transition-colors"
          style={{ color: MUTED }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#C09330")}
          onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
        >
          Clear cart
        </button>
      </aside>
    </div>
  );
}
