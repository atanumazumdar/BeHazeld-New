'use client';

/**
 * CustomerSelector — searchable customer dropdown with inline quick-add form.
 *
 * States:
 *  - Idle: shows "Walk-in / No customer" placeholder
 *  - Searching: shows typeahead results from GET /sales/customers?search=…
 *  - Selected: shows selected customer name with clear button
 *  - Creating: shows inline form (name + phone) for quick walk-in registration
 */

import { useState, useRef, useEffect } from 'react';
import { useDebounce } from 'use-debounce';
import { toast } from 'sonner';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';

import { useCustomerSearch, useCreateCustomer } from '@/hooks/use-sales';
import { ApiError } from '@/types/api';
import type { CustomerResponse } from '@/types/sales';

interface CustomerSelectorProps {
  value: CustomerResponse | null;
  onChange: (customer: CustomerResponse | null) => void;
}

export function CustomerSelector({ value, onChange }: CustomerSelectorProps) {
  const [searchText, setSearchText] = useState('');
  const [debouncedSearch] = useDebounce(searchText, 300);
  const [showDropdown, setShowDropdown] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: customers = [], isLoading } = useCustomerSearch(debouncedSearch);
  const createCustomer = useCreateCustomer();

  // Close dropdown on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  const handleSelect = (customer: CustomerResponse) => {
    onChange(customer);
    setSearchText('');
    setShowDropdown(false);
  };

  const handleClear = () => {
    onChange(null);
    setSearchText('');
  };

  const handleQuickAdd = async () => {
    if (!newName.trim()) return;
    setIsCreating(true);
    try {
      const created = await createCustomer.mutateAsync({
        name: newName.trim(),
        phone: newPhone.trim() || null,
        email: null,
        address: null,
      });
      toast.success(`Customer "${created.name}" created.`);
      onChange(created);
      setShowCreateForm(false);
      setShowDropdown(false);
      setNewName('');
      setNewPhone('');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to create customer.';
      toast.error(msg);
    } finally {
      setIsCreating(false);
    }
  };

  // ── Selected state ──────────────────────────────────────────────────────────
  if (value) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-emerald-800 truncate">{value.name}</p>
          {value.phone && (
            <p className="text-xs text-emerald-600">{value.phone}</p>
          )}
        </div>
        <button
          onClick={handleClear}
          className="text-emerald-500 hover:text-emerald-700 text-lg leading-none font-light shrink-0"
          aria-label="Clear customer"
        >
          ×
        </button>
      </div>
    );
  }

  // ── Search / create state ───────────────────────────────────────────────────
  return (
    <div ref={containerRef} className="relative">
      <div className="flex gap-2">
        <Input
          placeholder="Search customer name or phone…"
          value={searchText}
          onChange={(e) => {
            setSearchText(e.target.value);
            setShowDropdown(true);
            setShowCreateForm(false);
          }}
          onFocus={() => setShowDropdown(true)}
          className="bg-white"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0 text-xs"
          onClick={() => {
            setShowCreateForm((v) => !v);
            setShowDropdown(false);
          }}
        >
          + New
        </Button>
      </div>

      {/* Walk-in note */}
      {!showDropdown && !showCreateForm && (
        <p className="mt-1 text-xs text-stone-400">
          Leave blank for a Walk-in / Cash sale.
        </p>
      )}

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-stone-200 bg-white shadow-lg">
          {isLoading ? (
            <div className="p-3 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : customers.length === 0 ? (
            <div className="p-3 text-sm text-stone-400">
              {debouncedSearch ? 'No customers found.' : 'Type to search…'}
            </div>
          ) : (
            <ul className="max-h-52 overflow-y-auto py-1">
              {customers.map((c) => (
                <li key={c.id}>
                  <button
                    className="w-full px-3 py-2 text-left hover:bg-stone-50 text-sm"
                    onMouseDown={() => handleSelect(c)}
                  >
                    <span className="font-medium text-slate-700">{c.name}</span>
                    {c.phone && (
                      <span className="ml-2 text-stone-400 text-xs">{c.phone}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Quick-add inline form */}
      {showCreateForm && (
        <div className="mt-2 rounded-lg border border-stone-200 bg-stone-50 p-3 space-y-3">
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
            Quick Add Customer
          </p>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">Name *</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Full name"
                className="h-8 text-sm bg-white"
                onKeyDown={(e) => e.key === 'Enter' && handleQuickAdd()}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Phone</Label>
              <Input
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="+91 98765…"
                className="h-8 text-sm bg-white"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => setShowCreateForm(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!newName.trim() || isCreating}
              onClick={handleQuickAdd}
              className="h-7 text-xs bg-slate-800 hover:bg-slate-700 text-white"
            >
              {isCreating ? 'Saving…' : 'Add Customer'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
