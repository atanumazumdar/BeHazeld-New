'use client';

/**
 * StockAdjustmentForm — records a manual stock movement for a given SKU.
 *
 * Supported movement types (manual, user-facing):
 *   opening_stock, adjustment_in, adjustment_out, purchase_in, return_in
 *
 * Critical behaviour:
 *   - On 409 SALE_STOCK_NOT_AVAILABLE → shows a clear error toast (not a generic one)
 *   - On success → parent's onSuccess() is called so the ledger / balance refreshes
 */

import { useEffect, useRef, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { toast } from 'sonner';
import { Download, HelpCircle, Upload } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

import { useImportLocationsBins, useLocations, useRecordMovement } from '@/hooks/use-inventory';
import { ApiError } from '@/types/api';
import type { MovementType } from '@/types/inventory';

interface AdjustmentFormValues {
  location_id: string;
  bin_id: string;
  movement_type: MovementType;
  quantity: string;
  unit_cost: string;
  notes: string;
}

interface StockAdjustmentFormProps {
  variantId: string;
  defaultUnitCost?: string | null;
  onSuccess?: () => void;
}

const MOVEMENT_LABELS: Record<string, string> = {
  opening_stock: 'Opening Stock',
  purchase_in: 'Purchase In',
  adjustment_in: 'Adjustment In (+)',
  adjustment_out: 'Adjustment Out (−)',
  return_in: 'Return In',
};

const MANUAL_MOVEMENT_TYPES = Object.keys(MOVEMENT_LABELS) as MovementType[];

function normalizeUnitCost(value: string | null | undefined): string {
  if (!value) return '0';
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  return String(amount);
}

export function StockAdjustmentForm({ variantId, defaultUnitCost, onSuccess }: StockAdjustmentFormProps) {
  const { data: locations = [] } = useLocations();
  const recordMovement = useRecordMovement();
  const importLocationsBins = useImportLocationsBins();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [selectedLocationId, setSelectedLocationId] = useState<string>('');
  const resolvedDefaultUnitCost = normalizeUnitCost(defaultUnitCost);
  const bins =
    locations.find((l) => l.id === selectedLocationId)?.bins.filter((b) => b.is_active) ?? [];

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
    setValue,
  } = useForm<AdjustmentFormValues>({
    defaultValues: {
      location_id: '',
      bin_id: '',
      movement_type: 'adjustment_in',
      quantity: '',
      unit_cost: resolvedDefaultUnitCost,
      notes: '',
    },
  });

  useEffect(() => {
    setValue('unit_cost', resolvedDefaultUnitCost, {
      shouldDirty: false,
      shouldTouch: false,
    });
  }, [resolvedDefaultUnitCost, setValue]);

  const onSubmit = handleSubmit(async (values) => {
    try {
      await recordMovement.mutateAsync({
        product_variant_id: variantId,
        location_id: values.location_id,
        bin_id: values.bin_id,
        movement_type: values.movement_type,
        quantity: values.quantity,
        unit_cost: values.unit_cost || '0',
        batch_number: null,
        notes: values.notes || null,
      });
      toast.success('Stock movement recorded successfully.');
      reset({
        location_id: '',
        bin_id: '',
        movement_type: 'adjustment_in',
        quantity: '',
        unit_cost: resolvedDefaultUnitCost,
        notes: '',
      });
      setSelectedLocationId('');
      onSuccess?.();
    } catch (err) {
      if (err instanceof ApiError && err.errorCode === 'SALE_STOCK_NOT_AVAILABLE') {
        toast.error('Insufficient stock — there is not enough available quantity for this adjustment.', {
          description: 'Check the current balance and reduce the quantity.',
        });
      } else {
        const msg = err instanceof ApiError ? err.message : 'Failed to record stock movement.';
        toast.error(msg);
      }
    }
  });

  const handleCsvSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    try {
      const result = await importLocationsBins.mutateAsync(file);
      const summary = `${result.created_locations} location${result.created_locations === 1 ? '' : 's'}, ${result.created_bins} bin${result.created_bins === 1 ? '' : 's'}, ${result.skipped} skipped`;
      if (result.errors.length > 0) {
        toast.warning(`CSV imported with issues: ${summary}.`);
      } else {
        toast.success(`CSV imported: ${summary}.`);
      }
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : 'Failed to import CSV.';
      toast.error(msg);
    }
  };

  const downloadCsvTemplate = () => {
    const csv = [
      'location_name,address,bin_name,is_default',
      'Main Store,Shop floor,Front Rack,true',
      'Main Store,Shop floor,Back Stock,false',
      'Warehouse,Warehouse address,Main,true',
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'inventory-locations-bins-template.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-stone-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Record Stock Movement
          </h3>
          <p className="mt-1 text-xs text-stone-400">
            CSV columns: location_name, address, bin_name, is_default
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={handleCsvSelected}
          />
          <Button type="button" variant="outline" onClick={downloadCsvTemplate}>
            <Download className="mr-2 h-4 w-4" />
            CSV Template
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={importLocationsBins.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mr-2 h-4 w-4" />
            {importLocationsBins.isPending ? 'Importing...' : 'Import Locations/Bins'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Location */}
        <div className="space-y-1.5">
          <Label>Location <span className="text-red-500">*</span></Label>
          <Controller
            name="location_id"
            control={control}
            rules={{ required: true }}
            render={({ field }) => (
              <Select
                onValueChange={(val) => {
                  const v = val ?? '';
                  field.onChange(v);
                  setSelectedLocationId(v);
                  setValue('bin_id', '');
                }}
                value={field.value}
                items={locations.map((l) => ({ value: l.id, label: l.name }))}
              >
                <SelectTrigger className={`bg-white ${errors.location_id ? 'border-red-400' : ''}`}>
                  <SelectValue placeholder="Select location…" />
                </SelectTrigger>
                <SelectContent>
                  {locations.map((l) => (
                    <SelectItem key={l.id} value={l.id} label={l.name}>{l.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {/* Bin */}
        <div className="space-y-1.5">
          <Label>Bin <span className="text-red-500">*</span></Label>
          <Controller
            name="bin_id"
            control={control}
            rules={{ required: true }}
            render={({ field }) => (
              <Select
                onValueChange={(val) => field.onChange(val ?? '')}
                value={field.value}
                disabled={!selectedLocationId}
                items={bins.map((b) => ({
                  value: b.id,
                  label: `${b.name}${b.is_default ? ' (default)' : ''}`,
                }))}
              >
                <SelectTrigger className={`bg-white ${errors.bin_id ? 'border-red-400' : ''}`}>
                  <SelectValue placeholder={selectedLocationId ? 'Select bin…' : 'Choose location first'} />
                </SelectTrigger>
                <SelectContent>
                  {bins.map((b) => (
                    <SelectItem
                      key={b.id}
                      value={b.id}
                      label={`${b.name}${b.is_default ? ' (default)' : ''}`}
                    >
                      {b.name}{b.is_default ? ' (default)' : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {/* Movement type */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Label>Movement Type <span className="text-red-500">*</span></Label>
            <TooltipProvider delay={150}>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <button
                      type="button"
                      className="inline-flex h-4 w-4 items-center justify-center rounded-full text-stone-400 hover:text-slate-700"
                      aria-label="Movement type help"
                    />
                  }
                >
                  <HelpCircle className="h-4 w-4" />
                </TooltipTrigger>
                <TooltipContent side="right" align="start" className="max-w-sm items-start text-left leading-relaxed">
                  <div className="space-y-1">
                    <div><span className="font-semibold">opening_stock:</span> first time adding stock for this SKU</div>
                    <div><span className="font-semibold">adjustment_in:</span> increase stock manually</div>
                    <div><span className="font-semibold">adjustment_out:</span> reduce stock manually</div>
                    <div><span className="font-semibold">purchase_in:</span> stock received from purchase/vendor</div>
                    <div><span className="font-semibold">return_in:</span> stock returned by customer</div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <Controller
            name="movement_type"
            control={control}
            rules={{ required: true }}
            render={({ field }) => (
              <Select
                onValueChange={(val) => field.onChange((val ?? 'adjustment_in') as MovementType)}
                value={field.value}
                items={MANUAL_MOVEMENT_TYPES.map((mt) => ({ value: mt, label: MOVEMENT_LABELS[mt] }))}
              >
                <SelectTrigger className="bg-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MANUAL_MOVEMENT_TYPES.map((mt) => (
                    <SelectItem key={mt} value={mt} label={MOVEMENT_LABELS[mt]}>
                      {MOVEMENT_LABELS[mt]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </div>

        {/* Quantity */}
        <div className="space-y-1.5">
          <Label>Quantity <span className="text-red-500">*</span></Label>
          <Controller
            name="quantity"
            control={control}
            rules={{
              required: true,
              validate: (value) => Number(value) >= 1,
            }}
            render={({ field }) => (
              <Input
                {...field}
                type="number"
                min="1"
                step="1"
                inputMode="numeric"
                placeholder="e.g. 50"
                className={`bg-white ${errors.quantity ? 'border-red-400' : ''}`}
              />
            )}
          />
          {errors.quantity && (
            <p className="text-xs text-red-500">Quantity must be 1 or more.</p>
          )}
        </div>

        {/* Unit cost */}
        <div className="space-y-1.5">
          <Label>Unit Cost</Label>
          <Controller
            name="unit_cost"
            control={control}
            rules={{ min: 0 }}
            render={({ field }) => (
              <Input
                {...field}
                type="number"
                step="0.01"
                placeholder="0.00"
                className="bg-white"
              />
            )}
          />
          <p className="text-xs text-stone-400">
            Auto-filled from variant cost price. Leave 0 for non-purchase adjustments.
          </p>
        </div>

        {/* Notes */}
        <div className="space-y-1.5">
          <Label>Notes</Label>
          <Input
            {...register('notes')}
            placeholder="Optional reason or reference…"
            className="bg-white"
          />
        </div>
      </div>

      <div className="flex justify-end pt-1">
        <Button
          type="submit"
          disabled={recordMovement.isPending}
          className="bg-slate-800 hover:bg-slate-700 text-white"
        >
          {recordMovement.isPending ? 'Saving…' : 'Record Movement'}
        </Button>
      </div>
    </form>
  );
}
