import { useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const T = {
  gold:      { 300: '#DFBF6A', 400: '#D4A83A', 500: '#C09330' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614', 600: '#3D1E0F' },
  bark:      { 300: '#B19870', 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF' },
};
const SILK = [0.76, 0, 0.24, 1];

const NAV_LINKS = {
  'Collections': ['Bridal', 'Evening Wear', 'Essentials', 'Lookbook'],
  'Atelier':     ['Our Story', 'Craft Process', 'Appointments', 'Press'],
  'Support':     ['Sizing Guide', 'Shipping & Returns', 'Care Instructions', 'Contact'],
};

function HazelLeafSmall() {
  return (
    <svg width="18" height="28" viewBox="0 0 18 28" fill="none">
      <path d="M9 26 C9 26 1 18 1 12 C1 6 4.5 1 9 1 C13.5 1 17 6 17 12 C17 18 9 26 9 26Z" stroke={T.gold[500]} strokeWidth="0.8" fill="none" />
      <line x1="9" y1="1" x2="9" y2="26" stroke={T.gold[500]} strokeWidth="0.7" />
      <line x1="9" y1="9" x2="5" y2="14" stroke={T.gold[500]} strokeWidth="0.6" />
      <line x1="9" y1="14" x2="13" y2="19" stroke={T.gold[500]} strokeWidth="0.6" />
    </svg>
  );
}

export default function SiteFooter() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email.trim()) {
      setSubmitted(true);
    }
  };

  return (
    <footer style={{ background: T.hazel[500] }}>
      {/* Newsletter Band */}
      <div
        ref={ref}
        style={{
          borderBottom: `1px solid ${T.gold[500]}22`,
          padding: 'clamp(56px, 8vh, 80px) clamp(32px, 6vw, 80px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 40,
          flexWrap: 'wrap',
        }}
      >
        {/* Left copy */}
        <div style={{ maxWidth: 400 }}>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 1.0, ease: SILK }}
            style={{
              fontFamily: "'Jost', sans-serif",
              fontSize: 9, fontWeight: 400,
              letterSpacing: '0.46em', textTransform: 'uppercase',
              color: T.gold[400], marginBottom: 14,
            }}
          >The Hazel Letter</motion.p>
          <motion.h3
            initial={{ opacity: 0, y: 14 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 1.1, ease: SILK, delay: 0.15 }}
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: 'clamp(22px, 2.5vw, 34px)',
              fontWeight: 300, fontStyle: 'italic',
              color: T.parchment[100], lineHeight: 1.2,
              letterSpacing: '0.02em', marginBottom: 12,
            }}
          >Wear the story before anyone else does</motion.h3>
          <motion.p
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 1.0, delay: 0.3 }}
            style={{
              fontFamily: "'Jost', sans-serif",
              fontSize: 12, fontWeight: 300,
              color: `${T.bark[300]}aa`, lineHeight: 1.8,
              letterSpacing: '0.02em',
            }}
          >
            New arrivals, private previews, and the stories behind each piece — delivered to your inbox.
          </motion.p>
        </div>

        {/* Right: form */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 1.1, ease: SILK, delay: 0.35 }}
          style={{ minWidth: 300, flex: 1, maxWidth: 440 }}
        >
          {submitted ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ textAlign: 'center', padding: '32px 0' }}
            >
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
                <HazelLeafSmall />
              </div>
              <p style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: 20, fontStyle: 'italic', fontWeight: 300,
                color: T.parchment[100], marginBottom: 8,
              }}>Welcome to the Atelier</p>
              <p style={{
                fontFamily: "'Jost', sans-serif",
                fontSize: 11, fontWeight: 300,
                color: `${T.bark[300]}99`, letterSpacing: '0.04em',
              }}>Your first letter is on its way.</p>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'flex', gap: 0 }}>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  aria-label="Email address for newsletter"
                  style={{
                    flex: 1, padding: '14px 18px',
                    background: `${T.parchment[200]}18`,
                    border: `1px solid ${T.gold[500]}44`,
                    borderRight: 'none',
                    color: T.parchment[100],
                    fontFamily: "'Jost', sans-serif",
                    fontSize: 12, fontWeight: 300,
                    letterSpacing: '0.04em',
                    outline: 'none',
                    transition: 'border-color 0.3s',
                  }}
                  onFocus={e => e.target.style.borderColor = `${T.gold[500]}88`}
                  onBlur={e => e.target.style.borderColor = `${T.gold[500]}44`}
                />
                <button
                  type="submit"
                  style={{
                    padding: '14px 22px', flexShrink: 0,
                    background: T.gold[500], border: `1px solid ${T.gold[500]}`,
                    cursor: 'pointer',
                    fontFamily: "'Jost', sans-serif",
                    fontSize: 9, fontWeight: 400,
                    letterSpacing: '0.28em', textTransform: 'uppercase',
                    color: T.parchment[50],
                    transition: 'background 0.4s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = T.hazel[400]}
                  onMouseLeave={e => e.currentTarget.style.background = T.gold[500]}
                >Join</button>
              </div>
              <p style={{
                fontFamily: "'Jost', sans-serif",
                fontSize: 10, fontWeight: 300,
                color: `${T.bark[300]}66`, letterSpacing: '0.04em',
                marginTop: 10,
              }}>No spam. Unsubscribe anytime.</p>
            </form>
          )}
        </motion.div>
      </div>

      {/* Main footer grid */}
      <div style={{
        padding: 'clamp(48px, 7vh, 72px) clamp(32px, 6vw, 80px) clamp(32px, 5vh, 48px)',
        display: 'grid',
        gridTemplateColumns: '2fr repeat(3, 1fr)',
        gap: 'clamp(32px, 4vw, 64px)',
        maxWidth: 1400, margin: '0 auto',
      }}>
        {/* Brand column */}
        <div>
          <div style={{ marginBottom: 20 }}>
            <img src="/Logo.png" alt="BeHAZEL'd" style={{ height: 72, width: 'auto', display: 'block', filter: 'brightness(0) invert(1) sepia(1) saturate(0.4) brightness(0.85)' }} />
          </div>
          <p style={{
            fontFamily: "'Jost', sans-serif",
            fontSize: 12, fontWeight: 300,
            color: `${T.bark[300]}99`, lineHeight: 1.9,
            letterSpacing: '0.02em', maxWidth: 240, marginBottom: 28,
          }}>
            Ethnic luxury couture. Handcrafted in India. Designed for the woman who knows herself.
          </p>

          {/* Social links */}
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            {[
              { label: 'Instagram', path: 'M16 11.37A4 4 0 1112.63 8 4 4 0 0116 11.37zm1.5-4.87h.01M7.5 21H4a1 1 0 01-1-1V4a1 1 0 011-1h16a1 1 0 011 1v16a1 1 0 01-1 1h-3.5' },
              { label: 'Pinterest', path: 'M12 2C6.48 2 2 6.48 2 12c0 4.24 2.65 7.86 6.39 9.29-.09-.78-.17-1.98.03-2.83.19-.76 1.26-5.33 1.26-5.33s-.32-.65-.32-1.6c0-1.5.87-2.62 1.95-2.62.92 0 1.36.69 1.36 1.52 0 .93-.59 2.31-.9 3.6-.26 1.08.54 1.96 1.6 1.96 1.92 0 3.4-2.02 3.4-4.94 0-2.59-1.86-4.4-4.51-4.4-3.07 0-4.87 2.3-4.87 4.68 0 .93.36 1.92.8 2.46a.32.32 0 01.07.31c-.08.33-.26 1.08-.3 1.23-.05.2-.16.24-.38.15-1.42-.66-2.3-2.75-2.3-4.42 0-3.6 2.61-6.9 7.53-6.9 3.95 0 7.02 2.82 7.02 6.57 0 3.92-2.47 7.08-5.9 7.08-1.15 0-2.23-.6-2.6-1.3l-.71 2.64c-.26.98-.95 2.21-1.41 2.96.06.02.13.03.2.04.51.08 1.03.12 1.56.12z' },
              { label: 'WhatsApp', path: 'M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z M12 2a10 10 0 100 20A10 10 0 0012 2z' },
            ].map(({ label, path }) => (
              <button
                key={label}
                aria-label={label}
                style={{
                  background: 'none',
                  border: `1px solid ${T.gold[500]}33`,
                  cursor: 'pointer', padding: 8,
                  color: `${T.bark[300]}99`,
                  transition: 'border-color 0.3s, color 0.3s',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = T.gold[500]; e.currentTarget.style.color = T.gold[400]; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = `${T.gold[500]}33`; e.currentTarget.style.color = `${T.bark[300]}99`; }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d={path} />
                </svg>
              </button>
            ))}
          </div>
        </div>

        {/* Nav columns */}
        {Object.entries(NAV_LINKS).map(([section, links]) => (
          <div key={section}>
            <p style={{
              fontFamily: "'Jost', sans-serif",
              fontSize: 9, fontWeight: 400,
              letterSpacing: '0.4em', textTransform: 'uppercase',
              color: T.gold[500], marginBottom: 20,
            }}>{section}</p>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 13 }}>
              {links.map(link => (
                <li key={link}>
                  <button
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                      fontFamily: "'Jost', sans-serif",
                      fontSize: 12, fontWeight: 300,
                      letterSpacing: '0.04em',
                      color: `${T.bark[300]}99`,
                      transition: 'color 0.3s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = T.parchment[100]}
                    onMouseLeave={e => e.currentTarget.style.color = `${T.bark[300]}99`}
                  >{link}</button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Bottom bar */}
      <div style={{
        borderTop: `1px solid ${T.gold[500]}18`,
        padding: 'clamp(20px, 3vh, 28px) clamp(32px, 6vw, 80px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        maxWidth: 1400, margin: '0 auto',
      }}>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 10, fontWeight: 300,
          color: `${T.bark[300]}55`, letterSpacing: '0.04em',
        }}>© 2026 BeHAZEL'd. All rights reserved. Made in India.</p>
        <p style={{
          fontFamily: "'Cormorant Garamond', Georgia, serif",
          fontSize: 16, fontStyle: 'italic', fontWeight: 400,
          color: `${T.gold[500]}88`, letterSpacing: '0.06em',
        }}>be you, with HAZEL.</p>
      </div>
    </footer>
  );
}
