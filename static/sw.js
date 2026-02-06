/**
 * Social Contract — Service Worker
 * Cache-first for static assets, network-first for pages/API
 */

const CACHE_VERSION = '__SW_VERSION__';
const STATIC_CACHE = CACHE_VERSION + '-static';
const PAGES_CACHE = CACHE_VERSION + '-pages';

// Static assets to pre-cache on install
const PRECACHE_ASSETS = [
    '/static/style.css',
    '/static/script.js',
    '/static/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/offline'
];

// ========================
// INSTALL — Pre-cache shell
// ========================
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(STATIC_CACHE).then(function(cache) {
            return cache.addAll(PRECACHE_ASSETS);
        }).then(function() {
            return self.skipWaiting();
        })
    );
});

// ========================
// ACTIVATE — Clean old caches
// ========================
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames
                    .filter(function(name) {
                        return name.startsWith('sc-') && name !== STATIC_CACHE && name !== PAGES_CACHE;
                    })
                    .map(function(name) {
                        return caches.delete(name);
                    })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

// ========================
// Helper: Check if truly offline
// ========================
function isOffline() {
    return !navigator.onLine;
}

// ========================
// FETCH — Strategy router
// ========================
self.addEventListener('fetch', function(event) {
    var request = event.request;
    var url = new URL(request.url);

    // Only handle same-origin requests
    if (url.origin !== location.origin) return;

    // Skip non-GET requests (POST check-ins, etc.)
    if (request.method !== 'GET') return;

    // API calls — network only (no caching)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request).catch(function() {
                return new Response(JSON.stringify({ error: 'You are offline' }), {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Static assets — cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then(function(cached) {
                if (cached) {
                    // Return cache, but update in background
                    fetch(request).then(function(response) {
                        if (response.ok) {
                            caches.open(STATIC_CACHE).then(function(cache) {
                                cache.put(request, response);
                            });
                        }
                    }).catch(function() {});

                    return cached;
                }

                // Not in cache — fetch and cache
                return fetch(request).then(function(response) {
                    if (response.ok) {
                        var responseClone = response.clone();
                        caches.open(STATIC_CACHE).then(function(cache) {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                });
            })
        );
        return;
    }

    // HTML pages — network-first with offline fallback
    if (request.headers.get('Accept') && request.headers.get('Accept').includes('text/html')) {
        event.respondWith(
            fetch(request).then(function(response) {
                // Cache successful page loads
                if (response.ok) {
                    var responseClone = response.clone();
                    caches.open(PAGES_CACHE).then(function(cache) {
                        cache.put(request, responseClone);
                    });
                }
                return response;
            }).catch(function(error) {
                // ONLY show offline page if we're actually offline
                // Otherwise, let the error propagate so the user sees the real error
                if (!navigator.onLine) {
                    return caches.match(request).then(function(cached) {
                        if (cached) return cached;
                        return caches.match('/offline');
                    });
                }
                // If we're online but fetch failed, throw to show browser error
                throw error;
            })
        );
        return;
    }
});
