'use client';

/**
 * /catalog/products — Product management page.
 *
 * Houses the ProductTable (search + filters + pagination) and the
 * CreateProductWizard dialog triggered by the "+ New Product" button.
 */

import { useState } from 'react';
import { ProductTable } from '@/components/catalog/product-table';
import { CreateProductWizard } from '@/components/catalog/create-product-wizard';

export default function ProductsPage() {
  const [wizardOpen, setWizardOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Products</h1>
        <p className="mt-1 text-sm text-stone-500">
          Manage your product catalogue — create products and add SKU variants.
        </p>
      </div>

      {/* Table with inline "+ New Product" button */}
      <ProductTable onCreateClick={() => setWizardOpen(true)} />

      {/* Creation wizard dialog */}
      <CreateProductWizard open={wizardOpen} onOpenChange={setWizardOpen} />
    </div>
  );
}
