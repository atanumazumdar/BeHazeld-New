'use client';

/**
 * Catalog hooks — TanStack Query v5 wrappers over the catalog API.
 *
 * Query keys follow the pattern: ['catalog', entity, ...filters]
 * so that invalidateQueries({ queryKey: ['catalog'] }) busts the whole domain.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import {
  createMasterDataAction,
  importMasterDataAction,
  listMasterDataAction,
} from '@/lib/catalog-actions';
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
  MasterDataImportResponse,
  MasterDataImportType,
  ProductGroupResponse,
  ProductResponse,
  ProductTypeResponse,
  ProductVariantResponse,
  SizeResponse,
} from '@/types/catalog';

interface ActionResult<T> {
  success: boolean;
  data?: T;
  message?: string;
}

function requireActionData<T>(
  result: ActionResult<T> | undefined,
  fallbackMessage: string,
): T {
  if (!result) {
    throw new Error('No response from the server. Please refresh and try again.');
  }
  if (!result.success || !result.data) {
    throw new Error(result.message ?? fallbackMessage);
  }
  return result.data;
}

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
    queryFn: async () => {
      const result = await listMasterDataAction('categories');
      return requireActionData(result, 'Failed to load categories.') as CategoryResponse[];
    },
  });
}

export function useProductGroups() {
  return useQuery({
    queryKey: catalogKeys.productGroups(),
    queryFn: async () => {
      const result = await listMasterDataAction('product-groups');
      return requireActionData(result, 'Failed to load product groups.') as ProductGroupResponse[];
    },
  });
}

export function useProductTypes() {
  return useQuery({
    queryKey: catalogKeys.productTypes(),
    queryFn: async () => {
      const result = await listMasterDataAction('product-types');
      return requireActionData(result, 'Failed to load product types.') as ProductTypeResponse[];
    },
  });
}

export function useBrands() {
  return useQuery({
    queryKey: catalogKeys.brands(),
    queryFn: async () => {
      const result = await listMasterDataAction('brands');
      return requireActionData(result, 'Failed to load brands.') as BrandResponse[];
    },
  });
}

export function useSizes() {
  return useQuery({
    queryKey: catalogKeys.sizes(),
    queryFn: async () => {
      const result = await listMasterDataAction('sizes');
      return requireActionData(result, 'Failed to load sizes.') as SizeResponse[];
    },
  });
}

export function useColors() {
  return useQuery({
    queryKey: catalogKeys.colors(),
    queryFn: async () => {
      const result = await listMasterDataAction('colors');
      return requireActionData(result, 'Failed to load colors.') as ColorResponse[];
    },
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
    mutationFn: async (data: CreateCategoryPayload) => {
      const result = await createMasterDataAction('categories', data);
      return requireActionData(result, 'Failed to create category.') as CategoryResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.categories() }),
  });
}

export function useCreateProductGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateMasterPayload) => {
      const result = await createMasterDataAction('product-groups', data);
      return requireActionData(result, 'Failed to create product group.') as ProductGroupResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.productGroups() }),
  });
}

export function useCreateProductType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateMasterPayload) => {
      const result = await createMasterDataAction('product-types', data);
      return requireActionData(result, 'Failed to create product type.') as ProductTypeResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.productTypes() }),
  });
}

export function useCreateBrand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateMasterPayload) => {
      const result = await createMasterDataAction('brands', data);
      return requireActionData(result, 'Failed to create brand.') as BrandResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.brands() }),
  });
}

export function useCreateSize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateSizePayload) => {
      const result = await createMasterDataAction('sizes', data);
      return requireActionData(result, 'Failed to create size.') as SizeResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.sizes() }),
  });
}

export function useCreateColor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateColorPayload) => {
      const result = await createMasterDataAction('colors', data);
      return requireActionData(result, 'Failed to create color.') as ColorResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.colors() }),
  });
}

export function useImportMasterData(entityType: MasterDataImportType) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append('file', file);
      const result = await importMasterDataAction(entityType, form);
      return requireActionData(result, 'Failed to import CSV.');
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: catalogKeys.all }),
  });
}
