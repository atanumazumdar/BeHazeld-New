'use client';

import Link from 'next/link';
import { ArrowLeft, FilePlus2, PackagePlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useVendors } from '@/hooks/use-purchases';
import { useLocations } from '@/hooks/use-inventory';

export default function NewPurchasePage() {
  const { data: vendors = [], isLoading: vendorsLoading } = useVendors();
  const { data: locations = [], isLoading: locationsLoading } = useLocations();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/purchases"
            className="mb-2 inline-flex items-center gap-1 text-sm text-stone-500 hover:text-slate-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Purchases
          </Link>
          <h1 className="text-2xl font-semibold text-slate-800">New Purchase</h1>
          <p className="mt-1 text-sm text-stone-500">
            Record vendor bills and stock receipts.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Vendors Available</p>
          <p className="mt-2 text-xl font-bold text-slate-800">{vendorsLoading ? '-' : vendors.length}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Stock Locations</p>
          <p className="mt-2 text-xl font-bold text-slate-800">{locationsLoading ? '-' : locations.length}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Purchase Entry</p>
          <p className="mt-2 text-xl font-bold text-slate-800">Ready</p>
        </div>
      </div>

      <div className="rounded-xl border border-stone-200 bg-white p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
              <FilePlus2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-800">Purchase bill entry form</h2>
              <p className="mt-1 max-w-2xl text-sm text-stone-500">
                The purchase backend is available. The next step is adding the full bill-entry form with vendor,
                bill number, location, bin, SKU lines, quantity, unit cost, and GST.
              </p>
            </div>
          </div>
          <Button className="bg-slate-800 text-white hover:bg-slate-700" disabled>
            <PackagePlus className="h-4 w-4" />
            Record Purchase
          </Button>
        </div>

        <div className="mt-6 rounded-lg border border-dashed border-stone-300 bg-stone-50 p-4">
          <p className="text-sm font-medium text-slate-700">Fields that will be captured here:</p>
          <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-stone-600 sm:grid-cols-2 lg:grid-cols-3">
            <span>Vendor</span>
            <span>Bill number</span>
            <span>Bill date</span>
            <span>Location</span>
            <span>Bin</span>
            <span>SKU / Variant</span>
            <span>Quantity</span>
            <span>Unit cost</span>
            <span>GST rate</span>
          </div>
        </div>
      </div>
    </div>
  );
}
