import { useState } from 'react';
import { motion } from 'framer-motion';

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   TOKENS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
const T = {
  gold:      { 400: '#D4A83A', 500: '#C09330', 600: '#A67C26' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614', 600: '#3D1E0F' },
  bark:      { 300: '#B19870', 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF', 300: '#E2DAC9' },
};
const SILK   = [0.76, 0, 0.24, 1];

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   DATA — replace gradients with product photography
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
const FILTERS = ['All', 'Lehengas', 'Sarees', 'Anarkalis', 'Blouses', 'Sets'];

const PRODUCTS = [
  { id: 1,  name: 'Ivory Bloom Lehenga',       category: 'Lehenga',  price: '₹45,000', tag: 'New Arrival',
    gradient: 'linear-gradient(148deg, #F8F4EC 0%, #E8D09A 52%, #C09330 100%)' },
  { id: 2,  name: 'Hazel Silk Dupatta',         category: 'Dupatta',  price: '₹12,500',
    gradient: 'linear-gradient(162deg, #F0E8D0 0%, #C4A035 55%, #8C651C 100%)' },
  { id: 3,  name: 'Antique Gold Anarkali',      category: 'Anarkali', price: '₹58,000', tag: 'Bestseller',
    gradient: 'linear-gradient(138deg, #F5EDD0 0%, #D4A83A 48%, #7A4A28 100%)' },
  { id: 4,  name: 'Heritage Kanjivaram Saree',  category: 'Saree',    price: '₹89,000', tag: 'Heirloom',
    gradient: 'linear-gradient(155deg, #E8E0CC 0%, #B19870 42%, #4B2614 100%)' },
  { id: 5,  name: 'Pearl Embroidery Blouse',    category: 'Blouse',   price: '₹18,000',
    gradient: 'linear-gradient(142deg, #FDFCF9 0%, #E0C870 52%, #977649 100%)' },
  { id: 6,  name: 'Champagne Zari Lehenga',     category: 'Lehenga',  price: '₹67,000', tag: 'New Arrival',
    gradient: 'linear-gradient(152deg, #EEE9DF 0%, #C8A860 42%, #5C3D1E 100%)' },
  { id: 7,  name: 'Rose Gold Sharara Set',      category: 'Set',      price: '₹52,000',
    gradient: 'linear-gradient(146deg, #F8F0E8 0%, #D4B070 55%, #8C5A28 100%)' },
  { id: 8,  name: 'Bridal Mehendi Suit',        category: 'Suit',     price: '₹38,000', tag: 'Bestseller',
    gradient: 'linear-gradient(160deg, #F0EAD6 0%, #C09330 52%, #6B4020 100%)' },
  { id: 9,  name: 'Minimal Ivory Occasion Gown',category: 'Gown',     price: '₹41,000',
    gradient: 'linear-gradient(136deg, #FDFCF9 0%, #DFD0A8 55%, #977649 100%)' },
];

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   DIAMOND RULE (shared ornament)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
function DiamondRule({ delay = 0.4, width = 180 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, width, margin: '20px auto 0' }}>
      <motion.div
        style={{ flex: 1, height: 1, background: T.gold[500], transformOrigin: 'left' }}
        initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
        transition={{ duration: 1.0, ease: SILK, delay }}
      />
      <motion.div
        initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
        transition={{ duration: 0.5, delay: delay + 0.1 }}
      >
        <svg width="6" height="6" viewBox="0 0 6 6">
          <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={T.gold[500]} />
        </svg>
      </motion.div>
      <motion.div
        style={{ flex: 1, height: 1, background: T.gold[500], transformOrigin: 'right' }}
        initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
        transition={{ duration: 1.0, ease: SILK, delay }}
      />
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   PRODUCT CARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
function ProductCard({ product, index, onAddToCart }) {
  const [hovered, setHovered] = useState(false);
  const col = index % 3;

  return (
    <motion.article
      initial={{ opacity: 0, y: 44 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 1.1, ease: SILK, delay: col * 0.14 }}
      style={{ cursor: 'pointer' }}
    >
      {/* ── Image container ─────────────────────────────── */}
      <div
        style={{ position: 'relative', overflow: 'hidden', aspectRatio: '3 / 4' }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Zooming placeholder (replace div with <img> in production) */}
        <motion.div
          style={{ width: '100%', height: '100%' }}
          animate={{ scale: hovered ? 1.07 : 1.0 }}
          transition={{ duration: 0.85, ease: [0.25, 0.1, 0, 1] }}
        >
          <div style={{ width: '100%', height: '100%', background: product.gradient, position: 'relative' }}>
            {/* Subtle "H" watermark */}
            <span style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 140, fontStyle: 'italic', fontWeight: 300,
              color: 'rgba(255,255,255,0.07)',
              userSelect: 'none', pointerEvents: 'none',
            }}>H</span>
          </div>
        </motion.div>

        {/* Tag badge */}
        {product.tag && (
          <div style={{
            position: 'absolute', top: 16, left: 0, zIndex: 5,
            background: T.gold[500],
            padding: '5px 12px',
            fontFamily: "'Jost', sans-serif",
            fontSize: 8, letterSpacing: '0.36em', textTransform: 'uppercase',
            color: T.parchment[50],
          }}>
            {product.tag}
          </div>
        )}

        {/* ── Hover overlay — slides up from bottom ───── */}
        <motion.div
          style={{
            position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 4,
            background: 'rgba(48, 24, 8, 0.90)',
            backdropFilter: 'blur(4px)',
            padding: '22px 20px 20px',
          }}
          initial={false}
          animate={{ y: hovered ? 0 : '100%' }}
          transition={{ duration: 0.52, ease: SILK }}
        >
          {/* Thin gold rule */}
          <div style={{ height: 1, background: `${T.gold[500]}66`, marginBottom: 14 }} />

          <p style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 17, fontStyle: 'italic', fontWeight: 400,
            color: T.parchment[100], letterSpacing: '0.02em',
            marginBottom: 18,
          }}>
            {product.name}
          </p>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={() => onAddToCart && onAddToCart(product)}
              style={{
                flex: 1, padding: '11px 0',
                fontFamily: "'Jost', sans-serif", fontSize: 9,
                letterSpacing: '0.3em', textTransform: 'uppercase',
                color: T.parchment[50], background: T.gold[500],
                border: 'none', cursor: 'pointer',
                transition: 'background 0.35s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.background = T.hazel[500]}
              onMouseLeave={e => e.currentTarget.style.background = T.gold[500]}
            >
              Add to Bag
            </button>

            {/* Wishlist icon */}
            <button style={{
              width: 40, height: 40, flexShrink: 0,
              background: 'none',
              border: `1px solid rgba(248,244,236,0.35)`,
              cursor: 'pointer', color: T.parchment[100],
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'border-color 0.3s ease',
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = T.gold[500]; e.currentTarget.querySelector('svg').style.stroke = T.gold[500]; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(248,244,236,0.35)'; e.currentTarget.querySelector('svg').style.stroke = T.parchment[100]; }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={T.parchment[100]} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'stroke 0.3s ease' }}>
                <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
              </svg>
            </button>
          </div>
        </motion.div>
      </div>

      {/* ── Product info ─────────────────────────────────── */}
      <div style={{ paddingTop: 18 }}>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 9, fontWeight: 400,
          letterSpacing: '0.4em', textTransform: 'uppercase',
          color: T.gold[500], marginBottom: 7,
        }}>
          {product.category}
        </p>
        <motion.p
          animate={{ color: hovered ? T.hazel[400] : T.hazel[500] }}
          transition={{ duration: 0.35 }}
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 19, fontWeight: 400,
            letterSpacing: '0.01em',
            marginBottom: 6,
          }}
        >
          {product.name}
        </motion.p>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 13, fontWeight: 300,
          color: T.bark[500], letterSpacing: '0.02em',
        }}>
          {product.price}
        </p>
      </div>
    </motion.article>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   COLLECTIONS PAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
