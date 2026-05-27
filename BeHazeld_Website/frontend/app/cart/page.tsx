import { CartView } from "@/components/cart/CartView";

export default function CartPage() {
  return (
    <main>
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-7">
          <p className="text-[10px] font-light uppercase tracking-[0.46em] text-accent">Cart</p>
          <h1 className="font-serif mt-2 text-4xl font-light italic text-[var(--parchment)]">Review your pieces.</h1>
        </div>

        <CartView />
      </section>
    </main>
  );
}
