'use client';

/**
 * /sales/new — Point of Sale page.
 *
 * Layout: two-column on desktop
 *   Left  (2/3): Customer + SKU search
 *   Right (1/3): Receipt-style cart + totals + payment + post button
 *
 * Golden Sale flow:
 *   1. Select customer (optional) or leave blank for walk-in
 *   2. Pick location + bin (inventory source)
 *   3. Add variants to cart; adjust quantities inline
 *   4. Set payment mode + amount (defaults to Grand Total)
 *   5. "Confirm & Post" → POST /sales/bills → receive SaleBillResponse
 *   6. On success: toast ✓, show invoice preview modal
 *   7. On 409 SALE_STOCK_NOT_AVAILABLE: red toast with specific message
 */

import { useState, useMemo } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { CustomerSelector } from '@/components/sales/customer-selector';
import { VariantSearch } from '@/components/sales/variant-search';
import { InvoicePreviewModal } from '@/components/sales/invoice-preview-modal';

import { useLocations } from '@/hooks/use-inventory';
import { useCreateSale } from '@/hooks/use-sales';
import { ApiError } from '@/types/api';
import type { CustomerResponse } from '@/types/sales';
import type { CartLine, SalePaymentMode } from '@/types/sales';
import type { ProductResponse, ProductVariantResponse } from '@/types/catalog';

