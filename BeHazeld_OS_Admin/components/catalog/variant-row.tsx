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
import { useSizes, useColors } from '@/hooks/use-catalog';
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

  const variantErrors = errors.variants?.[index];

  return (
    <div className="grid grid-cols-12 gap-2 items-start p-3 rounded-lg bg-stone-50 border border-stone-200">
      {/* Size */}
      <div className="col-span-2">
        <Controller
          name={`variants.${index}.size_id`}
          control={control}
          rules={{ required: true }}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger className={`h-9 bg-white text-sm ${variantErrors?.size_id ? 'border-red-400' : ''}`}>
                <SelectValue placeholder="Size" />
              </SelectTrigger>
              <SelectContent>
                {sizes.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      {/* Color */}
      <div className="col-span-2">
        <Controller
          name={`variants.${index}.color_id`}
          control={control}
          rules={{ required: true }}
          render={({ field }) => (
            <Select onValueChange={field.onChange} value={field.value}>
              <SelectTrigger className={`h-9 bg-white text-sm ${variantErrors?.color_id ? 'border-red-400' : ''}`}>
                <SelectValue placeholder="Color" />
              </SelectTrigger>
              <SelectContent>
                {colors.map((c) => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </div>

      {/* MRP */}
      <div className="col-span-2">
        <Input
          {...register(`variants.${index}.mrp`, { required: true, min: 0 })}
          type="number"
          step="0.01"
          placeholder="MRP"
          className={`h-9 bg-white text-sm ${variantErrors?.mrp ? 'border-red-400' : ''}`}
        />
      </div>

      {/* Selling Price */}
      <div className="col-span-2">
        <Input
          {...register(`variants.${index}.selling_price`, { required: true, min: 0 })}
          type="number"
          step="0.01"
          placeholder="Sell Price"
          className={`h-9 bg-white text-sm ${variantErrors?.selling_price ? 'border-red-400' : ''}`}
        />
      </div>

      {/* Cost Price */}
      <div className="col-span-2">
        <Input
          {...register(`variants.${index}.cost_price`, { required: true, min: 0 })}
          type="number"
          step="0.01"
          placeholder="Cost"
          className={`h-9 bg-white text-sm ${variantErrors?.cost_price ? 'border-red-400' : ''}`}
        />
      </div>

      {/* Fabric (optional) */}
      <div className="col-span-1">
        <Input
          {...register(`variants.${index}.fabric`)}
          placeholder="Fabric"
          className="h-9 bg-white text-sm"
        />
      </div>

      {/* Remove button */}
      <div className="col-span-1 flex justify-end">
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
