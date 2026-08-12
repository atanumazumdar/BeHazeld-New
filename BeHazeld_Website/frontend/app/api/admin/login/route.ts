/**
 * POST /api/admin/login
 *
 * Validates the admin password, issues a signed session cookie.
 * Rate-limited to 10 attempts per 15-minute window using an in-memory map.
 * (For multi-instance deployments, replace with Redis / Upstash.)
 */

import { NextRequest, NextResponse } from "next/server";
import { createSessionToken, setSessionCookie } from "@/lib/admin-session";

const ADMIN_KEY = process.env.ADMIN_API_KEY ?? "change-me-before-production";

// ── Simple in-memory rate limiter ────────────────────────────────────
const attempts = new Map<string, { count: number; resetAt: number }>();
const WINDOW_MS     = 15 * 60 * 1000;  // 15 minutes
const MAX_ATTEMPTS  = 10;
const MAX_PASSWORD_LENGTH = 128;

function checkRateLimit(ip: string): boolean {
  const now    = Date.now();
  const record = attempts.get(ip);

  if (!record || now > record.resetAt) {
    attempts.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return true;   // allowed
  }
  if (record.count >= MAX_ATTEMPTS) return false;  // blocked
  record.count++;
  return true;
}

function getIp(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"
  );
}

export async function POST(req: NextRequest) {
  const ip = getIp(req);

  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { error: "Too many attempts. Try again in 15 minutes." },
      { status: 429 },
    );
  }

  const body = await req.json().catch(() => ({}));
  const { password } = body as { password?: string };

  // Constant-time comparison to prevent timing attacks
  const expected = ADMIN_KEY;
  const received = password ?? "";
  if (received.length > MAX_PASSWORD_LENGTH) {
    return NextResponse.json({ error: "Password is too long" }, { status: 400 });
  }

  let diff = expected.length !== received.length ? 1 : 0;
  for (let i = 0; i < Math.max(expected.length, received.length); i++) {
    diff |= (expected.charCodeAt(i) || 0) ^ (received.charCodeAt(i) || 0);
  }

  if (diff !== 0) {
    return NextResponse.json({ error: "Incorrect password" }, { status: 401 });
  }

  // Issue session cookie
  const token = await createSessionToken();
  await setSessionCookie(token);

  return NextResponse.json({ success: true });
}
