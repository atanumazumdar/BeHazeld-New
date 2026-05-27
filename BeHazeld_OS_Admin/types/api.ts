// Shared API response types for BeHazeld Admin Frontend
// These mirror the FastAPI Pydantic schemas.

export interface ApiErrorResponse {
  success: false;
  error_code: string;
  message: string;
  correlation_id: string;
}

export class ApiError extends Error {
  constructor(
    public readonly errorCode: string,
    message: string,
    public readonly correlationId: string,
    public readonly statusCode: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  tenant_id: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
