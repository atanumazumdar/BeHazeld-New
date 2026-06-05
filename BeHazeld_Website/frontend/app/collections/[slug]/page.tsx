/**
 * Dynamic collection page — /collections/[slug]
 *
 * generateStaticParams: in production it fetches collection slugs from the
 * backend. In local dev it returns [] so Next does not prefetch remote catalog
 * data during the compiling phase.
 *
 * If the backend is down at build time, generateStaticParams returns []
 * and all pages are rendered on-demand (SSR fallback).
 */

import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ProductListingPage } from "@/components/collection/ProductListingPage";
import { getCollection, getCollections } from "@/lib/collections";

type Props = { params: Promise<{ slug: string }> };

/**
 * Brand taglines for each collection.
 * Format: [primary line (tagline box), secondary line (tagline box)]
 * The third item is the subtitle shown in the smaller box below.
 */
const COLLECTION_TAGLINES: Record<string, [string, string]> = {
  "campus-muse":       ["Effortless. Expressive. Unapologetically You.", "Where Comfort Meets Quiet Confidence."],
  "power-edit":        ["Tailored for Ambition.", "Styled for Impact."],
  "afterglow-evenings":["Turn Moments", "Into Statements."],
  "ultra-luxe":        ["Reserved for the Extraordinary.", "Crafted for the Unforgettable."],
  "accessories":       ["Every Detail, Intentional.", "Every Piece, Essential."],
  "pre-loved":         ["Second Life.", "First Love."],
};

// ── Static params (build-time SSG + ISR) ─────────────────────────
export async function generateStaticParams() {
  if (process.env.NODE_ENV !== "production") return [];
  const collections = await getCollections();
  return collections.map((c) => ({ slug: c.slug }));
}

// ── Metadata ──────────────────────────────────────────────────────
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const name = slug
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return {
    title: `${name || "Collection"} | BeHAZEL'd`,
    description: `Shop the ${name || "collection"} collection at BeHAZEL'd`,
  };
}

// ── Page ─────────────────────────────────────────────────────────
export default async function CollectionPage({ params }: Props) {
  const { slug } = await params;
  const data = await getCollection(slug);
  if (!data) notFound();

  const taglines = COLLECTION_TAGLINES[slug];

  return <ProductListingPage collection={data} taglines={taglines} />;
}
