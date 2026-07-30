/* ============================================================
   Ham Radio Logbook — main application logic
   ============================================================ */
'use strict';

// ── Global 401 interceptor — redirect to login on session expiry ─────────
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  if (r.status === 401) {
    window.location.href = '/login';
  }
  return r;
};

// ── Service Worker registration ──────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(console.warn);

  navigator.serviceWorker.addEventListener('message', event => {
    const { type } = event.data;
    if (type === 'QUEUED') {
      updateOfflineQueueCount(1);
      showToast('QSO salvato in coda offline', 'warning');
    } else if (type === 'QUEUE_DRAINED') {
      const { sent } = event.data;
      if (sent > 0) {
        showToast(`${sent} QSO sincronizzati con il server`, 'success');
        loadQSOs();
        updateSyncStatus();
      }
    } else if (type === 'DRAIN_RESULT') {
      loadQSOs();
      updateSyncStatus();
    }
  });
}

// ── Offline / online detection ───────────────────────────────
let _isServerReachable = true;
let _offlineQueueCount = 0;

window.addEventListener('online',  onNetworkOnline);
window.addEventListener('offline', onNetworkOffline);

function onNetworkOnline() {
  document.getElementById('offline-banner').style.display = 'none';
  document.getElementById('online-dot').className = 'sync-dot ok';
  // Ask SW to drain queue
  if (navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'DRAIN_QUEUE' });
  }
  // Also ask server to sync to MFH
  pingServer().then(ok => { if (ok) triggerSync(); });
}

function onNetworkOffline() {
  document.getElementById('offline-banner').style.display = 'block';
  document.getElementById('online-dot').className = 'sync-dot warn';
}

async function pingServer() {
  try {
    const r = await fetch('/api/ping', { cache: 'no-store' });
    _isServerReachable = r.ok;
    return r.ok;
  } catch (_) {
    _isServerReachable = false;
    return false;
  }
}

function updateOfflineQueueCount(delta) {
  _offlineQueueCount = Math.max(0, _offlineQueueCount + delta);
  const badge = document.getElementById('sync-badge');
  const cnt   = document.getElementById('sync-count');
  cnt.textContent = _offlineQueueCount;
  badge.className = _offlineQueueCount > 0
    ? 'badge bg-warning text-dark'
    : 'badge bg-secondary';
}

// ── Navigation ────────────────────────────────────────────────
const SECTIONS = ['dashboard', 'new', 'report', 'map', 'station', 'adif', 'settings'];

function showSection(name) {
  SECTIONS.forEach(s => {
    const el = document.getElementById(`sec-${s}`);
    if (el) el.style.display = s === name ? '' : 'none';
  });
  // Update active nav link
  document.querySelectorAll('.nav-link').forEach(a => a.classList.remove('active'));

  // Collapse mobile menu
  const bsCollapse = bootstrap.Collapse.getInstance(document.getElementById('navmenu'));
  if (bsCollapse) bsCollapse.hide();

  if (name === 'dashboard') loadQSOs();
  if (name === 'settings') loadSettings();
  if (name === 'new')      { setTodayNow(); loadAntennaOptions(); }
  if (name === 'report')   loadReport();
  if (name === 'map')      initMap();
  if (name === 'station')  loadEquipment();

  // Handle ?section= query param
  history.replaceState(null, '', name === 'dashboard' ? '/' : `/?section=${name}`);
}

