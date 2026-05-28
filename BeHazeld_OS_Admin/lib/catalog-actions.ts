'use server';

import { cookies } from 'next/headers';

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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const ACCESS_MAX_AGE = 30 * 60;
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

export interface ImportMasterDataResult {
  success: boolean;
  data?: MasterDataImportResponse;
  message?: string;
}

type MasterDataListResponse =
  | CategoryResponse[]
  | ProductGroupResponse[]
  | ProductTypeResponse[]
  | BrandResponse[]
  | SizeResponse[]
  | ColorResponse[];

type MasterDataCreatePayload =
  | CreateCategoryPayload
  | CreateMasterPayload
  | CreateSizePayload
  | CreateColorPayload;

type MasterDataCreateResponse =
  | CategoryResponse
  | ProductGroupResponse
  | ProductTypeResponse
  | BrandResponse
  | SizeResponse
  | ColorResponse;

interface ProductFilters {
  status?: string;
  search?: string;
  category_id?: string;
  brand_id?: string;
  skip?: number;
  limit?: number;
}

export interface CatalogActionResult<T> {
  success: boolean;
  data?: T;
  message?: string;
}

const MASTER_DATA_ENDPOINTS: Record<MasterDataImportType, string> = {
  categories: '/api/v1/catalog/categories',
  'product-groups': '/api/v1/catalog/product-groups',
  'product-types': '/api/v1/catalog/product-types',
  brands: '/api/v1/catalog/brands',
  sizes: '/api/v1/catalog/sizes',
  colors: '/api/v1/catalog/colors',
};

async function getAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get('access_token')?.value ?? null;
}

async function refreshAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('refresh_token')?.value;

  if (!refreshToken) return null;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return null;
  }

  if (!response.ok) return null;

  const body = await response.json();
  const isProduction = process.env.NODE_ENV === 'production';
  const baseOptions = {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax' as const,
    path: '/',
  };

  cookieStore.set('access_token', body.access_token, {
    ...baseOptions,
    maxAge: ACCESS_MAX_AGE,
  });
  cookieStore.set('refresh_token', body.refresh_token, {
    ...baseOptions,
    maxAge: REFRESH_MAX_AGE,
  });

  return body.access_token as string;
}

async function fetchWithAuth(path: string, init: RequestInit): Promise<Response | null> {
  const accessToken = await getAccessToken();

  if (!accessToken) return null;

  const withAuth = (token: string): RequestInit => ({
    ...init,
    headers: {
      ...(init.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });

  let response = await fetch(`${API_URL}${path}`, withAuth(accessToken));
  if (response.status !== 401) return response;

  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) return response;

  response = await fetch(`${API_URL}${path}`, withAuth(refreshedToken));
  return response;
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    if (body.message) return body.message;
  } catch {
    // ignore parse error
  }
  return fallback;
}

export async function listMasterDataAction(
  entityType: MasterDataImportType,
): Promise<CatalogActionResult<MasterDataListResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(MASTER_DATA_ENDPOINTS[entityType], {
      method: 'GET',
      cache: 'no-store',
    });
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, `Failed to load ${entityType}.`),
    };
  }

  return {
    success: true,
    data: (await response.json()) as MasterDataListResponse,
  };
}

export async function createMasterDataAction(
  entityType: MasterDataImportType,
  payload: MasterDataCreatePayload,
): Promise<CatalogActionResult<MasterDataCreateResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(MASTER_DATA_ENDPOINTS[entityType], {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, `Failed to create ${entityType}.`),
    };
  }

  return {
    success: true,
    data: (await response.json()) as MasterDataCreateResponse,
  };
}

export async function importMasterDataAction(
  entityType: MasterDataImportType,
  formData: FormData,
): Promise<ImportMasterDataResult> {
  let response: Response;
  try {
    const result = await fetchWithAuth(
      `/api/v1/catalog/import/master-data?entity_type=${entityType}`,
      {
        method: 'POST',
        body: formData,
      },
    );
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, 'Failed to import CSV.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as MasterDataImportResponse,
  };
}

async function authenticatedJsonRequest<T>(
  path: string,
  payload: unknown,
  fallback: string,
): Promise<CatalogActionResult<T>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, fallback),
    };
  }

  return {
    success: true,
    data: (await response.json()) as T,
  };
}

export async function listProductsAction(
  filters: ProductFilters = {},
): Promise<CatalogActionResult<ProductResponse[]>> {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  if (filters.category_id) params.set('category_id', filters.category_id);
  if (filters.brand_id) params.set('brand_id', filters.brand_id);
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));

  const qs = params.toString();
  let response: Response;
  try {
    const result = await fetchWithAuth(`/api/v1/catalog/products${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      cache: 'no-store',
    });
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, 'Failed to load products.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as ProductResponse[],
  };
}

export async function createProductAction(
  payload: CreateProductPayload,
): Promise<CatalogActionResult<ProductResponse>> {
  return authenticatedJsonRequest<ProductResponse>(
    '/api/v1/catalog/products',
    payload,
    'Failed to create product.',
  );
}

export async function deleteProductAction(
  productId: string,
): Promise<CatalogActionResult<ProductResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(`/api/v1/catalog/products/${productId}`, {
      method: 'DELETE',
    });
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, 'Failed to archive product.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as ProductResponse,
  };
}

export async function createVariantAction(
  productId: string,
  payload: CreateVariantPayload,
): Promise<CatalogActionResult<ProductVariantResponse>> {
  return authenticatedJsonRequest<ProductVariantResponse>(
    `/api/v1/catalog/products/${productId}/variants`,
    payload,
    'Failed to create variant.',
  );
}

export async function uploadVariantImageAction(
  productId: string,
  variantId: string,
  formData: FormData,
): Promise<CatalogActionResult<ProductVariantResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(
      `/api/v1/catalog/products/${productId}/variants/${variantId}/image`,
      {
        method: 'POST',
        body: formData,
      },
    );
    if (!result) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = result;
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return {
      success: false,
      message: await readErrorMessage(response, 'Failed to upload variant image.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as ProductVariantResponse,
  };
}
