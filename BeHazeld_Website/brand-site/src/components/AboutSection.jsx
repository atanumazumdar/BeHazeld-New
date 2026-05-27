import { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

const T = {
  gold:      { 300: '#DFBF6A', 400: '#D4A83A', 500: '#C09330' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614', 600: '#3D1E0F' },
  bark:      { 300: '#B19870', 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF', 300: '#E2DAC9' },
};
const SILK = [0.76, 0, 0.24, 1];

const PILLARS = [
  { label: 'Handcrafted', description: 'Every stitch placed by artisan hands — never machine-finished.' },
  { label: 'Botanical', description: 'Design language drawn from the hazel tree — its leaf, berry, and branch.' },
  { label: 'Bespoke', description: 'Made to your exact silhouette. No two pieces are identical.' },
];

export default function AboutSection() {
  const sectionRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] });
  const imgY = useTransform(scrollYProgress, [0, 1], ['-6%', '6%']);

  return (
    <section
      ref={sectionRef}
      style={{ background: T.hazel[600], overflow: 'hidden', position: 'relative' }}
    >
      {/* Decorative letter watermark */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        fontFamily: "'Cormorant Garamond', serif",
        fontSize: 'clamp(300px, 40vw, 500px)', fontStyle: 'italic', fontWeight: 300,
        color: `${T.hazel[500]}55`,
        pointerEvents: 'none', userSelect: 'none',
        lineHeight: 1, zIndex: 0,
      }}>H</div>

      <div style={{
        position: 'relative', zIndex: 1,
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        maxWidth: 1400, margin: '0 auto',
        minHeight: 'clamp(520px, 70vh, 820px)',
      }}>
        {/* Left: Image with parallax */}
        <div style={{ position: 'relative', overflow: 'hidden' }}>
          <motion.div style={{ position: 'absolute', inset: '-10%', y: imgY }}>
            <img
              src="https://images.unsplash.com/photo-1583391733956-6c78276477e2?auto=format&fit=crop&w=900&q=80"
              alt="BeHazel'd artisan at work"
              style={{ width: '100%', height: '120%', objectFit: 'cover', objectPosition: 'center top', filter: 'sepia(0.2) brightness(0.6)' }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <div style={{
              position: 'absolute', inset: 0, zIndex: -1,
              background: `linear-gradient(148deg, ${T.hazel[600]} 0%, ${T.hazel[500]} 55%, ${T.bark[500]} 100%)`,
            }} />
          </motion.div>

          <div style={{
            position: 'absolute', inset: 0,
            background: `linear-gradient(to right, transparent 60%, ${T.hazel[600]} 100%)`,
          }} />

          {/* Pull quote */}
          <div style={{
            position: 'absolute', bottom: 'clamp(32px, 5vh, 56px)', left: 'clamp(32px, 4vw, 56px)',
            maxWidth: 260,
          }}>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 1.2, ease: SILK, delay: 0.4 }}
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: 'clamp(18px, 2.2vw, 26px)',
                fontStyle: 'italic', fontWeight: 300,
                color: T.parchment[100], lineHeight: 1.45,
                letterSpacing: '0.02em',
              }}
            >
              "Clothing is not a costume.<br />It is a declaration of self."
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1.0, delay: 0.7 }}
              style={{
                fontFamily: "'Jost', sans-serif",
                fontSize: 9, fontWeight: 300,
                letterSpacing: '0.38em', textTransform: 'uppercase',
                color: T.gold[300], marginTop: 14,
              }}
            >— Hazel, Founder</motion.p>
          </div>
        </div>

        {/* Right: Story content */}
        <div style={{
          padding: 'clamp(56px, 8vh, 96px) clamp(40px, 6vw, 88px)',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
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
              color: T.gold[500], marginBottom: 20,
            }}
          >Our Story</motion.p>

          <div style={{ overflow: 'hidden', marginBottom: 24 }}>
            <motion.h2
              initial={{ y: '110%' }}
              whileInView={{ y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 1.3, ease: SILK, delay: 0.2 }}
              style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: 'clamp(32px, 3.5vw, 54px)',
                fontWeight: 300, fontStyle: 'italic',
                color: T.parchment[100], lineHeight: 1.1,
                letterSpacing: '0.02em',
              }}
            >
              be you,<br />
              <span style={{ color: T.gold[300] }}>with HAZEL.</span>
            </motion.h2>
          </div>

          <motion.div
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1.1, ease: SILK, delay: 0.4 }}
            style={{ height: 1, background: `${T.gold[500]}55`, marginBottom: 28, transformOrigin: 'left' }}
          />

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1.1, ease: SILK, delay: 0.45 }}
            style={{
              fontFamily: "'Jost', sans-serif",
              fontSize: 13, fontWeight: 300,
              color: `${T.parchment[300]}cc`, lineHeight: 1.95,
              letterSpacing: '0.02em', marginBottom: 18,
            }}
          >
            BeHAZEL'd was born from one belief: that every woman deserves to wear something that feels as singular as she is. We reject mass production. We reject the ordinary.
          </motion.p>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1.1, ease: SILK, delay: 0.6 }}
            style={{
              fontFamily: "'Jost', sans-serif",
              fontSize: 13, fontWeight: 300,
              color: `${T.parchment[300]}99`, lineHeight: 1.95,
              letterSpacing: '0.02em', marginBottom: 36,
            }}
          >
            Each silhouette is a collaboration — between you and the artisans who hand-embroider every motif, weave every thread, and press every pleat with intention. This is not fashion. This is heritage, worn forward.
          </motion.p>

          {/* Pillars */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {PILLARS.map((pillar, i) => (
              <motion.div
                key={pillar.label}
                initial={{ opacity: 0, x: -16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 1.0, ease: SILK, delay: 0.75 + i * 0.14 }}
                style={{
                  display: 'flex', gap: 16, alignItems: 'flex-start',
                  paddingBlock: 16,
                  borderBottom: i < PILLARS.length - 1 ? `1px solid ${T.gold[500]}18` : 'none',
                }}
              >
                <span style={{ color: T.gold[500], fontSize: 8, marginTop: 4, flexShrink: 0 }}>✦</span>
                <div>
                  <p style={{
                    fontFamily: "'Jost', sans-serif",
                    fontSize: 9, fontWeight: 400,
                    letterSpacing: '0.36em', textTransform: 'uppercase',
                    color: T.gold[400], marginBottom: 5,
                  }}>{pillar.label}</p>
                  <p style={{
                    fontFamily: "'Jost', sans-serif",
                    fontSize: 12, fontWeight: 300,
                    color: `${T.parchment[300]}99`, lineHeight: 1.7,
                    letterSpacing: '0.02em',
                  }}>{pillar.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
