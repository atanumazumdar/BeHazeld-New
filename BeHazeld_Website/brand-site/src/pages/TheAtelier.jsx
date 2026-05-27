import { useState } from 'react';
import { motion } from 'framer-motion';

const PAGE = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.65, ease: [0.76, 0, 0.24, 1] } },
};

const SILK = [0.76, 0, 0.24, 1];

const GLASS = {
  background: 'rgba(255,255,255,0.06)',
  backdropFilter: 'blur(18px)',
  WebkitBackdropFilter: 'blur(18px)',
  border: '1px solid rgba(192,147,48,0.22)',
  boxShadow: '0 8px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.07)',
};

/* ── Midjourney / DALL-E prompts embedded for each card ──────────
   Card 1 — Campus Muse:
   "A confident young South Asian woman in a richly embroidered
    churidar-kurta set — champagne gold on ivory — standing in a sunlit
    university courtyard, autumn leaves drifting. Shot on Hasselblad.
    Warm editorial light. Vogue India aesthetic. --ar 3:4 --style raw"

   Card 2 — Power Edit:
   "A commanding South Asian woman in a structured indo-western
    blazer-lehenga, deep mahogany with champagne-gold trim, standing
    in a glass-and-marble corporate atrium. Hard directional rim light.
    Harper's Bazaar cover. Phase One. --ar 3:4 --style raw"

   Card 3 — Afterglow Evenings:
   "A luminous South Asian woman in a floor-length zari gown, sheer
    gold dupatta, inside a chandelier-lit ballroom. Bokeh lights.
    Champagne ambient warmth. Vanity Fair editorial. Leica M11.
    --ar 3:4 --style raw"
─────────────────────────────────────────────────────────────── */
const COLLECTIONS = [
  {
    id: 'campus-muse',
    label: 'I',
    title: 'Campus Muse',
    tagline: 'Effortless. Expressive.\nUnapologetically You.',
    detail: 'Where comfort meets quiet confidence.',
    image: 'https://images.unsplash.com/photo-1529139574466-a303027614d4?auto=format&fit=crop&w=800&q=80',
  },
  {
    id: 'power-edit',
    label: 'II',
    title: 'Power Edit',
    tagline: 'Tailored for ambition.\nStyled for impact.',
    detail: 'Because presence is your power move.',
    image: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=800&q=80',
  },
  {
    id: 'afterglow',
    label: 'III',
    title: 'Afterglow Evenings',
    tagline: 'Turn moments\ninto statements.',
    detail: 'Soft lights. Strong impressions.',
    image: 'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=800&q=80',
  },
];

function DiamondDivider() {
  return (
    <div className="flex items-center gap-2 my-3">
      <div className="h-px w-6" style={{ background: '#C09330' }} />
      <svg width="4" height="4" viewBox="0 0 6 6">
        <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
      </svg>
    </div>
  );
}

