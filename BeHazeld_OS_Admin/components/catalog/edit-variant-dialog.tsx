'use client';

import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useColors,
  useSizes,
  useUpdateVariant,
  useUploadVariantImage,
} from '@/hooks/use-catalog';
import { prepareProductImageForUpload } from '@/lib/image-upload';
import type { ProductResponse, ProductVariantResponse } from '@/types/catalog';

interface EditVariantDialogProps {
  product: ProductResponse | null;
  variant: ProductVariantResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface EditVariantFormValues {
  size_id: string;
  color_id: string;
  mrp: string;
  selling_price: string;
  cost_price: string;
  fabric: string;
  image_file: File | null;
}

export function EditVariantDialog({
  product,
  variant,
  open,
  onOpenChange,
}: EditVariantDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { data: sizes = [] } = useSizes();
  const { data: colors = [] } = useColors();
  const updateVariant = useUpdateVariant(product?.id ?? '');
  const uploadVariantImage = useUploadVariantImage(product?.id ?? '');
  const sizeItems = sizes.map((s) => ({ value: s.id, label: s.name }));
  const colorItems = colors.map((c) => ({ value: c.id, label: c.name }));

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EditVariantFormValues>({
    defaultValues: {
      size_id: '',
      color_id: '',
      mrp: '',
      selling_price: '',
      cost_price: '',
      fabric: '',
      image_file: null,
    },
  });

  useEffect(() => {
    if (!variant) return;
    reset({
      size_id: variant.size_id,
      color_id: variant.color_id,
      mrp: String(variant.mrp ?? ''),
      selling_price: String(variant.selling_price ?? ''),
      cost_price: String(variant.cost_price ?? ''),
      fabric: variant.fabric ?? '',
      image_file: null,
    });
  }, [reset, variant]);

  const handleClose = () => {
    if (isSubmitting) return;
    onOpenChange(false);
  };

  const handleVariantSubmit = handleSubmit(async (values) => {
    if (!product || !variant) return;
    setIsSubmitting(true);

    try {
      const updatedVariant = await updateVariant.mutateAsync({
        variantId: variant.id,
        data: {
          size_id: values.size_id,
          color_id: values.color_id,
          mrp: values.mrp,
          selling_price: values.selling_price,
          cost_price: values.cost_price,
          fabric: values.fabric || null,
          image_url: variant.image_url,
          reorder_level: String(variant.reorder_level ?? '0'),
        },
      });

      if (values.image_file) {
        await uploadVariantImage.mutateAsync({
          variantId: updatedVariant.id,
          file: values.image_file,
        });
      }

      toast.success('Variant updated.');
      handleClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update variant.';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  });

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="w-[calc(100vw-2rem)] max-w-[calc(100vw-2rem)] sm:max-w-[760px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-slate-800">
            Edit Variant{product ? ` — ${product.name}` : ''}
          </DialogTitle>
        </DialogHeader>

        <Separator />

        <form onSubmit={handleVariantSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Size</Label>
              <Controller
                name="size_id"
                control={control}
                rules={{ required: true }}
                render={({ field }) => (
                  <Select items={sizeItems} onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger className={`bg-white ${errors.size_id ? 'border-red-400' : ''}`}>
                      <SelectValue placeholder="Select size" />
                    </SelectTrigger>
                    <SelectContent>
                      {sizes.map((size) => (
                        <SelectItem key={size.id} value={size.id} label={size.name}>
                          {size.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="space-y-1.5">
              <Label>Color</Label>
              <Controller
                name="color_id"
                control={control}
                rules={{ required: true }}
                render={({ field }) => (
                  <Select items={colorItems} onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger className={`bg-white ${errors.color_id ? 'border-red-400' : ''}`}>
                      <SelectValue placeholder="Select color" />
                    </SelectTrigger>
                    <SelectContent>
                      {colors.map((color) => (
                        <SelectItem key={color.id} value={color.id} label={color.name}>
                          {color.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <PriceInput name="mrp" label="MRP" control={control} hasError={Boolean(errors.mrp)} />
            <PriceInput
              name="selling_price"
              label="Selling Price"
              control={control}
              hasError={Boolean(errors.selling_price)}
            />
            <PriceInput
              name="cost_price"
              label="Cost Price"
              control={control}
              hasError={Boolean(errors.cost_price)}
            />

            <div className="space-y-1.5">
              <Label>Fabric</Label>
              <Controller
                name="fabric"
                control={control}
                render={({ field }) => (
                  <Input
                    value={field.value}
                    onValueChange={field.onChange}
                    onBlur={field.onBlur}
                    placeholder="Optional fabric"
                    className="bg-white"
                  />
                )}
              />
            </div>

            <div className="col-span-2 space-y-1.5">
              <Label>Picture</Label>
              <Controller
                name="image_file"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <label className="flex h-10 cursor-pointer items-center justify-center rounded-lg border border-input bg-white px-3 text-sm text-stone-600 hover:bg-stone-50">
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
                    <span className="truncate">
                      {value ? value.name : variant?.image_url ? 'Replace existing picture' : 'Upload picture'}
                    </span>
                  </label>
                )}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-slate-800 hover:bg-slate-700 text-white"
            >
              {isSubmitting ? 'Saving…' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function PriceInput({
  name,
  label,
  control,
  hasError,
}: {
  name: 'mrp' | 'selling_price' | 'cost_price';
  label: string;
  control: ReturnType<typeof useForm<EditVariantFormValues>>['control'];
  hasError: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Controller
        name={name}
        control={control}
        rules={{
          validate: (value) => (value !== '' && Number(value) > 0) || `${label} is required`,
        }}
        render={({ field }) => (
          <Input
            value={field.value}
            onValueChange={field.onChange}
            onBlur={field.onBlur}
            type="number"
            step="0.01"
            placeholder={label}
            className={`bg-white ${hasError ? 'border-red-400' : ''}`}
          />
        )}
      />
    </div>
  );
}
