import { useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import './index.css';

import WatermarkBg  from './components/WatermarkBg';
import SiteNav      from './components/SiteNav';
import HeroSection  from './components/HeroSection';
import CollectionsGrid from './components/CollectionsGrid';
import ProductShowcase from './components/ProductShowcase';
import AboutSection from './components/AboutSection';
import CollectionsPage from './components/CollectionsPage';
import SlideCart from './components/SlideCart';
import SiteFooter from './components/SiteFooter';
import OurStory     from './pages/OurStory';
import TheAtelier   from './pages/TheAtelier';

const ROUTES = {
  home: '/',
  collections: '/collections',
  featured: '/featured',
  atelier: '/atelier',
  story: '/story',
};

function HomePage({ onAddToCart }) {
  const navigate = useNavigate();
  const goTo = (page) => navigate(ROUTES[page] || '/');

  return (
    <>
      <HeroSection onNavigate={goTo} />
      <CollectionsGrid onNavigate={goTo} />
      <ProductShowcase onAddToCart={onAddToCart} />
      <AboutSection />
    </>
  );
}

function AppRoutes({ onAddToCart }) {
  const location = useLocation();

  return (
    <Routes location={location}>
      <Route path="/"            element={<HomePage onAddToCart={onAddToCart} />} />
      <Route path="/collections" element={<CollectionsPage onAddToCart={onAddToCart} />} />
      <Route path="/featured"    element={<ProductShowcase onAddToCart={onAddToCart} />} />
      <Route path="/atelier"     element={<TheAtelier />} />
      <Route path="/story"       element={<OurStory />} />
      <Route path="*"            element={<HomePage onAddToCart={onAddToCart} />} />
    </Routes>
  );
}

export default function App() {
  const [cartOpen, setCartOpen] = useState(false);
  const [cartItems, setCartItems] = useState([]);

  const addToCart = (product) => {
    setCartItems((items) => {
      const existing = items.find((item) => item.id === product.id);

      if (existing) {
        return items.map((item) =>
          item.id === product.id ? { ...item, qty: item.qty + 1 } : item
        );
      }

      return [...items, { ...product, qty: 1 }];
    });
    setCartOpen(true);
  };

  const removeFromCart = (id) => {
    setCartItems((items) => items.filter((item) => item.id !== id));
  };

  const updateQty = (id, qty) => {
    if (qty < 1) {
      removeFromCart(id);
      return;
    }

    setCartItems((items) =>
      items.map((item) => item.id === id ? { ...item, qty } : item)
    );
  };

  const cartCount = cartItems.reduce((sum, item) => sum + item.qty, 0);

  return (
    <BrowserRouter>
      <WatermarkBg />
      <SiteNav cartCount={cartCount} onOpenCart={() => setCartOpen(true)} />
      <div className="relative z-10">
        <AppRoutes onAddToCart={addToCart} />
        <SiteFooter />
      </div>
      <SlideCart
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        items={cartItems}
        onRemove={removeFromCart}
        onQty={updateQty}
      />
    </BrowserRouter>
  );
}
