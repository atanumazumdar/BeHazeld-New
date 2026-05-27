/**
 * Server-side session helpers.
 * The session cookie value is an HMAC-SHA256 signature of a fixed payload
 * using ADMIN_SESSION_SECRET. This prevents forgery without a DB.
 *
 * Cookie name : behazeld_admin
 * Cookie value: <timestamp>.<hmac>
 */

import { cookies } from "next/headers";

const COOKIE_NAME    = "behazeld_admin";
const SESSION_SECRET = process.env.ADMIN_SESSION_SECRET
  ?? process.env.ADMIN_API_KEY
  ?? "change-me-before-production";
const SESSION_TTL_S  = 8 * 60 * 60; // 8 hours

// ── HMAC helpers ──────────────────────────────────────────────────────
async function hmac(message: string): Promise<string> {
  const enc     = new TextEncoder();
  const keyData = enc.encode(SESSION_SECRET);
  const key     = await crypto.subtle.importKey(
    "raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Buffer.from(sig).toString("hex");
}

// ── Token ─────────────────────────────────────────────────────────────
export async function createSessionToken(): Promise<string> {
  const ts  = Math.floor(Date.now() / 1000).toString();
  const sig = await hmac(ts);
  return `${ts}.${sig}`;
}

export async function verifySessionToken(token: string): Promise<boolean> {
  const [ts, sig] = token.split(".");
  if (!ts || !sig) return false;

  // Check expiry
  const age = Math.floor(Date.now() / 1000) - parseInt(ts, 10);
  if (age > SESSION_TTL_S || age < 0) return false;

  // Constant-time comparison
  const expected = await hmac(ts);
  if (expected.length !== sig.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
  }
  return diff === 0;
}

// ── Cookie helpers (server components / route handlers) ───────────────
export async function setSessionCookie(token: string) {
  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly:  true,
    secure:    process.env.NODE_ENV === "production",
    sameSite:  "strict",
    maxAge:    SESSION_TTL_S,
    path:      "/",
  });
}

export async function clearSessionCookie() {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

export async function getSessionToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(COOKIE_NAME)?.value ?? null;
}

export { COOKIE_NAME };