export default function CollectionsPage({ onAddToCart }) {
  const [activeFilter, setActiveFilter] = useState('All');

  const filtered = activeFilter === 'All'
    ? PRODUCTS
    : PRODUCTS.filter(p => p.category.toLowerCase() === activeFilter.toLowerCase().replace(/s$/, ''));

  return (
    <div style={{ background: T.parchment[200], minHeight: '100vh', paddingTop: 80 }}>

      {/* ── Page Header ───────────────────────────────────── */}
      <header style={{ textAlign: 'center', padding: 'clamp(56px, 8vh, 96px) 40px 0' }}>

        {/* Eyebrow */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.4, ease: 'easeOut', delay: 0.2 }}
          style={{
            fontFamily: "'Jost', sans-serif",
            fontSize: 9, fontWeight: 400,
            letterSpacing: '0.48em', textTransform: 'uppercase',
            color: T.gold[500], marginBottom: 20,
          }}
        >
          Handcrafted · Heirloom · Couture
        </motion.p>

        {/* Title */}
        <div style={{ overflow: 'hidden', display: 'inline-block' }}>
          <motion.h1
            initial={{ y: '105%' }}
            animate={{ y: 0 }}
            transition={{ duration: 1.3, ease: SILK, delay: 0.35 }}
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 'clamp(44px, 6vw, 88px)',
              fontWeight: 300, fontStyle: 'italic',
              color: T.hazel[500], lineHeight: 1.0,
              letterSpacing: '0.02em',
            }}
          >
            The Hazel Edit
          </motion.h1>
        </div>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.1, ease: SILK, delay: 0.7 }}
          style={{
            fontFamily: "'Jost', sans-serif",
            fontSize: 12, fontWeight: 300,
            letterSpacing: '0.06em',
            color: T.bark[500], marginTop: 14,
          }}
        >
          Each piece, a story. Each thread, a promise.
        </motion.p>

        <DiamondRule delay={0.8} width={160} />

        {/* Filter bar */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.0, ease: SILK, delay: 1.0 }}
          style={{
            display: 'flex', justifyContent: 'center',
            gap: 'clamp(20px, 3vw, 44px)',
            marginTop: 32, flexWrap: 'wrap',
          }}
        >
          {FILTERS.map(label => {
            const active = activeFilter === label;
            return (
              <button
                key={label}
                onClick={() => setActiveFilter(label)}
                style={{
                  fontFamily: "'Jost', sans-serif",
                  fontSize: 10, fontWeight: active ? 400 : 300,
                  letterSpacing: '0.32em', textTransform: 'uppercase',
                  color: active ? T.hazel[500] : T.bark[300],
                  background: 'none', border: 'none', cursor: 'pointer',
                  paddingBottom: 6,
                  borderBottom: active ? `1px solid ${T.gold[500]}` : '1px solid transparent',
                  transition: 'color 0.35s ease, border-color 0.35s ease',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.color = T.hazel[400]; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.color = T.bark[300]; }}
              >
                {label}
              </button>
            );
          })}
        </motion.div>

        {/* Product count */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.0, delay: 1.2 }}
          style={{
            fontFamily: "'Jost', sans-serif",
            fontSize: 10, fontWeight: 300,
            letterSpacing: '0.16em', color: T.bark[300],
            marginTop: 28,
          }}
        >
          {filtered.length} {filtered.length === 1 ? 'piece' : 'pieces'}
        </motion.p>
      </header>

      {/* Horizontal rule spanning full width */}
      <motion.div
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 1.6, ease: SILK, delay: 1.0 }}
        style={{
          height: 1, background: `${T.gold[500]}33`,
          margin: 'clamp(28px, 4vh, 48px) clamp(40px, 6vw, 80px) 0',
          transformOrigin: 'left',
        }}
      />

      {/* ── Product Grid ──────────────────────────────────── */}
      <main style={{
        padding: 'clamp(40px, 5vh, 64px) clamp(40px, 6vw, 80px) clamp(80px, 10vh, 120px)',
        maxWidth: 1440, margin: '0 auto',
      }}>
        {filtered.length > 0 ? (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 'clamp(40px, 5vh, 64px) clamp(20px, 2.5vw, 36px)',
          }}>
            {filtered.map((product, i) => (
              <ProductCard key={product.id} product={product} index={i} onAddToCart={onAddToCart} />
            ))}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <p style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 24, fontStyle: 'italic', fontWeight: 300,
              color: T.bark[300],
            }}>
              This collection is being curated.
            </p>
          </div>
        )}
      </main>

      {/* ── Footer tagline ────────────────────────────────── */}
      <footer style={{
        textAlign: 'center',
        borderTop: `1px solid ${T.gold[500]}22`,
        padding: '32px 40px',
      }}>
        <p style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 13, fontStyle: 'italic', fontWeight: 300,
          color: T.bark[300], letterSpacing: '0.06em',
        }}>
          Each piece is made to order — allow 4–6 weeks for delivery
        </p>
      </footer>
    </div>
  );
}
