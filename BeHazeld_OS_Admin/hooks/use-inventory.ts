'use client';

/**
 * Inventory hooks — TanStack Query v5 wrappers over the inventory API.
 *
 * Key design note:
 * - recordMovement invalidates BOTH balance and ledger so the UI refreshes
 *   automatically after a stock adjustment.
 * - ApiError with errorCode === 'SALE_STOCK_NOT_AVAILABLE' surfaces a clear
 *   message to callers — they should show a toast without rethrowing.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type {
  InventoryLocationImportResponse,
  LocationResponse,
  RecordMovementPayload,
  StockBalanceResponse,
  StockMovementResponse,
} from '@/types/inventory';

// ── Query keys ────────────────────────────────────────────────────────────────

export const inventoryKeys = {
  all: ['inventory'] as const,
  locations: () => [...inventoryKeys.all, 'locations'] as const,
  balance: (variantId: string, locationId: string, binId: string) =>
    [...inventoryKeys.all, 'balance', variantId, locationId, binId] as const,
  summary: (variantId: string) =>
    [...inventoryKeys.all, 'summary', variantId] as const,
  ledger: (variantId: string, locationId: string) =>
    [...inventoryKeys.all, 'ledger', variantId, locationId] as const,
};

// ── Queries ───────────────────────────────────────────────────────────────────

export function useLocations() {
  return useQuery({
    queryKey: inventoryKeys.locations(),
    queryFn: () => apiClient.get<LocationResponse[]>('/api/v1/inventory/locations'),
  });
}

export function useStockBalance(
  variantId: string,
  locationId: string,
  binId: string,
) {
  return useQuery({
    queryKey: inventoryKeys.balance(variantId, locationId, binId),
    queryFn: () =>
      apiClient.get<StockBalanceResponse | null>(
        `/api/v1/inventory/balance?product_variant_id=${variantId}&location_id=${locationId}&bin_id=${binId}`,
      ),
    enabled: Boolean(variantId && locationId && binId),
  });
}

export function useStockSummary(variantId: string) {
  return useQuery({
    queryKey: inventoryKeys.summary(variantId),
    queryFn: () =>
      apiClient.get<StockBalanceResponse[]>(
        `/api/v1/inventory/summary/${variantId}`,
      ),
    enabled: Boolean(variantId),
  });
}

export function useLedger(variantId: string, locationId: string, limit = 100) {
  return useQuery({
    queryKey: inventoryKeys.ledger(variantId, locationId),
    queryFn: () =>
      apiClient.get<StockMovementResponse[]>(
        `/api/v1/inventory/ledger/${variantId}?location_id=${locationId}&limit=${limit}`,
      ),
    enabled: Boolean(variantId && locationId),
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useRecordMovement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RecordMovementPayload) =>
      apiClient.post<StockMovementResponse>('/api/v1/inventory/movements', data),
    onSuccess: (_data, variables) => {
      // Invalidate balance, summary, and ledger for the affected variant
      qc.invalidateQueries({
        queryKey: inventoryKeys.balance(
          variables.product_variant_id,
          variables.location_id,
          variables.bin_id,
        ),
      });
      qc.invalidateQueries({
        queryKey: inventoryKeys.summary(variables.product_variant_id),
      });
      qc.invalidateQueries({
        queryKey: inventoryKeys.ledger(
          variables.product_variant_id,
          variables.location_id,
        ),
      });
    },
  });
}

export function useImportLocationsBins() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return apiClient.postForm<InventoryLocationImportResponse>(
        '/api/v1/inventory/import/locations-bins',
        form,
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: inventoryKeys.locations() }),
  });
}
