"use client";

import { useRef, useState } from "react";
import { formatCurrency } from "@/lib/format";

/* ── Brand tokens ──────────────────────────────────────────────────── */
const GOLD   = "#C09330";
const CREAM  = "rgba(248,240,232,0.88)";
const MUTED  = "rgba(177,152,112,0.72)";
const BORDER = "rgba(192,147,48,0.22)";

const GLASS: React.CSSProperties = {
  background:          "rgba(18,10,5,0.72)",
  backdropFilter:      "blur(20px)",
  WebkitBackdropFilter:"blur(20px)",
  border:              `1px solid ${BORDER}`,
  boxShadow:           "0 8px 32px rgba(0,0,0,0.45)",
};

/* ── Constants ─────────────────────────────────────────────────────── */
const COLLECTIONS = [
  { label: "Campus Muse",       slug: "campus-muse"       },
  { label: "Power Edit",        slug: "power-edit"        },
  { label: "Afterglow Evenings",slug: "afterglow-evenings"},
];

const PRESET_SIZES = ["32","34","36","38","40","42","44","46","48"];

/* ── Sub-components ─────────────────────────────────────────────────── */
function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="block font-sans font-light uppercase mb-2"
      style={{ fontSize: 8.5, letterSpacing: "0.46em", color: MUTED }}>
      {children}
    </span>
  );
}

function GoldDivider() {
  return (
    <div className="flex items-center gap-3 my-7">
      <div className="h-px flex-1" style={{ background: `linear-gradient(to right, ${GOLD}, rgba(192,147,48,0.1))` }} />
      <svg width="4" height="4" viewBox="0 0 6 6">
        <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={GOLD} />
      </svg>
    </div>
  );
}

type ImageSlot = { file: File; preview: string } | null;

type Status = "idle" | "uploading" | "success" | "error";

