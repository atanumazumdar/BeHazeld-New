'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import {
  useBrands,
  useCreateBrand,
  useDeleteMasterData,
  useImportMasterData,
  useUpdateMasterData,
} from '@/hooks/use-catalog';

export default function BrandsPage() {
  const { data: brands = [], isLoading } = useBrands();
  const createBrand = useCreateBrand();
  const updateBrand = useUpdateMasterData('brands');
  const deleteBrand = useDeleteMasterData('brands');
  const importCsv = useImportMasterData('brands');

  return (
    <MasterDataPage
      title="Brands"
      description="Manage the brands associated with your products."
      items={brands as MasterItem[]}
      isLoading={isLoading}
      columns={[{ key: 'name', label: 'Brand Name' }]}
      formFields={[
        { key: 'name', label: 'Brand Name', required: true, placeholder: 'e.g. Zara' },
      ]}
      onCreate={(data) => createBrand.mutateAsync({ name: data.name })}
      onUpdate={(id, data) => updateBrand.mutateAsync({ id, data: { name: data.name } })}
      onDelete={(id) => deleteBrand.mutateAsync(id)}
      onImportCsv={(file) => importCsv.mutateAsync(file)}
      csvColumns={['name']}
    />
  );
}
