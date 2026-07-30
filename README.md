# 📻 Ham Radio Logbook

<p align="center">
  <img src="static/icons/icon-192.svg" width="80" alt="Ham Radio Logbook logo">
</p>

<p align="center">
  <strong>Logbook radioamatoriale ADIF — PWA offline-first, multi-utente, con sync MapForHam</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-3.x-003B57?logo=sqlite&logoColor=white">
  <img alt="Bootstrap" src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white">
  <img alt="PWA" src="https://img.shields.io/badge/PWA-offline--first-5A0FC8?logo=pwa&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## ✨ Caratteristiche

| Funzionalità | Dettaglio |
|---|---|
| 📋 **Logbook ADIF** | Registrazione QSO completa (campo per campo standard ADIF) |
| 👥 **Multi-utente** | Ogni operatore ha il proprio account — dati completamente isolati |
| 📶 **Offline-first** | Service Worker + IndexedDB: funziona senza rete, sincronizza al ritorno |
| 🔄 **Sync MapForHam** | Sincronizzazione automatica e manuale con [mapforham.com](https://www.mapforham.com) |
| 🔍 **QRZ Lookup** | Auto-fill del form: MFH Callbook → HamDB.org (gratuito, no API key) |
| 📊 **Report & KPI** | Ultimo QSO, top banda/modo, top DXCC, QSO per antenna, trend 6 mesi |
| 🗺️ **Mappa QSO** | Leaflet.js con linee colorate per banda e conversione Maidenhead |
| 🔧 **Gestione stazione** | Catalogo radio, antenne e accessori; collegamento antenna→QSO |
| 📥 **Export/Import** | ADIF, CSV (Excel-ready UTF-8 BOM), PDF (A4 landscape) |
| 🔒 **Sicurezza** | PBKDF2-SHA256, rate limiting, CSP, HTTPS-ready, sessioni HTTPOnly |
| 📱 **PWA installabile** | App nativa su Android, iOS e desktop (Chrome/Edge) |
| 🛠️ **Migrazioni DB** | Schema versionato con `manage_db.py` (init/migrate/seed/backup/reset) |

---

## 🚀 Quick Start

### Prerequisiti
- **Python 3.9+** — [python.org](https://www.python.org/downloads/) (Windows: spuntare "Add Python to PATH")
- **pip** (incluso con Python)

### Installazione in 5 minuti

```bash
# 1. Clona il repository
git clone https://github.com/IU8VBG/ham-radio-logbook.git
cd ham-radio-logbook

# 2. Ambiente virtuale (consigliato)
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# 3. Installa le dipendenze
pip install -r requirements.txt

# 4. Configura le variabili d'ambiente
cp .env.example .env
# Modifica .env: imposta SECRET_KEY con una stringa casuale

# 5. Inizializza il database
python manage_db.py init

# 6. Avvia
python app.py
```

Aprire il browser su **http://localhost:5000** e registrare il proprio account.

### Avvio rapido (Windows)
```bat
start.bat
```

### Avvio rapido (Linux/macOS)
```bash
./start.sh
```

---

## 🏗️ Architettura

```
Browser / PWA  ──────────────────────────────────────────
  index.html · app.js · style.css · sw.js · manifest.json
        │
        │  HTTP / Fetch API (JSON)
        ▼
  Flask (app.py)  ──  auth.py  ──  db.py (SQLite)
                   ──  adif.py
                   ──  mapforham.py  ──►  MapForHam API
                                    ──►  HamDB.org API
```

**Stack:**
- **Backend:** Python / Flask + SQLite (zero dipendenze esterne dal DB)
- **Frontend:** Vanilla JS ES2020 + Bootstrap 5.3 + Leaflet.js
- **PWA:** Service Worker (cache-first) + IndexedDB (offline queue)

---

## 📁 Struttura del progetto

```
ham-radio-logbook/
├── app.py              # Entry point Flask, tutte le route API
├── auth.py             # Autenticazione multi-utente, rate limiting
├── config.py           # Configurazione da .env
├── db.py               # Layer SQLite: schema, CRUD, migrazioni
├── adif.py             # Parser e generatore formato ADIF
├── mapforham.py        # Client API MapForHam
├── manage_db.py        # CLI gestione database
├── requirements.txt
├── .env.example        # Template variabili d'ambiente
├── docs/
│   ├── TECNICA.md      # Documentazione tecnica per sviluppatori
│   ├── INSTALLAZIONE.md # Guida installazione e produzione
│   └── UTENTE.md       # Manuale utente
└── static/
    ├── index.html      # SPA principale (7 sezioni)
    ├── login.html      # Pagina di login
    ├── register.html   # Pagina di registrazione
    ├── app.js          # Logica SPA (~850 righe)
    ├── style.css
    ├── sw.js           # Service Worker
    ├── manifest.json   # PWA manifest
    └── icons/
```

---

## 🗄️ Database

Schema SQLite con 3 tabelle principali:

```
users          qso                    equipment
────────       ──────────────────     ──────────────────
id             id                     id
username  ──── user_id (FK)           user_id (FK)
password_hash  qso_date               type
email          time_on                name
full_name      callsign               brand / model
mfh_username   mode / band / freq     band_coverage
mfh_api_key    rst_sent / rst_rcvd    power_w / gain_dbi
my_gridsquare  gridsquare / qth       height_m
sync_interval  dxcc / cq_zone         active
               antenna_id (FK) ───────┘
               synced / mfh_id
```

---

## 🔌 API REST (riepilogo)

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/register` | Registrazione nuovo utente |
| POST | `/login` | Login |
| GET | `/logout` | Logout |
| GET/POST | `/api/qso` | Lista / Crea QSO |
| PUT/DELETE | `/api/qso/<id>` | Modifica / Elimina QSO |
| POST | `/api/sync` | Sincronizza con MapForHam |
| GET | `/api/report` | KPI e statistiche |
| GET | `/api/map/qso` | QSO per mappa (filtro periodo) |
| GET/POST | `/api/equipment` | Lista / Crea attrezzatura |
| GET | `/api/export/adif` | Download ADIF |
| GET | `/api/export/csv` | Download CSV |
| GET | `/api/export/pdf` | Download PDF |
| POST | `/api/import/adif` | Importa file ADIF |
| GET | `/api/lookup/<call>` | QRZ lookup cascade |
| GET/POST | `/api/settings` | Impostazioni utente |

---

## 🔧 Gestione database

```bash
python manage_db.py init      # Crea schema e applica migrazioni
python manage_db.py migrate   # Applica migrazioni pendenti
python manage_db.py info      # Statistiche e cronologia migrazioni
python manage_db.py seed      # Inserisce dati demo
python manage_db.py backup    # Backup timestampato
python manage_db.py reset     # ⚠ Reset completo (chiede conferma)
```

---

## 🌐 Deployment in produzione

### ☁️ Render (cloud — raccomandato)

Il modo più semplice per pubblicare online senza gestire server.

**1. Crea il Web Service su [render.com](https://render.com):**
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn -w 1 -b 0.0.0.0:$PORT app:app`

**2. Aggiungi un Persistent Disk** (scheda *Disks*):
- Mount path: `/var/data`

**3. Variabili d'ambiente** (scheda *Environment*):
```
DATABASE_PATH  = /var/data/logbook.db
SECRET_KEY     = <stringa-random-64-chars>
DEBUG          = false
```

> 📖 Guida dettagliata con tutti i passi: [`docs/INSTALLAZIONE.md § 7.5`](docs/INSTALLAZIONE.md)

---

### 🖥️ Gunicorn + Nginx (VPS Linux)

```bash
# Installa Gunicorn
pip install gunicorn

# Avvia
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

Configurazione Nginx minima:
```nginx
server {
    listen 80;
    server_name logbook.mio-dominio.it;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 10M;
    }
}
```

HTTPS gratuito con Let's Encrypt:
```bash
sudo certbot --nginx -d logbook.mio-dominio.it
```

> 📖 Vedere [`docs/INSTALLAZIONE.md`](docs/INSTALLAZIONE.md) per la guida completa con systemd service.

---

## 🔒 Sicurezza

- **Password:** PBKDF2-SHA256 via Werkzeug (mai in chiaro)
- **Sessioni:** cookie HTTPOnly, SameSite=Lax, Secure in produzione
- **Rate limiting:** max 5 tentativi / 5 minuti per IP
- **Header HTTP:** CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **Isolamento dati:** ogni query filtra per `user_id` — impossibile leggere dati altrui

---

## 📚 Documentazione

| Documento | Contenuto |
|-----------|-----------|
| [`docs/TECNICA.md`](docs/TECNICA.md) | Architettura, schema DB, API, moduli, estendibilità |
| [`docs/INSTALLAZIONE.md`](docs/INSTALLAZIONE.md) | Installazione locale, Render (cloud), VPS, Nginx, systemd, HTTPS, backup |
| [`docs/UTENTE.md`](docs/UTENTE.md) | Manuale d'uso completo per l'operatore |

---

## 📜 Licenza

Distribuito sotto licenza **MIT**. Vedere `LICENSE` per i dettagli.

---

<p align="center">
  &copy; <strong>IU8VBG</strong> — Ham Radio Logbook<br>
  <em>73 de IU8VBG</em>
</p>
