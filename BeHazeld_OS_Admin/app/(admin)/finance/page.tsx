'use client';

/**
 * /finance — Financial Reporting page.
 *
 * Tab 1: Trial Balance — all accounts, DR/CR totals, net balance, balance check
 * Tab 2: P&L Statement — grouped by account type, date-range filterable
 *
 * Both tabs have a CSV export button (streams from the backend).
 * All numbers use professional financial formatting (red for negative).
 */

import { type ChangeEvent, useRef, useState } from 'react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

import {
  useTrialBalance,
  useProfitAndLoss,
  useImportAccountCodes,
  useImportJournalEntries,
  downloadTrialBalanceCsv,
  downloadProfitLossCsv,
} from '@/hooks/use-reports';

// ── Helpers ───────────────────────────────────────────────────────────────────

function money(value: string | number, showSign = false): string {
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(n)) return '—';
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Math.abs(n));
  if (showSign && n < 0) return `(${formatted})`;
  return formatted;
}

function moneyClass(value: string): string {
  const n = parseFloat(value);
  if (isNaN(n) || n === 0) return 'text-stone-600';
  return n < 0 ? 'text-red-600' : 'text-slate-700';
}

function importSummary(label: string, result: { imported: number; updated: number; skipped: number; errors: string[] }) {
  const summary = `${result.imported} imported${result.updated ? `, ${result.updated} updated` : ''}${result.skipped ? `, ${result.skipped} skipped` : ''}`;
  if (result.errors.length > 0) {
    const visibleErrors = result.errors.slice(0, 4).join('\n');
    const extraErrors = result.errors.length > 4 ? `\n...and ${result.errors.length - 4} more.` : '';
    toast.warning(`${label}: ${summary}.`, {
      description: `${visibleErrors}${extraErrors}`,
      duration: 12000,
    });
  } else {
    toast.success(`${label}: ${summary}.`);
  }
}

function FinanceImportToolbar() {
  const accountInputRef = useRef<HTMLInputElement | null>(null);
  const journalInputRef = useRef<HTMLInputElement | null>(null);
  const importAccounts = useImportAccountCodes();
  const importJournals = useImportJournalEntries();

  const handleAccountFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    try {
      const result = await importAccounts.mutateAsync(file);
      importSummary('Account codes imported', result);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to import account codes.';
      toast.error(message);
    }
  };

  const handleJournalFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    try {
      const result = await importJournals.mutateAsync(file);
      importSummary('Journal entries imported', result);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to import journal entries.';
      toast.error(message);
    }
  };

  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-700">Finance CSV Imports</p>
          <p className="mt-1 text-xs text-stone-500">
            Import account codes first, then journal entries.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <a
            href="/templates/finance_account_codes_reference.csv"
            className="inline-flex h-8 items-center rounded-lg border border-stone-200 px-2.5 text-xs font-medium text-slate-700 hover:bg-stone-50"
          >
            Account Template
          </a>
          <a
            href="/templates/finance_journal_entries_template.csv"
            className="inline-flex h-8 items-center rounded-lg border border-stone-200 px-2.5 text-xs font-medium text-slate-700 hover:bg-stone-50"
          >
            Journal Template
          </a>
          <Button
            variant="outline"
            size="sm"
            onClick={() => accountInputRef.current?.click()}
            disabled={importAccounts.isPending}
          >
            {importAccounts.isPending ? 'Importing…' : 'Import Account Codes'}
          </Button>
          <Button
            size="sm"
            onClick={() => journalInputRef.current?.click()}
            disabled={importJournals.isPending}
          >
            {importJournals.isPending ? 'Importing…' : 'Import Journal Entries'}
          </Button>
        </div>
      </div>
      <input
        ref={accountInputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={handleAccountFile}
      />
      <input
        ref={journalInputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={handleJournalFile}
      />
    </div>
  );
}

// ── Trial Balance tab ─────────────────────────────────────────────────────────

