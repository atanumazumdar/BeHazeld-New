import { motion, MotionConfig } from 'framer-motion';

/* ─────────────────────────────────────────────────────────────
   SHARED VARIANTS — single source of truth for all animations
   ───────────────────────────────────────────────────────────── */
const variants = {

  // H1 wrapper: staggers each word child
  // Each word starts 0.09s after the previous one
  headlineWrap: {
    hidden: {},
    visible: {
      transition: { staggerChildren: 0.09, delayChildren: 0.65 },
    },
  },

  // Each word slides down from above and fades in
  // Headline fully visible: 0.65 + 5×0.09 + 0.65 ≈ 1.75s
  word: {
    hidden: { opacity: 0, y: -28 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.65, ease: [0.76, 0, 0.24, 1] },
    },
  },

  // Sub-headline: fades in 0.3s after headline completes → delay 2.05s
  subtitle: {
    hidden: { opacity: 0, y: 14 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.9, ease: 'easeOut', delay: 2.05 },
    },
  },

  // CTA: spring scales from 0, 0.5s after headline → delay 2.25s
  cta: {
    hidden: { scale: 0, opacity: 0 },
    visible: {
      scale: 1,
      opacity: 1,
      transition: { type: 'spring', stiffness: 200, damping: 15, delay: 2.25 },
    },
  },

  // Eyebrow — first element, gentle fade
  eyebrow: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 1.2, ease: 'easeOut', delay: 0.2 },
    },
  },

  // Horizontal gold rule — draws in from centre outward
  divider: {
    hidden: { scaleX: 0 },
    visible: {
      scaleX: 1,
      transition: { duration: 1.0, ease: [0.76, 0, 0.24, 1], delay: 0.38 },
    },
  },

  // Logo — fades up and scales in
  logo: {
    hidden: { opacity: 0, y: 14, scale: 0.92 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: { duration: 1.1, ease: [0.76, 0, 0.24, 1], delay: 0.42 },
    },
  },

  // Left image panel — wipes in from left
  imagePanel: {
    hidden: { clipPath: 'inset(0 100% 0 0)' },
    visible: {
      clipPath: 'inset(0 0% 0 0)',
      transition: { duration: 1.6, ease: [0.76, 0, 0.24, 1], delay: 0.1 },
    },
  },

  // Vertical gold thread — grows downward from top
  thread: {
    hidden: { scaleY: 0 },
    visible: {
      scaleY: 1,
      transition: { duration: 1.5, ease: [0.76, 0, 0.24, 1], delay: 0.6 },
    },
  },

  // Scroll indicator — appears last
  scrollIndicator: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 1.0, ease: 'easeOut', delay: 3.2 },
    },
  },
};

/* ─────────────────────────────────────────────────────────────
   CONTENT
   ───────────────────────────────────────────────────────────── */
const HEADLINE    = 'Every silhouette, a story worth wearing.';
const WORDS       = HEADLINE.split(' ');
const SUBHEADLINE = 'Handcrafted ethnic couture from The Hazel Atelier — each piece made to order for you alone.';

