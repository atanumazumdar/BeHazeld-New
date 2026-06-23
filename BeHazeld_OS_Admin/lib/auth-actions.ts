'use server';

/**
 * Server Actions for authentication.
 *
 * loginAction: POSTs credentials to FastAPI. Reads tokens from the JSON
 *   body response and sets them as httpOnly cookies via next/headers.
 *   Returns { success: true } or { success: false, message: string }.
 *
 * logoutAction: POSTs to FastAPI /auth/logout with the refresh_token
 *   (read from cookies), clears both cookies via next/headers,
 *   then redirects to /login.
 */

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import type { UserResponse } from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const ACCESS_MAX_AGE = 30 * 60;
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

export interface LoginResult {
  success: boolean;
  message?: string;
}

export interface ForgotPasswordResult {
  success: boolean;
  message?: string;
  resetToken?: string | null;
}

export interface CurrentUserResult {
  success: boolean;
  user?: UserResponse;
  message?: string;
}

function cookieOptions() {
  const isProduction = process.env.NODE_ENV === 'production';
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax' as const,
    path: '/',
  };
}

async function refreshAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('refresh_token')?.value;
  if (!refreshToken) return null;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return null;
  }

  if (!response.ok) return null;

  const body = await response.json();
  const options = cookieOptions();
  cookieStore.set('access_token', body.access_token, {
    ...options,
    maxAge: ACCESS_MAX_AGE,
  });
  cookieStore.set('refresh_token', body.refresh_token, {
    ...options,
    maxAge: REFRESH_MAX_AGE,
  });

  return body.access_token as string;
}

export async function loginAction(formData: FormData): Promise<LoginResult> {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    let message = 'Login failed. Please check your credentials.';
    try {
      const body = await response.json();
      if (body.message) message = body.message;
    } catch {
      // ignore parse error
    }
    return { success: false, message };
  }

  // Parse tokens from body and set them as cookies via next/headers
  // so Next.js middleware can read them on subsequent requests.
  const body = await response.json();
  const cookieStore = await cookies();

  const baseOptions = cookieOptions();

  cookieStore.set('access_token', body.access_token, {
    ...baseOptions,
    maxAge: ACCESS_MAX_AGE,
  });
  cookieStore.set('refresh_token', body.refresh_token, {
    ...baseOptions,
    maxAge: REFRESH_MAX_AGE,
  });

  return { success: true };
}

export async function forgotPasswordAction(formData: FormData): Promise<ForgotPasswordResult> {
  const email = formData.get('email') as string;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    return { success: false, message: 'Could not start password reset. Please try again.' };
  }

  const body = await response.json();
  return {
    success: true,
    message: body.message ?? 'If the account exists, a reset token has been generated.',
    resetToken: body.reset_token ?? null,
  };
}

export async function resetPasswordAction(formData: FormData): Promise<LoginResult> {
  const resetToken = formData.get('reset_token') as string;
  const newPassword = formData.get('new_password') as string;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
    });
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    let message = 'Could not reset password. Please try again.';
    try {
      const body = await response.json();
      if (body.message) message = body.message;
      if (body.detail) message = body.detail;
    } catch {
      // ignore parse error
    }
    return { success: false, message };
  }

  const body = await response.json();
  return { success: true, message: body.message ?? 'Password has been reset. Please sign in.' };
}

export async function getCurrentUserAction(): Promise<CurrentUserResult> {
  const cookieStore = await cookies();
  let accessToken = cookieStore.get('access_token')?.value ?? null;

  if (!accessToken) {
    accessToken = await refreshAccessToken();
  }
  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: 'no-store',
    });
  } catch {
    return { success: false, message: 'Unable to reach the server.' };
  }

  if (response.status === 401) {
    const refreshedToken = await refreshAccessToken();
    if (!refreshedToken) {
      return { success: false, message: 'Session expired. Please sign in again.' };
    }
    response = await fetch(`${API_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${refreshedToken}` },
      cache: 'no-store',
    });
  }

  if (!response.ok) {
    return { success: false, message: `Unable to load user profile (HTTP ${response.status}).` };
  }

  return { success: true, user: (await response.json()) as UserResponse };
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('refresh_token')?.value;

  // Notify backend to revoke the refresh token
  if (refreshToken) {
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Best-effort — clear cookies regardless
    }
  }

  // Clear cookies on the Next.js side
  cookieStore.delete('access_token');
  cookieStore.delete('refresh_token');

  redirect('/login');
}
