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
import { useUpdateProduct } from '@/hooks/use-catalog';
import type { ProductResponse } from '@/types/catalog';

interface EditProductDialogProps {
  product: ProductResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface EditProductFormValues {
  name: string;
  description: string;
}

export function EditProductDialog({
  product,
  open,
  onOpenChange,
}: EditProductDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const updateProduct = useUpdateProduct();
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EditProductFormValues>({
    defaultValues: {
      name: '',
      description: '',
    },
  });

  useEffect(() => {
    if (!product) return;
    reset({
      name: product.name,
      description: product.description ?? '',
    });
  }, [product, reset]);

  const handleClose = () => {
    if (isSubmitting) return;
    onOpenChange(false);
  };

  const handleProductSubmit = handleSubmit(async (values) => {
    if (!product) return;
    setIsSubmitting(true);

    try {
      await updateProduct.mutateAsync({
        productId: product.id,
        data: {
          name: values.name,
          description: values.description || null,
          category_id: product.category_id,
          product_group_id: product.product_group_id,
          product_type_id: product.product_type_id,
          brand_id: product.brand_id,
          image_url: product.image_url,
        },
      });
      toast.success('Product updated.');
      handleClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update product.';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  });

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="w-[calc(100vw-2rem)] max-w-[calc(100vw-2rem)] sm:max-w-[640px]">
        <DialogHeader>
          <DialogTitle className="text-slate-800">Edit Product</DialogTitle>
        </DialogHeader>

        <Separator />

        <form onSubmit={handleProductSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>
              Product Name <span className="text-red-500">*</span>
            </Label>
            <Controller
              name="name"
              control={control}
              rules={{
                validate: (value) => value.trim().length > 0 || 'Name is required',
              }}
              render={({ field }) => (
                <Input
                  value={field.value}
                  onValueChange={field.onChange}
                  onBlur={field.onBlur}
                  className={`bg-white ${errors.name ? 'border-red-400' : ''}`}
                />
              )}
            />
            {errors.name && (
              <p className="text-xs text-red-500">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Description</Label>
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <Input
                  value={field.value}
                  onValueChange={field.onChange}
                  onBlur={field.onBlur}
                  placeholder="Optional description"
                  className="bg-white"
                />
              )}
            />
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
              {isSubmitting ? 'Saving…' : 'Save Product'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
