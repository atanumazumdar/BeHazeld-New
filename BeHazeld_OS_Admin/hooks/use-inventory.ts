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
import {
  getLedgerAction,
  getStockSummaryAction,
  importLocationsBinsAction,
  listLocationsAction,
  recordMovementAction,
} from '@/lib/inventory-actions';
import type {
  InventoryLocationImportResponse,
  LocationResponse,
  RecordMovementPayload,
  StockBalanceResponse,
  StockMovementResponse,
} from '@/types/inventory';

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
    queryFn: async () => {
      const result = await listLocationsAction();
      return requireActionData(result, 'Failed to load locations.');
    },
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
    queryFn: async () => {
      const result = await getStockSummaryAction(variantId);
      return requireActionData(result, 'Failed to load stock summary.');
    },
    enabled: Boolean(variantId),
  });
}

export function useLedger(variantId: string, locationId: string, limit = 100) {
  return useQuery({
    queryKey: inventoryKeys.ledger(variantId, locationId),
    queryFn: async () => {
      const result = await getLedgerAction(variantId, locationId, limit);
      return requireActionData(result, 'Failed to load movement ledger.');
    },
    enabled: Boolean(variantId && locationId),
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useRecordMovement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: RecordMovementPayload) => {
      const result = await recordMovementAction(data);
      return requireActionData(result, 'Failed to record stock movement.');
    },
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
    mutationFn: async (file: File): Promise<InventoryLocationImportResponse> => {
      const form = new FormData();
      form.append('file', file);
      const result = await importLocationsBinsAction(form);
      return requireActionData(result, 'Failed to import locations/bins CSV.');
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: inventoryKeys.locations() }),
  });
}
