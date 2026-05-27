"use client";

import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import Link from "next/link";

const SILK = [0.76, 0, 0.24, 1] as const;

const PAGE: Variants = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.65, ease: [0.76, 0, 0.24, 1] as [number, number, number, number] } },
};

const GLASS: React.CSSProperties = {
  background: "rgba(18,10,5,0.76)",
  backdropFilter: "blur(18px)",
  WebkitBackdropFilter: "blur(18px)",
  border: "1px solid rgba(192,147,48,0.22)",
  boxShadow: "0 8px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.07)",
};

/*
 * AI image generation prompts:
 *
 * Campus Muse:
 * "A confident young South Asian woman in a richly embroidered churidar-kurta
 *  set — champagne gold on ivory — standing in a sunlit university courtyard,
 *  autumn leaves drifting. Shot on Hasselblad. Vogue India aesthetic. --ar 3:4"
 *
 * Power Edit:
 * "A commanding South Asian woman in a structured indo-western blazer-lehenga,
 *  deep mahogany with champagne-gold trim, glass-and-marble corporate atrium.
 *  Hard directional rim light. Harper's Bazaar cover. --ar 3:4"
 *
 * Afterglow Evenings:
 * "A luminous South Asian woman in a floor-length zari gown, sheer gold dupatta,
 *  chandelier-lit ballroom. Bokeh lights. Champagne ambient warmth.
 *  Vanity Fair editorial. Leica M11. --ar 3:4"
 */
const COLLECTIONS = [
  {
    id: "campus-muse", label: "I",
    title: "Campus Muse",
    href: "/collections/campus-muse",
    tagline: "Effortless. Expressive.\nUnapologetically You.",
    detail: "Where comfort meets quiet confidence.",
    image: "/campus-muse-new.png",
  },
  {
    id: "power-edit", label: "II",
    title: "Power Edit",
    href: "/collections/power-edit",
    tagline: "Tailored for ambition.\nStyled for impact.",
    detail: "Because presence is your power move.",
    image: "/power-edit.png",
  },
  {
    id: "afterglow", label: "III",
    title: "Afterglow Evenings",
    href: "/collections/afterglow-evenings",
    tagline: "Turn moments\ninto statements.",
    detail: "Soft lights. Strong impressions.",
    image: "/afterglow-evenings-new.png",
  },
];

