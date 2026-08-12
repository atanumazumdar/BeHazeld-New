"use client";

import { useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

const GOLD  = "#C09330";
const CREAM = "rgba(248,240,232,0.9)";
const MUTED = "rgba(177,152,112,0.72)";

function LoginForm() {
  const [password, setPassword] = useState("");
  const [status, setStatus]     = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage]   = useState("");
  const inputRef                = useRef<HTMLInputElement>(null);
  const router                  = useRouter();
  const params                  = useSearchParams();
  const redirect                = params.get("redirect") ?? "/admin/upload";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setMessage("");

    const res  = await fetch("/api/admin/login", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ password }),
    });
    const data = await res.json();

    if (res.ok) {
      router.push(redirect);
    } else {
      setStatus("error");
      setMessage(data.error ?? "Login failed");
      setPassword("");
      inputRef.current?.focus();
    }
  }

  return (
    <main
      className="min-h-screen flex items-center justify-center px-5"
      style={{ color: CREAM }}
    >
      <div
        style={{
          width: "100%", maxWidth: 400,
          background: "rgba(18,10,5,0.82)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          border: `1px solid rgba(192,147,48,0.2)`,
          boxShadow: "0 24px 64px rgba(0,0,0,0.6)",
        }}
      >
        <div className="p-10">
          {/* Logo mark */}
          <div className="text-center mb-8">
            <p className="font-sans font-normal uppercase mb-3"
              style={{ fontSize: 8, letterSpacing: "0.6em", color: "rgba(192,147,48,0.55)" }}>
              BeHAZEL&apos;d · Admin
            </p>
            <h1 className="font-display font-light italic"
              style={{ fontSize: "clamp(24px, 3vw, 32px)", color: CREAM, lineHeight: 1.1 }}>
              Atelier Access
            </h1>
            {/* Gold ornament */}
            <div className="flex items-center justify-center gap-3 mt-4">
              <div className="h-px w-12" style={{ background: `linear-gradient(to right, transparent, ${GOLD})` }} />
              <svg width="4" height="4" viewBox="0 0 6 6">
                <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={GOLD} />
              </svg>
              <div className="h-px w-12" style={{ background: `linear-gradient(to left, transparent, ${GOLD})` }} />
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block font-sans font-light uppercase mb-2"
                style={{ fontSize: 8.5, letterSpacing: "0.44em", color: MUTED }}>
                Admin Password
              </label>
              <input
                ref={inputRef}
                type="password"
                required
                maxLength={128}
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="glass-input h-12 w-full px-4 text-sm"
              />
            </div>

            {message && (
              <p className="font-sans font-light text-sm px-3 py-2"
                style={{
                  background: "rgba(180,40,40,0.12)",
                  border:     "1px solid rgba(180,40,40,0.3)",
                  color:      "#f87171",
                  letterSpacing: "0.02em",
                }}>
                {message}
              </p>
            )}

            <button
              type="submit"
              disabled={status === "loading"}
              className="btn-couture flex h-12 w-full items-center justify-center px-4 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {status === "loading" ? "Verifying…" : "Enter"}
            </button>
          </form>

          <p className="font-sans font-light text-center mt-8"
            style={{ fontSize: 10, color: "rgba(177,152,112,0.35)", letterSpacing: "0.04em" }}>
            This area is restricted to authorised personnel only.
          </p>
        </div>
      </div>
    </main>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
