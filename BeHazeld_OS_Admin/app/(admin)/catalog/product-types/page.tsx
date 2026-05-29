'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import {
  useCreateProductType,
  useImportMasterData,
  useProductTypes,
  useUpdateMasterData,
} from '@/hooks/use-catalog';

export default function ProductTypesPage() {
  const { data: types = [], isLoading } = useProductTypes();
  const createType = useCreateProductType();
  const updateType = useUpdateMasterData('product-types');
  const importCsv = useImportMasterData('product-types');

  return (
    <MasterDataPage
      title="Product Types"
      description="Manage garment or item types used when creating products."
      items={types as MasterItem[]}
      isLoading={isLoading}
      columns={[{ key: 'name', label: 'Type Name' }]}
      formFields={[
        { key: 'name', label: 'Type Name', required: true, placeholder: 'e.g. Dress' },
      ]}
      onCreate={(data) => createType.mutateAsync({ name: data.name })}
      onUpdate={(id, data) => updateType.mutateAsync({ id, data: { name: data.name } })}
      onImportCsv={(file) => importCsv.mutateAsync(file)}
      csvColumns={['name']}
    />
  );
}
