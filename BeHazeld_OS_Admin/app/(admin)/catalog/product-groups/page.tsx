'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import {
  useCreateProductGroup,
  useImportMasterData,
  useProductGroups,
} from '@/hooks/use-catalog';

export default function ProductGroupsPage() {
  const { data: groups = [], isLoading } = useProductGroups();
  const createGroup = useCreateProductGroup();
  const importCsv = useImportMasterData('product-groups');

  return (
    <MasterDataPage
      title="Product Groups"
      description="Manage collection and campaign groupings for products."
      items={groups as MasterItem[]}
      isLoading={isLoading}
      columns={[
        { key: 'name', label: 'Group Name' },
        { key: 'description', label: 'Description' },
      ]}
      formFields={[
        { key: 'name', label: 'Group Name', required: true, placeholder: 'e.g. Campus Muse' },
        { key: 'description', label: 'Description', placeholder: 'Optional description…' },
      ]}
      onCreate={(data) =>
        createGroup.mutateAsync({
          name: data.name,
          description: data.description || null,
        })
      }
      onImportCsv={(file) => importCsv.mutateAsync(file)}
      csvColumns={['name', 'description']}
    />
  );
}
