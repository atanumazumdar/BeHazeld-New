export type CheckoutPayload = {
  customer_email: string;
  customer_name: string;
  customer_phone?: string;
  shipping_address: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  total_amount: string;
  items: {
    product_variant_id: string;
    quantity: number;
  }[];
};

export type CheckoutOrder = {
  order_id: string;
  total_amount: string;
  order_summary: string;
  whatsapp_message: string;
};
