import type { CheckoutOrder, CheckoutPayload } from "@/types/checkout";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "").replace(/\/api$/, "");
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID;

export async function createCheckout(payload: CheckoutPayload): Promise<CheckoutOrder> {
  if (!TENANT_ID) {
    throw new Error("NEXT_PUBLIC_TENANT_ID is not configured");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/public/${TENANT_ID}/checkout`, {
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