/* ── Main form ──────────────────────────────────────────────────────── */
export function ProductUploadForm({ showAlways = false }: { showAlways?: boolean }) {
  const [open, setOpen]             = useState(false);
  const [collection, setCollection] = useState(COLLECTIONS[0].slug);
  const [name, setName]             = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice]           = useState("");
  const [sizes, setSizes]           = useState<string[]>([]);
  const [colors, setColors]         = useState<string[]>(["Ivory"]);
  const [images, setImages]         = useState<[ImageSlot, ImageSlot]>([null, null]);
  const [status, setStatus]         = useState<Status>("idle");
  const [message, setMessage]       = useState("");
  const [newColor, setNewColor]     = useState("");
  const [createdSlug, setCreatedSlug] = useState("");

  const fileRefs = [useRef<HTMLInputElement>(null), useRef<HTMLInputElement>(null)];

  /* Helpers */
  function toggleSize(s: string) {
    setSizes((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  function addColor() {
    const c = newColor.trim();
    if (c && !colors.includes(c)) { setColors([...colors, c]); setNewColor(""); }
  }

  function pickImage(idx: 0 | 1, file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const next: [ImageSlot, ImageSlot] = [...images] as [ImageSlot, ImageSlot];
      next[idx] = { file, preview: e.target?.result as string };
      setImages(next);
    };
    reader.readAsDataURL(file);
  }

  /* Validate */
  function validate(): string | null {
    if (!name.trim())          return "Product name is required";
    if (!price || isNaN(Number(price)) || Number(price) <= 0) return "Enter a valid price";
    if (sizes.length === 0)    return "Select at least one size";
    if (colors.length === 0)   return "Add at least one colour";
    if (!images[0] && !images[1]) return "Upload at least one product image";
    return null;
  }

  /* Submit */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate();
    if (err) { setMessage(err); setStatus("error"); return; }

    setStatus("uploading");
    setMessage("Creating product…");

    try {
      /* 1 — Create product + variants */
      const prodRes = await fetch("/api/admin/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          collectionSlug: collection,
          name:           name.trim(),
          description:    description.trim(),
          base_price:     Number(price),
          sizes,
          colors,
        }),
      });

      const prodData = await prodRes.json();
      if (!prodRes.ok) throw new Error(prodData.error ?? "Product creation failed");

      const productId = prodData.productId;
      let usingPlaceholder = false;
      setCreatedSlug(prodData.slug);
      setMessage(`Product created. Uploading images…`);

      /* 2 — Upload images */
      const uploadSlots = images
        .map((slot, i) => ({ slot, index: i }))
        .filter(({ slot }) => slot !== null) as { slot: NonNullable<ImageSlot>; index: number }[];

      for (const { slot, index } of uploadSlots) {
        const fd = new FormData();
        fd.append("file",          slot.file);
        fd.append("productId",     String(productId));
        fd.append("isPrimary",     String(index === 0));
        fd.append("displayOrder",  String(index));
        fd.append("altText",       `${name} — photo ${index + 1}`);

        const imgRes = await fetch("/api/admin/images", { method: "POST", body: fd });
        const imgData = await imgRes.json();
        if (!imgRes.ok) throw new Error(imgData.error ?? `Image ${index + 1} upload failed`);
        // Flag if Cloudinary isn't set up (photo saved as placeholder)
        if (imgData.cloudinary === false) usingPlaceholder = true;
      }

      setStatus("success");
      const collectionLabel = COLLECTIONS.find(c => c.slug === collection)?.label;
      setMessage(
        `"${name}" added to ${collectionLabel}. It will appear on the collection page within 60 seconds.` +
        (usingPlaceholder
          ? "\n\nNote: Photos saved as placeholders — add Cloudinary credentials to .env.local to store real images."
          : "")
      );

      /* Reset form */
      setName(""); setDescription(""); setPrice("");
      setSizes([]); setColors(["Ivory"]); setImages([null, null]);

    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  /* ── Collapsed trigger ─────────────────────────────────────────── */
  if (!open && !showAlways) {
    return (
      <div className="text-center mt-4 mb-10">
        <button
          onClick={() => setOpen(true)}
          className="font-sans font-light uppercase transition-colors duration-300"
          style={{ fontSize: 9, letterSpacing: "0.44em", color: "rgba(192,147,48,0.5)", background: "none", border: "none", cursor: "pointer" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = GOLD)}
          onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(192,147,48,0.5)")}
        >
          + Add New Product
        </button>
      </div>
    );
  }

  /* ── Form ──────────────────────────────────────────────────────── */
  return (
    <div className="px-8 md:px-14 lg:px-20 pb-16 mt-2">
      <div style={{ ...GLASS, borderRadius: 2, maxWidth: 780, margin: "0 auto" }}>
        <div className="p-8 md:p-10">

          {/* Header */}
          <div className="flex items-start justify-between mb-2">
            <div>
              <p className="font-sans font-normal uppercase mb-2"
                style={{ fontSize: 8.5, letterSpacing: "0.52em", color: GOLD }}>
                Admin · Add Product
              </p>
              <h2 className="font-display font-light italic"
                style={{ fontSize: "clamp(22px, 2.8vw, 34px)", color: CREAM, lineHeight: 1.1 }}>
                New Piece
              </h2>
            </div>
            <button
              onClick={() => { setOpen(false); setStatus("idle"); setMessage(""); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: MUTED, fontSize: 20, lineHeight: 1, padding: "4px 8px" }}
              aria-label="Close form"
            >
              ×
            </button>
          </div>

          <GoldDivider />

          <form onSubmit={handleSubmit} className="space-y-7">

            {/* ── Section 1: Category ─────────────────────────── */}
            <div>
              <Label>Collection / Category</Label>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {COLLECTIONS.map((c) => (
                  <button
                    key={c.slug}
                    type="button"
                    onClick={() => setCollection(c.slug)}
                    className="font-sans font-light uppercase transition-all duration-300 cursor-pointer px-5 py-2.5"
                    style={{
                      fontSize: 9, letterSpacing: "0.28em",
                      border:     `1px solid ${collection === c.slug ? GOLD : BORDER}`,
                      background: collection === c.slug ? "rgba(192,147,48,0.12)" : "transparent",
                      color:      collection === c.slug ? GOLD : MUTED,
                    }}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Section 2: Product name + price ─────────────── */}
            <div style={{ display: "grid", gap: 18, gridTemplateColumns: "1fr 160px" }}>
              <div>
                <Label>Product Name</Label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Pearl Chikan Kurta"
                  className="glass-input h-11 w-full px-4 text-sm"
                />
              </div>
              <div>
                <Label>Price (₹)</Label>
                <input
                  required
                  type="number"
                  min="1"
                  step="100"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="18500"
                  className="glass-input h-11 w-full px-4 text-sm"
                />
              </div>
            </div>

            {price && Number(price) > 0 && (
              <p className="font-sans font-light -mt-4"
                style={{ fontSize: 11, color: GOLD, letterSpacing: "0.04em" }}>
                Display price: {formatCurrency(Number(price))}
              </p>
            )}

            {/* ── Section 3: Description (optional) ───────────── */}
            <div>
              <Label>Description <span style={{ color: "rgba(177,152,112,0.4)", textTransform: "none", letterSpacing: 0 }}>(optional)</span></Label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Hand-embroidered ivory silk with champagne zari work…"
                rows={3}
                className="glass-input w-full px-4 py-3 text-sm resize-none"
                style={{ lineHeight: 1.7 }}
              />
            </div>

            <GoldDivider />

            {/* ── Section 4: Sizes ────────────────────────────── */}
            <div>
              <Label>Sizes Available <span style={{ color: GOLD, textTransform: "none", letterSpacing: 0 }}>({sizes.length} selected)</span></Label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {PRESET_SIZES.map((s) => {
                  const sel = sizes.includes(s);
                  return (
                    <button
                      key={s}
                      type="button"
                      onClick={() => toggleSize(s)}
                      className="font-sans font-light uppercase transition-all duration-200 cursor-pointer px-4 py-2"
                      style={{
                        fontSize: 9, letterSpacing: "0.22em",
                        border:     `1px solid ${sel ? GOLD : BORDER}`,
                        background: sel ? "rgba(192,147,48,0.12)" : "transparent",
                        color:      sel ? GOLD : MUTED,
                      }}
                    >
                      {s}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ── Section 5: Colours ──────────────────────────── */}
            <div>
              <Label>Colors Available</Label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
                {colors.map((c) => (
                  <span
                    key={c}
                    className="flex items-center gap-2 font-sans font-light uppercase px-3 py-1.5"
                    style={{ fontSize: 9, letterSpacing: "0.22em", border: `1px solid ${GOLD}`, color: GOLD }}
                  >
                    {c}
                    <button
                      type="button"
                      onClick={() => setColors(colors.filter((x) => x !== c))}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "rgba(192,147,48,0.5)", fontSize: 14, lineHeight: 1, padding: 0 }}
                      aria-label={`Remove ${c}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  value={newColor}
                  onChange={(e) => setNewColor(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addColor(); } }}
                  placeholder="Type a color, press Enter"
                  className="glass-input h-10 flex-1 px-4 text-sm"
                />
                <button
                  type="button"
                  onClick={addColor}
                  className="font-sans font-light uppercase px-4 h-10 transition-colors duration-300"
                  style={{ fontSize: 9, letterSpacing: "0.28em", border: `1px solid ${BORDER}`, color: MUTED, background: "transparent", cursor: "pointer" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = GOLD; (e.currentTarget as HTMLButtonElement).style.color = GOLD; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = BORDER; (e.currentTarget as HTMLButtonElement).style.color = MUTED; }}
                >
                  Add
                </button>
              </div>
            </div>

            <GoldDivider />

            {/* ── Section 6: Images ───────────────────────────── */}
            <div>
              <Label>Product Photos (upload 2)</Label>
              <p className="font-sans font-light mb-3"
                style={{ fontSize: 10, color: "rgba(177,152,112,0.5)", letterSpacing: "0.02em" }}>
                JPG · PNG · WebP · max 10 MB each.{" "}
                {!process.env.NEXT_PUBLIC_CLOUDINARY_CONFIGURED && (
                  <span style={{ color: "rgba(192,147,48,0.55)" }}>
                    Cloudinary not configured — photos will be saved as placeholders until credentials are added to .env.local.
                  </span>
                )}
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {([0, 1] as const).map((idx) => (
                  <div key={idx}>
                    <input
                      ref={fileRefs[idx]}
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      style={{ display: "none" }}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) pickImage(idx, f);
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => fileRefs[idx].current?.click()}
                      className="w-full transition-colors duration-300 cursor-pointer"
                      style={{
                        height:      180,
                        border:      images[idx]
                          ? `1px solid ${GOLD}`
                          : `1px dashed ${BORDER}`,
                        background:  "rgba(18,10,5,0.45)",
                        position:    "relative",
                        overflow:    "hidden",
                      }}
                    >
                      {images[idx] ? (
                        <>
                          <img
                            src={images[idx]!.preview}
                            alt={`Preview ${idx + 1}`}
                            style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }}
                          />
                          <div style={{
                            position: "absolute", inset: 0,
                            background: "rgba(18,10,5,0.45)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            opacity: 0,
                            transition: "opacity 0.3s",
                          }}
                            className="hover:opacity-100"
                          >
                            <span className="font-sans font-light uppercase"
                              style={{ fontSize: 9, letterSpacing: "0.38em", color: CREAM }}>
                              Change
                            </span>
                          </div>
                          <div style={{ position: "absolute", top: 8, left: 8, background: "rgba(192,147,48,0.9)", padding: "2px 8px" }}>
                            <span className="font-sans font-light uppercase"
                              style={{ fontSize: 7.5, letterSpacing: "0.3em", color: "#120A05" }}>
                              {idx === 0 ? "Primary" : "Secondary"}
                            </span>
                          </div>
                        </>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 8 }}>
                          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={MUTED} strokeWidth="1.2">
                            <rect x="3" y="3" width="18" height="18" rx="1" />
                            <circle cx="8.5" cy="8.5" r="1.5" fill={MUTED} stroke="none" />
                            <polyline points="21 15 16 10 5 21" />
                          </svg>
                          <div className="font-sans font-light text-center" style={{ color: MUTED }}>
                            <div style={{ fontSize: 9, letterSpacing: "0.28em", textTransform: "uppercase" }}>
                              {idx === 0 ? "Primary" : "Secondary"}
                            </div>
                          </div>
                        </div>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <GoldDivider />

            {/* ── Status message ──────────────────────────────── */}
            {message && (
              <div
                className="px-4 py-3 font-sans font-light text-sm"
                style={{
                  border:     `1px solid ${status === "error" ? "rgba(180,40,40,0.4)" : status === "success" ? "rgba(192,147,48,0.5)" : BORDER}`,
                  background: status === "error" ? "rgba(180,40,40,0.12)" : status === "success" ? "rgba(192,147,48,0.1)" : "transparent",
                  color:      status === "error" ? "#f87171" : status === "success" ? GOLD : CREAM,
                  lineHeight: 1.7,
                  letterSpacing: "0.02em",
                }}
              >
                {message}
                {status === "success" && createdSlug && (
                  <a
                    href={`/products/${encodeURIComponent(createdSlug)}`}
                    className="block mt-2 font-sans font-light uppercase transition-colors"
                    style={{ fontSize: 9, letterSpacing: "0.36em", color: GOLD }}
                  >
                    View product →
                  </a>
                )}
              </div>
            )}

            {/* ── Submit ─────────────────────────────────────── */}
            <button
              type="submit"
              disabled={status === "uploading"}
              className="btn-couture flex h-12 w-full items-center justify-center px-4 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {status === "uploading" ? "Saving…" : "Save Product"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