// Restore section from URL on load
(function () {
  const p = new URLSearchParams(location.search);
  const s = p.get('section');
  if (s && SECTIONS.includes(s)) showSection(s);
})();

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const el   = document.getElementById('app-toast');
  const body = document.getElementById('toast-body');
  el.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : type} border-0`;
  body.textContent = msg;
  bootstrap.Toast.getOrCreateInstance(el, { delay: 3500 }).show();
}

// ── Date / time helpers ───────────────────────────────────────
function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function nowHHMM() {
  return new Date().toTimeString().slice(0, 5);
}
function setTodayNow() {
  if (!document.getElementById('edit-id').value) {
    document.getElementById('qso_date').value  = todayISO();
    document.getElementById('time_on').value   = nowHHMM();
  }
}

// ── Antenna dropdown for new QSO form ────────────────────────
async function loadAntennaOptions() {
  const sel = document.getElementById('antenna_id');
  if (!sel) return;
  const current = sel.value;
  try {
    const data = await fetch('/api/equipment').then(r => r.json());
    const antennas = data.filter(e => e.type === 'antenna' && e.active);
    sel.innerHTML = '<option value="">— Nessuna / non specificata —</option>' +
      antennas.map(a =>
        `<option value="${a.id}">${a.name}${a.band_coverage ? ' ('+a.band_coverage+')' : ''}</option>`
      ).join('');
    if (current) sel.value = current;
  } catch (_) { /* server offline, keep placeholder */ }
}

// ── Band → default frequency ──────────────────────────────────
const BAND_FREQ = {
  '160m': '1.850', '80m': '3.700', '60m': '5.355', '40m': '7.150',
  '30m': '10.125', '20m': '14.225', '17m': '18.100', '15m': '21.200',
  '12m': '24.940', '10m': '28.500', '6m': '50.150', '4m': '70.200',
  '2m': '144.300', '70cm': '432.100', '23cm': '1296.000',
};
function bandToFreq() {
  const band = document.getElementById('band').value;
  if (band && BAND_FREQ[band]) document.getElementById('freq').value = BAND_FREQ[band];
}

// ── Band colour class ─────────────────────────────────────────
function bandClass(band) {
  const map = {
    '160m':'band-160m','80m':'band-80m','40m':'band-40m','30m':'band-30m',
    '20m':'band-20m','17m':'band-17m','15m':'band-15m','12m':'band-12m',
    '10m':'band-10m','6m':'band-6m','2m':'band-2m','70cm':'band-70cm',
  };
  return map[band] || '';
}

// ── QSO list ─────────────────────────────────────────────────
let _allQSOs = [];

async function loadQSOs() {
  try {
    const r = await fetch('/api/qso');
    _allQSOs = await r.json();
    renderTable(_allQSOs);
    updateSyncStatus();
  } catch (_) {
    document.getElementById('qso-tbody').innerHTML =
      '<tr><td colspan="10" class="text-center text-danger">Server non raggiungibile — modalità offline</td></tr>';
  }
}

function filterTable() {
  const q = document.getElementById('search-input').value.trim().toUpperCase();
  if (!q) { renderTable(_allQSOs); return; }
  renderTable(_allQSOs.filter(r => (r.callsign || '').includes(q) || (r.name || '').toUpperCase().includes(q)));
}

function renderTable(list) {
  const tbody = document.getElementById('qso-tbody');
  document.getElementById('qso-count').textContent =
    `${list.length} QSO${list.length !== _allQSOs.length ? ` (filtrati su ${_allQSOs.length})` : ''}`;

  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">Nessun QSO trovato</td></tr>';
    return;
  }

  tbody.innerHTML = list.map(q => {
    const syncIcon = q.synced
      ? '<i class="bi bi-cloud-check text-success" title="Sincronizzato con MFH"></i>'
      : '<i class="bi bi-clock text-warning" title="In attesa di sync"></i>';
    const bc = bandClass(q.band);
    const bandHtml = q.band
      ? `<span class="band-dot ${bc}"></span>${q.band}`
      : '—';
    return `<tr>
      <td>${q.qso_date || '—'}</td>
      <td>${q.time_on || '—'}</td>
      <td><strong>${q.callsign || ''}</strong></td>
      <td>${bandHtml}</td>
      <td>${q.mode || '—'}</td>
      <td>${q.rst_sent || '—'}</td>
      <td>${q.rst_rcvd || '—'}</td>
      <td>${q.name || '—'}</td>
      <td class="text-center">${syncIcon}</td>
      <td>
        <div class="d-flex gap-1">
          <button class="btn btn-sm btn-outline-primary py-0 px-1" onclick="editQSO(${q.id})" title="Modifica"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="confirmDelete(${q.id},'${(q.callsign||'').replace(/'/g,"\\'")} ${q.qso_date||''}')" title="Elimina"><i class="bi bi-trash"></i></button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Sync status bar ───────────────────────────────────────────
async function updateSyncStatus() {
  try {
    const r = await fetch('/api/sync/status');
    const s = await r.json();
    const dot  = document.getElementById('status-dot');
    const text = document.getElementById('sync-status-text');
    if (!s.configured) {
      dot.className = 'sync-dot off';
      text.textContent = 'MFH non configurato — vai in Impostazioni';
    } else if (s.pending === 0) {
      dot.className = 'sync-dot ok';
      text.textContent = `Tutto sincronizzato${s.last_sync ? ` · ultimo sync ${fmtDate(s.last_sync)}` : ''}`;
    } else {
      dot.className = 'sync-dot warn';
      text.textContent = `${s.pending} QSO in attesa di sync${s.next_sync ? ` · prossimo ${fmtDate(s.next_sync)}` : ''}`;
    }
  } catch (_) { /* offline */ }
}

function fmtDate(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }); }
  catch (_) { return iso; }
}

async function triggerSync() {
  try {
    const r = await fetch('/api/sync', { method: 'POST' });
    const d = await r.json();
    if (d.ok) {
      showToast(`Sync: ${d.synced} inviati, ${d.failed} falliti`, d.failed ? 'warning' : 'success');
      loadQSOs();
    }
  } catch (_) {
    showToast('Server non raggiungibile', 'error');
  }
}

// ── QSO form ──────────────────────────────────────────────────
const QSO_FIELDS = [
  'qso_date','qso_date_off','time_on','time_off','callsign','name',
  'mode','freq','band','rst_sent','rst_rcvd','gridsquare','my_gridsquare',
  'qth','tx_pwr','dxcc','cq_zone','itu_zone','antenna_id',
  'my_pota_ref','pota_ref','comment','notes',
];

function resetForm() {
  document.getElementById('edit-id').value = '';
  document.getElementById('form-title').textContent = 'Nuovo QSO';
  document.getElementById('submit-label').textContent = 'Salva QSO';
  QSO_FIELDS.forEach(f => {
    const el = document.getElementById(f);
    if (el) el.value = '';
  });
  document.getElementById('callsign-info').textContent = '';
  document.getElementById('callsign-info').className = 'form-text text-success mt-1';
  const dxccRow = document.getElementById('dxcc-row');
  if (dxccRow) dxccRow.style.display = 'none';
  const countryEl = document.getElementById('country_display');
  if (countryEl) countryEl.value = '';
  setTodayNow();
}

