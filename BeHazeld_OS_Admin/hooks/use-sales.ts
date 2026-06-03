'use client';

/**
 * Sales hooks — TanStack Query v5 wrappers over the sales API.
 *
 * Key design:
 * - useCustomerSearch: debounced-ready (caller passes debouncedSearch)
 * - useCreateSale: on success invalidates bills list; caller handles PDF trigger
 * - downloadInvoicePdf: non-hook imperative helper that streams PDF bytes
 *   from the API and triggers a browser download. Usable in event handlers.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import {
  createCustomerAction,
  createSaleBillAction,
  getSalesBillAction,
  importSalesInvoicesAction,
  listCustomersAction,
  listSalesBillsAction,
} from '@/lib/sales-actions';
import type {
  CreateCustomerPayload,
  CreateSaleBillPayload,
  CustomerResponse,
  SaleBillResponse,
  SalesInvoiceImportResponse,
} from '@/types/sales';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

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

export const salesKeys = {
  all: ['sales'] as const,
  customers: (search?: string) => [...salesKeys.all, 'customers', search] as const,
  bills: (filters?: Record<string, string | undefined>) =>
    [...salesKeys.all, 'bills', filters] as const,
  bill: (id: string) => [...salesKeys.all, 'bill', id] as const,
};

// ── Customer queries ──────────────────────────────────────────────────────────

export function useCustomerSearch(search: string) {
  return useQuery({
    queryKey: salesKeys.customers(search),
    queryFn: async () => {
      const result = await listCustomersAction(search);
      return requireActionData(result, 'Failed to load customers.');
    },
    staleTime: 10_000,
  });
}

// ── Bill queries ──────────────────────────────────────────────────────────────

interface BillFilters {
  skip?: number;
  limit?: number;
  customer_id?: string;
  date_from?: string;
  date_to?: string;
}

export function useBills(filters: BillFilters = {}) {
  const params = new URLSearchParams();
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.customer_id) params.set('customer_id', filters.customer_id);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);

  return useQuery({
    queryKey: salesKeys.bills(Object.fromEntries(params)),
    queryFn: async () => {
      const result = await listSalesBillsAction(filters);
      return requireActionData(result, 'Failed to load sales history.');
    },
  });
}

export function useBill(billId: string) {
  return useQuery({
    queryKey: salesKeys.bill(billId),
    queryFn: async () => {
      const result = await getSalesBillAction(billId);
      return requireActionData(result, 'Failed to load sale bill.');
    },
    enabled: Boolean(billId),
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useCreateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateCustomerPayload) => {
      const result = await createCustomerAction(data);
      return requireActionData(result, 'Failed to create customer.');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...salesKeys.all, 'customers'] });
    },
  });
}

export function useCreateSale() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateSaleBillPayload) => {
      const result = await createSaleBillAction(data);
      return requireActionData(result, 'Failed to post sale.');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.all });
    },
  });
}

export function useImportSalesInvoices() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append('file', file);
      const result = await importSalesInvoicesAction(form);
      if (!result.success || !result.data) {
        throw new Error(result.message ?? 'Failed to import sales invoices.');
      }
      return result.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: salesKeys.all });
    },
  });
}

// ── PDF helpers (imperative, not hooks) ──────────────────────────────────────

/**
 * Stream the invoice PDF from the API and trigger a browser download.
 * Returns `true` on success, `false` on failure.
 */
export async function downloadInvoicePdf(billId: string): Promise<boolean> {
  try {
    const response = await fetch(
      `${BASE_URL}/api/v1/sales/bills/${billId}/pdf`,
      { credentials: 'include' },
    );
    if (!response.ok) return false;

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    // Extract filename from Content-Disposition if present
    const cd = response.headers.get('Content-Disposition') ?? '';
    const match = cd.match(/filename=([^\s;]+)/);
    a.download = match?.[1] ?? `invoice-${billId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Fetch the invoice PDF as a blob URL suitable for iframe/embed preview.
 * Caller must call URL.revokeObjectURL() when done.
 */
export async function getInvoicePreviewUrl(billId: string): Promise<string | null> {
  try {
    const response = await fetch(
      `${BASE_URL}/api/v1/sales/bills/${billId}/pdf`,
      { credentials: 'include' },
    );
    if (!response.ok) return null;
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch {
    return null;
  }
}
