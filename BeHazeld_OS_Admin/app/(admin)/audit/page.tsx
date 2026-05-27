'use client';

/**
 * /audit — Audit Trail page.
 *
 * Displays a filterable, paginated log of all API mutations.
 * Filters: endpoint search (debounced), HTTP method, response status.
 * Columns: timestamp, method badge, endpoint, status badge, user, IP, payload (expandable).
 */

import { useState } from 'react';
import { useDebounce } from 'use-debounce';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

import { useAuditLogs } from '@/hooks/use-reports';

// ── Constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

const METHOD_COLORS: Record<string, string> = {
  GET:    'bg-sky-100 text-sky-700',
  POST:   'bg-emerald-100 text-emerald-700',
  PUT:    'bg-amber-100 text-amber-700',
  PATCH:  'bg-violet-100 text-violet-700',
  DELETE: 'bg-red-100 text-red-700',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTs(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function statusClass(status: number): string {
  if (status >= 500) return 'bg-red-100 text-red-700';
  if (status >= 400) return 'bg-amber-100 text-amber-700';
  if (status >= 300) return 'bg-sky-100 text-sky-700';
  return 'bg-emerald-100 text-emerald-700';
}

function prettyPayload(raw: string | null): string {
  if (!raw) return '';
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AuditPage() {
  const [endpointInput, setEndpointInput] = useState('');
  const [userInput, setUserInput] = useState('');
  const [method, setMethod] = useState('');
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [debouncedEndpoint] = useDebounce(endpointInput, 400);
  const [debouncedUser] = useDebounce(userInput, 400);

  const { data: logs = [], isLoading } = useAuditLogs({
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
    user_id: debouncedUser || undefined,
    endpoint: debouncedEndpoint || undefined,
    method: method || undefined,
  });

  const hasPrev = page > 0;
  const hasNext = logs.length === PAGE_SIZE;

  function resetPage() {
    setPage(0);
  }

  function clearFilters() {
    setEndpointInput('');
    setUserInput('');
    setMethod('');
    setPage(0);
  }

  const hasActiveFilters = endpointInput || userInput || method;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Audit Trail</h1>
        <p className="mt-1 text-sm text-stone-500">
          Immutable log of all API mutations — tenant-scoped, newest first.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Endpoint search */}
        <Input
          placeholder="Search endpoint…"
          value={endpointInput}
          onChange={(e) => { setEndpointInput(e.target.value); resetPage(); }}
          className="w-56 h-9 bg-white text-sm"
        />

        {/* User ID search */}
        <Input
          placeholder="Filter by user ID…"
          value={userInput}
          onChange={(e) => { setUserInput(e.target.value); resetPage(); }}
          className="w-52 h-9 bg-white text-sm"
        />

        {/* Method filter buttons */}
        <div className="flex items-center gap-1.5">
          {HTTP_METHODS.map((m) => (
            <button
              key={m}
              onClick={() => { setMethod(method === m ? '' : m); resetPage(); }}
              className={cn(
                'px-2.5 py-1 rounded text-xs font-semibold transition-colors border',
                method === m
                  ? METHOD_COLORS[m] + ' border-transparent'
                  : 'bg-white text-stone-500 border-stone-200 hover:border-stone-300',
              )}
            >
              {m}
            </button>
          ))}
        </div>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="text-stone-400 h-9 text-xs"
            onClick={clearFilters}
          >
            Clear filters
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              <TableHead className="text-stone-600 font-medium text-xs w-44">When</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs w-20">Method</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs">Endpoint</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs w-16 text-center">Status</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs w-64">User</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs w-32">IP Address</TableHead>
              <TableHead className="text-stone-600 font-medium text-xs w-16 text-center">Payload</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-14 text-center text-stone-400">
                  {hasActiveFilters
                    ? 'No log entries match the current filters.'
                    : 'No audit entries recorded yet.'}
                </TableCell>
              </TableRow>
            ) : (
              logs.map((entry) => {
                const isExpanded = expandedId === entry.id;
                const payload = prettyPayload(entry.request_payload);
                return (
                  <>
                    <TableRow
                      key={entry.id}
                      className={cn(
                        'hover:bg-stone-50/60 transition-colors',
                        isExpanded && 'bg-stone-50',
                      )}
                    >
                      {/* Timestamp */}
                      <TableCell className="text-xs text-stone-500 font-mono whitespace-nowrap">
                        {formatTs(entry.created_at)}
                      </TableCell>

                      {/* Method */}
                      <TableCell>
                        <Badge className={cn('text-xs font-bold', METHOD_COLORS[entry.method] ?? 'bg-stone-100 text-stone-600')}>
                          {entry.method}
                        </Badge>
                      </TableCell>

                      {/* Endpoint */}
                      <TableCell className="font-mono text-xs text-slate-700 break-all">
                        {entry.endpoint}
                      </TableCell>

                      {/* Status */}
                      <TableCell className="text-center">
                        <Badge className={cn('text-xs font-semibold', statusClass(entry.response_status))}>
                          {entry.response_status}
                        </Badge>
                      </TableCell>

                      {/* User */}
                      <TableCell className="font-mono text-xs text-stone-500 break-all">
                        {entry.user_id ?? <span className="italic text-stone-300">anonymous</span>}
                      </TableCell>

                      {/* IP */}
                      <TableCell className="font-mono text-xs text-stone-500">
                        {entry.ip_address ?? '—'}
                      </TableCell>

                      {/* Payload toggle */}
                      <TableCell className="text-center">
                        {payload ? (
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                            className="text-xs text-blue-500 hover:text-blue-700 hover:underline"
                          >
                            {isExpanded ? 'Hide' : 'View'}
                          </button>
                        ) : (
                          <span className="text-xs text-stone-300">—</span>
                        )}
                      </TableCell>
                    </TableRow>

                    {/* Expanded payload row */}
                    {isExpanded && payload && (
                      <TableRow key={`${entry.id}-payload`} className="bg-stone-50 hover:bg-stone-50">
                        <TableCell colSpan={7} className="py-3 px-6">
                          <pre className="text-xs font-mono text-slate-700 bg-white border border-stone-200 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap break-all max-h-64">
                            {payload}
                          </pre>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {(hasPrev || hasNext) && (
        <div className="flex items-center justify-between text-sm text-stone-500">
          <span>
            Showing {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + logs.length}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!hasPrev}
              onClick={() => setPage((p) => p - 1)}
              className="text-xs"
            >
              ← Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasNext}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs"
            >
              Next →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
