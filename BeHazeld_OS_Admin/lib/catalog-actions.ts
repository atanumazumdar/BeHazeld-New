'use server';

import { cookies } from 'next/headers';

import type {
  BrandResponse,
  CategoryResponse,
  ColorResponse,
  CreateCategoryPayload,
  CreateColorPayload,
  CreateMasterPayload,
  CreateSizePayload,
  MasterDataImportResponse,
  MasterDataImportType,
  ProductGroupResponse,
  ProductTypeResponse,
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
