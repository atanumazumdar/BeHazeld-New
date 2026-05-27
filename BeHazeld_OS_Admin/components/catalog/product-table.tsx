'use client';

/**
 * ProductTable — server-side paginated, searchable, filterable product list.
 *
 * - Debounced search (400 ms) on product_code / name
 * - Category and Brand dropdowns (populated from master data)
 * - Status toggle: active / deleted
 * - Pagination: prev / next with skip/limit
 */

import { useState } from 'react';
import { useDebounce } from 'use-debounce';
import { toast } from 'sonner';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ProductStatusBadge, ProductRowActions } from './product-columns';
import { useProducts, useBrands, useCategories, useDeleteProduct } from '@/hooks/use-catalog';
import { ApiError } from '@/types/api';

const PAGE_SIZE = 20;

interface ProductTableProps {
  onCreateClick: () => void;
}

export function ProductTable({ onCreateClick }: ProductTableProps) {
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 400);
  const [categoryId, setCategoryId] = useState<string | undefined>(undefined);
  const [brandId, setBrandId] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState<string>('active');
  const [skip, setSkip] = useState(0);

  const { data: categories = [] } = useCategories();
  const { data: brands = [] } = useBrands();
  const { data: products = [], isLoading, isFetching } = useProducts({
    search: debouncedSearch || undefined,
    category_id: categoryId,
    brand_id: brandId,
    status,
    skip,
    limit: PAGE_SIZE,
  });

  const deleteMutation = useDeleteProduct();

  const handleDelete = async (id: string) => {
    if (!confirm('Archive this product? All variants will be hidden from the storefront.')) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Product archived successfully.');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to delete product.';
      toast.error(msg);
    }
  };

  const handleFilterChange =
    (setter: (v: string | undefined) => void) => (val: string | null) => {
      setter(!val || val === 'all' ? undefined : val);
      setSkip(0);
    };

  const loading = isLoading || isFetching;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search code or name…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setSkip(0); }}
          className="w-56 bg-white"
        />

        <Select onValueChange={handleFilterChange(setCategoryId)} defaultValue="all">
          <SelectTrigger className="w-44 bg-white">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {categories.map((c) => (
              <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select onValueChange={handleFilterChange(setBrandId)} defaultValue="all">
          <SelectTrigger className="w-40 bg-white">
            <SelectValue placeholder="All brands" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All brands</SelectItem>
            {brands.map((b) => (
              <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select onValueChange={(v) => { setStatus(v ?? 'active'); setSkip(0); }} defaultValue="active">
          <SelectTrigger className="w-36 bg-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="deleted">Deleted</SelectItem>
          </SelectContent>
        </Select>

        <div className="ml-auto">
          <Button onClick={onCreateClick} className="bg-slate-800 hover:bg-slate-700 text-white">
            + New Product
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-stone-600 font-medium">Code</TableHead>
              <TableHead className="text-stone-600 font-medium">Name</TableHead>
              <TableHead className="text-stone-600 font-medium">Category</TableHead>
              <TableHead className="text-stone-600 font-medium">Brand</TableHead>
              <TableHead className="text-stone-600 font-medium">Status</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-stone-400">
                  No products found.
                </TableCell>
              </TableRow>
            ) : (
              products.map((product) => (
                <TableRow key={product.id} className="hover:bg-stone-50/60">
                  <TableCell className="font-mono text-sm text-stone-700">
                    {product.product_code}
                  </TableCell>
                  <TableCell className="font-medium text-slate-800">{product.name}</TableCell>
                  <TableCell className="text-stone-600 text-sm">
                    {categories.find((c) => c.id === product.category_id)?.name ?? '—'}
                  </TableCell>
                  <TableCell className="text-stone-600 text-sm">
                    {brands.find((b) => b.id === product.brand_id)?.name ?? '—'}
                  </TableCell>
                  <TableCell>
                    <ProductStatusBadge status={product.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <ProductRowActions product={product} onDelete={handleDelete} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-stone-500">
        <span>
          {loading ? '…' : `${products.length} result${products.length !== 1 ? 's' : ''}`}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={skip === 0 || loading}
            onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={products.length < PAGE_SIZE || loading}
            onClick={() => setSkip(skip + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
