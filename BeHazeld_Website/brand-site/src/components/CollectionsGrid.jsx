import { motion } from 'framer-motion';

const T = {
  gold:      { 300: '#DFBF6A', 400: '#D4A83A', 500: '#C09330' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614', 600: '#3D1E0F' },
  bark:      { 300: '#B19870', 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF', 300: '#E2DAC9' },
};
const SILK = [0.76, 0, 0.24, 1];

const CATEGORIES = [
  {
    id: 'bridal',
    label: 'Bridal',
    subtitle: 'Eternal grace for your forever moment',
    tag: 'Signature Collection',
    gradient: 'linear-gradient(162deg, #F8F4EC 0%, #E8C97A 38%, #C09330 68%, #4B2614 100%)',
    span: 'large',
    image: 'https://images.unsplash.com/photo-1583391733956-6c78276477e2?auto=format&fit=crop&w=900&q=80',
  },
  {
    id: 'evening',
    label: 'Evening Wear',
    subtitle: 'Woven for the woman who commands a room',
    tag: 'Evening Edit',
    gradient: 'linear-gradient(148deg, #EEE9DF 0%, #B19870 45%, #7D5A30 100%)',
    span: 'small',
    image: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=700&q=80',
  },
  {
    id: 'essentials',
    label: 'Essentials',
    subtitle: 'Quiet luxury for every day',
    tag: 'Everyday Atelier',
    gradient: 'linear-gradient(152deg, #FDFCF9 0%, #DFD0A8 52%, #A67C26 100%)',
    span: 'small',
    image: 'https://images.unsplash.com/photo-1617537212953-b87fb2ffc370?auto=format&fit=crop&w=700&q=80',
  },
];

function DiamondRule() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: 160, margin: '20px auto 0' }}>
      <motion.div
        style={{ flex: 1, height: 1, background: T.gold[500], transformOrigin: 'left' }}
        initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
        transition={{ duration: 1.0, ease: SILK, delay: 0.4 }}
      />
      <motion.div
        initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.55 }}
      >
        <svg width="6" height="6" viewBox="0 0 6 6">
          <rect x="3" y="0" width="4.24" height="4.24" transform="rotate(45 3 3)" fill={T.gold[500]} />
        </svg>
      </motion.div>
      <motion.div
        style={{ flex: 1, height: 1, background: T.gold[500], transformOrigin: 'right' }}
        initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }}
        transition={{ duration: 1.0, ease: SILK, delay: 0.4 }}
      />
    </div>
  );
}

