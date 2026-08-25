/* Quantive PWA Service Worker — offline fallback + cache */
const CACHE_NAME = 'quantive-v1';
const OFFLINE_URL = '/offline.html';
const PRECACHE = [
  '/',
  '/offline.html',
  '/manifest.json',
  '/favicon.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  // Only handle GET
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Bypass API & non-GET
  if (url.pathname.startsWith('/api')) {
    // network-first for API, no cache
    event.respondWith(fetch(req).catch(() => new Response(JSON.stringify({ detail: 'Offline' }), { status: 503, headers: { 'Content-Type': 'application/json' } })));
    return;
  }

  // For navigation requests: network-first, fallback to cache, then offline page
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(c => c.put(req, clone));
        return res;
      }).catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        const offline = await caches.match(OFFLINE_URL);
        return offline || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/html' } });
      })
    );
    return;
  }

  // For assets: cache-first, fallback to network
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        // cache successful opaque & ok responses for same-origin assets
        if (res.ok && url.origin === self.location.origin) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(req, clone));
        }
        return res;
      }).catch(() => cached || Response.error());
    })
  );
});
