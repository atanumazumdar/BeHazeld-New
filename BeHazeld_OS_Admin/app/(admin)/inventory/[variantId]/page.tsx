'use client';

/**
 * /inventory/[variantId] — SKU stock detail page.
 *
 * Shows:
 *  - Stock summary table (one row per location/bin with on-hand / reserved / available)
 *  - Full stock ledger (last 100 movements) for a selected location
 *  - StockAdjustmentForm for recording manual movements
 *
 * Uses TanStack Query; queries auto-invalidate after a successful movement.
 */

import { use, useState } from 'react';
import { useStockSummary, useLedger, useLocations } from '@/hooks/use-inventory';
import { StockAdjustmentForm } from '@/components/inventory/stock-adjustment-form';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

// ── Movement type colour map ──────────────────────────────────────────────────

const MOVEMENT_COLOURS: Record<string, string> = {
  opening_stock: 'bg-blue-100 text-blue-700',
  purchase_in: 'bg-emerald-100 text-emerald-700',
  sale_out: 'bg-rose-100 text-rose-700',
  return_in: 'bg-amber-100 text-amber-700',
  adjustment_in: 'bg-teal-100 text-teal-700',
  adjustment_out: 'bg-orange-100 text-orange-700',
  transfer_in: 'bg-violet-100 text-violet-700',
  transfer_out: 'bg-purple-100 text-purple-700',
};

const MOVEMENT_LABELS: Record<string, string> = {
  opening_stock: 'Opening',
  purchase_in: 'Purchase In',
  sale_out: 'Sale Out',
  return_in: 'Return In',
  adjustment_in: 'Adj. In',
  adjustment_out: 'Adj. Out',
  transfer_in: 'Transfer In',
  transfer_out: 'Transfer Out',
};

// ── Page ──────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ variantId: string }>;
}

export default function InventoryVariantPage({ params }: PageProps) {
  const { variantId } = use(params);
  const [selectedLocationId, setSelectedLocationId] = useState<string>('');

  const { data: locations = [] } = useLocations();
  const { data: summary = [], isLoading: summaryLoading } = useStockSummary(variantId);
  const { data: ledger = [], isLoading: ledgerLoading } = useLedger(
    variantId,
    selectedLocationId,
  );

  const locationName = (id: string) =>
    locations.find((l) => l.id === id)?.name ?? id.slice(0, 8);
  const binName = (locationId: string, binId: string) =>
    locations.find((l) => l.id === locationId)?.bins.find((b) => b.id === binId)?.name ?? binId.slice(0, 8);

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <p className="text-xs text-stone-400 font-mono mb-1">SKU</p>
        <h1 className="text-2xl font-semibold text-slate-800 font-mono">{variantId}</h1>
        <p className="mt-1 text-sm text-stone-500">
          Stock balances and movement ledger for this variant.
        </p>
      </div>

      {/* ── Stock summary ── */}
      <section>
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">
          Stock Summary
        </h2>
        <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-stone-50 hover:bg-stone-50">
                <TableHead className="text-stone-600 font-medium">Location</TableHead>
                <TableHead className="text-stone-600 font-medium">Bin</TableHead>
                <TableHead className="text-stone-600 font-medium text-right">On Hand</TableHead>
                <TableHead className="text-stone-600 font-medium text-right">Reserved</TableHead>
                <TableHead className="text-stone-600 font-medium text-right">Available</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summaryLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : summary.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-10 text-center text-stone-400">
                    No stock found. Record an opening stock movement below.
                  </TableCell>
                </TableRow>
              ) : (
                summary.map((row) => {
                  const avail = parseFloat(row.quantity_available);
                  return (
                    <TableRow key={row.id} className="hover:bg-stone-50/60">
                      <TableCell className="text-slate-700">{locationName(row.location_id)}</TableCell>
                      <TableCell className="text-stone-500 text-sm">{binName(row.location_id, row.bin_id)}</TableCell>
                      <TableCell className="text-right font-mono text-slate-700">{row.quantity_on_hand}</TableCell>
                      <TableCell className="text-right font-mono text-stone-500">{row.quantity_reserved}</TableCell>
                      <TableCell className="text-right">
                        <span className={`font-mono font-medium ${avail <= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                          {row.quantity_available}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      {/* ── Stock adjustment form ── */}
      <StockAdjustmentForm variantId={variantId} />

      {/* ── Ledger ── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Movement Ledger
          </h2>
          <Select
            onValueChange={(val) => setSelectedLocationId(val ?? '')}
            value={selectedLocationId}
          >
            <SelectTrigger className="w-52 bg-white h-8 text-sm">
              <SelectValue placeholder="Filter by location…" />
            </SelectTrigger>
            <SelectContent>
              {locations.map((l) => (
                <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-stone-50 hover:bg-stone-50">
                <TableHead className="text-stone-600 font-medium">Type</TableHead>
                <TableHead className="text-stone-600 font-medium">Location</TableHead>
                <TableHead className="text-stone-600 font-medium">Bin</TableHead>
                <TableHead className="text-stone-600 font-medium text-right">Qty Change</TableHead>
                <TableHead className="text-stone-600 font-medium text-right">Unit Cost</TableHead>
                <TableHead className="text-stone-600 font-medium">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!selectedLocationId ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-stone-400">
                    Select a location above to view its ledger.
                  </TableCell>
                </TableRow>
              ) : ledgerLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : ledger.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-stone-400">
                    No movements found for this location.
                  </TableCell>
                </TableRow>
              ) : (
                ledger.map((entry) => {
                  const qty = parseFloat(entry.quantity_change);
                  return (
                    <TableRow key={entry.id} className="hover:bg-stone-50/60">
                      <TableCell>
                        <Badge
                          className={`text-xs font-medium ${MOVEMENT_COLOURS[entry.movement_type] ?? 'bg-stone-100 text-stone-600'}`}
                        >
                          {MOVEMENT_LABELS[entry.movement_type] ?? entry.movement_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-stone-600 text-sm">
                        {locationName(entry.location_id)}
                      </TableCell>
                      <TableCell className="text-stone-500 text-sm">
                        {binName(entry.location_id, entry.bin_id)}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={`font-mono font-medium ${qty >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                          {qty >= 0 ? '+' : ''}{entry.quantity_change}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-stone-600">
                        {entry.unit_cost}
                      </TableCell>
                      <TableCell className="text-stone-500 text-sm">
                        {entry.notes ?? '—'}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  );
}