const T = {
  gold:      { 300: '#DFBF6A', 400: '#D4A83A', 500: '#C09330' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614', 600: '#3D1E0F' },
  bark:      { 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF' },
};

/* ─────────────────────────────────────────────────────────────
   DIAMOND RULE ORNAMENT
   ───────────────────────────────────────────────────────────── */
function DiamondRule() {
  return (
    <div className="flex items-center gap-2.5 my-5 w-full">
      <motion.div
        variants={variants.divider}
        initial="hidden"
        animate="visible"
        className="flex-1 h-px bg-gold-500"
        style={{ transformOrigin: 'left' }}
      />
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.65, duration: 0.4 }}
      >
        <svg width="6" height="6" viewBox="0 0 6 6">
          <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={T.gold[500]} />
        </svg>
      </motion.div>
      <motion.div
        variants={variants.divider}
        initial="hidden"
        animate="visible"
        className="flex-1 h-px bg-gold-500"
        style={{ transformOrigin: 'right' }}
      />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   HERO SECTION
   ───────────────────────────────────────────────────────────── */
export default function HeroSection({ onNavigate }) {
  return (
    <MotionConfig reducedMotion="user">
      <section
        className="relative w-full overflow-hidden grain"
        style={{ height: '100dvh', minHeight: 680, background: T.parchment[200] }}
      >
        <div className="flex flex-col md:flex-row h-full">

          {/* ── LEFT: Image Panel ──────────────────────────── */}
          <motion.div
            variants={variants.imagePanel}
            initial="hidden"
            animate="visible"
            className="relative overflow-hidden h-[38vh] md:h-auto md:w-[55%] flex-shrink-0"
          >
            <motion.div
              className="absolute inset-0"
              initial={{ scale: 1.1 }}
              animate={{ scale: 1.0 }}
              transition={{ duration: 3.2, ease: 'easeOut' }}
            >
              <img
                src="https://images.unsplash.com/photo-1583391733956-6c78276477e2?auto=format&fit=crop&w=900&q=80"
                alt="BeHazel'd bridal collection"
                className="w-full h-full object-cover object-top"
                style={{ filter: 'sepia(0.1) brightness(0.93)' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <div className="absolute inset-0 hidden md:block" style={{ background: `linear-gradient(to right, transparent 48%, ${T.parchment[200]} 100%)` }} />
              <div className="absolute inset-0" style={{ background: `linear-gradient(to top, ${T.hazel[600]}99 0%, transparent 48%)` }} />
              <div className="absolute inset-0" style={{ background: `linear-gradient(to right, ${T.hazel[600]}55 0%, transparent 22%)` }} />
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 2.0, duration: 1.0 }}
              className="absolute left-4 top-1/2 z-10 hidden md:block"
              style={{
                transform: 'translateY(-50%) rotate(180deg)',
                writingMode: 'vertical-rl',
                fontFamily: "'Jost', sans-serif",
                fontSize: 8, fontWeight: 300,
                letterSpacing: '0.46em', textTransform: 'uppercase',
                color: `${T.parchment[100]}66`,
              }}
            >
              The Hazel Atelier · Collection 2026
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 2.3, duration: 1.0 }}
              className="absolute bottom-6 left-6 z-10"
              style={{ fontFamily: "'Jost', sans-serif", fontSize: 8, fontWeight: 300, letterSpacing: '0.4em', textTransform: 'uppercase', color: `${T.parchment[50]}55` }}
            >
              Handcrafted in India
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 1.9, duration: 0.8 }}
              className="absolute inset-3.5 z-10 pointer-events-none hidden md:block"
              style={{ border: `1px solid ${T.gold[500]}18` }}
            />
          </motion.div>

          {/* ── GOLD THREAD — desktop divider ───────────────── */}
          <motion.div
            variants={variants.thread}
            initial="hidden"
            animate="visible"
            className="absolute left-[55%] top-0 w-px h-full z-20 hidden md:block"
            style={{
              transformOrigin: 'top',
              background: `linear-gradient(to bottom, transparent 0%, ${T.gold[500]} 8%, ${T.gold[500]} 92%, transparent 100%)`,
            }}
          />

          {/* ── RIGHT: Content Panel ────────────────────────── */}
          <div className="
            flex-1 relative z-10 flex flex-col justify-center
            items-center md:items-start
            text-center md:text-left
            px-8 sm:px-12 md:px-10 lg:px-16
            py-8 md:py-0
          ">
            {/* Eyebrow */}
            <motion.span
              variants={variants.eyebrow}
              initial="hidden"
              animate="visible"
              className="font-sans font-normal uppercase"
              style={{ fontSize: 9, letterSpacing: '0.46em', color: T.gold[500] }}
            >
              Luxury · Bridal · Couture
            </motion.span>

            {/* Diamond Rule */}
            <DiamondRule />

            {/* Logo with perpetual float — uses logo variant then infinite y */}
            <motion.div
              variants={variants.logo}
              initial="hidden"
              animate="visible"
              className="mb-5 md:mb-6"
            >
              <motion.img
                src="/Logo.png"
                alt="BeHAZEL'd"
                className="block"
                style={{ width: 'clamp(120px, 16vw, 230px)' }}
                animate={{ y: [0, -9, 0] }}
                transition={{ repeat: Infinity, duration: 5.5, ease: 'easeInOut', delay: 2.5 }}
              />
            </motion.div>

            {/* ── H1 HEADLINE — word-by-word stagger ──────────
                Each <span> inherits "hidden"→"visible" from the
                headlineWrap parent and uses the `word` variant.   */}
            <motion.h1
              variants={variants.headlineWrap}
              initial="hidden"
              animate="visible"
              className="font-serif font-light italic leading-[1.1] mb-4"
              style={{ fontSize: 'clamp(22px, 2.8vw, 46px)', color: T.hazel[500], letterSpacing: '0.01em' }}
            >
              {WORDS.map((word, i) => (
                <motion.span
                  key={i}
                  variants={variants.word}
                  style={{ display: 'inline-block', marginRight: '0.2em' }}
                >
                  {word}
                </motion.span>
              ))}
            </motion.h1>

            {/* ── SUB-HEADLINE — 0.3s after headline ─────────── */}
            <motion.p
              variants={variants.subtitle}
              initial="hidden"
              animate="visible"
              className="font-sans font-light leading-[1.9] mb-9"
              style={{ fontSize: 13, letterSpacing: '0.02em', color: T.hazel[400], maxWidth: 300 }}
            >
              {SUBHEADLINE}
            </motion.p>

            {/* ── CTA — spring scales in 0.5s after headline ─── */}
            <motion.div
              variants={variants.cta}
              initial="hidden"
              animate="visible"
              className="flex items-center gap-8 flex-wrap"
            >
              <motion.button
                className="btn-primary"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => onNavigate?.('collections')}
              >
                Explore Collection
              </motion.button>

              <motion.button
                className="btn-ghost"
                whileHover={{ x: 4 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                onClick={() => onNavigate?.('story')}
              >
                Our Story
                <motion.span
                  animate={{ x: [0, 5, 0] }}
                  transition={{ repeat: Infinity, duration: 2.6, ease: 'easeInOut', delay: 4 }}
                >→</motion.span>
              </motion.button>
            </motion.div>

            {/* Decorative hazel leaf */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.1 }}
              transition={{ duration: 0.8, delay: 3.0 }}
              className="absolute bottom-6 right-5 pointer-events-none hidden md:block"
            >
              <svg width="72" height="118" viewBox="0 0 60 96" fill="none">
                <path d="M30 90 C30 90 6 68 6 44 C6 22 17 6 30 6 C43 6 54 22 54 44 C54 68 30 90 30 90Z" stroke={T.gold[500]} strokeWidth="1.3" fill="none" strokeLinecap="round" />
                <line x1="30" y1="6"  x2="30" y2="90" stroke={T.gold[500]} strokeWidth="1.3" strokeLinecap="round" />
                <line x1="30" y1="28" x2="15" y2="43" stroke={T.gold[500]} strokeWidth="1.3" strokeLinecap="round" />
                <line x1="30" y1="40" x2="45" y2="55" stroke={T.gold[500]} strokeWidth="1.3" strokeLinecap="round" />
                <line x1="30" y1="52" x2="15" y2="67" stroke={T.gold[500]} strokeWidth="1.3" strokeLinecap="round" />
              </svg>
            </motion.div>
          </div>
        </div>

        {/* ── SCROLL INDICATOR ──────────────────────────────── */}
        <motion.div
          variants={variants.scrollIndicator}
          initial="hidden"
          animate="visible"
          className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 flex flex-col items-center gap-2"
        >
          <span
            className="font-sans font-light uppercase"
            style={{ fontSize: 7, letterSpacing: '0.46em', color: T.bark[500] }}
          >
            Scroll
          </span>
          <motion.div
            className="w-px h-9"
            style={{ background: `linear-gradient(to bottom, ${T.gold[500]}, transparent)`, transformOrigin: 'top' }}
            animate={{ scaleY: [1, 0.15, 1], opacity: [0.9, 0.2, 0.9] }}
            transition={{ repeat: Infinity, duration: 2.3, ease: 'easeInOut' }}
          />
        </motion.div>
      </section>
    </MotionConfig>
  );
}
