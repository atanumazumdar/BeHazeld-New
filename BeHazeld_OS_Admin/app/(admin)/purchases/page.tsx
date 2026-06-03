'use client';

import Link from 'next/link';
import { useMemo } from 'react';
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
import { useFinanceAccounts, useJournalEntries } from '@/hooks/use-reports';

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

function numeric(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === 'string' ? parseFloat(value) : value;
  return Number.isFinite(parsed) ? parsed : 0;
}

function vendorFromText(value: string): string {
  const match = value.match(/\bfrom\s+([^()]+)/i);
  return match?.[1]?.trim() || 'Journal Entry';
}

function billNumberFromText(description: string, fallback: string): string {
  const match = description.match(/\(([^)]+)\)\s*$/);
  return match?.[1]?.trim() || fallback;
}

interface PurchaseRow {
  id: string;
  billNumber: string;
  vendor: string;
  date: string;
  tax: number;
  total: number;
  status: string;
  source: 'purchase_bill' | 'journal_entry';
}

export default function PurchasesPage() {
  const { data: bills = [], isLoading: billsLoading, error: billsError } = usePurchaseBills();
  const { data: vendors = [], isLoading: vendorsLoading } = useVendors();
  const { data: accounts = [], isLoading: accountsLoading } = useFinanceAccounts();
  const { data: journals = [], isLoading: journalsLoading } = useJournalEntries();

  const purchaseRows = useMemo<PurchaseRow[]>(() => {
    const vendorById = new Map(vendors.map((vendor) => [vendor.id, vendor.name]));
    const accountById = new Map(accounts.map((account) => [account.id, account]));
    const billRows: PurchaseRow[] = bills.map((bill) => ({
      id: bill.id,
      billNumber: bill.bill_number,
      vendor: vendorById.get(bill.vendor_id) ?? 'Purchase Bill',
      date: bill.bill_date,
      tax: numeric(bill.tax_amount),
      total: numeric(bill.total_amount),
      status: bill.status,
      source: 'purchase_bill',
    }));

    const existingBillNumbers = new Set(billRows.map((row) => row.billNumber));
    const journalRows = journals.flatMap((journal): PurchaseRow[] => {
        let inventoryDebit = 0;
        let taxDebit = 0;

        for (const line of journal.lines ?? []) {
          const account = accountById.get(line.account_id);
          const accountName = `${account?.account_code ?? ''} ${account?.name ?? ''}`.toLowerCase();
          const debit = numeric(line.debit_amount);
          if (debit <= 0) continue;

          const isInventoryAsset =
            account?.account_type === 'asset' &&
            (account?.account_code === '1200' ||
              account?.account_code === '1300' ||
              accountName.includes('inventory'));
          if (isInventoryAsset) {
            inventoryDebit += debit;
          }

          if (accountName.includes('gst')) {
            taxDebit += debit;
          }
        }

        if (inventoryDebit <= 0) return [];

        const billNumber = billNumberFromText(journal.description, journal.entry_number);
        if (existingBillNumbers.has(billNumber)) return [];

        return [{
          id: journal.id,
          billNumber,
          vendor: vendorFromText(journal.description),
          date: journal.entry_date,
          tax: taxDebit,
          total: inventoryDebit + taxDebit,
          status: 'from journal',
          source: 'journal_entry',
        }];
      });

    return [...billRows, ...journalRows].sort((a, b) => b.date.localeCompare(a.date));
  }, [accounts, bills, journals, vendors]);

  const totalPurchaseValue = purchaseRows.reduce((sum, row) => sum + row.total, 0);
  const derivedVendors = new Set(purchaseRows.map((row) => row.vendor).filter(Boolean));
  const loading = billsLoading || accountsLoading || journalsLoading;

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
          <p className="mt-2 text-xl font-bold text-slate-800">{loading ? '-' : purchaseRows.length}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Vendors</p>
          <p className="mt-2 text-xl font-bold text-slate-800">
            {vendorsLoading || journalsLoading ? '-' : Math.max(vendors.length, derivedVendors.size)}
          </p>
        </div>
      </div>

      {billsError && purchaseRows.length > 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Purchase bill records could not be loaded, so this page is showing purchases derived from Journal Entries.
        </div>
      ) : null}

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
            {loading ? (
              Array.from({ length: 4 }).map((_, rowIndex) => (
                <TableRow key={rowIndex}>
                  {Array.from({ length: 6 }).map((__, cellIndex) => (
                    <TableCell key={cellIndex}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : billsError && purchaseRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-red-500">
                  Failed to load purchases and no purchase Journal Entries were found.
                </TableCell>
              </TableRow>
            ) : purchaseRows.length === 0 ? (
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
              purchaseRows.map((row) => (
                <TableRow key={`${row.source}-${row.id}`}>
                  <TableCell className="font-mono text-sm text-slate-700">{row.billNumber}</TableCell>
                  <TableCell className="text-sm text-slate-700">{row.vendor}</TableCell>
                  <TableCell className="text-sm text-stone-500">{formatDate(row.date)}</TableCell>
                  <TableCell className="text-right font-mono text-sm text-stone-600">
                    {formatCurrency(row.tax)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-semibold text-slate-800">
                    {formatCurrency(row.total)}
                  </TableCell>
                  <TableCell className="text-right text-sm text-stone-500">{row.status}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
