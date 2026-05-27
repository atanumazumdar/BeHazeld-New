/* ─────────────────────────────────────────────────────────
   BeHAZEL'd Service Worker
   Strategy: Network-first with cache fallback
   ───────────────────────────────────────────────────────── */

const CACHE  = 'behazel-v1';
const STATIC = [
  '/',
  '/index.html',
  '/Logo.png',
  '/Logo2.png',
  '/favicon.svg',
  '/manifest.json',
];

/* Install — pre-cache shell assets */
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(STATIC))
      .then(() => self.skipWaiting())
  );
});

/* Activate — remove stale caches */
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

/* Fetch — network first, fall back to cache */
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;

  /* Skip chrome-extension and non-http requests */
  if (!e.request.url.startsWith('http')) return;

  e.respondWith(
    fetch(e.request)
      .then(response => {
        /* Cache successful responses */
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(e.request)
        .then(cached => cached || caches.match('/'))
      )
  );
});
