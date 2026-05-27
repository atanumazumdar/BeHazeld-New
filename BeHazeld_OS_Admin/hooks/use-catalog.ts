'use client';

/**
 * Catalog hooks — TanStack Query v5 wrappers over the catalog API.
 *
 * Query keys follow the pattern: ['catalog', entity, ...filters]
 * so that invalidateQueries({ queryKey: ['catalog'] }) busts the whole domain.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  BrandResponse,
  CategoryResponse,
  ColorResponse,
  CreateCategoryPayload,
  CreateColorPayload,
  CreateMasterPayload,
  CreateProductPayload,
  CreateSizePayload,
  CreateVariantPayload,
  ProductGroupResponse,
  ProductResponse,
  ProductTypeResponse,
  ProductVariantResponse,
  SizeResponse,
} from '@/types/catalog';

// ── Query keys ────────────────────────────────────────────────────────────────

export const catalogKeys = {
  all: ['catalog'] as const,
  categories: () => [...catalogKeys.all, 'categories'] as const,
  productGroups: () => [...catalogKeys.all, 'product-groups'] as const,
  productTypes: () => [...catalogKeys.all, 'product-types'] as const,
  brands: () => [...catalogKeys.all, 'brands'] as const,
  sizes: () => [...catalogKeys.all, 'sizes'] as const,
  colors: () => [...catalogKeys.all, 'colors'] as const,
  products: (filters?: Record<string, string | undefined>) =>
    [...catalogKeys.all, 'products', filters] as const,
  variants: (productId: string) =>
    [...catalogKeys.all, 'variants', productId] as const,
};

// ── Master data queries ───────────────────────────────────────────────────────

export function useCategories() {
  return useQuery({
    queryKey: catalogKeys.categories(),
    queryFn: () => apiClient.get<CategoryResponse[]>('/api/v1/catalog/categories'),
  });
}

export function useProductGroups() {
  return useQuery({
    queryKey: catalogKeys.productGroups(),
    queryFn: () => apiClient.get<ProductGroupResponse[]>('/api/v1/catalog/product-groups'),
  });
}

export function useProductTypes() {
  return useQuery({
    queryKey: catalogKeys.productTypes(),
    queryFn: () => apiClient.get<ProductTypeResponse[]>('/api/v1/catalog/product-types'),
  });
}

export function useBrands() {
  return useQuery({
    queryKey: catalogKeys.brands(),
    queryFn: () => apiClient.get<BrandResponse[]>('/api/v1/catalog/brands'),
  });
}

export function useSizes() {
  return useQuery({
    queryKey: catalogKeys.sizes(),
    queryFn: () => apiClient.get<SizeResponse[]>('/api/v1/catalog/sizes'),
  });
}

export function useColors() {
  return useQuery({
    queryKey: catalogKeys.colors(),
    queryFn: () => apiClient.get<ColorResponse[]>('/api/v1/catalog/colors'),
  });
}

// ── Product queries ───────────────────────────────────────────────────────────

interface ProductFilters {
  status?: string;
  search?: string;
  category_id?: string;
  brand_id?: string;
  skip?: number;
  limit?: number;
}

export function useProducts(filters: ProductFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  if (filters.category_id) params.set('category_id', filters.category_id);
  if (filters.brand_id) params.set('brand_id', filters.brand_id);
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));

  const qs = params.toString();
  return useQuery({
    queryKey: catalogKeys.products(Object.fromEntries(params)),
    queryFn: () =>
      apiClient.get<ProductResponse[]>(`/api/v1/catalog/products${qs ? `?${qs}` : ''}`),
  });
}

export function useVariants(productId: string) {
  return useQuery({
    queryKey: catalogKeys.variants(productId),
    queryFn: () =>
      apiClient.get<ProductVariantResponse[]>(`/api/v1/catalog/products/${productId}/variants`),
    enabled: Boolean(productId),
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateProductPayload) =>
      apiClient.post<ProductResponse>('/api/v1/catalog/products', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: catalogKeys.all });
    },
  });
}

export function useCreateVariant(productId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateVariantPayload) =>
      apiClient.post<ProductVariantResponse>(
        `/api/v1/catalog/products/${productId}/variants`,
        data,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: catalogKeys.variants(productId) });
    },
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (productId: string) =>
      apiClient.delete<ProductResponse>(`/api/v1/catalog/products/${productId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: catalogKeys.all });
    },
  });
}

// ── Master data mutations ─────────────────────────────────────────────────────

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateCategoryPayload) =>
      apiClient.post<CategoryResponse>('/api/v1/catalog/categories', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.categories() }),
  });
}

export function useCreateProductGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateMasterPayload) =>
      apiClient.post<ProductGroupResponse>('/api/v1/catalog/product-groups', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.productGroups() }),
  });
}

export function useCreateProductType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateMasterPayload) =>
      apiClient.post<ProductTypeResponse>('/api/v1/catalog/product-types', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.productTypes() }),
  });
}

export function useCreateBrand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateMasterPayload) =>
      apiClient.post<BrandResponse>('/api/v1/catalog/brands', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.brands() }),
  });
}

export function useCreateSize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateSizePayload) =>
      apiClient.post<SizeResponse>('/api/v1/catalog/sizes', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.sizes() }),
  });
}

export function useCreateColor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateColorPayload) =>
      apiClient.post<ColorResponse>('/api/v1/catalog/colors', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.colors() }),
  });
}
