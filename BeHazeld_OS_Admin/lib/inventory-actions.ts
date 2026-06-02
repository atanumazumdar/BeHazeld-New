'use server';

import { cookies } from 'next/headers';

import type {
  InventoryLocationImportResponse,
  LocationResponse,
  RecordMovementPayload,
  StockBalanceResponse,
  StockMovementResponse,
} from '@/types/inventory';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const ACCESS_MAX_AGE = 30 * 60;
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

export interface InventoryActionResult<T> {
  success: boolean;
  data?: T;
  message?: string;
}

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
    if (typeof body.message === 'string' && body.message.length > 0) {
      return body.message;
    }
    if (typeof body.detail === 'string' && body.detail.length > 0) {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail
        .map((item: { msg?: string; message?: string }) => item.msg ?? item.message ?? JSON.stringify(item))
        .join('; ');
    }
  } catch {
    // ignore parse error
  }
  return `${fallback} (HTTP ${response.status})`;
}

export async function listLocationsAction(): Promise<InventoryActionResult<LocationResponse[]>> {
  let response: Response;
  try {
    const result = await fetchWithAuth('/api/v1/inventory/locations', {
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
      message: await readErrorMessage(response, 'Failed to load locations.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as LocationResponse[],
  };
}

export async function importLocationsBinsAction(
  formData: FormData,
): Promise<InventoryActionResult<InventoryLocationImportResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth('/api/v1/inventory/import/locations-bins', {
      method: 'POST',
      body: formData,
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
      message: await readErrorMessage(response, 'Failed to import locations/bins CSV.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as InventoryLocationImportResponse,
  };
}

export async function recordMovementAction(
  payload: RecordMovementPayload,
): Promise<InventoryActionResult<StockMovementResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth('/api/v1/inventory/movements', {
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
      message: await readErrorMessage(response, 'Failed to record stock movement.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as StockMovementResponse,
  };
}

export async function getStockSummaryAction(
  variantId: string,
): Promise<InventoryActionResult<StockBalanceResponse[]>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(`/api/v1/inventory/summary/${variantId}`, {
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
      message: await readErrorMessage(response, 'Failed to load stock summary.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as StockBalanceResponse[],
  };
}

export async function listStockedVariantIdsAction(): Promise<InventoryActionResult<string[]>> {
  let response: Response;
  try {
    const result = await fetchWithAuth('/api/v1/inventory/stocked-variants', {
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
      message: await readErrorMessage(response, 'Failed to load recorded SKUs.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as string[],
  };
}

export async function getLedgerAction(
  variantId: string,
  locationId: string,
  limit = 100,
): Promise<InventoryActionResult<StockMovementResponse[]>> {
  const params = new URLSearchParams({
    location_id: locationId,
    limit: String(limit),
  });

  let response: Response;
  try {
    const result = await fetchWithAuth(
      `/api/v1/inventory/ledger/${variantId}?${params.toString()}`,
      {
        method: 'GET',
        cache: 'no-store',
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
      message: await readErrorMessage(response, 'Failed to load movement ledger.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as StockMovementResponse[],
  };
}
