/**
 * POST /api/admin/products
 *
 * Protected by middleware (session cookie required — no password field needed).
 * Server-side proxy that:
 *   1. Gets a JWT from FastAPI using the server-side ADMIN_API_KEY
 *   2. Creates the Product record
 *   3. Creates one ProductVariant per (size × color) combination
 */

import { NextRequest, NextResponse } from "next/server";

const API       = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const ADMIN_KEY = process.env.ADMIN_API_KEY ?? "change-me-before-production";

type Body = {
  collectionSlug: string;
  name:           string;
  description:    string;
  base_price:     number;
  sizes:          string[];
  colors:         string[];
};

async function getToken(): Promise<string> {
  const res = await fetch(`${API}/admin/auth/token`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ api_key: ADMIN_KEY }),
  });
  if (!res.ok) throw new Error("FastAPI auth failed");
  return (await res.json()).access_token;
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function buildSku(slug: string, color: string, size: string): string {
  const p = slug.replace(/-/g, "").slice(0, 8).toUpperCase();
  const c = color.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase() || "CLR";
  const s = size.replace(/\s+/g, "").toUpperCase().slice(0, 5);
  return `BH-${p}-${c}-${s}`;
}

export async function POST(req: NextRequest) {
  // Middleware already verified the session cookie — no extra auth check needed here
  try {
    const body: Body = await req.json();

    const token   = await getToken();
    const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };

    // Resolve collection_id
    const colRes = await fetch(`${API}/collections/${body.collectionSlug}`);
    if (!colRes.ok) {
      return NextResponse.json({ error: `Collection '${body.collectionSlug}' not found` }, { status: 404 });
    }
    const collection = await colRes.json();

    // Unique slug
    let slug = slugify(body.name);
    const exists = await fetch(`${API}/products/${slug}`, { cache: "no-store" });
    if (exists.ok) slug = `${slug}-${Date.now().toString(36)}`;

    // Ensure description meets the 10-char minimum
    const rawDesc = (body.description ?? "").trim();
    const description = rawDesc.length >= 10
      ? rawDesc
      : `Handcrafted ${body.name} — part of the ${collection.name} collection.`;

    // Create product
    const prodRes = await fetch(`${API}/admin/products/`, {
      method: "POST", headers,
      body: JSON.stringify({
        collection_id: collection.id,
        name:          body.name,
        slug,
        description,
        base_price:    body.base_price.toFixed(2),
      }),
    });
    if (!prodRes.ok) {
      const err = await prodRes.json();
      // Pydantic validation errors return detail as an array — flatten to a readable string
      const errorMsg = Array.isArray(err.detail)
        ? err.detail.map((e: { loc?: string[]; msg?: string }) =>
            `${(e.loc ?? []).slice(-1)[0] ?? "field"}: ${e.msg ?? "invalid"}`
          ).join(" · ")
        : (err.detail ?? err.message ?? "Product creation failed");
      return NextResponse.json({ error: errorMsg }, { status: 400 });
    }
    const product = await prodRes.json();

    // Create variants (color × size)
    let variantsCreated = 0;
    for (const color of body.colors) {
      for (const size of body.sizes) {
        const vRes = await fetch(`${API}/admin/products/${product.id}/variants`, {
          method: "POST", headers,
          body: JSON.stringify({
            sku: buildSku(slug, color, size), color, size,
            price_adjustment: "0.00", stock_count: 20, is_available: true,
          }),
        });
        if (vRes.ok) variantsCreated++;
      }
    }

    return NextResponse.json({ success: true, productId: product.id, slug: product.slug, variantsCreated });
  } catch (err) {
    console.error("[api/admin/products]", err);
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
