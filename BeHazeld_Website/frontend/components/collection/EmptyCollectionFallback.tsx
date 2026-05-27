import Link from "next/link";

/** Shown when the backend is unreachable at render time. */
export function EmptyCollectionFallback({ title }: { title: string }) {
  return (
    <main>
      <section
        className="mx-auto max-w-7xl px-5 sm:px-6 lg:px-8"
        style={{ paddingTop: 88, paddingBottom: 80 }}
      >
        <div className="glass-panel px-6 py-20 text-center max-w-lg mx-auto">
          <p
            className="font-sans font-normal uppercase mb-4"
            style={{ fontSize: 9, letterSpacing: "0.5em", color: "#C09330" }}
          >
            Coming Soon
          </p>
          <h1
            className="font-display font-light italic"
            style={{ fontSize: "clamp(28px, 3.5vw, 44px)", color: "rgba(248,240,232,0.9)" }}
          >
            {title}
          </h1>
          <p
            className="font-sans font-light mt-4"
            style={{ fontSize: 13, color: "rgba(177,152,112,0.7)", lineHeight: 1.8 }}
          >
            This collection is being curated. Check back soon.
          </p>
          <Link href="/atelier" className="btn-couture mt-8 inline-flex h-11 items-center justify-center px-8">
            Explore The Atelier
          </Link>
        </div>
      </section>
    </main>
  );
}
