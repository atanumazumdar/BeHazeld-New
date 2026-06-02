/**
 * Reports, Finance, and Audit domain types — mirrors FastAPI Pydantic schemas.
 */

// ── Dashboard / Reports ───────────────────────────────────────────────────────

export interface DashboardMetrics {
  total_revenue: string;      // Decimal as string
  total_cogs: string;
  gross_profit: string;
  total_tax_collected: string;
  active_skus: number;
}

export interface LowStockItem {
  variant_id: string;
  sku_code: string;
  product_id: string;
  reorder_level: number;
  total_on_hand: string;      // Decimal as string
}

export interface GstSummary {
  from_date: string | null;
  to_date: string | null;
  sales_tax_collected: string;
  purchase_tax_paid: string;
  net_gst_payable: string;
}

// ── Trial Balance ─────────────────────────────────────────────────────────────

export interface TrialBalanceLine {
  account_code: string;
  name: string;
  account_type: string;       // asset | liability | equity | income | expense
  total_debit: string;
  total_credit: string;
  net_balance: string;
}

export interface TrialBalanceResponse {
  lines: TrialBalanceLine[];
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
}

// ── P&L ──────────────────────────────────────────────────────────────────────

export interface ProfitAndLossReport {
  from_date: string | null;
  to_date: string | null;
  total_revenue: string;
  total_cogs: string;
  gross_profit: string;
  total_expenses: string;
  net_profit: string;
}

export interface FinanceImportResponse {
  imported: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface FinanceAccountResponse {
  id: string;
  tenant_id: string;
  parent_id: string | null;
  account_code: string;
  name: string;
  account_type: string;
  is_active: boolean;
}

export interface JournalLineResponse {
  id: string;
  account_id: string;
  debit_amount: string;
  credit_amount: string;
  memo: string | null;
}

export interface JournalEntryResponse {
  id: string;
  tenant_id: string;
  entry_number: string;
  entry_date: string;
  description: string;
  ref_type: string;
  ref_id: string | null;
  status: string;
  lines: JournalLineResponse[];
}

export interface CreateJournalLinePayload {
  account_id: string;
  debit_amount: string;
  credit_amount: string;
  memo: string | null;
}

export interface CreateJournalEntryPayload {
  entry_date: string;
  description: string;
  ref_type: 'manual';
  ref_id: string | null;
  lines: CreateJournalLinePayload[];
}

// ── Audit Log ─────────────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  tenant_id: string | null;
  user_id: string | null;
  method: string;
  endpoint: string;
  response_status: number;
  ip_address: string | null;
  request_payload: string | null;
  created_at: string;         // ISO datetime string
}
