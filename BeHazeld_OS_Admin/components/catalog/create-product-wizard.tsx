'use client';

/**
 * CreateProductWizard — 2-step dialog for creating products with variants.
 *
 * Step 1: Basic details — Name, Product Group, Product Type, Brand, Category
 * Step 2: Variants   — dynamic rows (Size, Color, MRP, Selling Price, Cost Price, Fabric)
 *
 * Flow:
 * 1. Submit Step 1 → POST /catalog/products → get product.id
 * 2. Submit Step 2 → POST /catalog/products/{id}/variants (one per row, sequential)
 * 3. Invalidate products query, close dialog, toast success
 *
 * If any variant POST fails, existing variants stay (backend is atomic per-variant).
 * The user is told which ones succeeded.
 */

import { useState } from 'react';
import { useForm, useFieldArray, Controller } from 'react-hook-form';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
import { VariantRow } from './variant-row';

import {
  useCreateProduct,
  useCreateVariant,
  useCategories,
  useProductGroups,
  useProductTypes,
  useBrands,
} from '@/hooks/use-catalog';
import { ApiError } from '@/types/api';

// ── Form shape ────────────────────────────────────────────────────────────────

export interface VariantFormRow {
  size_id: string;
  color_id: string;
  mrp: string;
  selling_price: string;
  cost_price: string;
  fabric: string;
}

export interface WizardFormValues {
  // Step 1
  name: string;
  category_id: string;
  product_group_id: string;
  product_type_id: string;
  brand_id: string;
  description: string;
  // Step 2
  variants: VariantFormRow[];
}

const DEFAULT_VARIANT: VariantFormRow = {
  size_id: '',
  color_id: '',
  mrp: '',
  selling_price: '',
  cost_price: '',
  fabric: '',
};

// ── Wizard component ──────────────────────────────────────────────────────────

interface CreateProductWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateProductWizard({ open, onOpenChange }: CreateProductWizardProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [createdProductId, setCreatedProductId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: categories = [] } = useCategories();
  const { data: productGroups = [] } = useProductGroups();
  const { data: productTypes = [] } = useProductTypes();
  const { data: brands = [] } = useBrands();

  const createProduct = useCreateProduct();

  const {
    register,
    handleSubmit,
    control,
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

  // The createVariant mutation depends on the product ID created in Step 1
  const createVariant = useCreateVariant(createdProductId ?? '');

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleClose = () => {
    if (isSubmitting) return;
    reset();
    setStep(1);
    setCreatedProductId(null);
    onOpenChange(false);
  };

  const handleStep1Submit = handleSubmit(async (values) => {
    setIsSubmitting(true);
    try {
      const product = await createProduct.mutateAsync({
        name: values.name,
        category_id: values.category_id || null,
        product_group_id: values.product_group_id || null,
        product_type_id: values.product_type_id || null,
        brand_id: values.brand_id || null,
        description: values.description || null,
        image_url: null,
      });
      setCreatedProductId(product.id);
      setStep(2);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to create product.';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  });

  const handleStep2Submit = handleSubmit(async (values) => {
    if (!createdProductId) return;
    setIsSubmitting(true);

    let succeeded = 0;
    let failed = 0;

    for (const variant of values.variants) {
      try {
        await createVariant.mutateAsync({
          size_id: variant.size_id,
          color_id: variant.color_id,
          mrp: variant.mrp,
          selling_price: variant.selling_price,
          cost_price: variant.cost_price,
          fabric: variant.fabric || null,
          reorder_level: '0',
        });
        succeeded++;
      } catch {
        failed++;
      }
    }

    setIsSubmitting(false);

    if (failed === 0) {
      toast.success(`Product created with ${succeeded} variant${succeeded !== 1 ? 's' : ''}.`);
    } else {
      toast.warning(
        `${succeeded} variant${succeeded !== 1 ? 's' : ''} added. ${failed} failed — check for duplicate size/color combinations.`,
      );
    }

    handleClose();
  });

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-slate-800">
            {step === 1 ? 'New Product — Basic Details' : 'Add Variants'}
          </DialogTitle>
          {/* Step indicator */}
          <div className="flex items-center gap-2 pt-1">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${step === 1 ? 'bg-slate-800 text-white' : 'bg-stone-200 text-stone-500'}`}>
              1 · Details
            </span>
            <div className="h-px flex-1 bg-stone-200" />
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${step === 2 ? 'bg-slate-800 text-white' : 'bg-stone-200 text-stone-500'}`}>
              2 · Variants
            </span>
          </div>
        </DialogHeader>

        <Separator className="my-2" />

        {/* ── Step 1 ── */}
        {step === 1 && (
          <form onSubmit={handleStep1Submit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Product Name */}
              <div className="col-span-2 space-y-1.5">
                <Label htmlFor="name">
                  Product Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="name"
                  {...register('name', { required: 'Name is required' })}
                  placeholder="e.g. Classic Linen Shirt"
                  className={errors.name ? 'border-red-400' : ''}
                />
                {errors.name && (
                  <p className="text-xs text-red-500">{errors.name.message}</p>
                )}
              </div>

              {/* Product Group */}
              <div className="space-y-1.5">
                <Label>Product Group</Label>
                <Controller
                  name="product_group_id"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Select group…" />
                      </SelectTrigger>
                      <SelectContent>
                        {productGroups.map((g) => (
                          <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              {/* Product Type */}
              <div className="space-y-1.5">
                <Label>Product Type</Label>
                <Controller
                  name="product_type_id"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Select type…" />
                      </SelectTrigger>
                      <SelectContent>
                        {productTypes.map((t) => (
                          <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              {/* Brand */}
              <div className="space-y-1.5">
                <Label>Brand</Label>
                <Controller
                  name="brand_id"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Select brand…" />
                      </SelectTrigger>
                      <SelectContent>
                        {brands.map((b) => (
                          <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              {/* Category */}
              <div className="space-y-1.5">
                <Label>Category</Label>
                <Controller
                  name="category_id"
                  control={control}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Select category…" />
                      </SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => (
                          <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              {/* Description */}
              <div className="col-span-2 space-y-1.5">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  {...register('description')}
                  placeholder="Optional product description…"
                />
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-slate-800 hover:bg-slate-700 text-white"
              >
                {isSubmitting ? 'Creating…' : 'Next → Add Variants'}
              </Button>
            </DialogFooter>
          </form>
        )}

        {/* ── Step 2 ── */}
        {step === 2 && (
          <form onSubmit={handleStep2Submit} className="space-y-4">
            {/* Column headers */}
            <div className="grid grid-cols-12 gap-2 px-3 text-xs font-medium text-stone-500 uppercase tracking-wide">
              <div className="col-span-2">Size</div>
              <div className="col-span-2">Color</div>
              <div className="col-span-2">MRP</div>
              <div className="col-span-2">Sell Price</div>
              <div className="col-span-2">Cost</div>
              <div className="col-span-1">Fabric</div>
              <div className="col-span-1" />
            </div>

            {/* Variant rows */}
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

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep(1)}
                disabled={isSubmitting}
              >
                ← Back
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting || fields.length === 0}
                className="bg-slate-800 hover:bg-slate-700 text-white"
              >
                {isSubmitting ? 'Saving…' : `Save ${fields.length} Variant${fields.length !== 1 ? 's' : ''}`}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
