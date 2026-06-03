export interface VendorResponse {
  id: string;
  tenant_id: string;
  name: string;
  gstin: string | null;
  address: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  is_active: boolean;
}

export interface PurchaseBillLineResponse {
  id: string;
  tenant_id: string;
  bill_id: string;
  product_variant_id: string;
  quantity: string;
  unit_cost: string;
  tax_rate: string;
  total_line_amount: string;
}

export interface PurchaseBillResponse {
  id: string;
  tenant_id: string;
  vendor_id: string;
  transporter_id: string | null;
  location_id: string;
  bin_id: string;
  bill_number: string;
  bill_date: string;
  total_amount: string;
  tax_amount: string;
  status: string;
  notes: string | null;
  lines: PurchaseBillLineResponse[];
}
