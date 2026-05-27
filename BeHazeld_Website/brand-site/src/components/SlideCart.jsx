import { motion, AnimatePresence } from 'framer-motion';

const T = {
  gold:      { 300: '#DFBF6A', 500: '#C09330' },
  hazel:     { 400: '#7A4A28', 500: '#4B2614' },
  bark:      { 300: '#B19870', 500: '#7D5A30' },
  parchment: { 50: '#FDFCF9', 100: '#F8F4EC', 200: '#EEE9DF' },
};
const SILK = [0.76, 0, 0.24, 1];

function CartItem({ item, onRemove, onQty }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.45, ease: SILK }}
      style={{
        display: 'flex', gap: 16, paddingBottom: 24,
        borderBottom: `1px solid ${T.gold[500]}22`,
        marginBottom: 24,
      }}
    >
      {/* Swatch / thumbnail */}
      <div style={{
        width: 72, height: 90, flexShrink: 0,
        background: item.gradient,
        position: 'relative', overflow: 'hidden',
      }}>
        <span style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 36, fontStyle: 'italic', fontWeight: 300,
          color: 'rgba(255,255,255,0.12)',
          userSelect: 'none',
        }}>H</span>
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 8, fontWeight: 400, letterSpacing: '0.32em',
          textTransform: 'uppercase', color: T.gold[500], marginBottom: 5,
        }}>{item.category}</p>
        <p style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 16, fontWeight: 400, fontStyle: 'italic',
          color: T.hazel[500], lineHeight: 1.25, marginBottom: 8,
        }}>{item.name}</p>
        <p style={{
          fontFamily: "'Jost', sans-serif",
          fontSize: 12, fontWeight: 300, color: T.bark[500], marginBottom: 12,
        }}>{item.price}</p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Qty stepper */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, border: `1px solid ${T.gold[500]}44` }}>
            <button
              onClick={() => onQty(item.id, item.qty - 1)}
              style={{
                width: 28, height: 28, background: 'none', border: 'none',
                cursor: 'pointer', color: T.bark[500],
                fontFamily: "'Jost', sans-serif", fontSize: 14, fontWeight: 300,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'color 0.25s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = T.gold[500]}
              onMouseLeave={e => e.currentTarget.style.color = T.bark[500]}
            >−</button>
            <span style={{
              width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: "'Jost', sans-serif", fontSize: 11, fontWeight: 300,
              color: T.hazel[500], borderLeft: `1px solid ${T.gold[500]}44`, borderRight: `1px solid ${T.gold[500]}44`,
            }}>{item.qty}</span>
            <button
              onClick={() => onQty(item.id, item.qty + 1)}
              style={{
                width: 28, height: 28, background: 'none', border: 'none',
                cursor: 'pointer', color: T.bark[500],
                fontFamily: "'Jost', sans-serif", fontSize: 14, fontWeight: 300,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'color 0.25s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = T.gold[500]}
              onMouseLeave={e => e.currentTarget.style.color = T.bark[500]}
            >+</button>
          </div>

          {/* Remove */}
          <button
            onClick={() => onRemove(item.id)}
            aria-label="Remove item"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: T.bark[300], padding: 4,
              transition: 'color 0.25s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = T.hazel[500]}
            onMouseLeave={e => e.currentTarget.style.color = T.bark[300]}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>
    </motion.div>
  );
}

export default function SlideCart({ open, onClose, items, onRemove, onQty }) {
  const total = items.reduce((sum, item) => {
    const num = parseInt(item.price.replace(/[^\d]/g, ''), 10);
    return sum + num * item.qty;
  }, 0);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 200,
              background: 'rgba(24,10,4,0.5)',
              backdropFilter: 'blur(2px)',
            }}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.6, ease: SILK }}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0,
              width: 'min(420px, 92vw)',
              zIndex: 201,
              background: T.parchment[100],
              display: 'flex', flexDirection: 'column',
              boxShadow: '-20px 0 60px rgba(24,10,4,0.18)',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '28px 32px 24px',
              borderBottom: `1px solid ${T.gold[500]}22`,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              flexShrink: 0,
            }}>
              <div>
                <p style={{
                  fontFamily: "'Jost', sans-serif",
                  fontSize: 8, fontWeight: 400,
                  letterSpacing: '0.42em', textTransform: 'uppercase',
                  color: T.gold[500], marginBottom: 4,
                }}>Your Selection</p>
                <h2 style={{
                  fontFamily: "'Cormorant Garamond', serif",
                  fontSize: 24, fontWeight: 400, fontStyle: 'italic',
                  color: T.hazel[500],
                }}>The Atelier Bag</h2>
              </div>
              <button
                onClick={onClose}
                aria-label="Close cart"
                style={{
                  background: 'none', border: `1px solid ${T.gold[500]}44`,
                  cursor: 'pointer', padding: 10,
                  color: T.hazel[400], transition: 'border-color 0.3s, color 0.3s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = T.gold[500]; e.currentTarget.style.color = T.gold[500]; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = `${T.gold[500]}44`; e.currentTarget.style.color = T.hazel[400]; }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {/* Items */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
              {items.length === 0 ? (
                <div style={{ textAlign: 'center', paddingTop: 80 }}>
                  <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke={T.bark[300]} strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 20px', display: 'block' }}>
                    <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <path d="M16 10a4 4 0 01-8 0" />
                  </svg>
                  <p style={{
                    fontFamily: "'Cormorant Garamond', serif",
                    fontSize: 20, fontStyle: 'italic', fontWeight: 300,
                    color: T.bark[300], marginBottom: 8,
                  }}>Your bag is empty</p>
                  <p style={{
                    fontFamily: "'Jost', sans-serif",
                    fontSize: 11, fontWeight: 300, letterSpacing: '0.04em',
                    color: T.bark[300],
                  }}>Discover our curated collections</p>
                </div>
              ) : (
                <AnimatePresence mode="popLayout">
                  {items.map(item => (
                    <CartItem key={item.id} item={item} onRemove={onRemove} onQty={onQty} />
                  ))}
                </AnimatePresence>
              )}
            </div>

            {/* Footer */}
            {items.length > 0 && (
              <div style={{
                padding: '24px 32px 32px',
                borderTop: `1px solid ${T.gold[500]}22`,
                flexShrink: 0,
              }}>
                {/* Subtotal */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
                  <span style={{
                    fontFamily: "'Jost', sans-serif", fontSize: 9,
                    letterSpacing: '0.3em', textTransform: 'uppercase', color: T.bark[500],
                  }}>Subtotal</span>
                  <span style={{
                    fontFamily: "'Cormorant Garamond', serif",
                    fontSize: 22, fontWeight: 400, color: T.hazel[500],
                  }}>₹{total.toLocaleString('en-IN')}</span>
                </div>

                <p style={{
                  fontFamily: "'Jost', sans-serif", fontSize: 10, fontWeight: 300,
                  letterSpacing: '0.04em', color: T.bark[300],
                  textAlign: 'center', marginBottom: 20,
                }}>
                  Made to order · 4–6 weeks delivery · Free shipping
                </p>

                <button className="btn-primary" style={{ width: '100%', textAlign: 'center', display: 'block', padding: '16px 0' }}>
                  Proceed to Checkout
                </button>

                <button
                  onClick={onClose}
                  className="btn-ghost"
                  style={{ width: '100%', justifyContent: 'center', marginTop: 14, fontSize: 9 }}
                >
                  Continue Shopping
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
