'use client';

/**
 * VariantRow — a single row in the multi-variant creation table inside the wizard.
 *
 * Props:
 * - index: row index (used for react-hook-form field paths)
 * - onRemove: callback to remove this row
 * - control, register, errors: forwarded from useFieldArray
 */

import type { Control, FieldErrors, UseFormRegister } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Controller } from 'react-hook-form';
import { toast } from 'sonner';
import { useSizes, useColors } from '@/hooks/use-catalog';
import { prepareProductImageForUpload } from '@/lib/image-upload';
import type { WizardFormValues } from './create-product-wizard';

interface VariantRowProps {
  index: number;
  onRemove: () => void;
  control: Control<WizardFormValues>;
  register: UseFormRegister<WizardFormValues>;
  errors: FieldErrors<WizardFormValues>;
}

export function VariantRow({ index, onRemove, control, register, errors }: VariantRowProps) {
  const { data: sizes = [] } = useSizes();
  const { data: colors = [] } = useColors();
  const sizeItems = sizes.map((s) => ({ value: s.id, label: s.name }));
  const colorItems = colors.map((c) => ({ value: c.id, label: c.name }));

  const variantErrors = errors.variants?.[index];
  void register;

  return (
    <div className="grid grid-cols-[minmax(6rem,1fr)_minmax(6rem,1fr)_minmax(5rem,0.8fr)_minmax(5rem,0.8fr)_minmax(5rem,0.8fr)_minmax(5rem,0.8fr)_minmax(7rem,1fr)_2.25rem] gap-2 items-start p-3 rounded-lg bg-stone-50 border border-stone-200">
      {/* Size */}
      <div>
        <Controller
          name={`variants.${index}.size_id`}
          control={control}
          rules={{ required: true }}
          render={({ field }) => (
            <Select items={sizeItems} onValueChange={field.onChange} value={field.value}>
              <SelectTrigger className={`h-9 bg-white text-sm ${variantErrors?.size_id ? 'border-red-400' : ''}`}>
                <SelectValue placeholder="Size" />
              </SelectTrigger>
              <SelectContent>
                {sizes.map((s) => (
                  <SelectItem key={s.id} value={s.id} label={s.name}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      {/* Color */}
      <div>
        <Controller
          name={`variants.${index}.color_id`}
          control={control}
          rules={{ required: true }}
          render={({ field }) => (
            <Select items={colorItems} onValueChange={field.onChange} value={field.value}>
              <SelectTrigger className={`h-9 bg-white text-sm ${variantErrors?.color_id ? 'border-red-400' : ''}`}>
                <SelectValue placeholder="Color" />
              </SelectTrigger>
              <SelectContent>
                {colors.map((c) => (
                  <SelectItem key={c.id} value={c.id} label={c.name}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      {/* MRP */}
      <div>
        <Controller
          name={`variants.${index}.mrp`}
          control={control}
          rules={{
            validate: (value) => (value !== '' && Number(value) >= 0) || 'MRP is required',
          }}
          render={({ field }) => (
            <Input
              value={field.value}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              type="number"
              step="0.01"
              placeholder="MRP"
              className={`h-9 bg-white text-sm ${variantErrors?.mrp ? 'border-red-400' : ''}`}
            />
          )}
        />
      </div>

      {/* Selling Price */}
      <div>
        <Controller
          name={`variants.${index}.selling_price`}
          control={control}
          rules={{
            validate: (value) => (value !== '' && Number(value) >= 0) || 'Selling price is required',
          }}
          render={({ field }) => (
            <Input
              value={field.value}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              type="number"
              step="0.01"
              placeholder="Sell Price"
              className={`h-9 bg-white text-sm ${variantErrors?.selling_price ? 'border-red-400' : ''}`}
            />
          )}
        />
      </div>

      {/* Cost Price */}
      <div>
        <Controller
          name={`variants.${index}.cost_price`}
          control={control}
          rules={{
            validate: (value) => (value !== '' && Number(value) >= 0) || 'Cost is required',
          }}
          render={({ field }) => (
            <Input
              value={field.value}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              type="number"
              step="0.01"
              placeholder="Cost"
              className={`h-9 bg-white text-sm ${variantErrors?.cost_price ? 'border-red-400' : ''}`}
            />
          )}
        />
      </div>

      {/* Fabric (optional) */}
      <div>
        <Controller
          name={`variants.${index}.fabric`}
          control={control}
          render={({ field }) => (
            <Input
              value={field.value}
              onValueChange={field.onChange}
              onBlur={field.onBlur}
              placeholder="Fabric"
              className="h-9 bg-white text-sm"
            />
          )}
        />
      </div>

      {/* Variant image */}
      <div>
        <Controller
          name={`variants.${index}.image_file`}
          control={control}
          render={({ field: { onChange, value } }) => (
            <label className="flex h-9 cursor-pointer items-center justify-center rounded-lg border border-input bg-white px-2 text-xs text-stone-600 hover:bg-stone-50">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={async (event) => {
                  const file = event.target.files?.[0] ?? null;
                  event.target.value = '';
                  if (!file) {
                    onChange(null);
                    return;
                  }

                  try {
                    const preparedFile = await prepareProductImageForUpload(file);
                    if (preparedFile.size < file.size) {
                      toast.info('Photo optimized for upload.');
                    }
                    onChange(preparedFile);
                  } catch (err) {
                    const msg = err instanceof Error ? err.message : 'Failed to prepare picture.';
                    toast.error(msg);
                    onChange(null);
                  }
                }}
              />
              <span className="truncate">{value ? value.name : 'Upload'}</span>
            </label>
          )}
        />
      </div>

      {/* Remove button */}
      <div className="flex justify-end">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-9 w-9 p-0 text-stone-400 hover:text-red-500 hover:bg-red-50"
          onClick={onRemove}
        >
          ✕
        </Button>
      </div>
    </div>
  );
}
