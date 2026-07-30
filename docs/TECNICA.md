# Documentazione Tecnica — Ham Radio Logbook

> **Versione:** 1.1 · **Autore:** IU8VBG · **Ultima modifica:** 2026

---

## Indice

1. [Panoramica architetturale](#1-panoramica-architetturale)
2. [Stack tecnologico](#2-stack-tecnologico)
3. [Struttura del progetto](#3-struttura-del-progetto)
4. [Schema del database](#4-schema-del-database)
5. [Moduli backend](#5-moduli-backend)
6. [API REST](#6-api-rest)
7. [Sistema di autenticazione multi-utente](#7-sistema-di-autenticazione-multi-utente)
8. [Sistema di migrazioni](#8-sistema-di-migrazioni)
9. [Frontend SPA](#9-frontend-spa)
10. [Progressive Web App (PWA)](#10-progressive-web-app-pwa)
11. [Sincronizzazione MapForHam](#11-sincronizzazione-mapforham)
12. [Sicurezza](#12-sicurezza)
13. [Estendibilità](#13-estendibilit%C3%A0)

---

## 1. Panoramica architetturale

```
┌─────────────────────────────────────────────────────────┐
│                      Browser / PWA                       │
│   index.html · app.js · style.css · sw.js · manifest   │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTP / Fetch API
┌──────────────────────▼──────────────────────────────────┐
│                   Flask (app.py)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  auth.py │  │   db.py  │  │  adif.py │  │mfh.py  │  │
│  └──────────┘  └────┬─────┘  └──────────┘  └────────┘  │
│                     │                                    │
│              SQLite (logbook.db)                         │
└─────────────────────────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  MapForHam API  │
              │  HamDB.org API  │
              └─────────────────┘
```

**Flusso principale:**
- Il browser carica la SPA (Single Page Application) da `/`
- Il Service Worker intercetta le richieste: se offline, serve dalla cache o accoda in IndexedDB
- La SPA comunica con il backend Flask tramite JSON REST
- Flask persiste i dati in SQLite locale e sincronizza con MapForHam quando disponibile

---

## 2. Stack tecnologico

| Layer | Tecnologia | Versione |
|-------|-----------|---------|
| Backend | Python / Flask | 3.9+ / 3.x |
| ORM/DB | SQLite (stdlib) | 3.x |
| Auth | Werkzeug security (PBKDF2-SHA256) | bundled con Flask |
| PDF export | fpdf2 | ≥ 2.7 |
| HTTP client | requests | ≥ 2.28 |
| Config | python-dotenv | ≥ 1.0 |
| Frontend | Vanilla JS (ES2020) | — |
| CSS | Bootstrap 5.3.3 (CDN) | 5.3.3 |
| Icone | Bootstrap Icons 1.11.3 (CDN) | 1.11.3 |
| Mappa | Leaflet.js 1.9.4 (CDN) | 1.9.4 |
| PWA | Service Worker + IndexedDB | Web standard |

---

## 3. Struttura del progetto

```
Logbook/
├── app.py              # Server Flask: route, auth hook, security headers
├── auth.py             # Autenticazione multi-utente, rate limiting
├── config.py           # Configurazione da .env
├── db.py               # Layer SQLite: schema, CRUD, migrazioni, stats
├── adif.py             # Parser/esportatore formato ADIF
├── mapforham.py        # Client API MapForHam
├── set_password.py     # CLI per generare password hash (legacy single-user)
├── manage_db.py        # CLI gestione database: init/migrate/reset/seed/backup
├── requirements.txt    # Dipendenze Python
├── .env.example        # Template variabili d'ambiente
├── .gitignore
├── start.bat / start.sh
├── README.md
├── docs/
│   ├── TECNICA.md          ← questo file
│   ├── INSTALLAZIONE.md
│   └── UTENTE.md
├── static/
│   ├── index.html      # SPA principale
│   ├── login.html      # Pagina di login (standalone)
│   ├── register.html   # Pagina di registrazione (standalone)
│   ├── app.js          # Logica SPA (~850 righe)
│   ├── style.css       # Stili personalizzati
│   ├── sw.js           # Service Worker (cache-first + offline queue)
│   ├── manifest.json   # PWA manifest
│   └── icons/
│       └── icon-192.svg
└── logbook.db          # Database SQLite (creato al primo avvio)
```

---

## 4. Schema del database

### Tabella `users`
```sql
CREATE TABLE users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- nominativo
    email             TEXT,
    password_hash     TEXT NOT NULL,                        -- PBKDF2-SHA256
    full_name         TEXT,
    mfh_username      TEXT DEFAULT '',  -- username MapForHam per sync
    mfh_api_key       TEXT DEFAULT '',  -- API key MapForHam
    my_gridsquare     TEXT DEFAULT '',  -- locator QTH operatore
    sync_interval_min INTEGER DEFAULT 5,
    is_active         INTEGER DEFAULT 1,
    created_at        TEXT DEFAULT (datetime('now'))
);
```

### Tabella `qso`
```sql
CREATE TABLE qso (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),  -- isolamento dati
    qso_date        TEXT NOT NULL,   -- formato: YYYY-MM-DD
    qso_date_off    TEXT,
    time_on         TEXT NOT NULL,   -- formato: HH:MM
    time_off        TEXT,
    callsign        TEXT NOT NULL,
    name            TEXT,
    mode            TEXT,            -- SSB, CW, FT8, FM, ...
    freq            TEXT,            -- MHz
    band            TEXT,            -- 80m, 40m, 20m, ...
    rst_sent        TEXT,
    rst_rcvd        TEXT,
    gridsquare      TEXT,            -- locator corrispondente
    my_gridsquare   TEXT,
    qth             TEXT,
    state           TEXT,
    dxcc            TEXT,            -- codice DXCC numerico
    cq_zone         TEXT,
    itu_zone        TEXT,
    tx_pwr          TEXT,
    my_pota_ref     TEXT,
    pota_ref        TEXT,
    comment         TEXT,
    notes           TEXT,
    mfh_id          TEXT,            -- ID QSO su MapForHam dopo sync
    antenna_id      INTEGER,         -- FK a equipment.id
    synced          INTEGER DEFAULT 0, -- 0=locale, 1=sincronizzato MFH
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### Tabella `equipment`
```sql
CREATE TABLE equipment (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    type          TEXT NOT NULL DEFAULT 'radio',  -- radio | antenna | accessory
    name          TEXT NOT NULL,
    brand         TEXT,
    model         TEXT,
    band_coverage TEXT,
    power_w       INTEGER,
    gain_dbi      REAL,
    height_m      REAL,
    connector     TEXT,
    notes         TEXT,
    active        INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now'))
);
```

### Tabella `_migrations`
```sql
CREATE TABLE _migrations (
    version     INTEGER PRIMARY KEY,
    description TEXT,
    applied_at  TEXT DEFAULT (datetime('now'))
);
```

### Indici raccomandati per produzione
```sql
CREATE INDEX idx_qso_user_date ON qso(user_id, qso_date DESC);
CREATE INDEX idx_qso_callsign ON qso(user_id, callsign);
CREATE INDEX idx_equipment_user ON equipment(user_id, type);
```

---

## 5. Moduli backend

### `app.py`
Entry point Flask. Contiene:
- **`require_login()`** — `before_request` hook: verifica `session["user_id"]` su ogni request non-pubblica
- **`add_security_headers()`** — `after_request` hook: applica CSP, X-Frame-Options, ecc.
- **`_uid()`** — helper che restituisce `session["user_id"]`; usato da tutte le route
- **Background sync thread** — daemon thread che ogni N minuti sincronizza i QSO non sincronizzati di tutti gli utenti con MapForHam

Percorsi pubblici (no auth):
```python
_PUBLIC_PATHS      = {"/login", "/logout", "/register", "/favicon.ico"}
_PUBLIC_EXTENSIONS = {".js", ".css", ".svg", ".png", ".ico", ".webmanifest"}
_PUBLIC_FILES      = {"sw.js", "manifest.json"}
```

### `db.py`
Layer dati. Convenzioni:
- Ogni funzione di lettura/scrittura riceve `user_id: int` → isolamento totale
- Usa `sqlite3.Row` per accesso ai dati sia per indice che per nome
- `get_conn()` restituisce una connection; usata sempre come context manager `with get_conn() as conn` (auto-commit/rollback)
- `run_migrations(conn=None)` — applicabile sia con connessione esterna che stand-alone

Funzioni principali:

| Categoria | Funzioni |
|-----------|---------|
| Utenti | `create_user`, `get_user_by_id`, `get_user_by_username`, `verify_user_password`, `username_exists`, `update_user_settings` |
| QSO | `insert_qso`, `get_all_qso`, `get_qso`, `update_qso`, `delete_qso`, `qso_exists`, `get_unsynced_qso`, `mark_synced` |
| Sync | `get_all_unsynced_qso` — join con users per ottenere le credenziali MFH per utente |
| Report | `get_report_stats(user_id)` — tutti i KPI in un'unica query |
| Mappa | `get_qso_for_map(period, user_id)` |
| Attrezzatura | `get_all_equipment`, `get_equipment`, `insert_equipment`, `update_equipment`, `delete_equipment` |
| DB | `init_db`, `run_migrations`, `MIGRATIONS` list |

### `auth.py`
- **Rate limiting in-memory**: dizionario `_attempts` → `{ip: [timestamps]}`. Max 5 tentativi in 300s.
- **`verify(username, password)`**: delega a `db.verify_user_password()` (Werkzeug `check_password_hash`)
- **`get_session_user_id()`** / **`get_session_username()`**: helper per Flask `session`
- Rispetta `X-Forwarded-For` per deployment dietro nginx

### `adif.py`
- **`logbook_to_adif(qso_list)`** — genera stringa ADIF da lista di QSO. Usa `_ADIF_TAG_MAP` per rinominare campi Python in tag ADIF standard (`callsign → CALL`, `cq_zone → CQZ`, `itu_zone → ITUZ`)
- **`parse_adif(text)`** — parser ADIF: normalizza date (`YYYYMMDD → YYYY-MM-DD`) e orari (`HHMM → HH:MM`)

### `mapforham.py`
- `read_logbook(username, api_key)` — GET logbook da MFH
- `insert_qso(username, api_key, qso_data)` — POST nuovo QSO
- `delete_qso(username, api_key, mfh_id)` — DELETE QSO da MFH
- `lookup_callsign(callsign, api_key)` — callbook lookup

### `config.py`
Carica tutte le variabili da `.env` con `python-dotenv`. Mantiene valori di default sensibili per sviluppo locale:

```python
SECRET_KEY          = os.getenv("SECRET_KEY", "change-me-in-production")
DEBUG               = os.getenv("FLASK_DEBUG", "1") == "1"
HOST                = os.getenv("FLASK_HOST", "0.0.0.0")
PORT                = int(os.getenv("FLASK_PORT", "5000"))
SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS", "7"))
SYNC_INTERVAL_MIN   = int(os.getenv("SYNC_INTERVAL_MIN", "5"))
MY_GRIDSQUARE       = os.getenv("MY_GRIDSQUARE", "")
```

---

## 6. API REST

### Autenticazione

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/login` | Pagina login |
| POST | `/login` | `{username, password}` → `{ok, username}` |
| GET | `/register` | Pagina registrazione |
| POST | `/register` | `{username, password, confirm, email, full_name}` → `{ok, username}` |
| GET | `/logout` | Invalida sessione, redirect `/login` |
| GET | `/api/me` | `{ok, id, username, full_name, email}` |

### QSO CRUD

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/qso` | Lista tutti i QSO dell'utente |
| POST | `/api/qso` | Crea QSO. Body: campi ADIF. Required: `qso_date`, `time_on`, `callsign` |
| GET | `/api/qso/<id>` | Singolo QSO |
| PUT | `/api/qso/<id>` | Aggiorna QSO |
| DELETE | `/api/qso/<id>` | Elimina QSO (locale + MFH se sincronizzato) |

### Sync

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/api/sync` | Sincronizza QSO pendenti con MapForHam |
| GET | `/api/sync/status` | Stato sync: pending, last_sync, configured |

### Export / Import

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/export/adif` | Download file `.adi` |
| GET | `/api/export/csv` | Download CSV (UTF-8 BOM, Excel-ready) |
| GET | `/api/export/pdf` | Download PDF (A4 landscape) |
| POST | `/api/import/adif` | Upload file ADIF; `{ok, imported, skipped}` |

### Report e Mappa

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/report` | Tutti i KPI (last QSO, top band/mode, top DXCC, QSO/antenna, trend 6 mesi) |
| GET | `/api/map/qso?period=today\|week\|month\|all` | QSO con gridsquare per la mappa |

### Attrezzatura

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/equipment[?type=radio\|antenna\|accessory]` | Lista attrezzatura |
| POST | `/api/equipment` | Crea elemento |
| GET | `/api/equipment/<id>` | Singolo elemento |
| PUT | `/api/equipment/<id>` | Aggiorna |
| DELETE | `/api/equipment/<id>` | Elimina |

### Impostazioni e Lookup

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/settings` | Impostazioni utente corrente |
| POST | `/api/settings` | Salva impostazioni |
| GET | `/api/lookup/<callsign>` | QRZ lookup: MFH → HamDB.org fallback |
| GET | `/api/mfh/logbook` | Legge logbook remoto da MapForHam |
| GET | `/api/mfh/callbook/<callsign>` | Callbook MFH diretto |

---

## 7. Sistema di autenticazione multi-utente

### Registrazione
```
POST /register
 └── Validazione: username ≥ 3 chars, password ≥ 8 chars, confirm match
 └── db.create_user() → werkzeug.generate_password_hash(password)
 └── Auto-login: session["user_id"] = new_user_id
 └── Redirect → /
```

### Login
```
POST /login
 ├── Rate check: _rate_ok(ip) — max 5 fail / 5 min per IP
 ├── db.verify_user_password() → check_password_hash()
 └── session["user_id"] = user.id
     session["username"] = user.username
```

### Sessioni Flask
```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE   = True  # solo in produzione (HTTPS)
PERMANENT_SESSION_LIFETIME = timedelta(days=SESSION_LIFETIME_DAYS)
```

### Isolamento dati
Ogni funzione DB riceve `user_id` come parametro obbligatorio. Non è possibile accedere ai dati di un altro utente: tutte le query hanno `WHERE user_id = ?`.

---

## 8. Sistema di migrazioni

Le migrazioni sono numerate e tracciate nella tabella `_migrations`. Per aggiungere una nuova migrazione:

```python
# In db.py, aggiungere in fondo a MIGRATIONS:
MIGRATIONS = [
    ...
    (8, "Add new_column to qso", "ALTER TABLE qso ADD COLUMN new_column TEXT"),
]
```

La funzione `run_migrations()` è idempotente: controlla le versioni già applicate e salta quelle esistenti. Gli errori SQL (es. colonna già presente) vengono ignorati silenziosamente.

Per applicare: `python manage_db.py migrate`

---

## 9. Frontend SPA

`static/app.js` è una SPA vanilla JavaScript suddivisa in sezioni:

| Sezione | Funzioni chiave |
|---------|----------------|
| Offline | `onNetworkOnline/Offline()`, `pingServer()` |
| Navigazione | `showSection(name)` — gestisce 7 sezioni: `dashboard`, `new`, `report`, `map`, `station`, `adif`, `settings` |
| Dashboard | `loadQSOs()`, `renderQSOTable()`, `editQSO()`, `deleteQSO()` |
| Nuovo QSO | `submitQSO()`, `lookupCallsign()`, `loadAntennaOptions()`, `resetForm()` |
| Report | `loadReport()`, `renderReport()` |
| Mappa | `initMap()`, `maidenheadToLatLon()`, `drawQSOLines()` |
| Attrezzatura | `loadEquipment()`, `saveEquipment()` |
| Impostazioni | `loadSettings()`, `saveSettings()`, `testConnection()`, `loadCurrentUser()` |
| Export | `exportADIF()`, `exportCSV()`, `exportPDF()`, `importADIF()` |

### Intercettore 401
```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  if (r.status === 401) window.location.href = '/login';
  return r;
};
```

### Conversione Maidenhead → LatLon
La funzione `maidenheadToLatLon(grid)` converte il locator (es. `JN70`) in coordinate geografiche per il posizionamento su mappa Leaflet.

---

## 10. Progressive Web App (PWA)

### Service Worker (`sw.js`)
Strategia cache-first per asset statici. Strategia network-first con fallback offline per le API:

```
GET /api/qso  →  network OK  →  salva in cache
              →  network FAIL →  serve da cache
POST /api/qso →  network OK  →  ok
              →  network FAIL →  accoda in IndexedDB
                              →  drena quando torna online
```

### Manifest (`manifest.json`)
```json
{
  "name": "Ham Radio Logbook",
  "short_name": "Logbook",
  "display": "standalone",
  "theme_color": "#1a3a5c",
  "background_color": "#0d1b2a"
}
```

### Installazione come app
Su Chrome/Edge: icona "Installa" nella barra indirizzo. Su iOS Safari: "Aggiungi a schermata Home".

---

## 11. Sincronizzazione MapForHam

### Flusso di sync per un QSO
```
1. Utente salva QSO → db.insert_qso() con synced=0
2. Se mfh_username e mfh_api_key configurati per l'utente:
   → mfh.insert_qso() in modalità sincrona
   → se ok: db.mark_synced(id, mfh_id)
3. Background thread ogni N minuti:
   → db.get_all_unsynced_qso() (join users per credenziali)
   → per ogni QSO: mfh.insert_qso() per il rispettivo utente
```

### Configurazione per utente
Ogni utente ha `mfh_username` e `mfh_api_key` nel proprio profilo (tabella `users`). Nessuna credenziale globale in `.env`.

---

## 12. Sicurezza

### Header HTTP (tutti i response)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net ...
```

### Password
- Algoritmo: PBKDF2-SHA256 via Werkzeug
- Mai memorizzate in chiaro
- Mai nel log o negli header

### Rate limiting
- 5 tentativi falliti per IP in 5 minuti → lockout
- Rispetta `X-Forwarded-For` per proxy nginx

### Session
- Cookie HttpOnly, SameSite=Lax, Secure=True in produzione
- `SECRET_KEY` casuale in `.env` (min 32 caratteri)

### Checklist produzione
- [ ] `FLASK_DEBUG=0`
- [ ] `SECRET_KEY` generato con `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] HTTPS con certificato valido (Let's Encrypt)
- [ ] nginx come reverse proxy (non esporre Flask direttamente)
- [ ] Backup automatico del DB (`manage_db.py backup`)

---

## 13. Estendibilità

### Aggiungere un nuovo campo QSO
1. Aggiungere migrazione in `db.MIGRATIONS`
2. Aggiungere il campo alla whitelist in `db.insert_qso()` e `db.update_qso()`
3. Aggiungere il campo in `adif.py` (export) e `ADIF_FIELDS` (import)
4. Aggiungere il campo al form HTML in `index.html`
5. Aggiungere il campo all'array `QSO_FIELDS` in `app.js`

### Aggiungere una nuova sezione
1. Aggiungere `<section id="sec-nuova">` in `index.html`
2. Aggiungere `'nuova'` all'array `SECTIONS` in `app.js`
3. Aggiungere il link in navbar
4. Aggiungere il caso in `showSection()` con relativa funzione di caricamento
5. Aggiungere route `/api/nuova` in `app.py`
