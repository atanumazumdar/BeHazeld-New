import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const EASE_OUT  = [0.16, 1, 0.3, 1];
const EASE_SILK = [0.76, 0, 0.24, 1];

const PAGE = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.5, ease: 'easeOut' } },
};

function up(delay) {
  return {
    initial:    { opacity: 0, y: 16 },
    animate:    { opacity: 1, y: 0 },
    transition: { duration: 0.75, ease: EASE_OUT, delay },
  };
}

/* Shared inline styles */
const BODY = {
  fontSize: 12.5, lineHeight: 1.78,
  color: 'rgba(248,240,232,0.68)', letterSpacing: '0.027em',
};
const SERIF_ITALIC = {
  fontFamily: "'Bodoni Moda', 'Playfair Display', Georgia, serif",
  fontStyle: 'italic', fontWeight: 300,
  color: 'rgba(248,240,232,0.88)', lineHeight: 1.6,
};

export default function OurStory() {
  const navigate = useNavigate();

  return (
    <motion.main
      variants={PAGE} initial="initial" animate="animate"
      className="relative z-10 flex flex-col md:flex-row"
      style={{ minHeight: 'calc(100vh - 64px)', paddingTop: 64, color: '#F8F0E8' }}
    >

      {/* ══════════════════════════════════════════════
          LEFT — sticky logo
          ══════════════════════════════════════════════ */}
      <div
        className="flex-shrink-0 w-full md:w-[44%] md:sticky
                   flex flex-col items-center justify-center
                   py-10 md:py-0"
        style={{ top: 64, height: 'calc(100vh - 64px)', alignSelf: 'flex-start' }}
      >
        {/* Ambient glow */}
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 72% 60% at 50% 50%, rgba(192,147,48,0.11) 0%, transparent 68%)' }} />

        {/* Gold thread divider */}
        <div className="absolute right-0 top-0 bottom-0 w-px hidden md:block pointer-events-none"
          style={{ background: 'linear-gradient(to bottom, transparent 8%, rgba(192,147,48,0.23) 26%, rgba(192,147,48,0.23) 74%, transparent 92%)' }} />

        {/* Entrance wrapper */}
        <motion.div
          initial={{ opacity: 0, scale: 0.88, y: 36 }}
          animate={{ opacity: 1, scale: 1.0, y: 0 }}
          transition={{ duration: 1.5, ease: EASE_OUT, delay: 0 }}
          className="relative z-10"
        >
          {/* Float wrapper */}
          <motion.div
            animate={{ y: [0, -14, 0] }}
            transition={{ repeat: Infinity, duration: 6.0, ease: 'easeInOut', delay: 1.9 }}
            className="relative"
          >
            {/* Glow bloom */}
            <div className="absolute pointer-events-none"
              style={{
                inset: '-24%', borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(192,147,48,0.20) 0%, transparent 65%)',
                filter: 'blur(32px)',
              }} />

            <img
              src="/Logo.png" alt="BeHAZEL'd" draggable="false"
              style={{
                width: 'clamp(240px, 80%, 600px)',
                display: 'block',
                /* Brightness: lift the muted tones off the dark bg
                   Contrast:   sharpen the illustration lines
                   Saturate:   restore the gold/ivory warmth
                   Drop-shadow: gold corona separates it from background */
                filter: [
                  'brightness(1.85)',
                  'contrast(1.12)',
                  'saturate(1.35)',
                  'drop-shadow(0 0 48px rgba(192,147,48,0.65))',
                  'drop-shadow(0 28px 64px rgba(192,147,48,0.38))',
                  'drop-shadow(0 4px 12px rgba(0,0,0,0.40))',
                ].join(' '),
              }}
            />
          </motion.div>
        </motion.div>

        <motion.p {...up(1.7)}
          className="font-sans font-light uppercase mt-4 hidden md:block"
          style={{ fontSize: 7.5, letterSpacing: '0.48em', color: 'rgba(192,147,48,0.32)' }}>
          Handcrafted in India · Est. 2024
        </motion.p>
      </div>

      {/* ══════════════════════════════════════════════
          RIGHT — literature (transparent bg, single viewport)
          ══════════════════════════════════════════════ */}
      <div
        className="flex-1 flex items-center
                   px-7 md:px-9 lg:px-14
                   py-10 md:py-0
                   md:overflow-hidden"
        style={{ minHeight: 'calc(100vh - 64px)' }}
      >
        <div className="w-full max-w-[600px]">

          {/* ── Eyebrow ────────────────────────────────── */}
          <motion.p {...up(0.55)}
            className="font-sans font-normal uppercase mb-3"
            style={{ fontSize: 7.5, letterSpacing: '0.55em', color: '#C09330' }}>
            Est. 2024 · The Hazel Atelier
          </motion.p>

          {/* ── H1 — three-tier typographic cascade ────────
              "The"   → thin italic Playfair, muted cream
              "Hazel" → bold italic Playfair, gold shimmer
              "Story" → bold italic Playfair, gold shimmer, larger  */}
          <div style={{ overflow: 'hidden' }}>
            <motion.h1
              initial={{ y: '108%' }} animate={{ y: 0 }}
              transition={{ duration: 1.1, ease: EASE_SILK, delay: 0.7 }}
              className="leading-none mb-4"
            >
              {/* Tier 1: thin italic Playfair */}
              <span className="font-display font-light italic block"
                style={{ fontSize: 'clamp(20px, 2.2vw, 30px)', color: 'rgba(248,240,232,0.55)', lineHeight: 1.1 }}>
                The
              </span>
              {/* Tier 2: bold italic shimmer — same size as Story but slightly less */}
              <span className="shimmer-gold font-display italic block"
                style={{ fontSize: 'clamp(38px, 4.5vw, 62px)', fontWeight: 700, lineHeight: 0.93 }}>
                Hazel
              </span>
              {/* Tier 3: bold italic shimmer — largest */}
              <span className="shimmer-gold font-display italic block"
                style={{ fontSize: 'clamp(46px, 5.5vw, 76px)', fontWeight: 700, lineHeight: 0.9 }}>
                Story
              </span>
            </motion.h1>
          </div>

          {/* ── Gold ornament ───────────────────────────── */}
          <motion.div
            initial={{ scaleX: 0, opacity: 0 }} animate={{ scaleX: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease: EASE_SILK, delay: 0.95 }}
            className="flex items-center gap-3 mb-4"
            style={{ transformOrigin: 'left' }}>
            <div className="h-px w-10" style={{ background: 'linear-gradient(to right, #C09330, rgba(192,147,48,0.12))' }} />
            <svg width="4" height="4" viewBox="0 0 6 6">
              <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill="#C09330" />
            </svg>
          </motion.div>

          {/* ── Opening quote — Playfair italic, larger ─── */}
          <motion.p {...up(1.1)} className="font-display font-light italic mb-3"
            style={{ fontSize: 'clamp(14px, 1.4vw, 17px)', ...SERIF_ITALIC }}>
            We believe fashion is not what you wear —
            it is what you become when you wear it.
          </motion.p>

          {/* ── Brand statement — gold accent ───────────── */}
          <motion.p {...up(1.2)} className="font-sans font-light mb-3"
            style={{ ...BODY, color: 'rgba(248,240,232,0.80)' }}>
            <span style={{ color: '#C09330', fontWeight: 400 }}>BeHAZEL'd</span> is not just a label. It is a story — Hazel's story.
          </motion.p>

          {/* ── Body §1: Mumbai → Fortune 500 → airports → Lucknow ── */}
          <motion.p {...up(1.3)} className="font-sans font-light mb-3" style={BODY}>
            Born in Mumbai and shaped by boardrooms across continents, Hazel built a career with a Fortune 500 organisation across geographies and time zones — each country a new layer, each culture a new perspective. Yet somewhere between airports and deadlines, she began searching for something quieter. Something more rooted.
          </motion.p>

          {/* ── Pull line — Playfair italic ──────────────── */}
          <motion.p {...up(1.4)} className="font-display font-light italic mb-3"
            style={{ fontSize: 'clamp(13px, 1.3vw, 16px)', ...SERIF_ITALIC, color: 'rgba(248,240,232,0.82)' }}>
            She found it in the timeless artistry of Lucknow.
          </motion.p>

          {/* ── Body §2: Chikan + return + designed for women ── */}
          <motion.p {...up(1.5)} className="font-sans font-light mb-3" style={BODY}>
            In the meditative craft of Chikan embroidery she discovered a rhythm mirroring her own journey — patient, intricate, expressive. BeHAZEL'd was born from that moment of return: every piece global in exposure, deeply Indian in soul, designed for women who move across roles and moments with quiet strength.
          </motion.p>

          {/* ── Gold left-border accent block ───────────── */}
          <motion.div {...up(1.6)} className="pl-4 mb-3"
            style={{ borderLeft: '2px solid rgba(192,147,48,0.45)' }}>
            {['For all moods.', 'For all occasions.', 'For all ages, all classes — because elegance does not discriminate.']
              .map((line, i) => (
                <p key={i} className="font-sans font-light"
                  style={{ ...BODY, lineHeight: 1.9, color: 'rgba(248,240,232,0.76)' }}>
                  {line}
                </p>
              ))}
          </motion.div>

          {/* ── Playfair italic poetry ───────────────────── */}
          <motion.div {...up(1.7)} className="mb-3">
            {['It stays with you.', 'It evolves with you.', 'It becomes you.'].map((line, i) => (
              <p key={i} className="font-display font-light italic"
                style={{ fontSize: 'clamp(12px, 1.2vw, 14.5px)', ...SERIF_ITALIC, lineHeight: 1.75, color: 'rgba(248,240,232,0.80)' }}>
                {line}
              </p>
            ))}
          </motion.div>

          {/* ── Finale: large gold Playfair ─────────────── */}
          <motion.p {...up(1.8)} className="font-display font-light italic mb-5"
            style={{ fontSize: 'clamp(18px, 1.9vw, 24px)', color: '#C09330', lineHeight: 1.2 }}>
            You become it.
          </motion.p>

          {/* ── CTA ─────────────────────────────────────── */}
          <motion.div {...up(1.9)} className="flex items-center justify-between flex-wrap gap-4">
            <motion.button
              onClick={() => navigate('/atelier')}
              className="flex items-center gap-2.5 font-sans font-light uppercase cursor-pointer"
              style={{ fontSize: 8.5, letterSpacing: '0.38em', color: '#C09330', background: 'none', border: 'none', padding: 0 }}
              whileHover={{ x: 6 }}
              transition={{ type: 'spring', stiffness: 280, damping: 22 }}
            >
              Enter The Atelier
              <motion.span
                animate={{ x: [0, 6, 0] }}
                transition={{ repeat: Infinity, duration: 2.6, ease: 'easeInOut', delay: 3 }}>
                →
              </motion.span>
            </motion.button>

            <p style={{
              fontFamily: "'Cormorant Garamond', Georgia, serif",
              fontStyle: 'italic',
              fontWeight: 400,
              fontSize: 'clamp(15px, 1.3vw, 19px)',
              letterSpacing: '0.06em',
              color: 'rgba(192,147,48,0.72)',
            }}>
              be you, with HAZEL
            </p>
          </motion.div>

        </div>
      </div>
    </motion.main>
  );
}
