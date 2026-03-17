// Service Worker for Twiiter PWA
// Strategy: cache-first for static assets, network-first for API calls

var CACHE_NAME = 'twiiter-v1';
var STATIC_ASSETS = [
    '/static/css/style.css',
    '/static/js/utils.js',
    '/static/js/tweets.js',
    '/static/js/profile.js',
    '/static/js/notifications.js',
    '/static/js/dm.js',
    '/static/js/search.js',
    '/static/js/mention.js',
    '/static/js/lists.js',
    '/static/js/emoji.js',
    '/static/js/app.js',
    '/static/icon.svg',
    '/static/manifest.json'
];

// Install — pre-cache static assets
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate — clean up old caches
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(k) { return k !== CACHE_NAME; })
                    .map(function(k) { return caches.delete(k); })
            );
        })
    );
    self.clients.claim();
});

// Fetch — network-first for /api/, cache-first for static assets
self.addEventListener('fetch', function(event) {
    var url = new URL(event.request.url);

    // Network-first for API calls
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).catch(function() {
                return new Response(JSON.stringify({ error: 'offline' }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Cache-first for static assets
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(function(cached) {
                return cached || fetch(event.request).then(function(response) {
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, clone);
                    });
                    return response;
                });
            })
        );
    }
});
