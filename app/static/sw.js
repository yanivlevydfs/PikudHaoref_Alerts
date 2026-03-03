const CACHE_NAME = 'pikud-haoref-cache-v15';
const ASSETS_TO_CACHE = [
  '/',
  '/static/style.css?v=15',
  '/static/script.js?v=15',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;600&display=swap',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://code.jquery.com/jquery-3.7.1.min.js',
  'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
  'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js'
];

self.addEventListener('install', (event) => {
  self.skipWaiting(); // Force the new service worker to activate immediately
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('PWA: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim()) // Take control of all open pages immediately
  );
});

self.addEventListener('fetch', (event) => {
  // Ignore non-GET requests inside the service worker
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    // Network-first strategy for our own files to ensure updates
    fetch(event.request)
      .then((networkResponse) => {
        // Just return the fresh response
        return networkResponse;
      })
      .catch(() => {
        // If network fails (offline), try the cache
        return caches.match(event.request);
      })
  );
});
