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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface LoginResult {
  success: boolean;
  message?: string;
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

  const isProduction = process.env.NODE_ENV === 'production';
  const baseOptions = {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax' as const,
    path: '/',
  };

  cookieStore.set('access_token', body.access_token, {
    ...baseOptions,
    maxAge: 30 * 60, // 30 minutes
  });
  cookieStore.set('refresh_token', body.refresh_token, {
    ...baseOptions,
    maxAge: 7 * 24 * 60 * 60, // 7 days
  });

  return { success: true };
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
