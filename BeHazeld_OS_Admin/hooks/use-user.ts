'use client';

import { useState, useEffect } from 'react';
import { getCurrentUserAction } from '@/lib/auth-actions';
import type { UserResponse } from '@/types/api';

interface UseUserResult {
  user: UserResponse | null;
  isLoading: boolean;
}

export function useUser(): UseUserResult {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    getCurrentUserAction()
      .then((result) => {
        if (!cancelled && result.success) setUser(result.user ?? null);
      })
      .catch(() => {
        // Keep the dashboard stable if the profile lookup fails.
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { user, isLoading };
}
