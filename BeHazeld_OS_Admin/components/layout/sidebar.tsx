'use client';

import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  Package,
  ArrowLeftRight,
  ShoppingCart,
  Truck,
  BookOpen,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { SidebarNavItem } from './sidebar-nav-item';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/catalog',   icon: Package,         label: 'Catalog' },
  { href: '/inventory', icon: ArrowLeftRight,   label: 'Inventory' },
  { href: '/sales',     icon: ShoppingCart,     label: 'Sales' },
  { href: '/purchases', icon: Truck,            label: 'Purchases' },
  { href: '/finance',   icon: BookOpen,         label: 'Finance' },
  { href: '/audit',     icon: ShieldCheck,      label: 'Audit Trail' },
] as const;

const SETTINGS_ITEM = { href: '/settings', icon: Settings, label: 'Settings' } as const;

const STORAGE_KEY = 'sidebar-collapsed';

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Read persisted state after mount to avoid hydration mismatch
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'true') setCollapsed(true);
    setMounted(true);
  }, []);

  function toggle() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }

  // Prevent flash of incorrect state during hydration
  if (!mounted) return null;

  return (
    <TooltipProvider delay={0}>
      <aside
        data-collapsed={collapsed}
        className={cn(
          'flex h-screen flex-col border-r border-stone-200 bg-stone-50 transition-all duration-200',
          collapsed ? 'w-16' : 'w-60',
        )}
      >
        {/* Logo / wordmark */}
        <div
          className={cn(
            'flex h-16 items-center border-b border-stone-200 px-4',
            collapsed ? 'justify-center' : '',
          )}
        >
          {collapsed ? (
            <span className="text-sm font-black text-rose-800">B</span>
          ) : (
            <span className="text-sm font-black text-stone-900 tracking-tight">
              BeHazeld <span className="text-rose-800">OS</span>
            </span>
          )}
        </div>

        {/* Main nav */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV_ITEMS.map((item) => (
            <SidebarNavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              collapsed={collapsed}
            />
          ))}
        </nav>

        {/* Bottom: settings + collapse toggle */}
        <div className="border-t border-stone-200 p-2 space-y-0.5">
          <SidebarNavItem
            href={SETTINGS_ITEM.href}
            icon={SETTINGS_ITEM.icon}
            label={SETTINGS_ITEM.label}
            collapsed={collapsed}
          />

          <button
            onClick={toggle}
            className={cn(
              'flex w-full items-center rounded-md px-3 py-2 text-sm text-stone-500',
              'hover:bg-stone-100 hover:text-stone-700 transition-colors',
              collapsed ? 'justify-center px-2' : 'gap-3',
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
