'use client';

/**
 * /sales — Sales History page.
 *
 * Shows all bills with date-range and customer filters.
 * Each row has: "View" → /sales/[billId], "Preview PDF", "Download PDF"
 */

import { useState } from 'react';
import Link from 'next/link';
import { toast } from 'sonner';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
// Note: Button's asChild is not available in Shadcn v4 (base-ui); use Link directly
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { InvoicePreviewModal } from '@/components/sales/invoice-preview-modal';

import { useBills } from '@/hooks/use-sales';
import { downloadInvoicePdf } from '@/hooks/use-sales';

const PAGE_SIZE = 20;

export default function SalesHistoryPage() {
  const [skip, setSkip] = useState(0);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [previewBill, setPreviewBill] = useState<{
    id: string;
    invoiceNumber: string;
  } | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const { data: bills = [], isLoading, isFetching } = useBills({
    skip,
    limit: PAGE_SIZE,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const handleDownload = async (billId: string) => {
    setDownloading(billId);
    const ok = await downloadInvoicePdf(billId);
    setDownloading(null);
    if (!ok) toast.error('Failed to download PDF.');
  };

  const loading = isLoading || isFetching;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Sales History</h1>
          <p className="mt-1 text-sm text-stone-500">
            All confirmed sale invoices for your account.
          </p>
        </div>
        <Link
          href="/sales/new"
          className="inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium bg-slate-800 hover:bg-slate-700 text-white transition-colors"
        >
          + New Sale
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <span>From</span>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setSkip(0); }}
            className="w-36 bg-white h-9 text-sm"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <span>To</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setSkip(0); }}
            className="w-36 bg-white h-9 text-sm"
          />
        </div>
        {(dateFrom || dateTo) && (
          <Button
            variant="ghost"
            size="sm"
            className="text-stone-400 h-9 text-xs"
            onClick={() => { setDateFrom(''); setDateTo(''); setSkip(0); }}
          >
            Clear dates
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-stone-600 font-medium">Invoice #</TableHead>
              <TableHead className="text-stone-600 font-medium">Date</TableHead>
              <TableHead className="text-stone-600 font-medium">Customer</TableHead>
              <TableHead className="text-stone-600 font-medium">Items</TableHead>
              <TableHead className="text-stone-600 font-medium">Status</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Total</TableHead>
              <TableHead className="text-stone-600 font-medium text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : bills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-stone-400">
                  No sales found.{' '}
                  <Link href="/sales/new" className="text-blue-500 hover:underline">
                    Create your first sale →
                  </Link>
                </TableCell>
              </TableRow>
            ) : (
              bills.map((bill) => (
                <TableRow key={bill.id} className="hover:bg-stone-50/60">
                  <TableCell className="font-mono text-sm text-slate-700">
                    {bill.invoice_number}
                  </TableCell>
                  <TableCell className="text-stone-600 text-sm">
                    {new Date(bill.bill_date).toLocaleDateString('en-IN', {
                      day: '2-digit', month: 'short', year: 'numeric',
                    })}
                  </TableCell>
                  <TableCell className="text-stone-600 text-sm">
                    {bill.customer_id ? (
                      <span className="text-slate-700">Customer</span>
                    ) : (
                      <span className="text-stone-400 italic">Walk-in</span>
                    )}
                  </TableCell>
                  <TableCell className="text-stone-600 text-sm">
                    {bill.lines.length} item{bill.lines.length !== 1 ? 's' : ''}
                  </TableCell>
                  <TableCell>
                    <Badge className={
                      bill.status === 'confirmed'
                        ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100'
                        : 'bg-red-100 text-red-700 hover:bg-red-100'
                    }>
                      {bill.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold text-slate-800">
                    ₹{parseFloat(bill.total_amount).toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Link
                        href={`/sales/${bill.id}`}
                        className="inline-flex items-center px-2 py-1 text-xs text-slate-600 hover:text-slate-800 hover:bg-stone-100 rounded transition-colors"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => setPreviewBill({ id: bill.id, invoiceNumber: bill.invoice_number })}
                        className="inline-flex items-center px-2 py-1 text-xs text-slate-600 hover:text-slate-800 hover:bg-stone-100 rounded transition-colors"
                      >
                        Preview
                      </button>
                      <button
                        onClick={() => handleDownload(bill.id)}
                        disabled={downloading === bill.id}
                        className="inline-flex items-center px-2 py-1 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors disabled:opacity-50"
                      >
                        {downloading === bill.id ? '…' : '⬇ PDF'}
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-stone-500">
        <span>{loading ? '…' : `${bills.length} result${bills.length !== 1 ? 's' : ''}`}</span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={skip === 0 || loading}
            onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={bills.length < PAGE_SIZE || loading}
            onClick={() => setSkip(skip + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>

      {/* PDF preview modal */}
      {previewBill && (
        <InvoicePreviewModal
          billId={previewBill.id}
          invoiceNumber={previewBill.invoiceNumber}
          onClose={() => setPreviewBill(null)}
        />
      )}
    </div>
  );
}
