'use client';

import { MasterDataPage, MasterItem } from '@/components/catalog/master-data-page';
import {
  useColors,
  useCreateColor,
  useDeleteMasterData,
  useImportMasterData,
  useUpdateMasterData,
} from '@/hooks/use-catalog';
import type { CreateColorPayload } from '@/types/catalog';

function ColorSwatch({ item }: { item: MasterItem }) {
  const hex = item.hex_code as string | null;
  return (
    <div className="flex items-center gap-2">
      {hex && (
        <span
          className="inline-block h-4 w-4 rounded-full border border-stone-200"
          style={{ backgroundColor: hex }}
        />
      )}
      <span className="font-mono text-sm text-stone-600">{hex ?? '—'}</span>
    </div>
  );
}

export default function ColorsPage() {
  const { data: colors = [], isLoading } = useColors();
  const createColor = useCreateColor();
  const updateColor = useUpdateMasterData('colors');
  const deleteColor = useDeleteMasterData('colors');
  const importCsv = useImportMasterData('colors');

  return (
    <MasterDataPage
      title="Colors"
      description="Define the colour options available for product variants."
      items={colors as MasterItem[]}
      isLoading={isLoading}
      columns={[
        { key: 'name', label: 'Color Name' },
        {
          key: 'hex_code',
          label: 'Hex Code',
          render: (item) => <ColorSwatch item={item} />,
        },
      ]}
      formFields={[
        { key: 'name', label: 'Color Name', required: true, placeholder: 'e.g. Midnight Blue' },
        { key: 'hex_code', label: 'Hex Code', placeholder: '#1a2b3c' },
      ]}
      onCreate={(data) =>
        createColor.mutateAsync({
          name: data.name,
          hex_code: data.hex_code || null,
        } as CreateColorPayload)
      }
      onUpdate={(id, data) =>
        updateColor.mutateAsync({
          id,
          data: {
            name: data.name,
            hex_code: data.hex_code || null,
          } as CreateColorPayload,
        })
      }
      onDelete={(id) => deleteColor.mutateAsync(id)}
      onImportCsv={(file) => importCsv.mutateAsync(file)}
      csvColumns={['name', 'hex_code']}
    />
  );
}
