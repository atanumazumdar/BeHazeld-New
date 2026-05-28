'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import { useCategories, useCreateCategory, useImportMasterData } from '@/hooks/use-catalog';
import type { CreateCategoryPayload } from '@/types/catalog';

export default function CategoriesPage() {
  const { data: categories = [], isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const importCsv = useImportMasterData('categories');

  return (
    <MasterDataPage
      title="Categories"
      description="Organise products into browsable categories."
      items={categories as MasterItem[]}
      isLoading={isLoading}
      columns={[
        { key: 'name', label: 'Name' },
        { key: 'description', label: 'Description' },
        { key: 'sort_order', label: 'Sort Order' },
      ]}
      formFields={[
        { key: 'name', label: 'Category Name', required: true, placeholder: 'e.g. Shirts' },
        { key: 'description', label: 'Description', placeholder: 'Optional description…' },
        { key: 'sort_order', label: 'Sort Order', type: 'number', defaultValue: 0 },
      ]}
      onCreate={(data) =>
        createCategory.mutateAsync({
          name: data.name,
          description: data.description || null,
          sort_order: Number(data.sort_order ?? 0),
        } as CreateCategoryPayload)
      }
      onImportCsv={(file) => importCsv.mutateAsync(file)}
      csvColumns={['name', 'description', 'sort_order']}
    />
  );
}
