import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const T = {
  gold:      { 300: '#DFBF6A', 400: '#D4A83A', 500: '#C09330' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614', 600: '#3D1E0F' },
  bark:      { 300: '#B19870', 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF', 300: '#E2DAC9' },
};
const SILK = [0.76, 0, 0.24, 1];

const FEATURED = [
  {
    id: 1, name: 'Ivory Bloom Lehenga',
    category: 'Bridal Lehenga', price: '₹45,000',
    tag: 'New Arrival',
    description: 'Hand-embroidered ivory silk with champagne zari work. Each motif is drawn from the hazel botanical — a personal signature woven into every hem.',
    details: ['Pure silk base fabric', 'Hand-embroidered zari', 'Custom sizing available', 'Ships in 6 weeks'],
    gradient: 'linear-gradient(148deg, #F8F4EC 0%, #E8D09A 52%, #C09330 100%)',
    image: 'https://images.unsplash.com/photo-1583391733956-6c78276477e2?auto=format&fit=crop&w=700&q=80',
  },
  {
    id: 3, name: 'Antique Gold Anarkali',
    category: 'Evening Wear', price: '₹58,000',
    tag: 'Bestseller',
    description: 'Floor-length anarkali in burnt gold tissue, with a trail that moves like liquid light. The neckline is hand-finished with antique pearl buttons.',
    details: ['Gold tissue fabric', 'Antique pearl finishing', 'Made to measure', 'Ships in 5 weeks'],
    gradient: 'linear-gradient(138deg, #F5EDD0 0%, #D4A83A 48%, #7A4A28 100%)',
    image: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=700&q=80',
  },
  {
    id: 4, name: 'Heritage Kanjivaram Saree',
    category: 'Heirloom Sarees', price: '₹89,000',
    tag: 'Heirloom',
    description: 'A Kanjivaram saree woven on handlooms in Varanasi. The deep palette is contrasted with a gold zari border — designed to be passed down.',
    details: ['Handloom Kanjivaram silk', 'Gold zari border', 'Certificate of authenticity', 'Ships in 4 weeks'],
    gradient: 'linear-gradient(155deg, #E8E0CC 0%, #B19870 42%, #4B2614 100%)',
    image: 'https://images.unsplash.com/photo-1617537212953-b87fb2ffc370?auto=format&fit=crop&w=700&q=80',
  },
];

function ProductCard({ product, index, onAddToCart }) {
  const [expanded, setExpanded] = useState(false);
  const isEven = index % 2 === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 60 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 1.3, ease: SILK }}
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 'clamp(32px, 5vw, 72px)',
        alignItems: 'center',
        padding: 'clamp(48px, 7vh, 80px) clamp(32px, 6vw, 96px)',
        borderBottom: `1px solid ${T.gold[500]}18`,
      }}
    >
      {/* Image Panel */}
      <div style={{ order: isEven ? 0 : 1, position: 'relative' }}>
        <motion.div
          style={{ position: 'relative', aspectRatio: '3/4', overflow: 'hidden' }}
          whileHover={{ scale: 1.01 }}
          transition={{ duration: 0.6, ease: [0.25, 0.1, 0, 1] }}
        >
          <img
            src={product.image}
            alt={product.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top', filter: 'sepia(0.06) brightness(0.9)', display: 'block' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          {/* Gradient fallback */}
          <div style={{ position: 'absolute', inset: 0, background: product.gradient, zIndex: -1 }}>
            <span style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 160, fontStyle: 'italic', fontWeight: 300,
              color: 'rgba(255,255,255,0.07)', userSelect: 'none',
            }}>H</span>
          </div>

          {product.tag && (
            <div style={{
              position: 'absolute', top: 20, left: 0, zIndex: 5,
              background: T.gold[500], padding: '5px 14px',
              fontFamily: "'Jost', sans-serif",
              fontSize: 8, letterSpacing: '0.36em', textTransform: 'uppercase',
              color: T.parchment[50],
            }}>{product.tag}</div>
          )}
          <div style={{ position: 'absolute', inset: 14, border: `1px solid ${T.gold[500]}18`, zIndex: 3, pointerEvents: 'none' }} />
        </motion.div>

        {/* Thumbnail dots */}
        <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'center' }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              width: 6, height: 6, borderRadius: '50%',
              background: i === 0 ? T.gold[500] : `${T.gold[500]}44`,
            }} />
          ))}
        </div>
      </div>

      {/* Content Panel */}
      <div style={{ order: isEven ? 1 : 0 }}>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 9, fontWeight: 400,
          letterSpacing: '0.44em', textTransform: 'uppercase',
          color: T.gold[500], marginBottom: 12,
        }}>{product.category}</p>

        <div style={{ overflow: 'hidden' }}>
          <motion.h3
            initial={{ y: '110%' }}
            whileInView={{ y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1.2, ease: SILK, delay: 0.15 }}
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 'clamp(28px, 3vw, 44px)',
              fontWeight: 300, fontStyle: 'italic',
              color: T.hazel[500], lineHeight: 1.1,
              letterSpacing: '0.01em',
            }}
          >{product.name}</motion.h3>
        </div>

        {/* Gold rule */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: 140, margin: '18px 0' }}>
          <motion.div
            style={{ flex: 1, height: 1, background: T.gold[500], transformOrigin: 'left' }}
            initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
            transition={{ duration: 1.0, ease: SILK, delay: 0.3 }}
          />
          <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}>
            <svg width="5" height="5" viewBox="0 0 6 6">
              <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={T.gold[500]} />
            </svg>
          </motion.div>
          <motion.div
            style={{ flex: 1, height: 1, background: T.gold[500], transformOrigin: 'right' }}
            initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
            transition={{ duration: 1.0, ease: SILK, delay: 0.3 }}
          />
        </div>

        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 13, fontWeight: 300,
          color: T.hazel[400], lineHeight: 1.9,
          letterSpacing: '0.02em', marginBottom: 20,
        }}>{product.description}</p>

        {/* Details accordion */}
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
            fontFamily: "'Jost', sans-serif",
            fontSize: 9, fontWeight: 300,
            letterSpacing: '0.32em', textTransform: 'uppercase',
            color: T.bark[500], marginBottom: 12,
            transition: 'color 0.3s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = T.gold[500]}
          onMouseLeave={e => e.currentTarget.style.color = T.bark[500]}
        >
          Craft Details
          <motion.span animate={{ rotate: expanded ? 45 : 0 }} transition={{ duration: 0.3 }} style={{ display: 'block', lineHeight: 1 }}>+</motion.span>
        </button>

        <AnimatePresence>
          {expanded && (
            <motion.ul
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.45, ease: SILK }}
              style={{ overflow: 'hidden', paddingLeft: 0, listStyle: 'none', marginBottom: 20 }}
            >
              {product.details.map((d, i) => (
                <li key={i} style={{
                  fontFamily: "'Jost', sans-serif",
                  fontSize: 12, fontWeight: 300,
                  color: T.bark[500], letterSpacing: '0.03em',
                  paddingBlock: 6,
                  borderBottom: `1px solid ${T.gold[500]}18`,
                  display: 'flex', alignItems: 'center', gap: 10,
                }}>
                  <span style={{ width: 4, height: 4, borderRadius: '50%', background: T.gold[500], display: 'block', flexShrink: 0 }} />
                  {d}
                </li>
              ))}
            </motion.ul>
          )}
        </AnimatePresence>

        {/* Price + CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', marginTop: 8 }}>
          <p style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 26, fontWeight: 400,
            color: T.hazel[500], letterSpacing: '0.01em',
          }}>{product.price}</p>
          <motion.button
            className="btn-primary"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onAddToCart(product)}
          >Add to Bag</motion.button>
        </div>
      </div>
    </motion.div>
  );
}

export default function ProductShowcase({ onAddToCart }) {
  return (
    <section style={{ background: T.parchment[50] }}>
      {/* Header */}
      <div style={{
        textAlign: 'center',
        padding: 'clamp(72px, 10vh, 108px) clamp(32px, 5vw, 80px) clamp(40px, 5vh, 64px)',
        borderBottom: `1px solid ${T.gold[500]}18`,
      }}>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 1.0, ease: SILK }}
          style={{
            fontFamily: "'Jost', sans-serif",
            fontSize: 9, fontWeight: 400,
            letterSpacing: '0.48em', textTransform: 'uppercase',
            color: T.gold[500], marginBottom: 18,
          }}
        >A Selection of Hazel's Finest</motion.p>

        <div style={{ overflow: 'hidden', display: 'inline-block' }}>
          <motion.h2
            initial={{ y: '110%' }}
            whileInView={{ y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1.3, ease: SILK, delay: 0.2 }}
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 'clamp(36px, 5vw, 72px)',
              fontWeight: 300, fontStyle: 'italic',
              color: T.hazel[500], lineHeight: 1.05,
              letterSpacing: '0.02em',
            }}
          >Featured Pieces</motion.h2>
        </div>

        <motion.div
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.1, ease: SILK, delay: 0.5 }}
          style={{ height: 1, background: `${T.gold[500]}66`, margin: '20px auto 0', maxWidth: 140, transformOrigin: 'center' }}
        />
      </div>

      {FEATURED.map((product, i) => (
        <ProductCard key={product.id} product={product} index={i} onAddToCart={onAddToCart} />
      ))}
    </section>
  );
}
