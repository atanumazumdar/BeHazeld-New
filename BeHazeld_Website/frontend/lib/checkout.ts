import type { CheckoutOrder, CheckoutPayload } from "@/types/checkout";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function createCheckout(payload: CheckoutPayload): Promise<CheckoutOrder> {
  const response = await fetch(`${API_BASE_URL}/checkout/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? "Checkout failed");
  }

  return response.json();
}
