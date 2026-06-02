'use client';

/**
 * Reports, Finance, and Audit hooks — TanStack Query v5 wrappers.
 *
 * URL map (all under /api/v1/):
 *   GET /dashboard/metrics          → DashboardMetrics
 *   GET /reports/low-stock          → LowStockItem[]
 *   GET /reports/gst                → GstSummary
 *   GET /finance/reports/trial-balance    → TrialBalanceResponse
 *   GET /finance/reports/profit-and-loss → ProfitAndLossReport
 *   GET /audit/logs                 → AuditLogEntry[]
 *   GET /exports/trial-balance.csv  → CSV download (imperative)
 *   GET /exports/profit-loss.csv    → CSV download (imperative)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import {
  importAccountCodesAction,
  importJournalEntriesAction,
  listFinanceAccountsAction,
  listJournalEntriesAction,
} from '@/lib/finance-actions';
import type {
  AuditLogEntry,
  DashboardMetrics,
  FinanceAccountResponse,
  FinanceImportResponse,
  GstSummary,
  JournalEntryResponse,
  LowStockItem,
  ProfitAndLossReport,
  TrialBalanceResponse,
} from '@/types/reports';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── Query keys ────────────────────────────────────────────────────────────────

export const reportKeys = {
  dashboardMetrics: ['reports', 'dashboard-metrics'] as const,
  lowStock: ['reports', 'low-stock'] as const,
  gst: (from?: string, to?: string) => ['reports', 'gst', from, to] as const,
  trialBalance: ['finance', 'trial-balance'] as const,
  pl: (from?: string, to?: string) => ['finance', 'pl', from, to] as const,
  accounts: ['finance', 'accounts'] as const,
  journals: ['finance', 'journals'] as const,
  auditLogs: (filters: Record<string, string | undefined>) =>
    ['audit', 'logs', filters] as const,
};

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

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function useDashboardMetrics() {
  return useQuery({
    queryKey: reportKeys.dashboardMetrics,
    queryFn: () => apiClient.get<DashboardMetrics>('/api/v1/dashboard/metrics'),
    staleTime: 60_000,        // refresh at most once per minute
    refetchInterval: 120_000, // background refresh every 2 min
  });
}

export function useLowStock() {
  return useQuery({
    queryKey: reportKeys.lowStock,
    queryFn: () => apiClient.get<LowStockItem[]>('/api/v1/reports/low-stock'),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}

export function useGstSummary(fromDate?: string, toDate?: string) {
  const params = new URLSearchParams();
  if (fromDate) params.set('from_date', fromDate);
  if (toDate) params.set('to_date', toDate);
  const qs = params.toString();

  return useQuery({
    queryKey: reportKeys.gst(fromDate, toDate),
    queryFn: () =>
      apiClient.get<GstSummary>(`/api/v1/reports/gst${qs ? `?${qs}` : ''}`),
  });
}

// ── Finance ───────────────────────────────────────────────────────────────────

export function useTrialBalance() {
  return useQuery({
    queryKey: reportKeys.trialBalance,
    queryFn: () =>
      apiClient.get<TrialBalanceResponse>('/api/v1/finance/reports/trial-balance'),
  });
}

export function useProfitAndLoss(fromDate?: string, toDate?: string) {
  const params = new URLSearchParams();
  if (fromDate) params.set('from_date', fromDate);
  if (toDate) params.set('to_date', toDate);
  const qs = params.toString();

  return useQuery({
    queryKey: reportKeys.pl(fromDate, toDate),
    queryFn: () =>
      apiClient.get<ProfitAndLossReport>(
        `/api/v1/finance/reports/profit-and-loss${qs ? `?${qs}` : ''}`,
      ),
  });
}

export function useFinanceAccounts() {
  return useQuery({
    queryKey: reportKeys.accounts,
    queryFn: async () => {
      const result = await listFinanceAccountsAction();
      return requireActionData(result, 'Failed to load accounting codes.');
    },
  });
}

export function useJournalEntries() {
  return useQuery({
    queryKey: reportKeys.journals,
    queryFn: async () => {
      const result = await listJournalEntriesAction();
      return requireActionData(result, 'Failed to load journal entries.');
    },
  });
}

export function useImportAccountCodes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File): Promise<FinanceImportResponse> => {
      const form = new FormData();
      form.append('file', file);
      const result = await importAccountCodesAction(form);
      return requireActionData(result, 'Failed to import account codes.');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.accounts });
      qc.invalidateQueries({ queryKey: reportKeys.trialBalance });
      qc.invalidateQueries({ queryKey: reportKeys.pl() });
    },
  });
}

export function useImportJournalEntries() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File): Promise<FinanceImportResponse> => {
      const form = new FormData();
      form.append('file', file);
      const result = await importJournalEntriesAction(form);
      return requireActionData(result, 'Failed to import journal entries.');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.journals });
      qc.invalidateQueries({ queryKey: reportKeys.trialBalance });
      qc.invalidateQueries({ queryKey: reportKeys.pl() });
    },
  });
}

// ── Audit ─────────────────────────────────────────────────────────────────────

interface AuditFilters {
  skip?: number;
  limit?: number;
  user_id?: string;
  endpoint?: string;
  method?: string;
}

export function useAuditLogs(filters: AuditFilters = {}) {
  const params = new URLSearchParams();
  if (filters.skip !== undefined) params.set('skip', String(filters.skip));
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.user_id) params.set('user_id', filters.user_id);
  if (filters.endpoint) params.set('endpoint', filters.endpoint);
  if (filters.method) params.set('method', filters.method);
  const qs = params.toString();

  return useQuery({
    queryKey: reportKeys.auditLogs(Object.fromEntries(params)),
    queryFn: () =>
      apiClient.get<AuditLogEntry[]>(`/api/v1/audit/logs${qs ? `?${qs}` : ''}`),
    staleTime: 30_000,
  });
}

// ── CSV export helpers (imperative) ──────────────────────────────────────────

async function _downloadCsv(path: string, filename: string): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}${path}`, { credentials: 'include' });
    if (!response.ok) return false;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return true;
  } catch {
    return false;
  }
}

export const downloadTrialBalanceCsv = () =>
  _downloadCsv('/api/v1/exports/trial-balance.csv', 'trial_balance.csv');

export const downloadProfitLossCsv = (fromDate?: string, toDate?: string) => {
  const params = new URLSearchParams();
  if (fromDate) params.set('from_date', fromDate);
  if (toDate) params.set('to_date', toDate);
  const qs = params.toString();
  return _downloadCsv(
    `/api/v1/exports/profit-loss.csv${qs ? `?${qs}` : ''}`,
    'profit_loss.csv',
  );
};