async function editQSO(id) {
  try {
    const r = await fetch(`/api/qso/${id}`);
    const q = await r.json();
    document.getElementById('edit-id').value = id;
    document.getElementById('form-title').textContent = `Modifica QSO — ${q.callsign}`;
    document.getElementById('submit-label').textContent = 'Aggiorna QSO';
    QSO_FIELDS.forEach(f => {
      const el = document.getElementById(f);
      if (el) el.value = q[f] || '';
    });
    // Show DXCC info row if any DXCC data is stored
    const dxccRow = document.getElementById('dxcc-row');
    if (dxccRow) {
      const hasDxcc = q.dxcc || q.cq_zone || q.itu_zone;
      dxccRow.style.display = hasDxcc ? '' : 'none';
      const srcEl = document.getElementById('lookup-source');
      if (srcEl) srcEl.textContent = hasDxcc ? 'dati salvati' : '';
    }
    showSection('new'); // also calls loadAntennaOptions() which restores antenna_id
  } catch (_) {
    showToast('Impossibile caricare il QSO', 'error');
  }
}

async function submitQSO(event) {
  event.preventDefault();
  const form = document.getElementById('qso-form');
  if (!form.checkValidity()) { form.classList.add('was-validated'); return; }
  form.classList.remove('was-validated');

  const editId = document.getElementById('edit-id').value;
  const payload = {};
  QSO_FIELDS.forEach(f => {
    const el = document.getElementById(f);
    if (el && el.value.trim()) payload[f] = el.value.trim();
  });
  // Ensure callsign uppercase
  if (payload.callsign) payload.callsign = payload.callsign.toUpperCase();

  try {
    let r, d;
    if (editId) {
      r = await fetch(`/api/qso/${editId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      d = await r.json();
      showToast(d.ok ? 'QSO aggiornato' : (d.error || 'Errore'), d.ok ? 'success' : 'error');
    } else {
      r = await fetch('/api/qso', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      d = await r.json();
      if (r.status === 202 && d.queued) {
        showToast('QSO salvato in coda offline', 'warning');
        updateOfflineQueueCount(1);
      } else if (r.status === 409) {
        showToast('QSO duplicato (già presente)', 'warning');
        return;
      } else {
        showToast(d.ok ? 'QSO salvato!' : (d.error || 'Errore'), d.ok ? 'success' : 'error');
      }
    }
    if (d.ok || d.queued) {
      resetForm();
      showSection('dashboard');
    }
  } catch (_) {
    showToast('Server non raggiungibile', 'error');
  }
}

// ── Delete QSO ────────────────────────────────────────────────
let _pendingDeleteId = null;

function confirmDelete(id, label) {
  _pendingDeleteId = id;
  document.getElementById('delete-modal-body').textContent =
    `Eliminare il QSO con ${label}? L'operazione rimuoverà il record anche da MapForHam se sincronizzato.`;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal')).show();
}

document.getElementById('delete-confirm-btn').addEventListener('click', async () => {
  if (!_pendingDeleteId) return;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal')).hide();
  try {
    const r = await fetch(`/api/qso/${_pendingDeleteId}`, { method: 'DELETE' });
    const d = await r.json();
    showToast(d.ok ? 'QSO eliminato' : (d.error || 'Errore'), d.ok ? 'success' : 'error');
    if (d.ok) loadQSOs();
  } catch (_) {
    showToast('Errore durante l\'eliminazione', 'error');
  }
  _pendingDeleteId = null;
});

// ── Callsign lookup (cascade: MFH → HamDB.org) ───────────────
async function lookupCallsign() {
  const cs = document.getElementById('callsign').value.trim().toUpperCase();
  const info = document.getElementById('callsign-info');
  if (!cs || cs.length < 3) { info.textContent = ''; return; }
  info.textContent = '🔍 Ricerca…';
  info.className = 'form-text text-muted mt-1';
  try {
    const r = await fetch(`/api/lookup/${cs}`);
    const d = await r.json();
    if (d.ok) {
      // Auto-fill form fields
      if (d.name)       document.getElementById('name').value       = d.name;
      if (d.qth)        document.getElementById('qth').value        = d.qth;
      if (d.gridsquare) document.getElementById('gridsquare').value = d.gridsquare.toUpperCase();
      if (d.dxcc)       document.getElementById('dxcc').value       = d.dxcc;
      if (d.cq_zone)    document.getElementById('cq_zone').value    = d.cq_zone;
      if (d.itu_zone)   document.getElementById('itu_zone').value   = d.itu_zone;

      // Show DXCC info row
      const dxccRow = document.getElementById('dxcc-row');
      const countryEl = document.getElementById('country_display');
      if (dxccRow) {
        dxccRow.style.display = '';
        if (countryEl && d.country) countryEl.value = d.country;
        const srcEl = document.getElementById('lookup-source');
        if (srcEl) {
          srcEl.textContent = `via ${d.source}`;
          srcEl.className = d.source === 'MapForHam'
            ? 'badge bg-primary' : 'badge bg-secondary';
        }
      }

      // Summary line
      const parts = [];
      if (d.name)    parts.push(d.name);
      if (d.country) parts.push(d.country);
      if (d.gridsquare) parts.push(`Loc: ${d.gridsquare}`);
      info.textContent = parts.join(' · ') || `Trovato (${d.source})`;
      info.className = 'form-text text-success mt-1';
    } else {
      info.textContent = '✗ Nominativo non trovato';
      info.className = 'form-text text-muted mt-1';
      const dxccRow = document.getElementById('dxcc-row');
      if (dxccRow) dxccRow.style.display = 'none';
    }
  } catch (_) {
    info.textContent = '';
  }
}

// ── Settings ──────────────────────────────────────────────────
async function loadCurrentUser() {
  try {
    const r = await fetch('/api/me');
    if (!r.ok) return;
    const u = await r.json();
    if (u.ok) {
      const el = document.getElementById('navbar-callsign');
      if (el) el.textContent = u.username;
    }
  } catch (_) {}
}

async function loadSettings() {
  try {
    const r = await fetch('/api/settings');
    const s = await r.json();
    document.getElementById('cfg-username').value      = s.username || '';
    document.getElementById('cfg-sync-interval').value = s.sync_interval_min || 5;
    document.getElementById('cfg-gridsquare').value    = s.my_gridsquare || '';
    document.getElementById('cfg-apikey').value        = '';
    if (document.getElementById('cfg-fullname'))
      document.getElementById('cfg-fullname').value = s.full_name || '';
    if (document.getElementById('cfg-email'))
      document.getElementById('cfg-email').value = s.email || '';
  } catch (_) {}

  // Server info
  try {
    const r = await fetch('/api/sync/status');
    const s = await r.json();
    document.getElementById('server-info').innerHTML =
      `QSO in attesa: <strong>${s.pending}</strong> &nbsp;|&nbsp; ` +
      `Intervallo sync: <strong>${s.sync_interval_min} min</strong> &nbsp;|&nbsp; ` +
      `MFH configurato: <strong>${s.configured ? 'Sì' : 'No'}</strong>`;
  } catch (_) {}
}

async function saveSettings(event) {
  event.preventDefault();
  const payload = {
    username:         document.getElementById('cfg-username').value.trim(),
    sync_interval_min: parseInt(document.getElementById('cfg-sync-interval').value) || 5,
    my_gridsquare:    document.getElementById('cfg-gridsquare').value.trim(),
  };
  if (document.getElementById('cfg-fullname'))
    payload.full_name = document.getElementById('cfg-fullname').value.trim();
  if (document.getElementById('cfg-email'))
    payload.email = document.getElementById('cfg-email').value.trim();
  const apiKey = document.getElementById('cfg-apikey').value.trim();
  if (apiKey) payload.api_key = apiKey;

  try {
    const r = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    const fb = document.getElementById('settings-feedback');
    if (d.ok) {
      fb.innerHTML = '<div class="alert alert-success py-2">Impostazioni salvate!</div>';
      showToast('Impostazioni salvate', 'success');
      setTimeout(() => { fb.innerHTML = ''; }, 3000);
    } else {
      fb.innerHTML = `<div class="alert alert-danger py-2">${d.error || 'Errore'}</div>`;
    }
  } catch (_) {
    showToast('Server non raggiungibile', 'error');
  }
}

async function testConnection() {
  const fb = document.getElementById('settings-feedback');
  fb.innerHTML = '<div class="alert alert-info py-2">Test in corso…</div>';
  try {
    const r = await fetch('/api/mfh/logbook');
    const d = await r.json();
    if (d.ok) {
      const count = Array.isArray(d.data) ? d.data.length : '?';
      fb.innerHTML = `<div class="alert alert-success py-2">✅ Connessione MFH OK — ${count} QSO remoti trovati</div>`;
    } else {
      fb.innerHTML = `<div class="alert alert-warning py-2">⚠️ ${d.error || 'Risposta non valida'}</div>`;
    }
  } catch (_) {
    fb.innerHTML = '<div class="alert alert-danger py-2">❌ Server Flask non raggiungibile</div>';
  }
}

function toggleApiKeyVisibility() {
  const input = document.getElementById('cfg-apikey');
  const icon  = document.getElementById('apikey-eye');
  if (input.type === 'password') {
    input.type = 'text';
    icon.className = 'bi bi-eye-slash';
  } else {
    input.type = 'password';
    icon.className = 'bi bi-eye';
  }
}

// ── ADIF Import ───────────────────────────────────────────────
function adifDragOver(e) {
  e.preventDefault();
  document.getElementById('adif-dropzone').classList.add('dragover');
}
function adifDragLeave(e) {
  document.getElementById('adif-dropzone').classList.remove('dragover');
}
function adifDrop(e) {
  e.preventDefault();
  adifDragLeave(e);
  const file = e.dataTransfer.files[0];
  if (file) importAdif(file);
}

async function importAdif(file) {
  if (!file) return;
  const result = document.getElementById('adif-result');
  result.innerHTML = '<div class="alert alert-info py-2">Importazione in corso…</div>';
  const form = new FormData();
  form.append('file', file);
  try {
    const r = await fetch('/api/import/adif', { method: 'POST', body: form });
    const d = await r.json();
    if (d.ok) {
      result.innerHTML = `<div class="alert alert-success py-2">✅ Importati: <strong>${d.imported}</strong> QSO · Saltati (duplicati): <strong>${d.skipped}</strong></div>`;
      showToast(`ADIF importato: ${d.imported} QSO`, 'success');
    } else {
      result.innerHTML = `<div class="alert alert-danger py-2">${d.error}</div>`;
    }
  } catch (_) {
    result.innerHTML = '<div class="alert alert-danger py-2">Errore di connessione</div>';
  }
  // Reset file input
  document.getElementById('adif-file').value = '';
}

// ── Init ──────────────────────────────────────────────────────
(async function init() {
  // Set initial online/offline state
  if (!navigator.onLine) onNetworkOffline();
  else pingServer();

  // Load current user (shows callsign in navbar)
  loadCurrentUser();

  // Check visible section
  const active = document.querySelector('[id^="sec-"]:not([style*="none"])');
  if (!active || active.id === 'sec-dashboard') loadQSOs();

  // Auto-refresh sync status every 30s
  setInterval(updateSyncStatus, 30_000);

  // Auto-drain SW queue every 30s when online
  setInterval(() => {
    if (navigator.onLine && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'DRAIN_QUEUE' });
    }
  }, 30_000);
})();

