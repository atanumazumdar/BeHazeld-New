"use client";

import { useRouter } from "next/navigation";
import { ProductUploadForm } from "@/components/admin/ProductUploadForm";

const GOLD  = "#C09330";
const MUTED = "rgba(177,152,112,0.6)";

export function AdminUploadShell() {
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/admin/logout", { method: "POST" });
    router.push("/admin/login");
  }

  return (
    <main className="min-h-screen" style={{ color: "rgba(248,240,232,0.9)" }}>
      {/* Admin top bar */}
      <div
        className="sticky top-0 z-50 flex items-center justify-between px-6 py-3"
        style={{
          background: "rgba(18,10,5,0.92)",
          backdropFilter: "blur(16px)",
          borderBottom: "1px solid rgba(192,147,48,0.18)",
        }}
      >
        <div className="flex items-center gap-4">
          <span className="font-sans font-normal uppercase"
            style={{ fontSize: 8, letterSpacing: "0.52em", color: GOLD }}>
            BeHAZEL&apos;d · Admin
          </span>
          <span style={{ color: "rgba(192,147,48,0.3)", fontSize: 14 }}>·</span>
          <span className="font-sans font-light uppercase"
            style={{ fontSize: 8, letterSpacing: "0.38em", color: MUTED }}>
            Add Product
          </span>
        </div>

        <div className="flex items-center gap-6">
          <a
            href="/atelier"
            className="font-sans font-light uppercase transition-colors duration-300"
            style={{ fontSize: 8, letterSpacing: "0.38em", color: MUTED }}
            onMouseEnter={(e) => (e.currentTarget.style.color = GOLD)}
            onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
          >
            ← View Atelier
          </a>
          <button
            onClick={handleLogout}
            className="font-sans font-light uppercase transition-colors duration-300 cursor-pointer"
            style={{ fontSize: 8, letterSpacing: "0.38em", color: MUTED, background: "none", border: "none" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#f87171")}
            onMouseLeave={(e) => (e.currentTarget.style.color = MUTED)}
          >
            Log out
          </button>
        </div>
      </div>

      {/* Page heading */}
      <div className="text-center px-8 pt-14 pb-4">
        <p className="font-sans font-normal uppercase mb-3"
          style={{ fontSize: 8.5, letterSpacing: "0.52em", color: GOLD }}>
          Admin · Collection Management
        </p>
        <h1 className="font-display font-light italic"
          style={{ fontSize: "clamp(28px, 3.5vw, 44px)", color: "rgba(248,240,232,0.92)", lineHeight: 1.1 }}>
          Add New Piece
        </h1>
      </div>

      {/* The upload form — no password field, session handles auth */}
      <ProductUploadForm showAlways />
    </main>
  );
}