const PAYMENT_MODES: { value: SalePaymentMode; label: string }[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'upi', label: 'UPI' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'cheque', label: 'Cheque' },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function SalesPOSPage() {
  // ── Location / bin ────────────────────────────────────────────────────────
  const { data: locations = [] } = useLocations();
  const [locationId, setLocationId] = useState('');
  const [binId, setBinId] = useState('');
  const bins = locations.find((l) => l.id === locationId)?.bins.filter((b) => b.is_active) ?? [];

  // ── Customer ──────────────────────────────────────────────────────────────
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);

  // ── Cart ──────────────────────────────────────────────────────────────────
  const [cart, setCart] = useState<CartLine[]>([]);

  const addToCart = (variant: ProductVariantResponse, product: ProductResponse) => {
    const price = parseFloat(variant.selling_price);
    setCart((prev) => {
      const idx = prev.findIndex((l) => l.variantId === variant.id);
      if (idx >= 0) {
        // Increment existing
        const updated = [...prev];
        updated[idx] = { ...updated[idx], quantity: updated[idx].quantity + 1 };
        return updated;
      }
      return [
        ...prev,
        {
          variantId: variant.id,
          skuCode: variant.sku_code,
          productName: product.name,
          quantity: 1,
          sellingPrice: price,
          taxRate: 0,
          discountAmount: 0,
        },
      ];
    });
  };

  const updateQty = (variantId: string, qty: number) => {
    if (qty <= 0) {
      setCart((prev) => prev.filter((l) => l.variantId !== variantId));
    } else {
      setCart((prev) =>
        prev.map((l) => (l.variantId === variantId ? { ...l, quantity: qty } : l)),
      );
    }
  };

  const updateDiscount = (variantId: string, discount: number) => {
    setCart((prev) =>
      prev.map((l) => (l.variantId === variantId ? { ...l, discountAmount: Math.max(0, discount) } : l)),
    );
  };

  const removeFromCart = (variantId: string) => {
    setCart((prev) => prev.filter((l) => l.variantId !== variantId));
  };

  // ── Totals (real-time) ────────────────────────────────────────────────────
  const { subtotal, taxTotal, grandTotal } = useMemo(() => {
    let sub = 0;
    let tax = 0;
    for (const line of cart) {
      const net = (line.sellingPrice - line.discountAmount) * line.quantity;
      const lineTax = net * line.taxRate;
      sub += net;
      tax += lineTax;
    }
    return { subtotal: sub, taxTotal: tax, grandTotal: sub + tax };
  }, [cart]);

  // ── Payment ───────────────────────────────────────────────────────────────
  const [paymentMode, setPaymentMode] = useState<SalePaymentMode>('cash');
  const [paymentAmount, setPaymentAmount] = useState('');
  const effectivePayment = paymentAmount ? parseFloat(paymentAmount) : grandTotal;

  // ── Post sale ─────────────────────────────────────────────────────────────
  const createSale = useCreateSale();
  const [postedBill, setPostedBill] = useState<{ id: string; invoiceNumber: string } | null>(null);

  const canPost =
    cart.length > 0 &&
    locationId &&
    binId &&
    effectivePayment > 0 &&
    !createSale.isPending;

  const handlePost = async () => {
    if (!canPost) return;

    try {
      const bill = await createSale.mutateAsync({
        location_id: locationId,
        bin_id: binId,
        bill_date: today(),
        customer_id: customer?.id ?? null,
        notes: null,
        lines: cart.map((l) => ({
          product_variant_id: l.variantId,
          quantity: String(l.quantity),
          selling_price: String(l.sellingPrice),
          tax_rate: String(l.taxRate),
          discount_amount: String(l.discountAmount),
        })),
        payment: {
          amount: String(effectivePayment.toFixed(2)),
          payment_mode: paymentMode,
          transaction_id: null,
          notes: null,
        },
      });

      toast.success(`Sale posted — Invoice ${bill.invoice_number}`, {
        description: `Total ₹${bill.total_amount}`,
      });

      // Show invoice preview
      setPostedBill({ id: bill.id, invoiceNumber: bill.invoice_number });

      // Reset POS
      setCart([]);
      setCustomer(null);
      setPaymentAmount('');
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === 'SALE_STOCK_NOT_AVAILABLE') {
        toast.error('Stock not available', {
          description:
            'One or more items in the cart have insufficient stock at the selected location. Check inventory and adjust quantities.',
          duration: 8000,
        });
      } else {
        const msg = err instanceof ApiError ? err.message : 'Failed to post sale.';
        toast.error(msg);
      }
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      <div className="flex flex-col lg:flex-row gap-6 h-full">

        {/* ── LEFT: inputs ── */}
        <div className="flex-1 space-y-6 min-w-0">
          {/* Page header */}
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">New Sale</h1>
            <p className="mt-1 text-sm text-stone-500">Point of Sale — add items and post the invoice in one step.</p>
          </div>

          {/* Location + Bin */}
          <div className="rounded-xl border border-stone-200 bg-white p-4 space-y-4">
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Inventory Source
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Location *</Label>
                <Select
                  onValueChange={(v) => { setLocationId(v ?? ''); setBinId(''); }}
                  value={locationId}
                >
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder="Select location…" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations.map((l) => (
                      <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Bin *</Label>
                <Select
                  onValueChange={(v) => setBinId(v ?? '')}
                  value={binId}
                  disabled={!locationId}
                >
                  <SelectTrigger className="bg-white">
                    <SelectValue placeholder={locationId ? 'Select bin…' : 'Choose location first'} />
                  </SelectTrigger>
                  <SelectContent>
                    {bins.map((b) => (
                      <SelectItem key={b.id} value={b.id}>
                        {b.name}{b.is_default ? ' (default)' : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Customer */}
          <div className="rounded-xl border border-stone-200 bg-white p-4 space-y-3">
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Customer
            </h2>
            <CustomerSelector value={customer} onChange={setCustomer} />
          </div>

          {/* Variant search */}
          <div className="rounded-xl border border-stone-200 bg-white p-4 space-y-3">
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Add Items
            </h2>
            <VariantSearch onAdd={addToCart} />
            {cart.length === 0 && (
              <p className="text-sm text-stone-400 text-center py-4">
                Search and click a SKU above to add it to the cart.
              </p>
            )}
          </div>

          {/* Cart table (only shown when not empty) */}
          {cart.length > 0 && (
            <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wide">
                    <th className="text-left px-4 py-2.5 font-medium">Item</th>
                    <th className="text-center px-3 py-2.5 font-medium w-24">Qty</th>
                    <th className="text-right px-3 py-2.5 font-medium w-24">Unit Price</th>
                    <th className="text-right px-3 py-2.5 font-medium w-24">Disc.</th>
                    <th className="text-right px-4 py-2.5 font-medium w-28">Line Total</th>
                    <th className="w-8" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {cart.map((line) => {
                    const net = (line.sellingPrice - line.discountAmount) * line.quantity;
                    return (
                      <tr key={line.variantId} className="hover:bg-stone-50/40">
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-700">{line.productName}</p>
                          <p className="text-xs text-stone-400 font-mono">{line.skuCode}</p>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => updateQty(line.variantId, line.quantity - 1)}
                              className="w-6 h-6 rounded text-stone-500 hover:bg-stone-100 flex items-center justify-center text-base leading-none"
                            >
                              −
                            </button>
                            <input
                              type="number"
                              value={line.quantity}
                              onChange={(e) => updateQty(line.variantId, parseInt(e.target.value) || 0)}
                              className="w-10 text-center text-sm border border-stone-200 rounded px-1 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                              min={1}
                            />
                            <button
                              onClick={() => updateQty(line.variantId, line.quantity + 1)}
                              className="w-6 h-6 rounded text-stone-500 hover:bg-stone-100 flex items-center justify-center text-base leading-none"
                            >
                              +
                            </button>
                          </div>
                        </td>
                        <td className="px-3 py-3 text-right text-slate-700 font-mono">
                          ₹{line.sellingPrice.toFixed(2)}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <input
                            type="number"
                            value={line.discountAmount || ''}
                            onChange={(e) => updateDiscount(line.variantId, parseFloat(e.target.value) || 0)}
                            className="w-16 text-right text-sm border border-stone-200 rounded px-1 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400 font-mono"
                            placeholder="0"
                            min={0}
                          />
                        </td>
                        <td className="px-4 py-3 text-right font-mono font-semibold text-slate-800">
                          ₹{net.toFixed(2)}
                        </td>
                        <td className="pr-3">
                          <button
                            onClick={() => removeFromCart(line.variantId)}
                            className="text-stone-300 hover:text-red-400 text-lg leading-none"
                            aria-label="Remove"
                          >
                            ×
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── RIGHT: Receipt + totals + payment ── */}
        <div className="w-full lg:w-80 shrink-0">
          <div className="sticky top-4 rounded-xl border border-stone-200 bg-white overflow-hidden">
            {/* Receipt header */}
            <div className="bg-slate-800 text-white px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-300">Receipt</p>
              <p className="text-sm text-slate-200 mt-0.5">
                {cart.length} item{cart.length !== 1 ? 's' : ''}
              </p>
            </div>

            <div className="p-4 space-y-4">
              {/* Line summary */}
              {cart.length === 0 ? (
                <p className="text-sm text-stone-400 text-center py-4">Cart is empty</p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {cart.map((line) => {
                    const net = (line.sellingPrice - line.discountAmount) * line.quantity;
                    return (
                      <li key={line.variantId} className="flex justify-between gap-2">
                        <span className="text-stone-600 truncate flex-1">
                          {line.productName}
                          <span className="text-stone-400 text-xs ml-1">×{line.quantity}</span>
                        </span>
                        <span className="font-mono text-slate-700 shrink-0">₹{net.toFixed(2)}</span>
                      </li>
                    );
                  })}
                </ul>
              )}

              <Separator />

              {/* Totals */}
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between text-stone-600">
                  <span>Subtotal</span>
                  <span className="font-mono">₹{subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-stone-600">
                  <span>Tax</span>
                  <span className="font-mono">₹{taxTotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-base font-semibold text-slate-800 pt-1 border-t border-stone-200">
                  <span>Grand Total</span>
                  <span className="font-mono">₹{grandTotal.toFixed(2)}</span>
                </div>
              </div>

              <Separator />

              {/* Payment */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Payment
                </h3>

                <div className="space-y-1.5">
                  <Label className="text-xs">Mode</Label>
                  <Select
                    onValueChange={(v) => setPaymentMode((v ?? 'cash') as SalePaymentMode)}
                    value={paymentMode}
                  >
                    <SelectTrigger className="bg-white h-9 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PAYMENT_MODES.map((m) => (
                        <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Amount Received</Label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder={`₹${grandTotal.toFixed(2)}`}
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    className="bg-white h-9 text-sm font-mono"
                  />
                  {paymentAmount && effectivePayment < grandTotal && (
                    <p className="text-xs text-amber-600">
                      Amount is less than Grand Total by ₹{(grandTotal - effectivePayment).toFixed(2)}.
                    </p>
                  )}
                  {paymentAmount && effectivePayment > grandTotal && (
                    <p className="text-xs text-emerald-600">
                      Change due: ₹{(effectivePayment - grandTotal).toFixed(2)}
                    </p>
                  )}
                </div>
              </div>

              {/* Post button */}
              <Button
                onClick={handlePost}
                disabled={!canPost}
                className={`w-full font-semibold transition-all ${
                  canPost
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                    : 'bg-stone-200 text-stone-400 cursor-not-allowed'
                }`}
              >
                {createSale.isPending ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
                    </svg>
                    Posting…
                  </span>
                ) : (
                  '✓ Confirm & Post'
                )}
              </Button>

              {(!locationId || !binId) && cart.length > 0 && (
                <p className="text-xs text-amber-600 text-center">
                  Select a location and bin to post the sale.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Invoice preview modal */}
      {postedBill && (
        <InvoicePreviewModal
          billId={postedBill.id}
          invoiceNumber={postedBill.invoiceNumber}
          onClose={() => setPostedBill(null)}
        />
      )}
    </>
  );
}
