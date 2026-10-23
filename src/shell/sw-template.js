/* Service worker for offline play (docs/PLAN.md step 3). The build fills in
 * VERSION and FILES (vite.config.ts). Every file is stored on the first
 * visit. A new version installs in the background and waits: it takes over
 * only when every window of the game has closed (the next cold launch),
 * never in the middle of play. */
const VERSION = '__VERSION__';
const FILES = __FILES__;
const CACHE = 'squishy-isle-web-' + VERSION;

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith('squishy-isle-web-') && k !== CACHE).map((k) => caches.delete(k)))),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const hit = await cache.match(req, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === 'navigate') {
        const page = await cache.match(new URL('./', self.registration.scope).href);
        if (page) return page;
      }
      return fetch(req);
    }),
  );
});
