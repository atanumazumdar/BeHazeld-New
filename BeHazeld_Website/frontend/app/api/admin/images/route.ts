/**
 * POST /api/admin/images
 *
 * Protected by middleware (session cookie — no password in form data).
 * Receives multipart/form-data with: file, productId, isPrimary, displayOrder, altText
 * Proxies to FastAPI local image storage.
 */

import { NextRequest, NextResponse } from "next/server";

const API       = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const ADMIN_KEY = process.env.ADMIN_API_KEY ?? "change-me-before-production";

async function getToken(): Promise<string> {
  const res = await fetch(`${API}/admin/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: ADMIN_KEY }),
  });
  if (!res.ok) throw new Error("Auth failed");
  return (await res.json()).access_token;
}

export async function POST(req: NextRequest) {
  try {
    const formData     = await req.formData();
    const file         = formData.get("file") as File | null;
    const productId    = formData.get("productId") as string;
    const isPrimary    = formData.get("isPrimary") === "true";
    const displayOrder = parseInt(formData.get("displayOrder") as string ?? "0", 10);
    const altText      = formData.get("altText") as string ?? "";

    if (!file || !productId) {
      return NextResponse.json({ error: "Missing file or productId" }, { status: 400 });
    }

    const token = await getToken();

    const upstream = new FormData();
    upstream.append("file", file);
    upstream.append("alt_text", altText);
    upstream.append("display_order", String(displayOrder));
    upstream.append("is_primary", String(isPrimary));

    const upRes = await fetch(`${API}/admin/products/${productId}/images/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: upstream,
    });

    if (!upRes.ok) {
      const err = await upRes.json().catch(() => ({ detail: upRes.statusText }));
      return NextResponse.json({ error: err.detail ?? "Upload failed" }, { status: upRes.status });
    }

    return NextResponse.json({ ...(await upRes.json()), storage: "local" });
  } catch (err) {
    console.error("[api/admin/images]", err);
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
