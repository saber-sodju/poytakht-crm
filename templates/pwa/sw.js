{% load static %}
/* Poytakht CRM — Service Worker
 * Strategy: Cache-first for static assets only.
 * HTML pages and all dynamic/private CRM data are NEVER cached.
 */

const CACHE_NAME = 'poytakht-static-v1';

/* Only these static assets are safe to cache */
const PRECACHE_URLS = [
  '{% static "css/crm.css" %}',
  '{% static "js/crm.js" %}',
  '{% static "img/logo.png" %}',
  '{% static "pwa/icons/icon-192.png" %}',
  '{% static "pwa/icons/icon-512.png" %}',
];

/* URL prefixes that should NEVER be cached (private/auth/dynamic) */
const NEVER_CACHE_PREFIXES = [
  '/auth/',
  '/dashboard/',
  '/clients/',
  '/sales/',
  '/payments/',
  '/expenses/',
  '/complex/',
  '/workers/',
  '/materials/',
  '/audit/',
  '/admin/',
  '/reports/',
  '/api/',
];

/* ── Install: pre-cache static assets ─────────────────────────────── */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return Promise.allSettled(
          PRECACHE_URLS.map(url => cache.add(url).catch(() => { /* skip missing */ }))
        );
      })
      .then(() => self.skipWaiting())
  );
});

/* ── Activate: delete old caches ──────────────────────────────────── */
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

/* ── Fetch: smart routing ─────────────────────────────────────────── */
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  /* 1. Skip non-GET and cross-origin */
  if (req.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  /* 2. NEVER cache HTML or private CRM pages */
  const acceptsHtml = req.headers.get('accept') && req.headers.get('accept').includes('text/html');
  if (acceptsHtml) return;

  const path = url.pathname;
  const isPrivate = NEVER_CACHE_PREFIXES.some(p => path.startsWith(p)) || path === '/';
  if (isPrivate) return;

  /* 3. Static assets: Cache-first, update in background */
  if (path.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then(cached => {
        const networkFetch = fetch(req).then(response => {
          if (response && response.ok && response.type === 'basic') {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
          }
          return response;
        }).catch(() => cached); /* fallback to cache if offline */

        return cached || networkFetch;
      })
    );
    return;
  }

  /* 4. Everything else: network-only */
});
