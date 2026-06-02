/**
 * Sales domain types — mirrors FastAPI Pydantic schemas.
 */

export type SalePaymentMode = 'cash' | 'bank_transfer' | 'cheque' | 'upi' | 'card' | 'other';

export interface CustomerResponse {
  id: string;
  tenant_id: string;
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  loyalty_points: number;
  is_active: boolean;
}

export interface SaleBillLineResponse {
  id: string;
  tenant_id: string;
  bill_id: string;
  product_variant_id: string;
  quantity: string;
  selling_price: string;
  unit_cost: string;
  tax_rate: string;
  discount_amount: string;
  total_line_amount: string;
}

export interface SalePaymentResponse {
  id: string;
  tenant_id: string;
  bill_id: string;
  payment_date: string;
  amount: string;
  payment_mode: SalePaymentMode;
  transaction_id: string | null;
  notes: string | null;
}

export interface SaleBillResponse {
  id: string;
  tenant_id: string;
  customer_id: string | null;
  location_id: string;
  bin_id: string;
  invoice_number: string;
  bill_date: string;
  total_amount: string;
  tax_amount: string;
  total_discount: string;
  status: string;
  notes: string | null;
  lines: SaleBillLineResponse[];
  payments: SalePaymentResponse[];
}

export interface SalesInvoiceImportResponse {
  imported: number;
  skipped: number;
  errors: string[];
  invoices: string[];
}

// ── Request payloads ──────────────────────────────────────────────────────────

export interface CreateCustomerPayload {
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
}

export interface CreateSaleBillLinePayload {
  product_variant_id: string;
  quantity: string;
  selling_price: string;
  tax_rate: string;
  discount_amount: string;
}

export interface CreateSalePaymentPayload {
  amount: string;
  payment_mode: SalePaymentMode;
  transaction_id: string | null;
  notes: string | null;
}

export interface CreateSaleBillPayload {
  location_id: string;
  bin_id: string;
  bill_date: string;          // ISO date string YYYY-MM-DD
  customer_id: string | null;
  notes: string | null;
  lines: CreateSaleBillLinePayload[];
  payment: CreateSalePaymentPayload;
}

// ── Cart state (client-only) ──────────────────────────────────────────────────

export interface CartLine {
  variantId: string;
  skuCode: string;
  productName: string;
  quantity: number;
  sellingPrice: number;  // number for arithmetic; serialised to string before POST
  taxRate: number;       // 0–1 fractional
  discountAmount: number;
}