// ============================================================
// ── REPORT ───────────────────────────────────────────────────
// ============================================================

async function loadReport() {
  try {
    const r = await fetch('/api/report');
    const d = await r.json();
    renderReport(d);
  } catch (_) {
    showToast('Server non raggiungibile', 'error');
  }
}

function renderReport(d) {
  // ── Ultimo QSO ──────────────────────────────────────────
  const lq = d.last_qso;
  if (lq) {
    document.getElementById('last-qso-callsign').textContent = lq.callsign || '—';
    const parts = [lq.qso_date, lq.time_on, lq.band, lq.mode].filter(Boolean);
    if (lq.name)  parts.push(`Nome: ${lq.name}`);
    if (lq.qth)   parts.push(lq.qth);
    if (lq.rst_sent) parts.push(`RST ${lq.rst_sent}/${lq.rst_rcvd || '?'}`);
    document.getElementById('last-qso-detail').textContent = parts.join('  ·  ');
  }

  // ── KPI cards ────────────────────────────────────────────
  const now = new Date();
  const monthName = now.toLocaleString('it-IT', { month: 'long', year: 'numeric' });
  document.getElementById('stat-month-total').textContent  = d.month_total ?? 0;
  document.getElementById('stat-month-label').textContent  = monthName;
  document.getElementById('stat-total-all').textContent    = d.total ?? 0;
  document.getElementById('stat-unique-calls').textContent = d.unique_callsigns ?? 0;

  // TX hours
  const mins = d.total_tx_minutes || 0;
  const txH  = Math.floor(mins / 60);
  const txM  = mins % 60;
  document.getElementById('stat-tx-hours').textContent = txH > 0 ? `${txH}h ${txM}m` : `${txM}m`;

  // ── Top band ─────────────────────────────────────────────
  const tb = d.top_band;
  document.getElementById('top-band-name').textContent  = tb ? tb.band  : '—';
  document.getElementById('top-band-count').textContent = tb ? `${tb.count} QSO` : '';
  renderBars('bands-bars', d.bands_all || [], 'band', bandColor);

  // ── Top mode ─────────────────────────────────────────────
  const tm = d.top_mode;
  document.getElementById('top-mode-name').textContent  = tm ? tm.mode  : '—';
  document.getElementById('top-mode-count').textContent = tm ? `${tm.count} QSO` : '';
  renderBars('modes-bars', d.modes_all || [], 'mode', () => '#009688');

  // ── Top DXCC ──────────────────────────────────────────────
  const dxEl = document.getElementById('top-dxcc-list');
  if (!d.top_dxcc?.length) {
    dxEl.innerHTML = '<li class="list-group-item text-muted">Nessun dato</li>';
  } else {
    const max = d.top_dxcc[0].count;
    dxEl.innerHTML = d.top_dxcc.map((c, i) => {
      const medals = ['🥇','🥈','🥉','4️⃣','5️⃣'];
      const pct = Math.round(c.count / max * 100);
      return `<li class="list-group-item py-2">
        <div class="d-flex align-items-center justify-content-between mb-1">
          <span>${medals[i] || ''} <strong>${c.prefix}</strong> <span class="text-muted small">${c.country}</span></span>
          <span class="badge bg-info text-dark rounded-pill">${c.count}</span>
        </div>
        <div class="progress" style="height:4px">
          <div class="progress-bar bg-info" style="width:${pct}%"></div>
        </div>
      </li>`;
    }).join('');
  }

  // ── QSO per antenna ───────────────────────────────────────────
  renderBars('antenna-bars', d.qso_per_antenna || [], 'antenna', () => '#1976d2');

  // ── Monthly trend bar chart ────────────────────────────────
  renderColumnChart('monthly-chart', d.monthly_totals || [], 'month', 110, '#1a3a5c');

  // ── Daily chart (current month) ────────────────────────────
  renderColumnChart('daily-chart', d.qso_per_day || [], 'date', 50, '#4fc3f7');
}

