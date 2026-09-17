'use client';

import { useEffect, useState } from 'react';
import { useFieldArray, useForm } from 'react-hook-form';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { VariantRow } from './variant-row';
import { useCreateVariant, useUploadVariantImage } from '@/hooks/use-catalog';
import type { ProductResponse } from '@/types/catalog';
import type { VariantFormRow, WizardFormValues } from './create-product-wizard';

const DEFAULT_VARIANT: VariantFormRow = {
  size_id: '',
  color_id: '',
  mrp: '',
  selling_price: '',
  cost_price: '',
  fabric: '',
  image_file: null,
};

interface AddVariantDialogProps {
  product: ProductResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddVariantDialog({ product, open, onOpenChange }: AddVariantDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const createVariant = useCreateVariant(product?.id ?? '');
  const uploadVariantImage = useUploadVariantImage(product?.id ?? '');

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<WizardFormValues>({
    defaultValues: {
      name: '',
      category_id: '',
      product_group_id: '',
      product_type_id: '',
      brand_id: '',
      description: '',
      variants: [{ ...DEFAULT_VARIANT }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'variants' });

  useEffect(() => {
    if (open) {
      reset({
        name: '',
        category_id: '',
        product_group_id: '',
        product_type_id: '',
        brand_id: '',
        description: '',
        variants: [{ ...DEFAULT_VARIANT }],
      });
    }
  }, [open, reset]);

  const handleClose = () => {
    if (isSubmitting) return;
    onOpenChange(false);
  };

  const handleVariantSubmit = handleSubmit(async (values) => {
    if (!product) return;

    setIsSubmitting(true);
    let succeeded = 0;
    let failed = 0;
    let imageFailed = 0;

    for (const variant of values.variants) {
      try {
        const createdVariant = await createVariant.mutateAsync({
          size_id: variant.size_id,
          color_id: variant.color_id,
          mrp: variant.mrp,
          selling_price: variant.selling_price,
          cost_price: variant.cost_price,
          fabric: variant.fabric || null,
          image_url: null,
          reorder_level: '0',
        });

        if (variant.image_file) {
          try {
            await uploadVariantImage.mutateAsync({
              variantId: createdVariant.id,
              file: variant.image_file,
            });
          } catch {
            imageFailed++;
          }
        }

        succeeded++;
      } catch {
        failed++;
      }
    }

    setIsSubmitting(false);

    if (failed === 0) {
      const imageNote = imageFailed > 0 ? ` ${imageFailed} image upload${imageFailed === 1 ? '' : 's'} failed.` : '';
      toast.success(`${succeeded} variant${succeeded === 1 ? '' : 's'} added.${imageNote}`);
      handleClose();
    } else {
      toast.warning(
        `${succeeded} variant${succeeded === 1 ? '' : 's'} added. ${failed} failed.`,
      );
    }
  });

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="w-[calc(100vw-2rem)] max-w-[calc(100vw-2rem)] sm:max-w-[1100px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-slate-800">
            Add Variants{product ? ` — ${product.name}` : ''}
          </DialogTitle>
        </DialogHeader>

        <Separator />

        <form onSubmit={handleVariantSubmit} className="space-y-4">
          <div className="grid grid-cols-[minmax(6rem,1fr)_minmax(6rem,1fr)_minmax(5rem,0.8fr)_minmax(5rem,0.8fr)_minmax(5rem,0.8fr)_minmax(5rem,0.8fr)_minmax(7rem,1fr)_2.25rem] gap-2 px-3 text-xs font-medium text-stone-500 uppercase tracking-wide">
            <div>Size</div>
            <div>Color</div>
            <div>MRP</div>
            <div>Sell before GST</div>
            <div>Cost before GST</div>
            <div>Fabric</div>
            <div>Photo</div>
            <div />
          </div>

          <div className="space-y-2">
            {fields.map((field, index) => (
              <VariantRow
                key={field.id}
                index={index}
                onRemove={() => remove(index)}
                control={control}
                register={register}
                errors={errors}
              />
            ))}
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append({ ...DEFAULT_VARIANT })}
            className="text-slate-700"
          >
            + Add another variant
          </Button>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || fields.length === 0}
              className="bg-slate-800 hover:bg-slate-700 text-white"
            >
              {isSubmitting ? 'Saving…' : `Save ${fields.length} Variant${fields.length === 1 ? '' : 's'}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