function TrialBalanceTab() {
  const { data: tb, isLoading } = useTrialBalance();
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    const ok = await downloadTrialBalanceCsv();
    setExporting(false);
    if (!ok) toast.error('Failed to download trial balance CSV.');
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {tb && (
            <Badge className={
              tb.is_balanced
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-red-100 text-red-700'
            }>
              {tb.is_balanced ? '✓ Balanced' : '⚠ Unbalanced'}
            </Badge>
          )}
          {tb && (
            <span className="text-xs text-stone-400">
              {tb.lines.length} accounts
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={exporting || isLoading}
          className="text-xs"
        >
          {exporting ? 'Exporting…' : '⬇ Export CSV'}
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-stone-600 font-medium text-xs w-24">Code</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs">Account</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs">Type</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs text-right">Debit</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs text-right">Credit</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs text-right">Net Balance</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : !tb || tb.lines.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-stone-400">
                  No journal entries yet. Post some transactions to see the trial balance.
                </TableCell>
              </TableRow>
            ) : (
              <>
                {tb.lines.map((line) => (
                  <TableRow key={line.account_code} className="hover:bg-stone-50/50">
                    <TableCell className="font-mono text-xs text-stone-400">
                      {line.account_code}
                    </TableCell>
                    <TableCell className="text-sm font-medium text-slate-700">
                      {line.name}
                    </TableCell>
                    <TableCell>
                      <span className="text-xs capitalize text-stone-500">
                        {line.account_type}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm text-slate-600">
                      {parseFloat(line.total_debit) > 0 ? money(line.total_debit) : '—'}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm text-slate-600">
                      {parseFloat(line.total_credit) > 0 ? money(line.total_credit) : '—'}
                    </TableCell>
                    <TableCell className={`text-right font-mono text-sm font-semibold ${moneyClass(line.net_balance)}`}>
                      {money(line.net_balance, true)}
                    </TableCell>
                  </TableRow>
                ))}

                {/* Totals footer */}
                <TableRow className="bg-slate-800 hover:bg-slate-800">
                  <TableCell colSpan={3} className="text-xs font-bold text-white py-3">
                    TOTALS
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-bold text-white">
                    {money(tb.total_debit)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-bold text-white">
                    {money(tb.total_credit)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-bold">
                    <Badge className={
                      tb.is_balanced
                        ? 'bg-emerald-500 text-white'
                        : 'bg-red-500 text-white'
                    }>
                      {tb.is_balanced ? 'BALANCED' : 'UNBALANCED'}
                    </Badge>
                  </TableCell>
                </TableRow>
              </>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ── P&L tab ───────────────────────────────────────────────────────────────────

function ProfitAndLossTab() {
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [exporting, setExporting] = useState(false);

  const { data: pl, isLoading } = useProfitAndLoss(fromDate || undefined, toDate || undefined);

  const handleExport = async () => {
    setExporting(true);
    const ok = await downloadProfitLossCsv(fromDate || undefined, toDate || undefined);
    setExporting(false);
    if (!ok) toast.error('Failed to download P&L CSV.');
  };

  const netProfitNum = pl ? parseFloat(pl.net_profit) : 0;
  const isProfit = netProfitNum >= 0;

  return (
    <div className="space-y-4">
      {/* Filters + export */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <span>From</span>
          <Input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="w-36 bg-white h-9 text-sm"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <span>To</span>
          <Input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="w-36 bg-white h-9 text-sm"
          />
        </div>
        {(fromDate || toDate) && (
          <Button
            variant="ghost"
            size="sm"
            className="text-stone-400 h-9 text-xs"
            onClick={() => { setFromDate(''); setToDate(''); }}
          >
            Clear
          </Button>
        )}
        <div className="ml-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={exporting || isLoading}
            className="text-xs"
          >
            {exporting ? 'Exporting…' : '⬇ Export CSV'}
          </Button>
        </div>
      </div>

      {/* P&L Statement */}
      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-5 w-full" />
            ))}
          </div>
        ) : !pl ? (
          <p className="p-8 text-center text-stone-400">No data available.</p>
        ) : (
          <div className="divide-y divide-stone-100">
            {/* Revenue section */}
            <div className="px-6 py-3 bg-stone-50">
              <p className="text-xs font-bold text-stone-500 uppercase tracking-wider">
                Revenue / Income
              </p>
            </div>
            <PLRow label="Total Revenue" value={pl.total_revenue} />

            <Separator />

            {/* COGS section */}
            <div className="px-6 py-3 bg-stone-50">
              <p className="text-xs font-bold text-stone-500 uppercase tracking-wider">
                Cost of Goods Sold
              </p>
            </div>
            <PLRow label="Total COGS (Purchase Cost)" value={pl.total_cogs} invert />

            {/* Gross Profit */}
            <PLRow
              label="Gross Profit"
              value={pl.gross_profit}
              isSummary
              isPositive={parseFloat(pl.gross_profit) >= 0}
            />

            <Separator />

            {/* Expenses section */}
            <div className="px-6 py-3 bg-stone-50">
              <p className="text-xs font-bold text-stone-500 uppercase tracking-wider">
                Operating Expenses
              </p>
            </div>
            <PLRow label="Total Expenses" value={pl.total_expenses} invert />

            <Separator />

            {/* Net Profit */}
            <div className={`px-6 py-4 ${isProfit ? 'bg-emerald-50' : 'bg-red-50'}`}>
              <div className="flex items-center justify-between">
                <p className="text-base font-bold text-slate-800">Net Profit / (Loss)</p>
                <p className={`text-xl font-bold tabular-nums ${isProfit ? 'text-emerald-700' : 'text-red-600'}`}>
                  {isProfit ? '' : '('}{money(pl.net_profit)}{isProfit ? '' : ')'}
                </p>
              </div>
              {pl.from_date && pl.to_date && (
                <p className="text-xs text-stone-400 mt-1">
                  Period: {pl.from_date} to {pl.to_date}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PLRow({
  label,
  value,
  invert = false,
  isSummary = false,
  isPositive,
}: {
  label: string;
  value: string;
  invert?: boolean;
  isSummary?: boolean;
  isPositive?: boolean;
}) {
  const n = parseFloat(value);
  let colorClass = 'text-slate-700';
  if (isSummary) {
    colorClass = isPositive ? 'text-emerald-700' : 'text-red-600';
  } else if (invert && n > 0) {
    colorClass = 'text-red-600';
  }

  return (
    <div className={`flex items-center justify-between px-6 py-3 ${isSummary ? 'bg-slate-50 border-t border-b border-stone-200' : ''}`}>
      <p className={`text-sm ${isSummary ? 'font-semibold text-slate-800' : 'text-stone-600'}`}>
        {label}
      </p>
      <p className={`font-mono text-sm tabular-nums ${isSummary ? 'font-bold text-base' : 'font-medium'} ${colorClass}`}>
        {invert && n > 0 ? `(${money(value)})` : money(value)}
      </p>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = 'trial-balance' | 'pl';

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<Tab>('trial-balance');

  const TABS: { id: Tab; label: string }[] = [
    { id: 'trial-balance', label: 'Trial Balance' },
    { id: 'pl', label: 'Profit & Loss' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Financial Reports</h1>
        <p className="mt-1 text-sm text-stone-500">
          Read-only financial statements — all figures are tenant-scoped.
        </p>
      </div>

      <FinanceImportToolbar />

      {/* Tab nav */}
      <nav className="flex gap-1 border-b border-stone-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-slate-800 text-slate-800'
                : 'border-transparent text-stone-500 hover:text-stone-700 hover:border-stone-300',
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      {activeTab === 'trial-balance' ? <TrialBalanceTab /> : <ProfitAndLossTab />}
    </div>
  );
}
