import type { Metadata } from "next";
import { ProductListingPage } from "@/components/collection/ProductListingPage";
import { getCollection } from "@/lib/collections";
import { EmptyCollectionFallback } from "@/components/collection/EmptyCollectionFallback";

export const metadata: Metadata = {
  title: "Accessories | BeHAZEL'd",
  description: "The finishing touch that defines the look — handcrafted adornments by BeHAZEL'd.",
};

export default async function AccessoriesPage() {
  const data = await getCollection("accessories");
  if (!data) return <EmptyCollectionFallback title="Accessories" />;
  return <ProductListingPage collection={data} eyebrow="Accessories · Collection 2026" taglines={["Every Detail, Intentional.", "Every Piece, Essential."]} />;
}
