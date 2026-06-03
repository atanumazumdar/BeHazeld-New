'use client';

import Link from 'next/link';
import { Plus, Truck } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { usePurchaseBills, useVendors } from '@/hooks/use-purchases';

function formatCurrency(value: string | number | undefined): string {
  const amount = typeof value === 'string' ? parseFloat(value) : value;
  if (amount === undefined || Number.isNaN(amount)) return '-';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(value: string | undefined): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export default function PurchasesPage() {
  const { data: bills = [], isLoading: billsLoading, error: billsError } = usePurchaseBills();
  const { data: vendors = [], isLoading: vendorsLoading } = useVendors();
  const vendorById = new Map(vendors.map((vendor) => [vendor.id, vendor.name]));

  const totalPurchaseValue = bills.reduce(
    (sum, bill) => sum + (parseFloat(bill.total_amount) || 0),
    0,
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Purchases</h1>
          <p className="mt-1 text-sm text-stone-500">
            Purchase bills, vendors, stock receipts, and input tax.
          </p>
        </div>
        <Link
          href="/purchases/new"
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-slate-800 px-3 text-sm font-semibold text-white hover:bg-slate-700"
        >
          <Plus className="h-4 w-4" />
          New Purchase
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Purchase Value</p>
          <p className="mt-2 text-xl font-bold text-slate-800">{formatCurrency(totalPurchaseValue)}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Bills</p>
          <p className="mt-2 text-xl font-bold text-slate-800">{billsLoading ? '-' : bills.length}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Vendors</p>
          <p className="mt-2 text-xl font-bold text-slate-800">{vendorsLoading ? '-' : vendors.length}</p>
        </div>
      </div>

      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-xs font-medium text-stone-600">Bill Number</TableHead>
              <TableHead className="text-xs font-medium text-stone-600">Vendor</TableHead>
              <TableHead className="text-xs font-medium text-stone-600">Date</TableHead>
              <TableHead className="text-xs font-medium text-stone-600 text-right">Tax</TableHead>
              <TableHead className="text-xs font-medium text-stone-600 text-right">Total</TableHead>
              <TableHead className="text-xs font-medium text-stone-600 text-right">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {billsLoading ? (
              Array.from({ length: 4 }).map((_, rowIndex) => (
                <TableRow key={rowIndex}>
                  {Array.from({ length: 6 }).map((__, cellIndex) => (
                    <TableCell key={cellIndex}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : billsError ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-red-500">
                  Failed to load purchases.
                </TableCell>
              </TableRow>
            ) : bills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-stone-400">
                  <div className="flex flex-col items-center gap-2">
                    <Truck className="h-7 w-7 text-stone-300" />
                    <span>No purchase bills recorded yet.</span>
                    <Button size="sm" className="mt-2 bg-slate-800 text-white hover:bg-slate-700">
                      <Link href="/purchases/new">Create first purchase</Link>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              bills.map((bill) => (
                <TableRow key={bill.id}>
                  <TableCell className="font-mono text-sm text-slate-700">{bill.bill_number}</TableCell>
                  <TableCell className="text-sm text-slate-700">
                    {vendorById.get(bill.vendor_id) ?? bill.vendor_id}
                  </TableCell>
                  <TableCell className="text-sm text-stone-500">{formatDate(bill.bill_date)}</TableCell>
                  <TableCell className="text-right font-mono text-sm text-stone-600">
                    {formatCurrency(bill.tax_amount)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-semibold text-slate-800">
                    {formatCurrency(bill.total_amount)}
                  </TableCell>
                  <TableCell className="text-right text-sm text-stone-500">{bill.status}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
