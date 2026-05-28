'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import { useSizes, useCreateSize, useImportMasterData } from '@/hooks/use-catalog';
import type { CreateSizePayload } from '@/types/catalog';

export default function SizesPage() {
  const { data: sizes = [], isLoading } = useSizes();
  const createSize = useCreateSize();
  const importCsv = useImportMasterData('sizes');

  return (
    <MasterDataPage
      title="Sizes"
      description="Define the size options available for product variants."
      items={sizes as MasterItem[]}
      isLoading={isLoading}
      columns={[
        { key: 'name', label: 'Size Name' },
        { key: 'sort_order', label: 'Sort Order' },
      ]}
      formFields={[
        { key: 'name', label: 'Size Name', required: true, placeholder: 'e.g. XL' },
        { key: 'sort_order', label: 'Sort Order', type: 'number', defaultValue: 0 },
      ]}
      onCreate={(data) =>
        createSize.mutateAsync({
          name: data.name,
          sort_order: Number(data.sort_order ?? 0),
        } as CreateSizePayload)
      }
      onImportCsv={(file) => importCsv.mutateAsync(file)}
      csvColumns={['name', 'sort_order']}
    />
  );
}