function bandColor(band) {
  const BAND_COLOR = {
    '160m':'#9c27b0','80m':'#673ab7','40m':'#3f51b5','30m':'#2196f3',
    '20m':'#009688','17m':'#4caf50','15m':'#8bc34a','12m':'#cddc39',
    '10m':'#ff9800','6m':'#ff5722','4m':'#e91e63','2m':'#f44336',
    '70cm':'#795548','23cm':'#607d8b',
  };
  return BAND_COLOR[band] || '#607d8b';
}

function renderBars(containerId, items, labelKey, colorFn) {
  const el = document.getElementById(containerId);
  if (!items.length) { el.innerHTML = '<span class="text-muted small">Nessun dato</span>'; return; }
  const max = items[0].count;
  el.innerHTML = items.slice(0, 8).map(item => {
    const pct = Math.round(item.count / max * 100);
    const color = colorFn(item[labelKey]);
    return `<div class="d-flex align-items-center gap-2 mb-1" style="font-size:.8rem">
      <span style="width:55px;text-align:right;font-weight:600">${item[labelKey]}</span>
      <div class="flex-grow-1 rounded" style="height:14px;background:#e9ecef;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${color};border-radius:3px;transition:width .4s"></div>
      </div>
      <span class="text-muted" style="width:36px">${item.count}</span>
    </div>`;
  }).join('');
}

