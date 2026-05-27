import { redirect } from 'next/navigation';

/** /catalog → /catalog/products */
export default function CatalogIndexPage() {
  redirect('/catalog/products');
}
