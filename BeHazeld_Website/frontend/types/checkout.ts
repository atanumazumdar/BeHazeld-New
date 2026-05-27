export type CheckoutPayload = {
  customer_email: string;
  customer_name: string;
  shipping_address: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  items: {
    product_id: number;
    quantity: number;
  }[];
};

export type CheckoutOrder = {
  id: number;
  status: string;
  subtotal: string;
  shipping_total: string;
  total: string;
  customer_email: string;
};