function renderColumnChart(containerId, items, labelKey, maxH, color) {
  const el = document.getElementById(containerId);
  if (!items.length) { el.innerHTML = '<span class="text-muted small px-2">Nessun dato nel periodo</span>'; return; }
  const max = Math.max(...items.map(i => i.count), 1);
  el.innerHTML = items.map(item => {
    const h = Math.max(6, Math.round(item.count / max * maxH));
    const label = item[labelKey]?.slice(-5) || '';  // last 5 chars (MM-DD or MM)
    return `<div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:24px;max-width:48px" title="${item[labelKey]}: ${item.count} QSO">
      <span style="font-size:.65rem;color:#6c757d;margin-bottom:2px">${item.count}</span>
      <div style="width:100%;height:${h}px;background:${color};border-radius:3px 3px 0 0;opacity:.85"></div>
      <span style="font-size:.6rem;color:#6c757d;margin-top:3px;white-space:nowrap">${label}</span>
    </div>`;
  }).join('');
}

// ============================================================
// ── MAPPA QSO (Leaflet) ──────────────────────────────────────
// ============================================================

let _leafletMap = null;
let _mapPeriod  = 'today';
let _mapLayers  = [];

// Maidenhead grid square → [lat, lon]
function gridToLatLon(grid) {
  if (!grid || grid.length < 4) return null;
  grid = grid.toUpperCase().trim();
  try {
    const A = 'A'.charCodeAt(0);
    const lon = (grid.charCodeAt(0) - A) * 20 - 180
              + parseInt(grid[2]) * 2
              + (grid.length >= 5 ? (grid.charCodeAt(4) - A) / 12 + 1/24 : 1);
    const lat = (grid.charCodeAt(1) - A) * 10 - 90
              + parseInt(grid[3])
              + (grid.length >= 6 ? (grid.charCodeAt(5) - A) / 24 + 1/48 : 0.5);
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
    return [lat, lon];
  } catch (_) { return null; }
}

// Band → colour
const BAND_COLOR = {
  '160m':'#9c27b0','80m':'#673ab7','40m':'#3f51b5','30m':'#2196f3',
  '20m':'#009688','17m':'#4caf50','15m':'#8bc34a','12m':'#cddc39',
  '10m':'#ff9800','6m':'#ff5722','4m':'#e91e63','2m':'#f44336',
  '70cm':'#795548','23cm':'#607d8b',
};
function bandColor(band) { return BAND_COLOR[band] || '#607d8b'; }

function setMapPeriod(period) {
  _mapPeriod = period;
  document.querySelectorAll('#map-period-btns button').forEach(b => {
    b.classList.toggle('active', b.dataset.period === period);
  });
  loadMapData();
}

async function initMap() {
  if (!_leafletMap) {
    _leafletMap = L.map('qso-map', { zoomControl: true }).setView([42, 12], 4);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(_leafletMap);
  }
  await loadMapData();
  // Fix Leaflet size when container was hidden
  setTimeout(() => _leafletMap.invalidateSize(), 100);
}

async function loadMapData() {
  if (!_leafletMap) return;
  // Clear existing layers
  _mapLayers.forEach(l => _leafletMap.removeLayer(l));
  _mapLayers = [];

  try {
    const r = await fetch(`/api/map/qso?period=${_mapPeriod}`);
    const d = await r.json();
    if (!d.ok) return;

    updateMapStats(d.stats);
    renderMapLegend(d.stats.bands);

    const myGS  = d.my_gridsquare;
    const myPos = myGS ? gridToLatLon(myGS) : null;

    // My station marker
    if (myPos) {
      const myIcon = L.divIcon({
        className: '',
        html: `<div style="background:#1a3a5c;color:#f0b429;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:14px;box-shadow:0 2px 6px rgba(0,0,0,.4);">📡</div>`,
        iconSize: [28, 28], iconAnchor: [14, 14],
      });
      const myMarker = L.marker(myPos, { icon: myIcon, zIndexOffset: 1000 })
        .bindPopup(`<strong>La mia stazione</strong><br>Grid: ${myGS}`);
      myMarker.addTo(_leafletMap);
      _mapLayers.push(myMarker);
    }

    // QSO markers and lines
    const bounds = myPos ? [myPos] : [];
    for (const q of d.qsos) {
      if (!q.gridsquare) continue;
      const pos = gridToLatLon(q.gridsquare);
      if (!pos) continue;

      const color = bandColor(q.band);

      // Line from my station
      if (myPos) {
        const line = L.polyline([myPos, pos], {
          color, weight: 2, opacity: 0.7,
        }).addTo(_leafletMap);
        _mapLayers.push(line);
      }

      // Marker
      const dot = L.circleMarker(pos, {
        radius: 7, color, fillColor: color, fillOpacity: 0.85, weight: 2,
      }).bindPopup(`
        <strong>${q.callsign}</strong>${q.name ? ` — ${q.name}` : ''}<br>
        ${q.qso_date} ${q.time_on}<br>
        ${q.band || ''}  ${q.mode || ''}<br>
        RST: ${q.rst_sent || '?'} / ${q.rst_rcvd || '?'}<br>
        Grid: ${q.gridsquare}${q.qth ? `<br>${q.qth}` : ''}
      `).addTo(_leafletMap);
      _mapLayers.push(dot);
      bounds.push(pos);
    }

    if (bounds.length > 1) {
      _leafletMap.fitBounds(bounds, { padding: [30, 30] });
    } else if (bounds.length === 1) {
      _leafletMap.setView(bounds[0], 6);
    }
  } catch (_) {
    showToast('Impossibile caricare i dati mappa', 'error');
  }
}

