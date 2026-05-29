'use client';

/**
 * MasterDataPage — generic, reusable CRUD page for flat master-data entities.
 *
 * Supports any entity that has: id, name, and an optional extra field (hex_code,
 * description, sort_order). The caller supplies the query result, mutation hook,
 * and column/form configuration.
 *
 * Usage: wrap this inside a specific page (e.g. CategoriesPage) and pass
 * entity-specific hooks and metadata as props.
 */

import { useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Upload } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ApiError } from '@/types/api';
import type { MasterDataImportResponse } from '@/types/catalog';

// ── Generic item shape ────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type MasterItem = { id: string; name: string } & Record<string, any>;

// ── Column descriptor ─────────────────────────────────────────────────────────

export interface MasterColumn {
  key: string;
  label: string;
  render?: (item: MasterItem) => React.ReactNode;
}

// ── Form field descriptor ─────────────────────────────────────────────────────

export interface MasterFormField {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'color';
  placeholder?: string;
  required?: boolean;
  defaultValue?: string | number;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface MasterDataPageProps {
  title: string;
  description: string;
  items: MasterItem[];
  isLoading: boolean;
  columns: MasterColumn[];
  formFields: MasterFormField[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onCreate: (data: any) => Promise<unknown>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onUpdate?: (id: string, data: any) => Promise<unknown>;
  onImportCsv?: (file: File) => Promise<MasterDataImportResponse>;
  csvColumns?: string[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MasterDataPage({
  title,
  description,
  items,
  isLoading,
  columns,
  formFields,
  onCreate,
  onUpdate,
  onImportCsv,
  csvColumns,
}: MasterDataPageProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<MasterItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const defaultValues = Object.fromEntries(
    formFields.map((f) => [f.key, f.defaultValue ?? '']),
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ defaultValues });

  const singularTitle = title.replace(/s$/, '');

  const openCreateDialog = () => {
    setEditingItem(null);
    reset(defaultValues);
    setDialogOpen(true);
  };

  const openEditDialog = (item: MasterItem) => {
    setEditingItem(item);
    reset({
      ...defaultValues,
      ...Object.fromEntries(
        formFields.map((field) => [field.key, item[field.key] ?? field.defaultValue ?? '']),
      ),
    });
    setDialogOpen(true);
  };

  const handleClose = () => {
    reset(defaultValues);
    setEditingItem(null);
    setDialogOpen(false);
  };

  const onSubmit = handleSubmit(async (values) => {
    setIsSubmitting(true);
    try {
      if (editingItem && onUpdate) {
        await onUpdate(editingItem.id, values);
        toast.success(`${singularTitle} updated successfully.`);
      } else {
        await onCreate(values);
        toast.success(`${singularTitle} created successfully.`);
      }
      handleClose();
    } catch (err) {
      const action = editingItem ? 'update' : 'create';
      const msg = err instanceof ApiError ? err.message : `Failed to ${action} ${title.toLowerCase()}.`;
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  });

  async function handleCsvSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !onImportCsv) return;

    setIsImporting(true);
    try {
      const result = await onImportCsv(file);
      const summary = `${result.created} created, ${result.skipped} skipped`;
      if (result.errors.length > 0) {
        toast.warning(`${summary}. ${result.errors.length} row issue${result.errors.length === 1 ? '' : 's'} found.`);
      } else {
        toast.success(`${title} imported. ${summary}.`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : `Failed to import ${title.toLowerCase()}.`;
      toast.error(msg);
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">{title}</h1>
          <p className="mt-1 text-sm text-stone-500">{description}</p>
          {csvColumns && (
            <p className="mt-1 text-xs text-stone-400">
              CSV columns: {csvColumns.join(', ')}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {onImportCsv && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={handleCsvSelected}
              />
              <Button
                type="button"
                variant="outline"
                disabled={isImporting}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="mr-2 h-4 w-4" />
                {isImporting ? 'Importing…' : 'Import CSV'}
              </Button>
            </>
          )}
          <Button
            onClick={openCreateDialog}
            className="bg-slate-800 hover:bg-slate-700 text-white"
          >
            + Add {singularTitle}
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-stone-200 bg-white overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-stone-50 hover:bg-stone-50">
              {columns.map((col) => (
                <TableHead key={col.key} className="text-stone-600 font-medium">
                  {col.label}
                </TableHead>
              ))}
              {onUpdate && (
                <TableHead className="text-stone-600 font-medium text-right">
                  Actions
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  {[...columns, ...(onUpdate ? [{ key: '__actions__', label: 'Actions' }] : [])].map((col) => (
                    <TableCell key={col.key}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length + (onUpdate ? 1 : 0)} className="py-12 text-center text-stone-400">
                  No {title.toLowerCase()} yet. Add the first one!
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow key={item.id} className="hover:bg-stone-50/60">
                  {columns.map((col) => (
                    <TableCell key={col.key} className="text-slate-700">
                      {col.render ? col.render(item) : String(item[col.key] ?? '—')}
                    </TableCell>
                  ))}
                  {onUpdate && (
                    <TableCell className="text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-slate-700 hover:bg-stone-100"
                        onClick={() => openEditDialog(item)}
                      >
                        Edit
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create dialog */}
      <Dialog open={dialogOpen} onOpenChange={handleClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-slate-800">
              {editingItem ? `Edit ${singularTitle}` : `Add ${singularTitle}`}
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={onSubmit} className="space-y-4 pt-2">
            {formFields.map((field) => (
              <div key={field.key} className="space-y-1.5">
                <Label htmlFor={field.key}>
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                <Input
                  id={field.key}
                  type={field.type ?? 'text'}
                  placeholder={field.placeholder}
                  {...register(field.key, { required: field.required ? `${field.label} is required` : false })}
                  className={`bg-white ${errors[field.key] ? 'border-red-400' : ''}`}
                />
                {errors[field.key] && (
                  <p className="text-xs text-red-500">
                    {String(errors[field.key]?.message ?? 'Required')}
                  </p>
                )}
              </div>
            ))}

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-slate-800 hover:bg-slate-700 text-white"
              >
                {isSubmitting ? 'Saving…' : editingItem ? 'Save Changes' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
