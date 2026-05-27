'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
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

    apiClient
      .get<UserResponse>('/api/v1/auth/me')
      .then((data) => {
        if (!cancelled) setUser(data);
      })
      .catch(() => {
        // 401 handled by api-client (redirects to /login)
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
