import type { Metadata } from "next";
import { ProductListingPage } from "@/components/collection/ProductListingPage";
import { getCollection } from "@/lib/collections";
import { EmptyCollectionFallback } from "@/components/collection/EmptyCollectionFallback";

export const metadata: Metadata = {
  title: "Ultra Luxe | BeHAZEL'd",
  description: "Couture craftsmanship without compromise — the BeHAZEL'd Ultra Luxe edit.",
};

export default async function UltraLuxePage() {
  const data = await getCollection("ultra-luxe");
  if (!data) return <EmptyCollectionFallback title="Ultra Luxe" />;
  return <ProductListingPage collection={data} eyebrow="Ultra Luxe · Collection 2026" taglines={["Reserved for the Extraordinary.", "Crafted for the Unforgettable."]} />;
}
