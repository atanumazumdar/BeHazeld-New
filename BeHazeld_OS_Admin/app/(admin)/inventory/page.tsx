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
import { useStockedVariantIds } from '@/hooks/use-inventory';
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

function formatWholeAmount(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';

  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;

  return amount.toLocaleString('en-IN', {
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  });
}

function formatCurrencyAmount(value: string | null | undefined): string {
  const amount = formatWholeAmount(value);
  return amount === '—' ? amount : `₹${amount}`;
}

function formatMarginPercent(costPrice: string | null | undefined, sellingPrice: string | null | undefined): string {
  const cost = Number(costPrice);
  const sell = Number(sellingPrice);

  if (!Number.isFinite(cost) || !Number.isFinite(sell) || cost <= 0) return '—';

  const margin = ((sell - cost) / cost) * 100;
  return `${margin.toLocaleString('en-IN', {
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  })}%`;
}

export default function InventoryPage() {
  const [search, setSearch] = useState('');
  const [showRecorded, setShowRecorded] = useState(false);
  const [debouncedSearch] = useDebounce(search, 400);

  const { data: products = [], isLoading } = useProducts({
    search: debouncedSearch || undefined,
    limit: 50,
  });
  const productVariantIds = products.flatMap((product) =>
    (product.variants ?? []).map((variant) => variant.id),
  );
  const {
    data: stockedVariantIds = [],
    error: stockedError,
    isLoading: stockedLoading,
  } = useStockedVariantIds(productVariantIds);
  const stockedVariantIdSet = new Set(stockedVariantIds);
  const visibleProductRows = products
    .map((product) => {
      const variants = product.variants ?? [];
      return {
        product,
        variants: showRecorded
          ? variants
          : variants.filter((variant) => !stockedVariantIdSet.has(variant.id)),
        totalVariants: variants.length,
      };
    })
    .filter((row) => row.variants.length > 0);
  const recordedSkuCount = products.reduce(
    (count, product) =>
      count + (product.variants ?? []).filter((variant) => stockedVariantIdSet.has(variant.id)).length,
    0,
  );
  const isTableLoading = isLoading || stockedLoading;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Inventory</h1>
        <p className="mt-1 text-sm text-stone-500">
          Select a SKU to view stock levels and record opening stock movements.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Input
          placeholder="Search products…"
          value={search}
          onValueChange={setSearch}
          className="w-64 bg-white"
        />
        <label className="flex items-center gap-2 text-sm text-stone-600">
          <input
            type="checkbox"
            checked={showRecorded}
            onChange={(event) => setShowRecorded(event.target.checked)}
            className="h-4 w-4 accent-slate-800"
          />
          Show SKUs with recorded stock
        </label>
      </div>

      {!showRecorded && recordedSkuCount > 0 ? (
        <p className="text-sm text-stone-500">
          {recordedSkuCount} recorded SKU{recordedSkuCount !== 1 ? 's are' : ' is'} hidden from this opening-stock queue.
        </p>
      ) : null}

      {stockedError ? (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Could not check which SKUs already have stock recorded. Please refresh after Railway finishes redeploying.
        </p>
      ) : null}

      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-stone-600 font-medium">Code</TableHead>
              <TableHead className="text-stone-600 font-medium">Product</TableHead>
              <TableHead className="text-stone-600 font-medium">Status</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">MRP</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Cost</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Sell</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Margin</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Variants</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isTableLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 8 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : visibleProductRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-12 text-center text-stone-400">
                  {showRecorded
                    ? 'No products found.'
                    : 'No SKUs need opening stock. Turn on “Show SKUs with recorded stock” to review existing stock.'}
                </TableCell>
              </TableRow>
            ) : (
              visibleProductRows.map(({ product, variants, totalVariants }) => (
                <ProductInventoryRow
                  key={product.id}
                  product={product}
                  variants={variants}
                  totalVariants={totalVariants}
                  stockedVariantIdSet={stockedVariantIdSet}
                />
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
  variants,
  totalVariants,
  stockedVariantIdSet,
}: {
  product: ProductResponse;
  variants: ProductVariantResponse[];
  totalVariants: number;
  stockedVariantIdSet: Set<string>;
}) {
  const variantCountLabel =
    variants.length === totalVariants
      ? `${variants.length} SKU${variants.length !== 1 ? 's' : ''}`
      : `${variants.length} of ${totalVariants} SKUs`;

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
          —
        </TableCell>
        <TableCell className="text-right text-stone-400 text-sm">
          —
        </TableCell>
        <TableCell className="text-right text-stone-400 text-sm">
          —
        </TableCell>
        <TableCell className="text-right text-stone-400 text-sm">
          —
        </TableCell>
        <TableCell className="text-right text-stone-400 text-sm">
          {variantCountLabel}
        </TableCell>
      </TableRow>

      {/* Variant rows */}
      {variants.map((variant) => (
        <InventoryVariantRow
          key={variant.id}
          variant={variant}
          isRecorded={stockedVariantIdSet.has(variant.id)}
        />
      ))}
    </>
  );
}

function InventoryVariantRow({
  variant,
  isRecorded,
}: {
  variant: ProductVariantResponse;
  isRecorded: boolean;
}) {
  const variantHref = `/inventory/${variant.id}?sku=${encodeURIComponent(variant.sku_code)}${
    variant.cost_price ? `&cost=${encodeURIComponent(variant.cost_price)}` : ''
  }`;

  return (
    <TableRow className="hover:bg-blue-50/30">
      <TableCell />
      <TableCell>
        <Link
          href={variantHref}
          className="font-mono text-sm text-slate-700 hover:text-blue-600 hover:underline"
        >
          {variant.sku_code}
        </Link>
      </TableCell>
      <TableCell>
        <Badge
          variant="secondary"
          className={
            isRecorded
              ? 'bg-blue-100 text-blue-800'
              : 'bg-amber-100 text-amber-800'
          }
        >
          {isRecorded ? 'recorded' : 'needs stock'}
        </Badge>
      </TableCell>
      <TableCell className="text-right text-stone-600 text-sm tabular-nums">
        {formatCurrencyAmount(variant.mrp)}
      </TableCell>
      <TableCell className="text-right text-stone-600 text-sm tabular-nums">
        {formatCurrencyAmount(variant.cost_price)}
      </TableCell>
      <TableCell className="text-right text-stone-600 text-sm tabular-nums">
        {formatCurrencyAmount(variant.selling_price)}
      </TableCell>
      <TableCell className="text-right text-stone-600 text-sm tabular-nums">
        {formatMarginPercent(variant.cost_price, variant.selling_price)}
      </TableCell>
      <TableCell className="text-right">
        <Link
          href={variantHref}
          className="text-xs text-blue-600 hover:underline"
        >
          View stock →
        </Link>
      </TableCell>
    </TableRow>
  );
}
