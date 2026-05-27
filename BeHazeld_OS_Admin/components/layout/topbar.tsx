'use client';

import { Bell, Search } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useUser } from '@/hooks/use-user';
import { logoutAction } from '@/lib/auth-actions';

interface TopbarProps {
  pageTitle?: string;
}

export function Topbar({ pageTitle = 'Dashboard' }: TopbarProps) {
  const { user } = useUser();

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : 'BH';

  function handleSignOut() {
    void logoutAction();
  }

  return (
    <header className="flex h-16 items-center border-b border-stone-200 bg-white px-6 gap-4">
      {/* Page title */}
      <h1 className="text-base font-semibold text-stone-800 flex-1">{pageTitle}</h1>

      {/* Tenant badge */}
      <span className="hidden sm:inline-block text-xs text-stone-400 font-medium bg-stone-100 px-2.5 py-1 rounded-full">
        BeHazeld
      </span>

      {/* Search (static placeholder) */}
      <button className="flex items-center gap-2 rounded-md border border-stone-200 bg-stone-50 px-3 py-1.5 text-sm text-stone-400 hover:bg-stone-100 transition-colors">
        <Search className="h-3.5 w-3.5" />
        <span className="hidden md:inline">Search…</span>
      </button>

      {/* Notification bell */}
      <button className="relative rounded-md p-1.5 text-stone-500 hover:bg-stone-100 transition-colors">
        <Bell className="h-4 w-4" />
      </button>

      {/* User avatar + dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-stone-100 transition-colors outline-none">
            <Avatar className="h-7 w-7">
              <AvatarFallback className="bg-rose-800 text-white text-xs font-bold">
                {initials}
              </AvatarFallback>
            </Avatar>
            {user && (
              <span className="hidden sm:inline-block text-sm font-medium text-stone-700">
                {user.username}
              </span>
            )}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          <DropdownMenuLabel className="text-xs text-stone-500">
            {user?.email ?? 'Loading…'}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Profile</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-rose-700 focus:text-rose-700 cursor-pointer"
            onSelect={handleSignOut}
          >
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