function AtelierCard({ coll, index }: { coll: typeof COLLECTIONS[0]; index: number }) {
  const [hovered, setHovered] = useState(false);
  const showFullImage = coll.id === "campus-muse" || coll.id === "power-edit";

  return (
    <Link href={coll.href} className="block h-full" aria-label={`Explore ${coll.title}`}>
      <motion.article
        initial={{ opacity: 0, y: 56 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.15, ease: SILK, delay: 0.3 + index * 0.18 }}
        className="group flex h-full cursor-pointer select-none flex-col overflow-hidden bg-[#1A0E08] transition-[border-color,box-shadow,transform] duration-500 hover:-translate-y-1"
        style={{
          borderRadius: 2,
          border: "1px solid rgba(192,147,48,0.22)",
          boxShadow: hovered ? "0 22px 70px rgba(0,0,0,0.48)" : "0 10px 34px rgba(0,0,0,0.24)",
          WebkitTapHighlightColor: "transparent",
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Image + zoom */}
        <motion.div
          className="relative shrink-0 overflow-hidden bg-[#120A05]"
          style={{ height: "clamp(220px, 32vh, 300px)" }}
          animate={{ scale: hovered ? 1.045 : 1.0 }}
          transition={{ duration: 0.9, ease: [0.25, 0.1, 0, 1] as [number, number, number, number] }}
        >
          <img
            src={coll.image} alt={coll.title}
            className={`h-full w-full ${showFullImage ? "object-contain object-center" : "object-cover object-top"}`}
            style={{ filter: hovered ? "brightness(0.92) sepia(0.08)" : "brightness(0.82) sepia(0.12)" }}
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
          />
          <div className="absolute inset-0"
            style={{ background: "linear-gradient(145deg, #1A0E08 0%, #3D2314 50%, #2C1810 100%)", zIndex: -1 }} />
        </motion.div>

        {/* Bottom vignette */}
        <div className="pointer-events-none absolute left-0 right-0 top-0"
          style={{ height: "clamp(220px, 32vh, 300px)", background: "linear-gradient(to top, rgba(12,6,2,0.32) 0%, rgba(12,6,2,0.04) 70%)" }} />

        {/* Gold border on hover */}
        <motion.div className="absolute inset-0 pointer-events-none"
          animate={{ opacity: hovered ? 1 : 0 }} transition={{ duration: 0.45 }}
          style={{ border: "1px solid rgba(192,147,48,0.65)", boxShadow: "inset 0 0 40px rgba(192,147,48,0.08)" }} />

        {/* Card copy */}
        <div className="flex shrink-0 flex-col items-center p-4 text-center" style={GLASS}>
          <div className="w-full">
            <h2 className="font-display font-normal italic"
              style={{ fontSize: "clamp(24px, 2vw, 32px)", color: "#F8F0E8", lineHeight: 1.05, letterSpacing: "0.01em", marginBottom: 4 }}>
              {coll.title}
            </h2>

            <div className="mb-2 flex items-center justify-center gap-2">
              <div className="h-px w-6" style={{ background: "#C09330" }} />
              <svg width="4" height="4" viewBox="0 0 6 6">
                <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
              </svg>
              <div className="h-px w-6" style={{ background: "#C09330" }} />
            </div>

            <p className="font-serif font-light italic leading-[1.35]"
              style={{ fontSize: "clamp(15px, 1.3vw, 19px)", color: "rgba(248,240,232,0.82)", letterSpacing: "0.02em", whiteSpace: "pre-line" }}>
              {coll.tagline}
            </p>

            <p className="mx-auto mt-2 max-w-[20rem] font-sans font-light uppercase"
              style={{ fontSize: 8, letterSpacing: "0.16em", lineHeight: 1.7, color: "rgba(192,147,48,0.72)" }}>
              {coll.detail}
            </p>
          </div>

          <span className="btn-couture mt-3 inline-flex h-9 shrink-0 items-center justify-center px-4 text-center">
            Explore the collection
          </span>
        </div>
      </motion.article>
    </Link>
  );
}

export default function TheAtelierPage() {
  return (
    <motion.main
      variants={PAGE} initial="initial" animate="animate"
      className="relative z-10 flex min-h-[calc(100vh-64px)] flex-col overflow-visible lg:min-h-[calc(100vh-80px)]"
      style={{ color: "#F8F0E8" }}
    >
      {/* Header */}
      <header className="mx-auto shrink-0 px-8 pb-2 pt-3 text-center max-w-xl">
        <motion.p
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.0, delay: 0.1 }}
          className="font-sans font-normal uppercase mb-2"
          style={{ fontSize: 8, letterSpacing: "0.42em", color: "#C09330" }}>
          Collection · 2026
        </motion.p>

        <div style={{ overflow: "hidden" }}>
          <motion.h1
            initial={{ y: "105%" }} animate={{ y: 0 }}
            transition={{ duration: 1.15, ease: SILK, delay: 0.2 }}
            className="font-display font-light italic leading-[1.05] mb-1"
            style={{ fontSize: "clamp(32px, 4.2vw, 54px)", color: "#F8F0E8" }}>
            The Atelier
          </motion.h1>
        </div>

        <motion.div
          initial={{ scaleX: 0 }} animate={{ scaleX: 1 }}
          transition={{ duration: 1.1, ease: SILK, delay: 0.42 }}
          className="mb-1 flex items-center justify-center gap-3"
          style={{ transformOrigin: "center" }}>
          <div className="h-px w-14" style={{ background: "rgba(192,147,48,0.5)" }} />
          <svg width="5" height="5" viewBox="0 0 6 6">
            <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
          </svg>
          <div className="h-px w-14" style={{ background: "rgba(192,147,48,0.5)" }} />
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ duration: 1.0, delay: 0.58 }}
          className="font-serif font-light italic leading-[1.35]"
          style={{ fontSize: "clamp(15px, 1.4vw, 19px)", color: "rgba(248,240,232,0.72)", letterSpacing: "0.02em" }}>
          Three stories. Three women. One language: BeHAZEL&apos;d.
        </motion.p>
      </header>

      {/* Grid */}
      <div style={{ padding: "0 40px 24px", overflowX: "auto" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 24,
          maxWidth: 1152,
          margin: "0 auto",
          alignItems: "start",
        }}>
          {COLLECTIONS.map((coll, i) => (
            <AtelierCard key={coll.id} coll={coll} index={i} />
          ))}
        </div>
      </div>

      {/* Footer line */}
      <motion.footer
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        transition={{ delay: 1.4, duration: 1.0 }}
        className="shrink-0 pb-4 text-center md:pb-2"
      >
        <div className="flex items-center justify-center gap-4 px-8">
          <div className="h-px flex-1 max-w-[180px]" style={{ background: "linear-gradient(to right, transparent, rgba(192,147,48,0.3))" }} />
          <p className="font-sans font-light uppercase"
            style={{ fontSize: 8, letterSpacing: "0.3em", color: "rgba(192,147,48,0.38)" }}>
            Each product Handpicked from the largest Chikankari market in the world · Handcrafted in India · 4–6 weeks
          </p>
          <div className="h-px flex-1 max-w-[180px]" style={{ background: "linear-gradient(to left, transparent, rgba(192,147,48,0.3))" }} />
        </div>
      </motion.footer>
    </motion.main>
  );
}
