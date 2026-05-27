"use client";

import Link from "next/link";
import { FormEvent, useState, useSyncExternalStore } from "react";

import { createCheckout } from "@/lib/checkout";
import { formatCurrency } from "@/lib/format";
import { useCartStore } from "@/store/cartStore";
import type { CheckoutOrder } from "@/types/checkout";

const SHIPPING_TOTAL = 0;
const CREAM = "rgba(248,240,232,0.88)";
const MUTED = "rgba(177,152,112,0.75)";

const inputCls =
  "glass-input h-11 w-full px-3 text-sm";

const subscribe = () => () => {};

function SectionHeader({ label, title }: { label: string; title: string }) {
  return (
    <>
      <p className="text-[9px] font-normal uppercase tracking-[0.46em]" style={{ color: "#C09330" }}>
        {label}
      </p>
      <h2 className="font-serif mt-2 text-2xl font-light italic" style={{ color: CREAM }}>
        {title}
      </h2>
    </>
  );
}

export function CheckoutForm() {
  const isHydrated = useSyncExternalStore(subscribe, () => true, () => false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error,        setError]        = useState<string | null>(null);
  const [order,        setOrder]        = useState<CheckoutOrder | null>(null);

  const items    = useCartStore((s) => s.items);
  const clearCart= useCartStore((s) => s.clearCart);
  const subtotal = useCartStore((s) => s.getSubtotal());
  const total    = subtotal + SHIPPING_TOTAL;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const fd = new FormData(e.currentTarget);
    try {
      const created = await createCheckout({
        customer_email:  String(fd.get("customer_email")),
        customer_name:   String(fd.get("customer_name")),
        shipping_address:String(fd.get("shipping_address")),
        city:            String(fd.get("city")),
        state:           String(fd.get("state")),
        postal_code:     String(fd.get("postal_code")),
        country:         String(fd.get("country")),
        items: items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
      });
      clearCart();
      setOrder(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isHydrated) return <div className="glass-panel px-5 py-12 min-h-[200px]" />;

  /* ── Order confirmed ────────────────────────────────────── */
  if (order) {
    return (
      <div className="glass-panel px-6 py-16 text-center max-w-lg mx-auto">
        <p className="text-[9px] font-normal uppercase tracking-[0.46em]" style={{ color: "#C09330" }}>
          Order #{order.id} · Confirmed
        </p>
        <h1 className="font-serif mt-3 text-4xl font-light italic" style={{ color: CREAM }}>
          Your order is placed.
        </h1>
        <p className="mx-auto mt-4 max-w-sm text-sm font-light leading-6" style={{ color: MUTED }}>
          Status: <span style={{ color: "#C09330" }}>{order.status.replace("_", " ")}</span>. Your piece will be handcrafted
          and delivered in 4–6 weeks.
        </p>
        <p className="font-serif mt-6 text-3xl font-normal" style={{ color: CREAM }}>
          {formatCurrency(order.total)}
        </p>
        <Link href="/" className="btn-couture mt-8 inline-flex h-11 items-center justify-center px-7">
          Continue shopping
        </Link>
      </div>
    );
  }

  /* ── Empty cart ─────────────────────────────────────────── */
  if (items.length === 0) {
    return (
      <div className="glass-panel px-6 py-14 text-center max-w-lg mx-auto">
        <h1 className="font-serif text-3xl font-light italic" style={{ color: CREAM }}>
          Your atelier bag is empty.
        </h1>
        <p className="mt-3 text-sm font-light" style={{ color: MUTED }}>Add items before checkout.</p>
        <Link href="/" className="btn-couture mt-7 inline-flex h-11 items-center justify-center px-7">
          Continue shopping
        </Link>
      </div>
    );
  }

  /* ── Checkout form ──────────────────────────────────────── */
  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
      <form onSubmit={handleSubmit} className="space-y-5">

        {/* Contact */}
        <section className="glass-panel p-6">
          <SectionHeader label="Contact" title="Who is this piece for?" />
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {[
              { label: "Name",  name: "customer_name",  type: "text",  auto: "name"  },
              { label: "Email", name: "customer_email", type: "email", auto: "email" },
            ].map(({ label, name, type, auto }) => (
              <label key={name} className="space-y-2">
                <span className="text-[10px] font-light uppercase tracking-[0.34em]" style={{ color: MUTED }}>
                  {label}
                </span>
                <input required name={name} type={type} autoComplete={auto} className={inputCls} />
              </label>
            ))}
          </div>
        </section>

        {/* Shipping */}
        <section className="glass-panel p-6">
          <SectionHeader label="Shipping" title="Where should it arrive?" />
          <div className="mt-5 grid gap-4">
            <label className="space-y-2">
              <span className="text-[10px] font-light uppercase tracking-[0.34em]" style={{ color: MUTED }}>Address</span>
              <input required name="shipping_address" autoComplete="street-address" className={inputCls} />
            </label>
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { label: "City",        name: "city",        auto: "address-level2" },
                { label: "State",       name: "state",       auto: "address-level1" },
                { label: "Postal code", name: "postal_code", auto: "postal-code"    },
              ].map(({ label, name, auto }) => (
                <label key={name} className="space-y-2">
                  <span className="text-[10px] font-light uppercase tracking-[0.34em]" style={{ color: MUTED }}>
                    {label}
                  </span>
                  <input required name={name} autoComplete={auto} className={inputCls} />
                </label>
              ))}
            </div>
            <label className="space-y-2">
              <span className="text-[10px] font-light uppercase tracking-[0.34em]" style={{ color: MUTED }}>Country</span>
              <input required name="country" autoComplete="country-name" defaultValue="India" className={inputCls} />
            </label>
          </div>
        </section>

        {error && (
          <p
            className="px-4 py-3 text-sm"
            style={{ background: "rgba(180,40,40,0.15)", border: "1px solid rgba(180,40,40,0.3)", color: "#f87171" }}
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-couture flex h-12 w-full items-center justify-center px-4 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isSubmitting ? "Placing order…" : "Place order"}
        </button>
      </form>

      {/* ── Order summary sidebar ───────────────────────── */}
      <aside className="glass-panel h-fit p-6">
        <p className="text-[9px] font-normal uppercase tracking-[0.46em]" style={{ color: "#C09330" }}>
          Your Selection
        </p>
        <h2 className="font-serif mt-2 text-2xl font-light italic" style={{ color: CREAM }}>
          Order summary
        </h2>

        <div className="mt-5 space-y-4">
          {items.map((item) => (
            <div key={item.productId} className="flex gap-3">
              <img src={item.imageUrl} alt={item.name} className="h-16 w-12 object-cover object-top" />
              <div className="min-w-0 flex-1">
                <p className="font-serif truncate text-base font-normal" style={{ color: CREAM }}>{item.name}</p>
                <p className="mt-1 text-xs" style={{ color: MUTED }}>Qty {item.quantity} · {item.color}</p>
              </div>
              <p className="text-sm font-medium shrink-0" style={{ color: "#C09330" }}>
                {formatCurrency(Number(item.price) * item.quantity)}
              </p>
            </div>
          ))}
        </div>

        <div
          className="mt-5 space-y-3 pt-5 text-sm"
          style={{ borderTop: "1px solid rgba(192,147,48,0.15)" }}
        >
          {[
            { label: "Subtotal", value: formatCurrency(subtotal) },
            { label: "Shipping", value: "Complimentary" },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center justify-between">
              <span style={{ color: MUTED }}>{label}</span>
              <span style={{ color: CREAM }}>{value}</span>
            </div>
          ))}
          <div className="flex items-center justify-between pt-1 text-base" style={{ borderTop: "1px solid rgba(192,147,48,0.1)" }}>
            <span className="font-medium" style={{ color: CREAM }}>Total</span>
            <span className="font-medium" style={{ color: "#C09330" }}>{formatCurrency(total)}</span>
          </div>
        </div>
      </aside>
    </div>
  );
}
