'use client';

import { useQuery } from '@tanstack/react-query';

import { listPurchaseBillsAction, listVendorsAction } from '@/lib/purchase-actions';

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

export const purchaseKeys = {
  all: ['purchases'] as const,
  bills: ['purchases', 'bills'] as const,
  vendors: ['purchases', 'vendors'] as const,
};

export function usePurchaseBills() {
  return useQuery({
    queryKey: purchaseKeys.bills,
    queryFn: async () => {
      const result = await listPurchaseBillsAction();
      return requireActionData(result, 'Failed to load purchase bills.');
    },
  });
}

export function useVendors() {
  return useQuery({
    queryKey: purchaseKeys.vendors,
    queryFn: async () => {
      const result = await listVendorsAction();
      return requireActionData(result, 'Failed to load vendors.');
    },
  });
}