function updateMapStats(s) {
  document.getElementById('stat-total').textContent    = `${s.total} QSO`;
  document.getElementById('stat-grid').textContent     = `${s.with_grid} con gridsquare`;
  document.getElementById('stat-countries').textContent= `${s.countries} prefissi`;
  document.getElementById('stat-band').textContent     = s.top_band ? `Banda: ${s.top_band}` : '—';
  document.getElementById('stat-mode').textContent     = s.top_mode ? `Modo: ${s.top_mode}` : '—';
}

function renderMapLegend(bands) {
  const el = document.getElementById('map-legend');
  if (!bands || !Object.keys(bands).length) { el.innerHTML = ''; return; }
  el.innerHTML = Object.entries(bands)
    .sort((a,b) => b[1]-a[1])
    .map(([band, cnt]) =>
      `<span class="badge" style="background:${bandColor(band)}">${band}: ${cnt}</span>`
    ).join('');
}


// ============================================================
// ── GESTIONE STAZIONE ─────────────────────────────────────────
// ============================================================

let _currentEqType = 'radio';
let _pendingDeleteEqId = null;

async function loadEquipment(type) {
  if (type !== undefined) _currentEqType = type;
  const grid = document.getElementById('equipment-grid');
  grid.innerHTML = '<div class="col-12 text-center py-4 text-muted"><div class="spinner-border spinner-border-sm me-2"></div>Caricamento…</div>';
  try {
    const url = _currentEqType ? `/api/equipment?type=${_currentEqType}` : '/api/equipment';
    const r = await fetch(url);
    const list = await r.json();
    renderEquipmentGrid(list);
  } catch (_) {
    grid.innerHTML = '<div class="col-12 text-center text-danger py-4">Server non raggiungibile</div>';
  }
}

function filterEquipment(type, btn) {
  _currentEqType = type;
  document.querySelectorAll('#station-tabs .nav-link').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  loadEquipment(type);
}

const EQ_TYPE_ICONS = { radio:'📻', antenna:'📡', accessory:'🔌' };
const EQ_TYPE_LABELS = { radio:'Ricetrasmettitore', antenna:'Antenna', accessory:'Accessorio' };

function renderEquipmentGrid(list) {
  const grid = document.getElementById('equipment-grid');
  if (!list.length) {
    grid.innerHTML = `<div class="col-12 text-center text-muted py-5">
      <div class="fs-1">📭</div>
      <p>Nessun apparato. <a href="#" onclick="openEquipmentModal()">Aggiungi il primo</a></p>
    </div>`;
    return;
  }
  grid.innerHTML = list.map(eq => {
    const icon  = EQ_TYPE_ICONS[eq.type]  || '🔧';
    const label = EQ_TYPE_LABELS[eq.type] || eq.type;
    const activeBadge = eq.active
      ? '<span class="badge bg-success ms-1">Attivo</span>'
      : '<span class="badge bg-secondary ms-1">Non in uso</span>';
    const details = [];
    if (eq.band_coverage) details.push(`<i class="bi bi-reception-4 me-1"></i>${eq.band_coverage}`);
    if (eq.power_w)       details.push(`<i class="bi bi-lightning-charge me-1"></i>${eq.power_w} W`);
    if (eq.gain_dbi != null && eq.gain_dbi !== '') details.push(`<i class="bi bi-graph-up me-1"></i>${eq.gain_dbi} dBi`);
    if (eq.height_m != null && eq.height_m !== '') details.push(`<i class="bi bi-arrows-vertical me-1"></i>${eq.height_m} m`);
    if (eq.connector)     details.push(`<i class="bi bi-plug me-1"></i>${eq.connector}`);

    return `<div class="col-12 col-md-6 col-lg-4">
      <div class="card section-card h-100 ${eq.active ? '' : 'opacity-60'}">
        <div class="card-body">
          <div class="d-flex align-items-start justify-content-between mb-2">
            <div>
              <span class="fs-4 me-2">${icon}</span>
              <small class="text-muted">${label}</small>${activeBadge}
            </div>
            <div class="dropdown">
              <button class="btn btn-sm btn-outline-secondary py-0" data-bs-toggle="dropdown"><i class="bi bi-three-dots-vertical"></i></button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="#" onclick="editEquipment(${eq.id})"><i class="bi bi-pencil me-2"></i>Modifica</a></li>
                <li><a class="dropdown-item" href="#" onclick="toggleEquipmentActive(${eq.id},${eq.active ? 0 : 1})">${eq.active ? '<i class="bi bi-pause-circle me-2"></i>Segna non in uso' : '<i class="bi bi-play-circle me-2"></i>Segna attivo'}</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-danger" href="#" onclick="confirmDeleteEquipment(${eq.id},'${(eq.name||'').replace(/'/g,"\\'")}')"><i class="bi bi-trash me-2"></i>Elimina</a></li>
              </ul>
            </div>
          </div>
          <h6 class="mb-1">${eq.name}</h6>
          ${eq.brand || eq.model ? `<div class="text-muted small mb-2">${[eq.brand,eq.model].filter(Boolean).join(' ')}</div>` : ''}
          ${details.length ? `<div class="d-flex flex-wrap gap-2 text-muted" style="font-size:.78rem">${details.map(d=>`<span>${d}</span>`).join('')}</div>` : ''}
          ${eq.notes ? `<p class="text-muted mt-2 mb-0" style="font-size:.8rem">${eq.notes}</p>` : ''}
        </div>
      </div>
    </div>`;
  }).join('');
}

