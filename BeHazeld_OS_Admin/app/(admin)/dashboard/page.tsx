'use client';

/**
 * Executive Dashboard — live KPI cards + low-stock alert table.
 *
 * Metrics fetched:
 *  - GET /dashboard/metrics    → revenue, COGS, gross profit, tax collected, active SKUs
 *  - GET /finance/reports/profit-and-loss → net_profit, total_expenses
 *  - GET /reports/gst          → net_gst_payable
 *  - GET /reports/low-stock    → low-stock variant list
 *
 * All queries use refetchInterval so numbers update without page reload.
 */

import Link from 'next/link';
import { useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Package,
  AlertTriangle,
  Coins,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  useDashboardMetrics,
  useGstSummary,
  useLowStock,
  useProfitAndLoss,
} from '@/hooks/use-reports';
import { useProducts } from '@/hooks/use-catalog';
import { useBills } from '@/hooks/use-sales';

// ── Formatters ────────────────────────────────────────────────────────────────

function fmt(value: string | number | undefined): string {
  if (value === undefined) return '—';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(n)) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtNum(value: number | undefined): string {
  if (value === undefined) return '—';
  return value.toLocaleString('en-IN');
}

function num(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === 'string' ? parseFloat(value) : value;
  return Number.isFinite(parsed) ? parsed : 0;
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

interface KpiCardProps {
  title: string;
  value: string;
  subtext?: string;
  icon: React.ElementType;
  loading: boolean;
  sentiment?: 'positive' | 'negative' | 'neutral' | 'warning';
}

const SENTIMENT_CLASSES = {
  positive: {
    icon: 'text-emerald-600',
    value: 'text-emerald-700',
    bar: 'bg-emerald-500',
  },
  negative: {
    icon: 'text-red-500',
    value: 'text-red-600',
    bar: 'bg-red-500',
  },
  neutral: {
    icon: 'text-slate-500',
    value: 'text-slate-800',
    bar: 'bg-slate-400',
  },
  warning: {
    icon: 'text-amber-500',
    value: 'text-amber-700',
    bar: 'bg-amber-500',
  },
};

function KpiCard({ title, value, subtext, icon: Icon, loading, sentiment = 'neutral' }: KpiCardProps) {
  const cls = SENTIMENT_CLASSES[sentiment];
  return (
    <Card className="border-stone-200 shadow-sm overflow-hidden">
      <div className={`h-0.5 w-full ${cls.bar}`} />
      <CardHeader className="flex flex-row items-start justify-between pb-1 pt-4 space-y-0 px-5">
        <CardTitle className="text-xs font-semibold text-stone-500 uppercase tracking-wider leading-tight">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${cls.icon}`} />
      </CardHeader>
      <CardContent className="px-5 pb-4">
        {loading ? (
          <Skeleton className="h-8 w-28 mt-1" />
        ) : (
          <p className={`text-2xl font-bold tabular-nums ${cls.value}`}>
            {value}
          </p>
        )}
        {subtext && (
          <p className="text-xs text-stone-400 mt-1">{subtext}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: pl, isLoading: plLoading } = useProfitAndLoss();
  const { data: gst, isLoading: gstLoading } = useGstSummary();
  const { data: lowStock = [], isLoading: lowStockLoading } = useLowStock();
  const { data: salesBills = [], isLoading: salesLoading } = useBills({ limit: 1000 });
  const { data: products = [], isLoading: productsLoading } = useProducts({
    status: 'active',
    limit: 1000,
  });

  const fallbackMetrics = useMemo(() => {
    const variantCost = new Map<string, number>();
    let activeSkus = 0;

    for (const product of products) {
      for (const variant of product.variants ?? []) {
        if (variant.status !== 'active') continue;
        activeSkus += 1;
        variantCost.set(variant.id, num(variant.cost_price));
      }
    }

    let totalRevenue = 0;
    let totalTaxCollected = 0;
    let totalCogs = 0;

    for (const bill of salesBills) {
      if (bill.status !== 'confirmed') continue;
      totalRevenue += num(bill.total_amount);
      totalTaxCollected += num(bill.tax_amount);

      for (const line of bill.lines ?? []) {
        const unitCost = num(line.unit_cost) || variantCost.get(line.product_variant_id) || 0;
        totalCogs += num(line.quantity) * unitCost;
      }
    }

    return {
      totalRevenue,
      totalTaxCollected,
      totalCogs,
      grossProfit: totalRevenue - totalCogs,
      activeSkus,
    };
  }, [products, salesBills]);

  const hasMetrics = Boolean(metrics);
  const dashboardLoading = hasMetrics
    ? false
    : metricsLoading || salesLoading || productsLoading;
  const totalRevenue = hasMetrics ? num(metrics?.total_revenue) : fallbackMetrics.totalRevenue;
  const totalCogs = hasMetrics ? num(metrics?.total_cogs) : fallbackMetrics.totalCogs;
  const grossProfit = hasMetrics ? num(metrics?.gross_profit) : fallbackMetrics.grossProfit;
  const activeSkus = hasMetrics ? metrics?.active_skus : fallbackMetrics.activeSkus;
  const taxCollected = gst ? num(gst.sales_tax_collected) : fallbackMetrics.totalTaxCollected;
  const taxPaid = gst ? num(gst.purchase_tax_paid) : 0;
  const gstPayable = gst ? num(gst.net_gst_payable) : taxCollected - taxPaid;

  const operatingExpenses = pl ? parseFloat(pl.total_expenses) : undefined;
  const netProfit =
    grossProfit === undefined || operatingExpenses === undefined
      ? undefined
      : grossProfit - operatingExpenses;
  const grossProfitSentiment =
    grossProfit === undefined ? 'neutral' : grossProfit >= 0 ? 'positive' : 'negative';
  const netProfitSentiment =
    netProfit === undefined ? 'neutral' : netProfit >= 0 ? 'positive' : 'negative';

  const gstSentiment =
    gstPayable === undefined ? 'neutral' : gstPayable <= 0 ? 'positive' : 'warning';

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Executive Dashboard</h1>
        <p className="mt-1 text-sm text-stone-500">
          Live business metrics — refreshes every 2 minutes.
        </p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          title="Total Revenue"
          value={dashboardLoading ? '—' : fmt(totalRevenue)}
          subtext="Confirmed sales"
          icon={TrendingUp}
          loading={dashboardLoading}
          sentiment="positive"
        />
        <KpiCard
          title="COGS"
          value={dashboardLoading ? '—' : fmt(totalCogs)}
          subtext="Cost of sold SKUs"
          icon={TrendingDown}
          loading={dashboardLoading}
          sentiment="neutral"
        />
        <KpiCard
          title="Gross Profit"
          value={dashboardLoading ? '—' : fmt(grossProfit)}
          subtext="Revenue − COGS"
          icon={TrendingUp}
          loading={dashboardLoading}
          sentiment={grossProfitSentiment}
        />
        <KpiCard
          title="Net Profit"
          value={netProfit === undefined ? '—' : fmt(netProfit)}
          subtext="Gross Profit − Expenses"
          icon={netProfit !== undefined && netProfit < 0 ? TrendingDown : TrendingUp}
          loading={dashboardLoading || plLoading}
          sentiment={netProfitSentiment}
        />
        <KpiCard
          title="GST Payable"
          value={gstLoading || dashboardLoading ? '—' : fmt(gstPayable)}
          subtext="Tax Collected − Tax Paid"
          icon={Coins}
          loading={gstLoading || dashboardLoading}
          sentiment={gstSentiment}
        />
        <KpiCard
          title="Active SKUs"
          value={dashboardLoading ? '—' : fmtNum(activeSkus)}
          subtext={`${lowStock.length} below reorder`}
          icon={Package}
          loading={dashboardLoading}
          sentiment={lowStock.length > 0 ? 'warning' : 'neutral'}
        />
      </div>

      {/* Secondary metrics row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">
            Tax Collected (Sales)
          </p>
          {gstLoading || dashboardLoading ? (
            <Skeleton className="h-5 w-24" />
          ) : (
            <p className="text-base font-semibold text-slate-700 tabular-nums">
              {fmt(taxCollected)}
            </p>
          )}
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">
            Tax Paid (Purchases / ITC)
          </p>
          {gstLoading ? (
            <Skeleton className="h-5 w-24" />
          ) : (
            <p className="text-base font-semibold text-slate-700 tabular-nums">
              {fmt(taxPaid)}
            </p>
          )}
        </div>
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-1">
            Total Operating Expenses
          </p>
          {plLoading ? (
            <Skeleton className="h-5 w-24" />
          ) : (
            <p className="text-base font-semibold text-slate-700 tabular-nums">
              {fmt(pl?.total_expenses)}
            </p>
          )}
        </div>
      </div>

      {/* Low Stock Alert Table */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-slate-700">
              Low Stock Alert
            </h2>
            {!lowStockLoading && lowStock.length > 0 && (
              <Badge className="bg-amber-100 text-amber-700 text-xs">
                {lowStock.length} SKU{lowStock.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <Link
            href="/inventory"
            className="text-xs text-blue-500 hover:underline"
          >
            View all inventory →
          </Link>
        </div>

        <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-stone-50 hover:bg-stone-50">
                <TableHead className="text-stone-600 font-medium text-xs">SKU Code</TableHead>
                <TableHead className="text-stone-600 font-medium text-xs text-right">On Hand</TableHead>
                <TableHead className="text-stone-600 font-medium text-xs text-right">Reorder Level</TableHead>
                <TableHead className="text-stone-600 font-medium text-xs text-right">Shortfall</TableHead>
                <TableHead className="text-stone-600 font-medium text-xs text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lowStockLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : lowStock.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="py-10 text-center text-stone-400">
                    <div className="flex flex-col items-center gap-1">
                      <Package className="h-6 w-6 text-stone-300" />
                      <span className="text-sm">All SKUs are above reorder level.</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                lowStock.map((item) => {
                  const onHand = parseFloat(item.total_on_hand);
                  const shortfall = item.reorder_level - onHand;
                  const isOut = onHand <= 0;
                  return (
                    <TableRow key={item.variant_id} className="hover:bg-amber-50/40">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/inventory/${item.variant_id}`}
                            className="font-mono text-sm text-slate-700 hover:text-blue-600 hover:underline"
                          >
                            {item.sku_code}
                          </Link>
                          {isOut && (
                            <Badge className="bg-red-100 text-red-700 text-xs py-0">
                              Out of Stock
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        <span className={isOut ? 'text-red-600 font-semibold' : 'text-amber-700'}>
                          {item.total_on_hand}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-stone-500">
                        {item.reorder_level}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-red-600 font-medium">
                        {shortfall > 0 ? `−${shortfall.toFixed(0)}` : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          href={`/purchases/new?sku=${item.sku_code}`}
                          className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-slate-800 text-white hover:bg-slate-700 transition-colors"
                        >
                          Reorder →
                        </Link>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      {/* Quick links */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { href: '/sales/new', label: '+ New Sale', color: 'bg-emerald-600 hover:bg-emerald-700' },
          { href: '/catalog/products', label: 'Manage Products', color: 'bg-slate-700 hover:bg-slate-800' },
          { href: '/finance', label: 'Financial Reports', color: 'bg-indigo-600 hover:bg-indigo-700' },
          { href: '/audit', label: 'Audit Trail', color: 'bg-stone-600 hover:bg-stone-700' },
        ].map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`flex items-center justify-center rounded-lg px-4 py-3 text-sm font-medium text-white transition-colors ${link.color}`}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
