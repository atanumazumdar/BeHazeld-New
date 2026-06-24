"use client";

import Link from "next/link";
import { FormEvent, useState, useSyncExternalStore } from "react";

import { createCheckout } from "@/lib/checkout";
import { formatCurrency } from "@/lib/format";
import { useCartStore } from "@/store/cartStore";
import type { CheckoutOrder } from "@/types/checkout";

const SHIPPING_TOTAL = 0;
const WHATSAPP_ORDER_URL = "https://wa.me/918626060038";
const PANEL_BG = "#fffdf8";
const PANEL_BORDER = "#111111";
const INK = "#171717";
const MUTED = "rgba(23,23,23,0.62)";
const GOLD = "#9f741b";
const DARK_CREAM = "rgba(248,240,232,0.88)";
const DARK_MUTED = "rgba(177,152,112,0.75)";

const inputCls =
  "h-9 w-full border bg-white px-3 text-sm text-black outline-none transition-colors";

const subscribe = () => () => {};

function SectionTitle({ children }: { children: string }) {
  return (
    <h2 className="text-2xl font-semibold leading-none" style={{ color: INK }}>
      {children}
    </h2>
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
        customer_phone:  String(fd.get("customer_phone") ?? ""),
        shipping_address:String(fd.get("shipping_address")),
        city:            String(fd.get("city")),
        state:           String(fd.get("state")),
        postal_code:     String(fd.get("postal_code")),
        country:         String(fd.get("country")),
        total_amount:    total.toFixed(2),
        items: items.map((i) => {
          if (!i.variantId) {
            throw new Error(`Please re-add ${i.name}; variant selection is missing.`);
          }
          return { product_variant_id: i.variantId, quantity: i.quantity };
        }),
      });
      const whatsappUrl = `${WHATSAPP_ORDER_URL}?text=${encodeURIComponent(created.whatsapp_message)}`;
      clearCart();
      setOrder(created);
      window.open(whatsappUrl, "_blank", "noopener,noreferrer");
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
          Order #{order.order_id} · Saved
        </p>
        <h1 className="font-serif mt-3 text-4xl font-light italic" style={{ color: DARK_CREAM }}>
          Your order is placed.
        </h1>
        <p className="mx-auto mt-4 max-w-sm text-sm font-light leading-6" style={{ color: DARK_MUTED }}>
          Your order has been saved. WhatsApp has opened with your order summary for confirmation.
        </p>
        <p className="font-serif mt-6 text-3xl font-normal" style={{ color: DARK_CREAM }}>
          {formatCurrency(order.total_amount)}
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
        <h1 className="font-serif text-3xl font-light italic" style={{ color: DARK_CREAM }}>
          Your atelier bag is empty.
        </h1>
        <p className="mt-3 text-sm font-light" style={{ color: DARK_MUTED }}>Add items before checkout.</p>
        <Link href="/" className="btn-couture mt-7 inline-flex h-11 items-center justify-center px-7">
          Continue shopping
        </Link>
      </div>
    );
  }

  /* ── Checkout form ──────────────────────────────────────── */
  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto grid max-w-[920px] overflow-hidden lg:grid-cols-2"
      style={{
        background: PANEL_BG,
        border: `2px solid ${PANEL_BORDER}`,
        color: INK,
      }}
    >
      <div
        className="min-h-[720px] p-3 sm:p-4"
        style={{ borderRight: `2px solid ${PANEL_BORDER}` }}
      >

        {/* Contact */}
        <section>
          <SectionTitle>Contact Details</SectionTitle>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {[
              { label: "Name",  name: "customer_name",  type: "text",  auto: "name"  },
              { label: "Email", name: "customer_email", type: "email", auto: "email" },
              { label: "Contact number", name: "customer_phone", type: "tel", auto: "tel" },
            ].map(({ label, name, type, auto }) => (
              <label key={name} className="space-y-2">
                <span className="text-[9px] font-medium uppercase tracking-[0.22em]" style={{ color: MUTED }}>
                  {label}
                </span>
                <input
                  required
                  name={name}
                  type={type}
                  autoComplete={auto}
                  maxLength={name === "customer_phone" ? 20 : undefined}
                  className={inputCls}
                  style={{ borderColor: "rgba(23,23,23,0.28)" }}
                />
              </label>
            ))}
          </div>
        </section>

        {/* Shipping */}
        <section className="mt-36 sm:mt-44">
          <SectionTitle>Shipping Details</SectionTitle>
          <div className="mt-5 grid gap-3">
            <label className="space-y-2">
              <span className="text-[9px] font-medium uppercase tracking-[0.22em]" style={{ color: MUTED }}>Address</span>
              <input required name="shipping_address" autoComplete="street-address" className={inputCls} style={{ borderColor: "rgba(23,23,23,0.28)" }} />
            </label>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: "City",        name: "city",        auto: "address-level2" },
                { label: "State",       name: "state",       auto: "address-level1" },
                { label: "Postal code", name: "postal_code", auto: "postal-code"    },
              ].map(({ label, name, auto }) => (
                <label key={name} className="space-y-2">
                  <span className="text-[9px] font-medium uppercase tracking-[0.22em]" style={{ color: MUTED }}>
                    {label}
                  </span>
                  <input required name={name} autoComplete={auto} className={inputCls} style={{ borderColor: "rgba(23,23,23,0.28)" }} />
                </label>
              ))}
            </div>
            <label className="space-y-2">
              <span className="text-[9px] font-medium uppercase tracking-[0.22em]" style={{ color: MUTED }}>Country</span>
              <input required name="country" autoComplete="country-name" defaultValue="India" className={inputCls} style={{ borderColor: "rgba(23,23,23,0.28)" }} />
            </label>
          </div>
        </section>

        {error && (
          <p
            className="px-4 py-3 text-sm"
            style={{ background: "rgba(180,40,40,0.08)", border: "1px solid rgba(180,40,40,0.22)", color: "#991b1b" }}
          >
            {error}
          </p>
        )}
      </div>

      {/* ── Order summary sidebar ───────────────────────── */}
      <aside className="grid min-h-[720px] grid-rows-[1fr_auto]">
        <div className="p-3 sm:p-4">
          <SectionTitle>Order Summary</SectionTitle>
          <p className="mt-2 text-xl font-semibold leading-tight" style={{ color: INK }}>
            (Picture of the product)
          </p>

          <div className="mt-8 space-y-5">
            {items.map((item) => (
              <div
                key={`${item.productId}:${item.variantId ?? "no-variant"}`}
                className="grid grid-cols-[92px_1fr_auto] gap-3"
              >
                {item.imageUrl ? (
                  <img
                    src={item.imageUrl}
                    alt={item.name}
                    className="h-28 w-[92px] object-cover object-top"
                    style={{ border: `1px solid ${PANEL_BORDER}` }}
                  />
                ) : (
                  <div
                    className="flex h-28 w-[92px] items-center justify-center"
                    style={{
                      background: "#e4dbce",
                      border: `1px solid ${PANEL_BORDER}`,
                    }}
                  >
                    <span className="text-[8px] uppercase tracking-[0.18em]" style={{ color: MUTED }}>
                      Photo
                    </span>
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-base font-semibold leading-snug" style={{ color: INK }}>{item.name}</p>
                  <p className="text-xs" style={{ color: MUTED }}>
                    {item.color} · {item.size} · Qty {item.quantity}
                  </p>
                </div>
                <p className="text-sm font-semibold" style={{ color: GOLD }}>
                  {formatCurrency(Number(item.price) * item.quantity)}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div
          className="p-3 text-2xl font-normal leading-tight sm:p-4"
          style={{ borderTop: `2px solid ${PANEL_BORDER}` }}
        >
          <p style={{ color: INK }}>Price</p>
          {[
            { label: "Subtotal", value: formatCurrency(subtotal) },
            { label: "Shipping", value: "Complimentary" },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-start justify-between gap-4">
              <span style={{ color: INK }}>{label}</span>
              <span className="text-base pt-1" style={{ color: INK }}>{value}</span>
            </div>
          ))}
          <div className="flex items-start justify-between gap-4">
            <span style={{ color: INK }}>Total</span>
            <span className="text-base pt-1 font-semibold" style={{ color: GOLD }}>{formatCurrency(total)}</span>
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-5 flex h-11 w-full items-center justify-center px-4 text-[10px] font-semibold uppercase tracking-[0.26em] disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              background: GOLD,
              color: "white",
              border: `1px solid ${GOLD}`,
            }}
          >
            {isSubmitting ? "Processing..." : "Place your Order"}
          </button>
        </div>
      </aside>
    </form>
  );
}