function openEquipmentModal(prefillType) {
  document.getElementById('eq-edit-id').value = '';
  document.getElementById('eq-modal-title').innerHTML = '<i class="bi bi-plus-circle me-2"></i>Aggiungi apparato';
  document.getElementById('eq-submit-label').textContent = 'Salva';
  document.getElementById('equipment-form').reset();
  if (prefillType) document.getElementById('eq-type').value = prefillType;
  updateEquipmentForm();
  bootstrap.Modal.getOrCreateInstance(document.getElementById('equipmentModal')).show();
}

function updateEquipmentForm() {
  const type = document.getElementById('eq-type').value;
  document.querySelectorAll('.eq-field-radio').forEach(el => el.style.display = type === 'radio' ? '' : 'none');
  document.querySelectorAll('.eq-field-antenna').forEach(el => el.style.display = type === 'antenna' ? '' : 'none');
}

async function editEquipment(id) {
  try {
    const r = await fetch(`/api/equipment/${id}`);
    const eq = await r.json();
    document.getElementById('eq-edit-id').value  = id;
    document.getElementById('eq-modal-title').innerHTML = '<i class="bi bi-pencil me-2"></i>Modifica apparato';
    document.getElementById('eq-submit-label').textContent = 'Aggiorna';
    document.getElementById('eq-type').value      = eq.type || 'radio';
    document.getElementById('eq-name').value      = eq.name || '';
    document.getElementById('eq-brand').value     = eq.brand || '';
    document.getElementById('eq-model').value     = eq.model || '';
    document.getElementById('eq-bands').value     = eq.band_coverage || '';
    document.getElementById('eq-power').value     = eq.power_w || '';
    document.getElementById('eq-gain').value      = eq.gain_dbi != null ? eq.gain_dbi : '';
    document.getElementById('eq-height').value    = eq.height_m != null ? eq.height_m : '';
    document.getElementById('eq-connector').value = eq.connector || '';
    document.getElementById('eq-notes').value     = eq.notes || '';
    document.getElementById('eq-active').checked  = !!eq.active;
    updateEquipmentForm();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('equipmentModal')).show();
  } catch (_) {
    showToast('Impossibile caricare i dati', 'error');
  }
}

async function submitEquipment() {
  const name = document.getElementById('eq-name').value.trim();
  if (!name) { showToast('Il nome è obbligatorio', 'warning'); return; }

  const editId = document.getElementById('eq-edit-id').value;
  const payload = {
    type:         document.getElementById('eq-type').value,
    name,
    brand:        document.getElementById('eq-brand').value.trim(),
    model:        document.getElementById('eq-model').value.trim(),
    band_coverage:document.getElementById('eq-bands').value.trim(),
    power_w:      parseInt(document.getElementById('eq-power').value) || null,
    gain_dbi:     parseFloat(document.getElementById('eq-gain').value) || null,
    height_m:     parseFloat(document.getElementById('eq-height').value) || null,
    connector:    document.getElementById('eq-connector').value,
    notes:        document.getElementById('eq-notes').value.trim(),
    active:       document.getElementById('eq-active').checked ? 1 : 0,
  };
  // Remove null values for cleanliness
  Object.keys(payload).forEach(k => { if (payload[k] === null || payload[k] === '') delete payload[k]; });

  try {
    const url    = editId ? `/api/equipment/${editId}` : '/api/equipment';
    const method = editId ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const d = await r.json();
    if (d.ok) {
      bootstrap.Modal.getOrCreateInstance(document.getElementById('equipmentModal')).hide();
      showToast(editId ? 'Apparato aggiornato' : 'Apparato aggiunto', 'success');
      loadEquipment();
    } else {
      showToast(d.error || 'Errore', 'error');
    }
  } catch (_) {
    showToast('Server non raggiungibile', 'error');
  }
}

async function toggleEquipmentActive(id, newActive) {
  try {
    await fetch(`/api/equipment/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: newActive }),
    });
    loadEquipment();
  } catch (_) {
    showToast('Errore durante l\'aggiornamento', 'error');
  }
}

function confirmDeleteEquipment(id, name) {
  _pendingDeleteId = null;  // clear QSO delete
  _pendingDeleteEqId = id;
  document.getElementById('delete-modal-body').textContent =
    `Eliminare "${name}" dall'inventario stazione?`;
  document.getElementById('delete-confirm-btn').onclick = deleteEquipmentConfirmed;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal')).show();
}

async function deleteEquipmentConfirmed() {
  if (!_pendingDeleteEqId) return;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal')).hide();
  try {
    const r = await fetch(`/api/equipment/${_pendingDeleteEqId}`, { method: 'DELETE' });
    const d = await r.json();
    showToast(d.ok ? 'Eliminato' : (d.error || 'Errore'), d.ok ? 'success' : 'error');
    if (d.ok) loadEquipment();
  } catch (_) {
    showToast('Errore di connessione', 'error');
  }
  _pendingDeleteEqId = null;
}

// Restore original QSO delete handler
document.getElementById('delete-confirm-btn').addEventListener('click', async function handler() {
  if (_pendingDeleteEqId) return; // handled by deleteEquipmentConfirmed
  if (!_pendingDeleteId) return;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal')).hide();
  try {
    const r = await fetch(`/api/qso/${_pendingDeleteId}`, { method: 'DELETE' });
    const d = await r.json();
    showToast(d.ok ? 'QSO eliminato' : (d.error || 'Errore'), d.ok ? 'success' : 'error');
    if (d.ok) loadQSOs();
  } catch (_) {
    showToast('Errore durante l\'eliminazione', 'error');
  }
  _pendingDeleteId = null;
});
