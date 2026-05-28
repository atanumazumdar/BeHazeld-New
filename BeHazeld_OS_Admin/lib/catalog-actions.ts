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
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${MASTER_DATA_ENDPOINTS[entityType]}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: 'no-store',
    });
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
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${MASTER_DATA_ENDPOINTS[entityType]}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
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
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(
      `${API_URL}/api/v1/catalog/import/master-data?entity_type=${entityType}`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      },
    );
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
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
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

export async function createProductAction(
  payload: CreateProductPayload,
): Promise<CatalogActionResult<ProductResponse>> {
  return authenticatedJsonRequest<ProductResponse>(
    '/api/v1/catalog/products',
    payload,
    'Failed to create product.',
  );
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
  const accessToken = await getAccessToken();

  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(
      `${API_URL}/api/v1/catalog/products/${productId}/variants/${variantId}/image`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      },
    );
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