function AtelierCard({ coll, index }) {
  const [hovered, setHovered] = useState(false);

  /* On touch devices a tap toggles the overlay */
  const handleTouch = (e) => {
    e.preventDefault();
    setHovered(h => !h);
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 56 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1.15, ease: SILK, delay: 0.3 + index * 0.18 }}
      className="relative overflow-hidden cursor-pointer select-none"
      style={{ aspectRatio: '3/4', borderRadius: 2, WebkitTapHighlightColor: 'transparent' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onTouchStart={handleTouch}
    >
      {/* ── Background image + zoom ───────────────────── */}
      <motion.div
        className="absolute inset-0"
        animate={{ scale: hovered ? 1.07 : 1.0 }}
        transition={{ duration: 0.9, ease: [0.25, 0.1, 0, 1] }}
      >
        <img
          src={coll.image}
          alt={coll.title}
          className="w-full h-full object-cover object-top"
          style={{ filter: 'brightness(0.7) sepia(0.2)' }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
        {/* Gradient fallback */}
        <div
          className="absolute inset-0"
          style={{ background: 'linear-gradient(145deg, #1A0E08 0%, #3D2314 50%, #2C1810 100%)', zIndex: -1 }}
        />
      </motion.div>

      {/* ── Persistent bottom vignette ─────────────────── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'linear-gradient(to top, rgba(12,6,2,0.95) 0%, rgba(12,6,2,0.55) 45%, transparent 72%)' }}
      />

      {/* ── Gold border glow on hover ──────────────────── */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        animate={{ opacity: hovered ? 1 : 0 }}
        transition={{ duration: 0.45 }}
        style={{
          border: '1px solid rgba(192,147,48,0.65)',
          boxShadow: 'inset 0 0 40px rgba(192,147,48,0.08)',
        }}
      />

      {/* ── Top badge ─────────────────────────────────── */}
      <div className="absolute top-5 left-5 z-10">
        <div
          className="font-sans font-light uppercase px-3 py-1.5"
          style={{
            fontSize: 8,
            letterSpacing: '0.38em',
            background: 'rgba(18,10,5,0.72)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            border: '1px solid rgba(192,147,48,0.28)',
            color: 'rgba(192,147,48,0.9)',
          }}
        >
          {coll.label} · The Atelier
        </div>
      </div>

      {/* ── Detail line — reveals on hover ────────────── */}
      <motion.p
        className="absolute z-10 font-sans font-light uppercase"
        style={{
          fontSize: 10,
          letterSpacing: '0.32em',
          color: 'rgba(192,147,48,0.88)',
          bottom: 'calc(100% - 68%)',
          left: 24,
          right: 24,
        }}
        animate={{ opacity: hovered ? 1 : 0, y: hovered ? 0 : 10 }}
        transition={{ duration: 0.42, ease: SILK }}
      >
        {coll.detail}
      </motion.p>

      {/* ── Glassmorphism card ─────────────────────────── */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 z-10 p-5"
        animate={{ y: hovered ? 0 : 6 }}
        transition={{ duration: 0.52, ease: SILK }}
      >
        <div style={GLASS} className="p-5">
          <h2
            className="font-display font-normal italic"
            style={{
              fontSize: 'clamp(20px, 2.2vw, 28px)',
              color: '#F8F0E8',
              lineHeight: 1.15,
              letterSpacing: '0.01em',
            }}
          >
            {coll.title}
          </h2>

          <DiamondDivider />

          <p
            className="font-sans font-light leading-[1.68]"
            style={{
              fontSize: 12,
              color: 'rgba(248,240,232,0.72)',
              letterSpacing: '0.04em',
              whiteSpace: 'pre-line',
            }}
          >
            {coll.tagline}
          </p>

          {/* Discover — animates in */}
          <motion.div
            style={{ overflow: 'hidden' }}
            animate={{ height: hovered ? 34 : 0, opacity: hovered ? 1 : 0 }}
            transition={{ duration: 0.42, ease: SILK }}
          >
            <div className="flex items-center gap-3 pt-3">
              <span className="font-sans font-light uppercase" style={{ fontSize: 9, letterSpacing: '0.38em', color: '#C09330' }}>
                Discover
              </span>
              <div className="flex-1 h-px" style={{ background: 'rgba(192,147,48,0.38)' }} />
              <span style={{ color: '#C09330', fontSize: 13 }}>→</span>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </motion.article>
  );
}

export default function TheAtelier() {
  return (
    <motion.main
      variants={PAGE} initial="initial" animate="animate"
      className="relative z-10 min-h-screen" style={{ paddingTop: 64, color: '#F8F0E8' }}
    >

      {/* ── Page Header ──────────────────────────────── */}
      <header className="text-center px-8 pt-16 pb-12 md:pt-20 md:pb-14 max-w-xl mx-auto">
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.0, delay: 0.1 }}
          className="font-sans font-normal uppercase mb-4"
          style={{ fontSize: 9, letterSpacing: '0.5em', color: '#C09330' }}
        >
          Collection · 2026
        </motion.p>

        <div style={{ overflow: 'hidden' }}>
          <motion.h1
            initial={{ y: '105%' }}
            animate={{ y: 0 }}
            transition={{ duration: 1.15, ease: SILK, delay: 0.2 }}
            className="font-display font-light italic leading-[1.05] mb-6"
            style={{ fontSize: 'clamp(40px, 5.5vw, 78px)', color: '#F8F0E8' }}
          >
            The Atelier
          </motion.h1>
        </div>

        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 1.1, ease: SILK, delay: 0.42 }}
          className="flex items-center justify-center gap-3 mb-6"
          style={{ transformOrigin: 'center' }}
        >
          <div className="h-px w-14" style={{ background: 'rgba(192,147,48,0.5)' }} />
          <svg width="5" height="5" viewBox="0 0 6 6">
            <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
          </svg>
          <div className="h-px w-14" style={{ background: 'rgba(192,147,48,0.5)' }} />
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.0, delay: 0.58 }}
          className="font-sans font-light leading-[1.9]"
          style={{ fontSize: 13, color: 'rgba(248,240,232,0.6)', letterSpacing: '0.03em' }}
        >
          Three stories. Three women. One language: BeHAZEL'd.
        </motion.p>
      </header>

      {/* ── 3-Column Gallery Grid ─────────────────────── */}
      <div className="px-8 md:px-14 lg:px-20 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6 max-w-6xl mx-auto">
          {COLLECTIONS.map((coll, i) => (
            <AtelierCard key={coll.id} coll={coll} index={i} />
          ))}
        </div>
      </div>

      {/* ── Footer line ──────────────────────────────── */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4, duration: 1.0 }}
        className="text-center pb-10"
      >
        <div className="flex items-center justify-center gap-6 px-8">
          <div className="h-px flex-1 max-w-[180px]" style={{ background: 'linear-gradient(to right, transparent, rgba(192,147,48,0.3))' }} />
          <p className="font-sans font-light uppercase" style={{ fontSize: 9, letterSpacing: '0.36em', color: 'rgba(192,147,48,0.38)' }}>
            Made to order · Handcrafted in India · 4–6 weeks
          </p>
          <div className="h-px flex-1 max-w-[180px]" style={{ background: 'linear-gradient(to left, transparent, rgba(192,147,48,0.3))' }} />
        </div>
      </motion.footer>
    </motion.main>
  );
}
