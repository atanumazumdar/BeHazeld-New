import type { Metadata } from "next";
import { ProductListingPage } from "@/components/collection/ProductListingPage";
import { getCollection } from "@/lib/collections";
import { EmptyCollectionFallback } from "@/components/collection/EmptyCollectionFallback";

export const metadata: Metadata = {
  title: "Pre Loved | BeHAZEL'd",
  description: "Sustainably yours. Uniquely Hazel — curated pre-owned BeHAZEL'd pieces.",
};

export default async function PreLovedPage() {
  const data = await getCollection("pre-loved");
  if (!data) return <EmptyCollectionFallback title="Pre Loved" />;
  return <ProductListingPage collection={data} eyebrow="Pre Loved · Sustainably Yours" taglines={["Second Life.", "First Love."]} />;
}
