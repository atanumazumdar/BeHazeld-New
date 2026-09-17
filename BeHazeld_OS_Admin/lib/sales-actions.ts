'use server';

import { cookies } from 'next/headers';

import type {
  CreateCustomerPayload,
  CreateSaleBillPayload,
  CustomerResponse,
  SaleBillResponse,
  SalesInvoiceImportResponse,
} from '@/types/sales';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const ACCESS_MAX_AGE = 30 * 60;
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

interface SalesActionResult<T> {
  success: boolean;
  data?: T;
  message?: string;
}

export interface InvoicePdfData {
  base64: string;
  filename: string;
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

async function authenticatedJsonRequest<T>(
  path: string,
  payload: unknown,
  fallback: string,
  method = 'POST',
): Promise<SalesActionResult<T>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(path, {
      method,
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

export async function listCustomersAction(
  search = '',
): Promise<SalesActionResult<CustomerResponse[]>> {
  const params = new URLSearchParams();
  if (search) params.set('search', search);

  return getSalesData<CustomerResponse[]>(
    `/api/v1/sales/customers${params.toString() ? `?${params.toString()}` : ''}`,
    'Failed to load customers.',
  );
}

export async function createCustomerAction(
  payload: CreateCustomerPayload,
): Promise<SalesActionResult<CustomerResponse>> {
  return authenticatedJsonRequest<CustomerResponse>(
    '/api/v1/sales/customers',
    payload,
    'Failed to create customer.',
  );
}

export async function createSaleBillAction(
  payload: CreateSaleBillPayload,
): Promise<SalesActionResult<SaleBillResponse>> {
  return authenticatedJsonRequest<SaleBillResponse>(
    '/api/v1/sales/bills',
    payload,
    'Failed to post sale.',
  );
}

export async function importSalesInvoicesAction(
  formData: FormData,
): Promise<SalesActionResult<SalesInvoiceImportResponse>> {
  let response: Response;
  try {
    const result = await fetchWithAuth('/api/v1/sales/bills/import', {
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
      message: await readErrorMessage(response, 'Failed to import sales invoices.'),
    };
  }

  return {
    success: true,
    data: (await response.json()) as SalesInvoiceImportResponse,
  };
}

interface BillFilters {
  skip?: number;
  limit?: number;
  customer_id?: string;
  date_from?: string;
  date_to?: string;
}

async function getSalesData<T>(
  path: string,
  fallback: string,
): Promise<SalesActionResult<T>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(path, {
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
      message: await readErrorMessage(response, fallback),
    };
  }

  return {
    success: true,
    data: (await response.json()) as T,
  };
}

export async function listSalesBillsAction(
  filters: BillFilters = {},
): Promise<SalesActionResult<SaleBillResponse[]>> {
  const params = new URLSearchParams();
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.customer_id) params.set('customer_id', filters.customer_id);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  const qs = params.toString();
  return getSalesData<SaleBillResponse[]>(
    `/api/v1/sales/bills${qs ? `?${qs}` : ''}`,
    'Failed to load sales history.',
  );
}

export async function getSalesBillAction(
  billId: string,
): Promise<SalesActionResult<SaleBillResponse>> {
  return getSalesData<SaleBillResponse>(
    `/api/v1/sales/bills/${billId}`,
    'Failed to load sale bill.',
  );
}

export async function getInvoicePdfAction(
  billId: string,
): Promise<SalesActionResult<InvoicePdfData>> {
  let response: Response;
  try {
    const result = await fetchWithAuth(`/api/v1/sales/bills/${billId}/pdf`, {
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
      message: await readErrorMessage(response, 'Failed to load invoice PDF.'),
    };
  }

  const contentDisposition = response.headers.get('Content-Disposition') ?? '';
  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  const bytes = await response.arrayBuffer();

  return {
    success: true,
    data: {
      base64: Buffer.from(bytes).toString('base64'),
      filename: filenameMatch?.[1] ?? `invoice-${billId}.pdf`,
    },
  };
}
