'use client';

/**
 * /sales/[billId] — Sale detail view.
 *
 * Shows:
 *  - Invoice header: number, date, status, customer
 *  - Line items table with qty, price, discount, tax, line total
 *  - Payment section: mode, amount, transaction ID
 *  - Bill-level totals: subtotal, tax, discount, grand total
 *  - "Preview PDF" and "Download PDF" actions
 */

import { useState } from 'react';
import Link from 'next/link';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { InvoicePreviewModal } from '@/components/sales/invoice-preview-modal';

import { useBill, downloadInvoicePdf } from '@/hooks/use-sales';

const PAYMENT_MODE_LABELS: Record<string, string> = {
  cash: 'Cash',
  upi: 'UPI',
  bank_transfer: 'Bank Transfer',
  cheque: 'Cheque',
};

interface PageProps {
  params: { billId: string };
}

export default function SaleDetailPage({ params }: PageProps) {
  const { billId } = params;
  const { data: bill, isLoading, error } = useBill(billId);
  const [showPreview, setShowPreview] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    const ok = await downloadInvoicePdf(billId);
    setDownloading(false);
    if (!ok) toast.error('Failed to download PDF.');
  };

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-3xl">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !bill) {
    return (
      <div className="text-center py-16">
        <p className="text-stone-500">Invoice not found.</p>
        <Link href="/sales" className="mt-3 text-sm text-blue-500 hover:underline">
          ← Back to Sales
        </Link>
      </div>
    );
  }

  const subtotal =
    parseFloat(bill.total_amount) +
    parseFloat(bill.total_discount) -
    parseFloat(bill.tax_amount);
  const payment = bill.payments[0];

  return (
    <>
      <div className="max-w-3xl space-y-6">
        {/* Nav */}
        <Link href="/sales" className="text-sm text-stone-400 hover:text-stone-600">
          ← Sales History
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800 font-mono">
              {bill.invoice_number}
            </h1>
            <p className="mt-1 text-sm text-stone-500">
              {new Date(bill.bill_date).toLocaleDateString('en-IN', {
                day: '2-digit', month: 'long', year: 'numeric',
              })}
              {' · '}
              <Badge className={
                bill.status === 'confirmed'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-red-100 text-red-700'
              }>
                {bill.status}
              </Badge>
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreview(true)}
              className="text-xs"
            >
              Preview PDF
            </Button>
            <Button
              size="sm"
              onClick={handleDownload}
              disabled={downloading}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-white"
            >
              {downloading ? 'Downloading…' : '⬇ Download PDF'}
            </Button>
          </div>
        </div>

        {/* Customer */}
        <div className="rounded-xl border border-stone-200 bg-white p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Customer</p>
          {bill.customer_id ? (
            <p className="text-sm text-slate-700">Customer ID: <span className="font-mono text-xs">{bill.customer_id}</span></p>
          ) : (
            <p className="text-sm text-stone-400 italic">Walk-in / Cash Customer</p>
          )}
        </div>

        {/* Line items */}
        <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
          <div className="px-4 py-3 bg-stone-50 border-b border-stone-200">
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Items ({bill.lines.length})
            </h2>
          </div>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-stone-500 font-medium text-xs">SKU</TableHead>
                <TableHead className="text-stone-500 font-medium text-xs text-right">Qty</TableHead>
                <TableHead className="text-stone-500 font-medium text-xs text-right">Price</TableHead>
                <TableHead className="text-stone-500 font-medium text-xs text-right">Discount</TableHead>
                <TableHead className="text-stone-500 font-medium text-xs text-right">Tax</TableHead>
                <TableHead className="text-stone-500 font-medium text-xs text-right">Line Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bill.lines.map((line) => (
                <TableRow key={line.id} className="hover:bg-stone-50/50">
                  <TableCell className="font-mono text-xs text-slate-600">
                    {line.product_variant_id.slice(0, 8)}…
                  </TableCell>
                  <TableCell className="text-right text-sm">{line.quantity}</TableCell>
                  <TableCell className="text-right font-mono text-sm">₹{line.selling_price}</TableCell>
                  <TableCell className="text-right font-mono text-sm text-stone-500">
                    {parseFloat(line.discount_amount) > 0 ? `₹${line.discount_amount}` : '—'}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm text-stone-500">
                    {parseFloat(line.tax_rate) > 0 ? `${(parseFloat(line.tax_rate) * 100).toFixed(0)}%` : '—'}
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold text-slate-800">
                    ₹{line.total_line_amount}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Totals footer */}
          <div className="border-t border-stone-200 px-4 py-3 space-y-1 bg-stone-50">
            <div className="flex justify-between text-sm text-stone-600">
              <span>Subtotal</span>
              <span className="font-mono">₹{subtotal.toFixed(2)}</span>
            </div>
            {parseFloat(bill.total_discount) > 0 && (
              <div className="flex justify-between text-sm text-stone-600">
                <span>Total Discount</span>
                <span className="font-mono text-emerald-600">−₹{bill.total_discount}</span>
              </div>
            )}
            <div className="flex justify-between text-sm text-stone-600">
              <span>Tax</span>
              <span className="font-mono">₹{bill.tax_amount}</span>
            </div>
            <Separator className="my-1" />
            <div className="flex justify-between text-base font-semibold text-slate-800">
              <span>Grand Total</span>
              <span className="font-mono">₹{bill.total_amount}</span>
            </div>
          </div>
        </div>

        {/* Payment */}
        {payment && (
          <div className="rounded-xl border border-stone-200 bg-white p-4 space-y-2">
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Payment</h2>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-xs text-stone-400 mb-0.5">Mode</p>
                <p className="font-medium text-slate-700">
                  {PAYMENT_MODE_LABELS[payment.payment_mode] ?? payment.payment_mode}
                </p>
              </div>
              <div>
                <p className="text-xs text-stone-400 mb-0.5">Amount</p>
                <p className="font-mono font-semibold text-slate-800">₹{payment.amount}</p>
              </div>
              {payment.transaction_id && (
                <div>
                  <p className="text-xs text-stone-400 mb-0.5">Transaction ID</p>
                  <p className="font-mono text-xs text-slate-600">{payment.transaction_id}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* PDF preview modal */}
      {showPreview && (
        <InvoicePreviewModal
          billId={billId}
          invoiceNumber={bill.invoice_number}
          onClose={() => setShowPreview(false)}
        />
      )}
    </>
  );
}
