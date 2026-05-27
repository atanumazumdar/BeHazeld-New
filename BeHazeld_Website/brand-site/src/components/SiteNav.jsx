import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const GLASS_NAV = {
  background: 'rgba(18, 10, 5, 0.82)',
  backdropFilter: 'blur(22px)',
  WebkitBackdropFilter: 'blur(22px)',
  borderBottom: '1px solid rgba(192, 147, 48, 0.16)',
};

const SILK = [0.76, 0, 0.24, 1];

export default function SiteNav({ cartCount = 0, onOpenCart }) {
  const location  = useLocation();
  const [open, setOpen] = useState(false);
  const isActive  = (path) => location.pathname === path;

  const links = [
    { label: 'Home',     path: '/'            },
    { label: 'Shop',     path: '/collections' },
    { label: 'Featured', path: '/featured'    },
    { label: 'Atelier',  path: '/atelier'     },
    { label: 'Story',    path: '/story'       },
  ];

  const closeMenu = () => setOpen(false);
  const openCart = () => {
    closeMenu();
    onOpenCart?.();
  };

  return (
    <>
      <motion.nav
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.0, ease: SILK, delay: 0.1 }}
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 md:px-14 lg:px-20"
        style={{ ...GLASS_NAV, height: 64, minHeight: 64 }}
      >
        {/* Logo */}
        <Link to="/" onClick={closeMenu} className="flex-shrink-0 leading-none" aria-label="Home">
          <img src="/Logo.png" alt="BeHAZEL'd" className="block" style={{ height: 42, width: 'auto' }} />
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-7 lg:gap-10">
          {links.map(({ label, path }) => (
            <Link
              key={path} to={path}
              className="relative font-sans font-light uppercase"
              style={{
                fontSize: 10, letterSpacing: '0.36em',
                color: isActive(path) ? '#C09330' : 'rgba(248,240,232,0.65)',
                transition: 'color 0.3s ease',
              }}
              onMouseEnter={e => { if (!isActive(path)) e.currentTarget.style.color = 'rgba(248,240,232,0.95)'; }}
              onMouseLeave={e => { if (!isActive(path)) e.currentTarget.style.color = 'rgba(248,240,232,0.65)'; }}
            >
              {label}
              {isActive(path) && (
                <motion.div layoutId="nav-active" className="absolute -bottom-1 left-0 right-0 h-px"
                  style={{ background: '#C09330' }}
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }} />
              )}
            </Link>
          ))}
        </div>

        {/* Desktop bag */}
        <button
          type="button"
          onClick={openCart}
          aria-label={`Open bag${cartCount > 0 ? `, ${cartCount} items` : ''}`}
          className="hidden md:flex items-center justify-center relative cursor-pointer"
          style={{ width: 36, height: 36, background: 'none', border: 'none', color: 'rgba(248,240,232,0.72)' }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <path d="M16 10a4 4 0 01-8 0" />
          </svg>
          {cartCount > 0 && (
            <span
              className="absolute"
              style={{
                top: 2,
                right: 1,
                minWidth: 15,
                height: 15,
                borderRadius: 999,
                background: '#C09330',
                color: '#FDFCF9',
                fontFamily: "'Jost', sans-serif",
                fontSize: 8,
                lineHeight: '15px',
                textAlign: 'center',
              }}
            >
              {cartCount}
            </span>
          )}
        </button>

        {/* Mobile hamburger */}
        <button
          onClick={() => setOpen(o => !o)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          className="md:hidden flex flex-col justify-center items-center gap-[5px] p-2 cursor-pointer"
          style={{ background: 'none', border: 'none', width: 44, height: 44 }}
        >
          <motion.span animate={{ rotate: open ? 45 : 0, y: open ? 7 : 0 }}
            transition={{ duration: 0.3 }}
            className="block h-px w-6"
            style={{ background: open ? '#C09330' : 'rgba(248,240,232,0.8)', transformOrigin: 'center' }} />
          <motion.span animate={{ opacity: open ? 0 : 1, scaleX: open ? 0 : 1 }}
            transition={{ duration: 0.2 }}
            className="block h-px w-6"
            style={{ background: 'rgba(248,240,232,0.8)' }} />
          <motion.span animate={{ rotate: open ? -45 : 0, y: open ? -7 : 0 }}
            transition={{ duration: 0.3 }}
            className="block h-px w-6"
            style={{ background: open ? '#C09330' : 'rgba(248,240,232,0.8)', transformOrigin: 'center' }} />
        </button>
      </motion.nav>

      {/* Mobile slide-down menu */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={closeMenu}
              className="fixed inset-0 z-40 md:hidden"
              style={{ background: 'rgba(10, 4, 1, 0.7)', backdropFilter: 'blur(4px)' }}
            />

            {/* Menu panel */}
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3, ease: SILK }}
              className="fixed left-0 right-0 z-50 md:hidden flex flex-col"
              style={{
                top: 64,
                background: 'rgba(18, 10, 5, 0.97)',
                backdropFilter: 'blur(24px)',
                borderBottom: '1px solid rgba(192,147,48,0.18)',
                boxShadow: '0 16px 40px rgba(0,0,0,0.5)',
              }}
            >
              {links.map(({ label, path }, i) => (
                <motion.div
                  key={path}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.08 * i, duration: 0.28 }}
                >
                  <Link
                    to={path} onClick={closeMenu}
                    className="flex items-center justify-between px-7 py-5 font-sans font-light uppercase"
                    style={{
                      fontSize: 11, letterSpacing: '0.38em',
                      color: isActive(path) ? '#C09330' : 'rgba(248,240,232,0.75)',
                      borderBottom: '1px solid rgba(192,147,48,0.08)',
                      minHeight: 64,
                    }}
                  >
                    {label}
                    {isActive(path) && (
                      <span style={{ color: '#C09330', fontSize: 14 }}>→</span>
                    )}
                  </Link>
                </motion.div>
              ))}

              <button
                type="button"
                onClick={openCart}
                className="flex items-center justify-between px-7 py-5 font-sans font-light uppercase"
                style={{
                  fontSize: 11,
                  letterSpacing: '0.38em',
                  color: 'rgba(248,240,232,0.75)',
                  background: 'none',
                  border: 'none',
                  borderBottom: '1px solid rgba(192,147,48,0.08)',
                  minHeight: 64,
                  textAlign: 'left',
                }}
              >
                Bag
                <span style={{ color: '#C09330', fontSize: 12 }}>{cartCount}</span>
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
