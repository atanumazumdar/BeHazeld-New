import type { CheckoutOrder, CheckoutPayload } from "@/types/checkout";

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID;

export async function createCheckout(payload: CheckoutPayload): Promise<CheckoutOrder> {
  if (!TENANT_ID) {
    throw new Error("NEXT_PUBLIC_TENANT_ID is not configured");
  }

  // Keep browser checkout same-origin. IIS proxies /api/* to FastAPI, avoiding
  // cross-origin DNS, TLS, and CORS failures from the public storefront.
  const response = await fetch(`/api/v1/public/${TENANT_ID}/checkout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.message ?? error?.detail ?? "Checkout failed");
  }

  return response.json();
}
