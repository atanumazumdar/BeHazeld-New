'use client';

/**
 * /inventory — Inventory landing page.
 *
 * Shows all active product variants from the catalog.
 * Clicking a SKU navigates to /inventory/[variantId] for the detail view.
 */

import { useState } from 'react';
import Link from 'next/link';
import { useProducts } from '@/hooks/use-catalog';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useDebounce } from 'use-debounce';
import type { ProductResponse, ProductVariantResponse } from '@/types/catalog';

export default function InventoryPage() {
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 400);

  const { data: products = [], isLoading } = useProducts({
    search: debouncedSearch || undefined,
    limit: 50,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Inventory</h1>
        <p className="mt-1 text-sm text-stone-500">
          Select a product to view SKU stock levels and record movements.
        </p>
      </div>

      <Input
        placeholder="Search products…"
        value={search}
        onValueChange={setSearch}
        className="w-64 bg-white"
      />

      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-stone-600 font-medium">Code</TableHead>
              <TableHead className="text-stone-600 font-medium">Product</TableHead>
              <TableHead className="text-stone-600 font-medium">Status</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Variants</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 4 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="py-12 text-center text-stone-400">
                  No products found.
                </TableCell>
              </TableRow>
            ) : (
              products.map((product) => (
                <ProductInventoryRow key={product.id} product={product} />
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ── Per-product row (lazy-loads variants) ─────────────────────────────────────

function ProductInventoryRow({
  product,
}: {
  product: ProductResponse;
}) {
  const variants = product.variants ?? [];

  return (
    <>
      {/* Product header row */}
      <TableRow className="bg-stone-50/40 hover:bg-stone-50">
        <TableCell className="font-mono text-xs text-stone-500">{product.product_code}</TableCell>
        <TableCell className="font-medium text-slate-800">{product.name}</TableCell>
        <TableCell>
          <Badge
            variant="secondary"
            className={
              product.status === 'active'
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-stone-100 text-stone-500'
            }
          >
            {product.status}
          </Badge>
        </TableCell>
        <TableCell className="text-right text-stone-400 text-sm">
          {`${variants.length} SKU${variants.length !== 1 ? 's' : ''}`}
        </TableCell>
      </TableRow>

      {/* Variant rows */}
      {variants.map((variant) => (
        <InventoryVariantRow key={variant.id} variant={variant} />
      ))}
    </>
  );
}

function InventoryVariantRow({ variant }: { variant: ProductVariantResponse }) {
  return (
    <TableRow className="hover:bg-blue-50/30">
      <TableCell />
      <TableCell>
        <Link
          href={`/inventory/${variant.id}`}
          className="font-mono text-sm text-slate-700 hover:text-blue-600 hover:underline"
        >
          {variant.sku_code}
        </Link>
      </TableCell>
      <TableCell className="text-stone-500 text-sm">
        MRP ₹{variant.mrp} · Sell ₹{variant.selling_price}
      </TableCell>
      <TableCell className="text-right">
        <Link
          href={`/inventory/${variant.id}`}
          className="text-xs text-blue-600 hover:underline"
        >
          View stock →
        </Link>
      </TableCell>
    </TableRow>
  );
}
