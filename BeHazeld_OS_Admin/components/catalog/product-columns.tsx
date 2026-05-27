'use client';

/**
 * Column definitions for the Product DataTable.
 * Uses Shadcn Table primitives directly (no @tanstack/react-table dependency required
 * for our simple server-side-paginated table pattern).
 */

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { ProductResponse } from '@/types/catalog';
import Link from 'next/link';

interface ProductActionsProps {
  product: ProductResponse;
  onDelete: (id: string) => void;
}

export function ProductStatusBadge({ status }: { status: string }) {
  const isActive = status === 'active';
  return (
    <Badge
      variant={isActive ? 'default' : 'secondary'}
      className={
        isActive
          ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-100'
          : 'bg-stone-100 text-stone-600 hover:bg-stone-100'
      }
    >
      {isActive ? 'Active' : 'Deleted'}
    </Badge>
  );
}

export function ProductRowActions({ product, onDelete }: ProductActionsProps) {
  return (
    <div className="flex items-center gap-2">
      <Link
        href={`/catalog/products/${product.id}`}
        className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 text-slate-700 hover:bg-stone-100 transition-colors"
      >
        View
      </Link>
      <Button
        variant="ghost"
        size="sm"
        className="text-red-600 hover:text-red-700 hover:bg-red-50"
        onClick={() => onDelete(product.id)}
        disabled={product.status !== 'active'}
      >
        Delete
      </Button>
    </div>
  );
}
