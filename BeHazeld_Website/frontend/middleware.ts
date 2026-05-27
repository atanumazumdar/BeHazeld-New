/**
 * Next.js Middleware — Admin route protection.
 *
 * Runs BEFORE every request matching the config.matcher patterns.
 * If the session cookie is absent or invalid, the request is redirected
 * to /admin/login (UI routes) or returned 401 (API routes).
 *
 * /api/admin/login and /api/admin/logout are excluded so the user
 * can actually log in and out.
 */

import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/admin-session";

const SESSION_SECRET =
  process.env.ADMIN_SESSION_SECRET ??
  process.env.ADMIN_API_KEY ??
  "change-me-before-production";

const SESSION_TTL_S = 8 * 60 * 60;

/** Inline HMAC verify (middleware runs in Edge runtime — no Node modules). */
async function verifyToken(token: string): Promise<boolean> {
  const [ts, sig] = token.split(".");
  if (!ts || !sig) return false;

  const age = Math.floor(Date.now() / 1000) - parseInt(ts, 10);
  if (age > SESSION_TTL_S || age < 0) return false;

  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(SESSION_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sigBytes = await crypto.subtle.sign("HMAC", key, enc.encode(ts));
  const expected = Buffer.from(sigBytes).toString("hex");

  if (expected.length !== sig.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
  }
  return diff === 0;
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow login / logout through without a session
  const isPublicAdminRoute =
    pathname === "/admin/login" ||
    pathname.startsWith("/api/admin/login") ||
    pathname.startsWith("/api/admin/logout");

  if (isPublicAdminRoute) return NextResponse.next();

  // Check session cookie
  const token   = req.cookies.get(COOKIE_NAME)?.value;
  const isValid = token ? await verifyToken(token) : false;

  if (!isValid) {
    // API route → 401 JSON
    if (pathname.startsWith("/api/admin/")) {
      return NextResponse.json(
        { error: "Not authenticated. Log in at /admin/login first." },
        { status: 401 },
      );
    }
    // UI route → redirect to login, remember where they were going
    const loginUrl = new URL("/admin/login", req.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Only run middleware on admin UI and API routes
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};
