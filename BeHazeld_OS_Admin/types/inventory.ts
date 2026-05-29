/**
 * Inventory domain types — mirrors FastAPI Pydantic schemas.
 */

export interface BinResponse {
  id: string;
  tenant_id: string;
  location_id: string;
  name: string;
  is_default: boolean;
  is_active: boolean;
}

export interface LocationResponse {
  id: string;
  tenant_id: string;
  name: string;
  address: string | null;
  is_active: boolean;
  bins: BinResponse[];
}

export interface InventoryLocationImportResponse {
  created_locations: number;
  created_bins: number;
  skipped: number;
  errors: string[];
}

export type MovementType =
  | 'opening_stock'
  | 'purchase_in'
  | 'sale_out'
  | 'return_in'
  | 'adjustment_in'
  | 'adjustment_out'
  | 'transfer_in'
  | 'transfer_out';

export interface StockMovementResponse {
  id: string;
  product_variant_id: string;
  location_id: string;
  bin_id: string;
  movement_type: MovementType;
  quantity_change: string;  // Decimal serialised as string
  unit_cost: string;
  notes: string | null;
}

export interface StockBalanceResponse {
  id: string;
  product_variant_id: string;
  location_id: string;
  bin_id: string;
  quantity_on_hand: string;
  quantity_reserved: string;
  quantity_available: string;
}

// ── Request payload ───────────────────────────────────────────────────────────

export interface RecordMovementPayload {
  product_variant_id: string;
  location_id: string;
  bin_id: string;
  movement_type: MovementType;
  quantity: string;    // always positive; sign derived by service
  unit_cost: string;
  batch_number: string | null;
  notes: string | null;
}
