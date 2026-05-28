'use server';

import { cookies } from 'next/headers';

import type { MasterDataImportResponse, MasterDataImportType } from '@/types/catalog';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ImportMasterDataResult {
  success: boolean;
  data?: MasterDataImportResponse;
  message?: string;
}

export async function importMasterDataAction(
  entityType: MasterDataImportType,
  formData: FormData,
): Promise<ImportMasterDataResult> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get('access_token')?.value;

  if (!accessToken) {
    return { success: false, message: 'Session expired. Please sign in again.' };
  }

  let response: Response;
  try {
    response = await fetch(
      `${API_URL}/api/v1/catalog/import/master-data?entity_type=${entityType}`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      },
    );
  } catch {
    return { success: false, message: 'Unable to reach the server. Please try again.' };
  }

  if (!response.ok) {
    let message = 'Failed to import CSV.';
    try {
      const body = await response.json();
      if (body.message) message = body.message;
    } catch {
      // ignore parse error
    }
    return { success: false, message };
  }

  return {
    success: true,
    data: (await response.json()) as MasterDataImportResponse,
  };
}
