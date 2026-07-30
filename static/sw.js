/* ============================================================
   Ham Radio Logbook — Service Worker
   - Cache-first for static assets (app shell)
   - Network-first for /api/* (fallback to offline queue)
   - Offline queue: POST /api/qso stored in IndexedDB and
     replayed when connection is restored
   ============================================================ */

const CACHE_NAME = 'ham-logbook-v1';
const APP_SHELL = ['/', '/style.css', '/app.js', '/manifest.json'];

// ── Install: cache app shell ─────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ───────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch handler ────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls: network-first, queue POST /api/qso on failure
  if (url.pathname.startsWith('/api/')) {
    if (event.request.method === 'POST' && url.pathname === '/api/qso') {
      event.respondWith(networkOrQueue(event.request));
    } else {
      event.respondWith(networkFirst(event.request));
    }
    return;
  }

  // Static assets: cache-first
  event.respondWith(cacheFirst(event.request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const resp = await fetch(request);
    if (resp.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, resp.clone());
    }
    return resp;
  } catch (_) {
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch (_) {
    const cached = await caches.match(request);
    return cached || new Response(JSON.stringify({ ok: false, error: 'offline' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } });
  }
}

// POST /api/qso: try network; on failure store in IDB queue
async function networkOrQueue(request) {
  try {
    const resp = await fetch(request.clone());
    return resp;
  } catch (_) {
    // Save to offline queue in IndexedDB
    const body = await request.clone().json().catch(() => null);
    if (body) {
      await enqueue(body);
      // Notify all clients
      const clients = await self.clients.matchAll();
      clients.forEach(c => c.postMessage({ type: 'QUEUED', qso: body }));
    }
    return new Response(
      JSON.stringify({ ok: true, queued: true, id: null }),
      { status: 202, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ── Background Sync ───────────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-qso') {
    event.waitUntil(drainQueue());
  }
});

// Also drain on message from page
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'DRAIN_QUEUE') {
    drainQueue().then(result => {
      if (event.source) event.source.postMessage({ type: 'DRAIN_RESULT', result });
    });
  }
});

// ── IndexedDB helpers ─────────────────────────────────────────
const IDB_NAME = 'ham-offline';
const IDB_STORE = 'qso-queue';

function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = e => {
      e.target.result.createObjectStore(IDB_STORE, { keyPath: 'swId', autoIncrement: true });
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

async function enqueue(qso) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readwrite');
    tx.objectStore(IDB_STORE).add(qso);
    tx.oncomplete = resolve;
    tx.onerror = e => reject(e.target.error);
  });
}

async function getAllQueued() {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readonly');
    const req = tx.objectStore(IDB_STORE).getAll();
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

async function deleteQueued(swId) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readwrite');
    tx.objectStore(IDB_STORE).delete(swId);
    tx.oncomplete = resolve;
    tx.onerror = e => reject(e.target.error);
  });
}

async function drainQueue() {
  const items = await getAllQueued();
  let sent = 0, failed = 0;
  for (const item of items) {
    const { swId, ...qso } = item;
    try {
      const resp = await fetch('/api/qso', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(qso),
      });
      if (resp.ok || resp.status === 409) {
        // 409 = duplicate, still remove from queue
        await deleteQueued(swId);
        sent++;
      } else {
        failed++;
      }
    } catch (_) {
      failed++;
    }
  }
  // Notify clients to refresh
  const clients = await self.clients.matchAll();
  clients.forEach(c => c.postMessage({ type: 'QUEUE_DRAINED', sent, failed }));
  return { sent, failed, total: items.length };
}
