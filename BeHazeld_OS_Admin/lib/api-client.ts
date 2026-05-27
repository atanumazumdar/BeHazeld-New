/**
 * BeHazeld Admin API Client
 *
 * - Always sends credentials (cookies) with `credentials: 'include'`
 * - Parses the FastAPI error envelope: { success, error_code, message, correlation_id }
 * - On 401: attempts one silent refresh via POST /api/v1/auth/refresh (cookie-based)
 *   If refresh fails, redirects to /login
 * - Never reads or stores tokens — browser manages httpOnly cookies automatically
 */

import { ApiError, ApiErrorResponse } from '@/types/api';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

// Tracks whether a refresh is already in-flight to prevent infinite loops
let _refreshing = false;

async function _parseError(response: Response): Promise<ApiError> {
  let body: Partial<ApiErrorResponse> = {};
  try {
    body = await response.json();
  } catch {
    // response body is not JSON
  }
  return new ApiError(
    body.error_code ?? 'UNKNOWN_ERROR',
    body.message ?? `HTTP ${response.status}`,
    body.correlation_id ?? '',
    response.status,
  );
}

async function _refreshTokens(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function _request<T>(
  method: Method,
  path: string,
  body?: unknown,
  isRetry = false,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {};
  let requestBody: string | undefined;

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(url, {
    method,
    headers,
    body: requestBody,
    credentials: 'include',
  });

  if (response.status === 401 && !isRetry && !_refreshing) {
    _refreshing = true;
    const refreshed = await _refreshTokens();
    _refreshing = false;

    if (refreshed) {
      return _request<T>(method, path, body, true);
    }

    // Refresh failed — redirect to login (client-side only)
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new ApiError('UNAUTHORIZED', 'Session expired', '', 401);
  }

  if (!response.ok) {
    throw await _parseError(response);
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string) => _request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => _request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => _request<T>('PATCH', path, body),
  put: <T>(path: string, body?: unknown) => _request<T>('PUT', path, body),
  delete: <T>(path: string) => _request<T>('DELETE', path),
};
