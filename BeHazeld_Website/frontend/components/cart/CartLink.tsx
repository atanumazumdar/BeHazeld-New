"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { useCartStore } from "@/store/cartStore";

const subscribe = () => () => {};

export function CartLink() {
  const isHydrated = useSyncExternalStore(subscribe, () => true, () => false);
  const itemCount = useCartStore((state) => state.getItemCount());

  return (
    <Link className="inline-flex h-10 items-center whitespace-nowrap px-2 transition hover:text-accent" href="/cart">
      Your Shopping Bag{isHydrated && itemCount > 0 ? ` (${itemCount})` : ""}
    </Link>
  );
}
