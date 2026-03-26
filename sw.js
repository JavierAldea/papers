/* TechVigilance v2 — Service Worker
   Strategy: cache-first with stale-while-revalidate for CSV/JSON data files.
   Non-GET requests pass through directly.
*/

const CACHE_NAME = 'techvigilance-v2';
const PRECACHE_URLS = [
  './index.html',
  './papers.csv',
  './pdfs/index.json',
  './manifest.json'
];

// ─── Install ─────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return Promise.allSettled(
        PRECACHE_URLS.map(url =>
          cache.add(url).catch(err => {
            console.warn('[SW] Pre-cache failed for', url, err);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ─── Activate ────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ─── Fetch ───────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Determine if this is a data file that benefits from stale-while-revalidate
  const isDataFile = url.pathname.endsWith('.csv') || url.pathname.endsWith('.json');

  if (isDataFile) {
    // Stale-while-revalidate: serve cached immediately, refresh cache in background
    event.respondWith(staleWhileRevalidate(event.request));
  } else {
    // Cache-first for all other GET requests
    event.respondWith(cacheFirst(event.request));
  }
});

/**
 * Cache-first strategy:
 * 1. Try cache first.
 * 2. If cache miss, fetch from network and cache the response.
 * 3. If network also fails, return whatever is in cache or a fallback error.
 */
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (err) {
    console.warn('[SW] Network failed, no cache for:', request.url, err);
    // Return a minimal offline response
    return new Response(
      '<html><body><p>Sin conexión. El recurso no está en caché.</p></body></html>',
      { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }
}

/**
 * Stale-while-revalidate strategy:
 * 1. Serve cached response immediately (if available).
 * 2. In background, fetch fresh copy and update cache.
 * 3. If no cache and network fails, return error response.
 */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  // Kick off background refresh regardless
  const networkPromise = fetch(request).then(networkResponse => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(err => {
    console.warn('[SW] Background refresh failed for:', request.url, err);
    return null;
  });

  if (cached) {
    // Return stale immediately, update in background
    return cached;
  }

  // No cache — wait for network
  try {
    const fresh = await networkPromise;
    if (fresh) return fresh;
    throw new Error('No network response');
  } catch (err) {
    return new Response(
      JSON.stringify({ error: 'Offline and no cache available' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
