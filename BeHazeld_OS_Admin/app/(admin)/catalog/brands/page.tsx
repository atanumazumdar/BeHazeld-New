'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import { useBrands, useCreateBrand } from '@/hooks/use-catalog';

export default function BrandsPage() {
  const { data: brands = [], isLoading } = useBrands();
  const createBrand = useCreateBrand();

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
    />
  );
}
