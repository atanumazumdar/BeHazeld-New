import { CheckoutForm } from "@/components/checkout/CheckoutForm";

export default function CheckoutPage() {
  return (
    <main>
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-7">
          <p className="text-[10px] font-light uppercase tracking-[0.46em] text-accent">Checkout</p>
          <h1 className="font-serif mt-2 text-4xl font-light italic text-[var(--parchment)]">Finish your order.</h1>
        </div>

        <CheckoutForm />
      </section>
    </main>
  );
}
