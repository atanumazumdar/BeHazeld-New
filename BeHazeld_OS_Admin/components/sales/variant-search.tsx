'use client';

/**
 * VariantSearch — fast SKU picker for the POS cart.
 *
 * Searches products by name/code (debounced), expands to show variants,
 * and fires onAdd(variant) on selection. Uses the same useProducts +
 * useVariants hooks as the catalog pages.
 *
 * Flow:
 *   Type in search box → product list appears → click product → variant list
 *   appears → click variant → onAdd() fires, search clears
 */

import { useState, useRef, useEffect } from 'react';
import { useDebounce } from 'use-debounce';

import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

import { useProducts, useVariants } from '@/hooks/use-catalog';
import type { ProductResponse, ProductVariantResponse } from '@/types/catalog';
import { addGst } from '@/lib/pricing';

interface VariantSearchProps {
  onAdd: (variant: ProductVariantResponse, product: ProductResponse) => void;
}

export function VariantSearch({ onAdd }: VariantSearchProps) {
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [expanded, setExpanded] = useState<string | null>(null); // product id
  const [showDropdown, setShowDropdown] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: products = [], isLoading } = useProducts({
    search: debouncedSearch || undefined,
    status: 'active',
    limit: 10,
  });

  // Close on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
        setExpanded(null);
      }
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  const handleAdd = (variant: ProductVariantResponse, product: ProductResponse) => {
    onAdd(variant, product);
    setSearch('');
    setShowDropdown(false);
    setExpanded(null);
  };

  return (
    <div ref={containerRef} className="relative">
      <Input
        placeholder="Search SKU or product name to add…"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setShowDropdown(true);
          setExpanded(null);
        }}
        onFocus={() => setShowDropdown(true)}
        className="bg-white"
        autoComplete="off"
      />

      {showDropdown && search.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-stone-200 bg-white shadow-xl max-h-80 overflow-y-auto">
          {isLoading ? (
            <div className="p-3 space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
            </div>
          ) : products.length === 0 ? (
            <p className="p-3 text-sm text-stone-400">No products found for &ldquo;{debouncedSearch}&rdquo;.</p>
          ) : (
            <ul className="py-1">
              {products.map((product) => (
                <ProductDropdownItem
                  key={product.id}
                  product={product}
                  isExpanded={expanded === product.id}
                  onToggle={() => setExpanded(expanded === product.id ? null : product.id)}
                  onAddVariant={(v) => handleAdd(v, product)}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ── Nested product → variant item ─────────────────────────────────────────────

function ProductDropdownItem({
  product,
  isExpanded,
  onToggle,
  onAddVariant,
}: {
  product: ProductResponse;
  isExpanded: boolean;
  onToggle: () => void;
  onAddVariant: (v: ProductVariantResponse) => void;
}) {
  const { data: variants = [], isLoading } = useVariants(isExpanded ? product.id : '');

  return (
    <li>
      <button
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-stone-50 text-left"
        onMouseDown={(e) => {
          e.preventDefault(); // prevent blur
          onToggle();
        }}
      >
        <div>
          <span className="text-sm font-medium text-slate-700">{product.name}</span>
          <span className="ml-2 font-mono text-xs text-stone-400">{product.product_code}</span>
        </div>
        <span className="text-stone-400 text-xs">{isExpanded ? '▲' : '▼'}</span>
      </button>

      {isExpanded && (
        <ul className="bg-stone-50 border-t border-stone-100">
          {isLoading ? (
            <li className="px-4 py-2">
              <Skeleton className="h-4 w-1/2" />
            </li>
          ) : variants.filter((v) => v.status === 'active').length === 0 ? (
            <li className="px-4 py-2 text-xs text-stone-400">No active variants.</li>
          ) : (
            variants
              .filter((v) => v.status === 'active')
              .map((v) => (
                <li key={v.id}>
                  <button
                    className="w-full flex items-center justify-between px-4 py-2 hover:bg-blue-50 text-left"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      onAddVariant(v);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-600">{v.sku_code}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className="bg-white text-slate-700 border border-stone-200 text-xs font-normal">
                        ₹{addGst(Number(v.selling_price)).toFixed(2)} incl. GST
                      </Badge>
                      <span className="text-blue-600 text-xs font-medium">+ Add</span>
                    </div>
                  </button>
                </li>
              ))
          )}
        </ul>
      )}
    </li>
  );
}