function CategoryCard({ cat, index, onNavigate }) {
  const isLarge = cat.span === 'large';

  return (
    <motion.div
      initial={{ opacity: 0, y: 48 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 1.2, ease: SILK, delay: index * 0.18 }}
      onClick={() => onNavigate('collections')}
      style={{
        position: 'relative',
        overflow: 'hidden',
        cursor: 'pointer',
        aspectRatio: isLarge ? '3 / 4' : '3 / 4',
        gridRow: isLarge ? 'span 2' : 'span 1',
      }}
    >
      {/* Image with zoom on hover */}
      <motion.div
        style={{ position: 'absolute', inset: 0 }}
        whileHover={{ scale: 1.07 }}
        transition={{ duration: 0.9, ease: [0.25, 0.1, 0, 1] }}
      >
        <img
          src={cat.image}
          alt={cat.label}
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top', filter: 'sepia(0.08) brightness(0.88)' }}
          onError={(e) => {
            e.currentTarget.style.display = 'none';
          }}
        />
        <div style={{ position: 'absolute', inset: 0, background: cat.gradient, zIndex: -1 }} />
      </motion.div>

      {/* Dark vignette */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(to top, rgba(24,10,4,0.78) 0%, rgba(24,10,4,0.22) 50%, transparent 100%)',
        zIndex: 2,
      }} />

      {/* Tag badge */}
      <div style={{
        position: 'absolute', top: 20, left: 0, zIndex: 5,
        background: `${T.gold[500]}dd`,
        padding: '5px 14px',
        fontFamily: "'Jost', sans-serif",
        fontSize: 8, letterSpacing: '0.38em', textTransform: 'uppercase',
        color: T.parchment[50],
      }}>
        {cat.tag}
      </div>

      {/* Content */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 4, padding: 'clamp(24px, 3vw, 36px)' }}>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 9, fontWeight: 300,
          letterSpacing: '0.38em', textTransform: 'uppercase',
          color: `${T.gold[300]}cc`, marginBottom: 10,
        }}>
          {cat.subtitle}
        </p>
        <h3 style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: isLarge ? 'clamp(32px, 3vw, 48px)' : 'clamp(26px, 2.4vw, 36px)',
          fontWeight: 300, fontStyle: 'italic',
          color: T.parchment[50], lineHeight: 1.1,
          letterSpacing: '0.02em', marginBottom: 18,
        }}>
          {cat.label}
        </h3>
        <motion.div
          initial={{ width: 0 }}
          whileHover={{ width: '100%' }}
          transition={{ duration: 0.55, ease: SILK }}
          style={{ height: 1, background: `${T.gold[400]}99`, marginBottom: 16 }}
        />
        <span style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 8, fontWeight: 300,
          letterSpacing: '0.36em', textTransform: 'uppercase',
          color: `${T.parchment[100]}99`,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          Explore →
        </span>
      </div>

      {/* Corner ornament */}
      <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 3, pointerEvents: 'none' }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M24 0 L24 24" stroke={`${T.gold[400]}44`} strokeWidth="0.8" />
          <path d="M0 0 L24 0" stroke={`${T.gold[400]}44`} strokeWidth="0.8" />
        </svg>
      </div>
      <div style={{ position: 'absolute', bottom: 12, left: 12, zIndex: 3, pointerEvents: 'none' }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M0 24 L0 0" stroke={`${T.gold[400]}44`} strokeWidth="0.8" />
          <path d="M24 24 L0 24" stroke={`${T.gold[400]}44`} strokeWidth="0.8" />
        </svg>
      </div>
    </motion.div>
  );
}

export default function CollectionsGrid({ onNavigate }) {
  return (
    <section style={{ background: T.parchment[200], padding: 'clamp(80px, 10vh, 120px) 0' }}>
      {/* Section Header */}
      <div style={{ textAlign: 'center', marginBottom: 'clamp(48px, 6vh, 72px)', padding: '0 clamp(32px, 5vw, 80px)' }}>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 1.1, ease: SILK }}
          style={{
            fontFamily: "'Jost', sans-serif",
            fontSize: 9, fontWeight: 400,
            letterSpacing: '0.48em', textTransform: 'uppercase',
            color: T.gold[500], marginBottom: 20,
          }}
        >
          Curated for the Discerning Woman
        </motion.p>

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
          >
            The Collections
          </motion.h2>
        </div>

        <DiamondRule />
      </div>

      {/* Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gridTemplateRows: 'repeat(2, 1fr)',
        gap: 'clamp(10px, 1.5vw, 18px)',
        maxWidth: 1400, margin: '0 auto',
        padding: '0 clamp(24px, 4vw, 64px)',
        minHeight: 'clamp(480px, 64vw, 860px)',
      }}>
        {CATEGORIES.map((cat, i) => (
          <CategoryCard key={cat.id} cat={cat} index={i} onNavigate={onNavigate} />
        ))}
      </div>

      {/* CTA */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 1.1, ease: SILK, delay: 0.4 }}
        style={{ textAlign: 'center', marginTop: 'clamp(40px, 5vh, 60px)' }}
      >
        <button className="btn-primary" onClick={() => onNavigate('collections')}>
          View All Pieces
        </button>
      </motion.div>
    </section>
  );
}
