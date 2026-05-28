'use client';

/**
 * Catalog section layout — adds a secondary tab navigation below the
 * admin topbar for quick switching between catalog sub-sections.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const CATALOG_TABS = [
  { href: '/catalog/products',   label: 'Products' },
  { href: '/catalog/product-groups', label: 'Groups' },
  { href: '/catalog/product-types', label: 'Types' },
  { href: '/catalog/categories', label: 'Categories' },
  { href: '/catalog/brands',     label: 'Brands' },
  { href: '/catalog/sizes',      label: 'Sizes' },
  { href: '/catalog/colors',     label: 'Colors' },
] as const;

export default function CatalogLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      {/* Secondary tab nav */}
      <nav className="flex gap-1 border-b border-stone-200 -mb-2">
        {CATALOG_TABS.map((tab) => {
          const isActive = pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                isActive
                  ? 'border-slate-800 text-slate-800'
                  : 'border-transparent text-stone-500 hover:text-stone-700 hover:border-stone-300',
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {/* Page content */}
      <div>{children}</div>
    </div>
  );
}
