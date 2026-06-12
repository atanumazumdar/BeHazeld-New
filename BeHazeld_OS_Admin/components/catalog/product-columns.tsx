'use client';

/**
 * Column definitions for the Product DataTable.
 * Uses Shadcn Table primitives directly (no @tanstack/react-table dependency required
 * for our simple server-side-paginated table pattern).
 */

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { type ChangeEvent, useRef } from 'react';
import { toast } from 'sonner';
import { useUploadVariantImage } from '@/hooks/use-catalog';
import { prepareProductImageForUpload } from '@/lib/image-upload';

interface ProductActionsProps {
  productId: string;
  variantId: string | null;
  hasImage: boolean;
  onEditProduct: () => void;
  onAddVariant: () => void;
  onEditVariant: () => void;
  onDelete: (id: string) => void;
}

export function ProductStatusBadge({ status }: { status: string }) {
  const isActive = status === 'active';
  return (
    <Badge
      variant={isActive ? 'default' : 'secondary'}
      className={
        isActive
          ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-100'
          : 'bg-stone-100 text-stone-600 hover:bg-stone-100'
      }
    >
      {isActive ? 'Active' : 'Deleted'}
    </Badge>
  );
}

export function ProductRowActions({
  productId,
  variantId,
  hasImage,
  onEditProduct,
  onAddVariant,
  onEditVariant,
  onDelete,
}: ProductActionsProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadVariantImage = useUploadVariantImage(productId);

  const handlePhotoChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !variantId) return;

    try {
      const preparedFile = await prepareProductImageForUpload(file);
      if (preparedFile.size < file.size) {
        toast.info('Photo optimized for upload.');
      }
      await uploadVariantImage.mutateAsync({ variantId, file: preparedFile });
      toast.success(hasImage ? 'Picture updated.' : 'Picture uploaded.');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to upload picture.';
      toast.error(msg);
    }
  };

  return (
    <div className="flex items-center justify-end gap-2">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handlePhotoChange}
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-slate-700 hover:bg-stone-100"
        onClick={onEditProduct}
      >
        Edit Product
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-slate-700 hover:bg-stone-100"
        disabled={!variantId}
        onClick={onEditVariant}
      >
        Edit Variant
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-slate-700 hover:bg-stone-100"
        onClick={onAddVariant}
      >
        Add Variant
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="text-slate-700 hover:bg-stone-100"
        disabled={!variantId || uploadVariantImage.isPending}
        onClick={() => inputRef.current?.click()}
      >
        {hasImage ? 'Edit Photo' : 'Add Photo'}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-red-600 hover:text-red-700 hover:bg-red-50"
        onClick={() => onDelete(productId)}
      >
        Archive
      </Button>
    </div>
  );
}
