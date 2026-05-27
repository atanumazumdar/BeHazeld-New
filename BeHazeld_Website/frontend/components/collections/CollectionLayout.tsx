import Link from "next/link";

type CollectionProduct = {
  name: string;
  price: string;
  image: string;
  note?: string;
};

type CollectionLayoutProps = {
  eyebrow: string;
  title: string;
  description: string;
  products: CollectionProduct[];
};

const COLLECTION_NAV = [
  { label: "Home", href: "/atelier" },
  { label: "Campus Muse", href: "/collections/campus-muse" },
  { label: "Power Edit", href: "/collections/power-edit" },
  { label: "Afterglow Evenings", href: "/collections/afterglow-evenings" },
];

export function CollectionLayout({ eyebrow, title, description, products }: CollectionLayoutProps) {
  const productSlots = Array.from({ length: 9 }, (_, index) => {
    const product = products[index];

    return {
      name: product?.name ?? `Product ${String(index + 1).padStart(2, "0")}`,
      price: product?.price ?? "Price on request",
      image:
        product?.image ??
        `https://placehold.co/900x1200/1a0e08/c09330?text=${encodeURIComponent(`${title} ${index + 1}`)}`,
      note: product?.note ?? "Coming soon",
      isPlaceholder: !product,
    };
  });

  return (
    <main className="relative z-10">
      <section className="mx-auto max-w-7xl px-5 py-14 sm:px-8 lg:px-12 lg:py-20">
        <div className="mx-auto max-w-3xl text-center">
          <nav aria-label="Collection navigation" className="flex flex-wrap items-center justify-center gap-3">
            {COLLECTION_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="inline-flex h-10 items-center justify-center border border-[rgba(192,147,48,0.36)] px-4 font-sans text-[9px] font-light uppercase text-[#C09330] transition duration-300 hover:border-[#C09330] hover:bg-[rgba(192,147,48,0.12)] hover:text-[#F8F0E8]"
                style={{ letterSpacing: "0.24em" }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <p
            className="mt-8 font-sans text-[9px] font-normal uppercase text-[#C09330]"
            style={{ letterSpacing: "0.52em" }}
          >
            {eyebrow}
          </p>
          <h1
            className="font-display mt-4 font-light italic leading-none text-[#F8F0E8]"
            style={{ fontSize: "clamp(48px, 7vw, 104px)" }}
          >
            {title}
          </h1>
          <div className="mx-auto my-7 flex max-w-xs items-center justify-center gap-3">
            <span className="h-px flex-1 bg-[rgba(192,147,48,0.48)]" />
            <span className="h-1.5 w-1.5 rotate-45 bg-[#C09330]" />
            <span className="h-px flex-1 bg-[rgba(192,147,48,0.48)]" />
          </div>
          <p
            className="font-serif text-xl font-light italic leading-8 text-[rgba(248,240,232,0.74)] md:text-2xl md:leading-9"
          >
            {description}
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {productSlots.map((product) => (
            <article
              key={product.name}
              className="group grid h-[500px] grid-cols-4 border border-[rgba(192,147,48,0.28)] bg-[rgba(18,10,5,0.58)] transition duration-500 hover:border-[rgba(192,147,48,0.68)] hover:bg-[rgba(26,14,8,0.82)]"
            >
              <div className="relative min-w-0 overflow-hidden border-r border-[rgba(192,147,48,0.22)] bg-[#1A0E08]">
                <img
                  src={product.image}
                  alt={product.name}
                  className="h-full w-full object-cover object-center transition duration-700 group-hover:scale-[1.045]"
                  style={{ filter: product.isPlaceholder ? "brightness(0.52) sepia(0.3)" : "brightness(0.82) sepia(0.1)" }}
                />
                <div className="absolute inset-0 bg-[linear-gradient(to_top,rgba(18,10,5,0.88),rgba(18,10,5,0.16)_42%,transparent)] opacity-75 transition duration-500 group-hover:opacity-95" />
                <div className="absolute inset-3 border border-[rgba(192,147,48,0.16)] transition duration-500 group-hover:border-[rgba(192,147,48,0.5)]" />
              </div>

              <div className="flex min-w-0 items-center justify-center border-r border-[rgba(192,147,48,0.22)] px-4 py-5 text-center">
                <h2 className="font-serif text-xl font-light italic leading-tight text-[#F8F0E8]">
                  {product.name}
                </h2>
              </div>

              <div className="flex min-w-0 items-center justify-center border-r border-[rgba(192,147,48,0.22)] px-4 py-5 text-center">
                <p className="font-sans text-[9px] font-light uppercase leading-5 text-[rgba(177,152,112,0.78)]" style={{ letterSpacing: "0.18em" }}>
                  {product.note}
                </p>
              </div>

              <div className="flex min-w-0 flex-col items-center justify-center px-4 py-5 text-center">
                <p className="font-sans text-[9px] font-light uppercase text-[#C09330]" style={{ letterSpacing: "0.28em" }}>
                  Quick View
                </p>
                <p className="font-serif mt-3 text-lg font-light italic leading-tight text-[#F8F0E8]">
                  {product.price}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export type { CollectionProduct };
