/**
 * ProductListingPage — Reusable Collection Product Listing Page.
 *
 * Hero:  dark espresso (#1C0D06) split — photo fills left, single bordered
 *        box (name + taglines) fills right. Both sides stretch to equal height.
 * Body:  warm cream (#E4DBCE) background below the hero.
 */

import Link from "next/link";
import { ProductGrid } from "@/components/product/ProductGrid";
import type { CollectionWithProducts } from "@/types/collection";

/* ── Brand palette tokens ─────────────────────────────────────── */
const HERO_BG   = "#1C0D06";   /* dark espresso  (screenshot 3) */
const BODY_BG   = "#E4DBCE";   /* warm cream     (screenshot 2) */
const GOLD      = "#C09330";
const GOLD_DIM  = "rgba(192,147,48,0.38)";
const GOLD_FADE = "rgba(192,147,48,0.14)";

type Props = {
  collection: CollectionWithProducts;
  eyebrow?: string;
  taglines?: [string, string];
};

function splitTaglines(desc: string): [string, string] {
  const sep = desc.indexOf(" · ");
  if (sep !== -1) return [desc.slice(0, sep).trim(), desc.slice(sep + 3).trim()];
  const mid = Math.ceil(desc.length / 2);
  const space = desc.lastIndexOf(" ", mid);
  const cut = space > 0 ? space : mid;
  return [desc.slice(0, cut).trim(), desc.slice(cut).trim()];
}

export function ProductListingPage({ collection, eyebrow: _eyebrow, taglines }: Props) {
  const hasProducts = collection.products.length > 0;
  const [tagline1, tagline2] = taglines ?? splitTaglines(collection.description || collection.name);

  return (
    <main>

      {/* ══════════════════════════════════════════════════════════════
          HERO — dark espresso background
          LEFT:  hero photo stretches to full panel height
          RIGHT: single bordered box — name + taglines
          grid alignItems="stretch" keeps both columns identical height
          ══════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "clamp(160px, 20vw, 260px) 1fr",
          alignItems: "stretch",
          background: HERO_BG,
          borderBottom: `1px solid ${GOLD_DIM}`,
        }}
      >
        {/* LEFT — photo fills the full height of the grid row */}
        <div className="relative overflow-hidden" style={{ background: HERO_BG }}>
          {collection.hero_image_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={collection.hero_image_url}
              alt={collection.name}
              className="absolute inset-0 h-full w-full object-cover object-top"
              style={{ filter: "brightness(0.95) sepia(0.04)" }}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <span
                className="font-display font-light italic select-none"
                style={{ fontSize: "clamp(56px, 8vw, 96px)", color: "rgba(192,147,48,0.18)" }}
              >
                H
              </span>
            </div>
          )}
          {/* right-edge fade into the panel */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: `linear-gradient(to right, transparent 60%, ${HERO_BG}88 100%)` }}
          />
        </div>

        {/* RIGHT — single bordered box, vertically centred */}
        <div
          style={{
            padding: "clamp(20px, 3.5vw, 48px) clamp(24px, 4.5vw, 64px)",
            background: `${HERO_BG}f8`,
            borderLeft: `1px solid ${GOLD_FADE}`,
            display: "flex",
            alignItems: "center",
          }}
        >
          <div
            style={{
              border: `1px solid ${GOLD_DIM}`,
              padding: "clamp(16px, 2.4vw, 32px) clamp(20px, 3.2vw, 44px)",
              width: "100%",
            }}
          >
            <h1
              className="font-display font-light italic leading-none"
              style={{
                fontSize: "clamp(30px, 5vw, 68px)",
                color: "rgba(248,240,232,0.97)",
                letterSpacing: "-0.01em",
                marginBottom: "clamp(12px, 1.6vw, 22px)",
              }}
            >
              {collection.name}
            </h1>

            <p
              className="font-serif font-light"
              style={{
                fontSize: "clamp(12px, 1.3vw, 17px)",
                color: "rgba(248,240,232,0.68)",
                lineHeight: 1.6,
                letterSpacing: "0.01em",
              }}
            >
              {tagline1}
              {tagline2 && <><br />{tagline2}</>}
            </p>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          BODY — warm cream background
          ══════════════════════════════════════════════════════════════ */}
      <div style={{ background: BODY_BG, minHeight: "60vh" }}>
        <div
          style={{
            maxWidth: 1400,
            margin: "0 auto",
            padding: "clamp(28px, 4vw, 56px) clamp(16px, 3vw, 40px) 96px",
          }}
        >
          {/* Piece count + divider */}
          <div className="flex items-center gap-3" style={{ marginBottom: "clamp(20px, 3vw, 40px)" }}>
            <div className="h-px flex-1" style={{ background: `linear-gradient(to right, ${GOLD}, rgba(192,147,48,0.1))` }} />
            <svg width="5" height="5" viewBox="0 0 6 6">
              <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={GOLD} />
            </svg>
            <p
              className="font-sans font-light uppercase flex-shrink-0"
              style={{ fontSize: 9, letterSpacing: "0.4em", color: "rgba(140,100,30,0.8)" }}
            >
              {hasProducts
                ? `${collection.products.length} piece${collection.products.length !== 1 ? "s" : ""}`
                : "Coming soon"}
            </p>
            <svg width="5" height="5" viewBox="0 0 6 6">
              <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={GOLD} />
            </svg>
            <div className="h-px flex-1" style={{ background: `linear-gradient(to left, ${GOLD}, rgba(192,147,48,0.1))` }} />
          </div>

          {/* Products or empty state */}
          {hasProducts ? (
            <ProductGrid products={collection.products} />
          ) : (
            <EmptyCollection collectionName={collection.name} />
          )}

          {/* Footer nav */}
          <div className="flex items-center gap-4" style={{ marginTop: 72 }}>
            <div className="h-px flex-1" style={{ background: "linear-gradient(to right, rgba(140,100,30,0.4), transparent)" }} />
            <Link
              href="/atelier"
              className="font-sans font-light uppercase flex-shrink-0 transition-colors duration-300"
              style={{ fontSize: 9, letterSpacing: "0.36em", color: "rgba(120,80,20,0.7)" }}
            >
              ← All Collections
            </Link>
            <div className="h-px flex-1" style={{ background: "linear-gradient(to left, rgba(140,100,30,0.4), transparent)" }} />
          </div>
        </div>
      </div>
    </main>
  );
}

// ── Empty state ────────────────────────────────────────────────────
function EmptyCollection({ collectionName }: { collectionName: string }) {
  return (
    <div
      className="px-6 py-20 text-center max-w-lg mx-auto"
      style={{
        border: "1px solid rgba(140,100,30,0.3)",
        background: "rgba(255,255,255,0.35)",
      }}
    >
      <p className="font-sans font-normal uppercase mb-4" style={{ fontSize: 9, letterSpacing: "0.5em", color: GOLD }}>
        Coming Soon
      </p>
      <h2 className="font-display font-light italic" style={{ fontSize: "clamp(24px, 3vw, 36px)", color: "#3A2210" }}>
        {collectionName}
      </h2>
      <p className="font-sans font-light mt-4" style={{ fontSize: 13, color: "rgba(80,50,20,0.7)", lineHeight: 1.8 }}>
        This collection is being curated. <br />
        New pieces will appear here automatically once they are ready.
      </p>
      <Link href="/atelier" className="btn-couture mt-8 inline-flex h-11 items-center justify-center px-8">
        Explore The Atelier
      </Link>
    </div>
  );
}
