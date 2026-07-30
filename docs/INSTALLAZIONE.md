# Guida all'Installazione — Ham Radio Logbook

> **Versione:** 1.1 · **Autore:** IU8VBG

---

## Indice

1. [Prerequisiti](#1-prerequisiti)
2. [Download e preparazione](#2-download-e-preparazione)
3. [Installazione dipendenze Python](#3-installazione-dipendenze-python)
4. [Configurazione `.env`](#4-configurazione-env)
5. [Inizializzazione del database](#5-inizializzazione-del-database)
6. [Primo avvio in sviluppo](#6-primo-avvio-in-sviluppo)
7. [Deployment in produzione](#7-deployment-in-produzione)
   - 7.1 [Gunicorn](#71-gunicorn)
   - 7.2 [Nginx come reverse proxy](#72-nginx-come-reverse-proxy)
   - 7.3 [Systemd service](#73-systemd-service)
   - 7.4 [HTTPS con Let's Encrypt](#74-https-con-lets-encrypt)
8. [Aggiornamento](#8-aggiornamento)
9. [Backup e ripristino](#9-backup-e-ripristino)
10. [Risoluzione problemi comuni](#10-risoluzione-problemi-comuni)

---

## 1. Prerequisiti

| Software | Versione minima | Note |
|----------|----------------|------|
| **Python** | 3.9+ | Verificare con `python --version` |
| **pip** | 21+ | Incluso con Python |
| **Git** | qualsiasi | Opzionale, per clonare |

> **Windows**: scarica Python da [python.org](https://www.python.org/downloads/) e seleziona "Add Python to PATH" durante l'installazione.
>
> **Linux/macOS**: Python è spesso già installato. In caso contrario: `sudo apt install python3 python3-pip` (Debian/Ubuntu) o `brew install python` (macOS).

---

## 2. Download e preparazione

### Opzione A — Con Git
```bash
git clone https://github.com/IU8VBG/ham-radio-logbook.git
cd ham-radio-logbook
```

### Opzione B — Download manuale
Scaricare il file ZIP del progetto, estrarlo e aprire un terminale nella cartella estratta.

### Ambiente virtuale (consigliato)
```bash
# Crea l'ambiente virtuale
python -m venv venv

# Attivalo
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

---

## 3. Installazione dipendenze Python

```bash
pip install -r requirements.txt
```

**Pacchetti installati:**

| Pacchetto | Scopo |
|-----------|-------|
| `flask` | Web framework |
| `flask-cors` | CORS headers |
| `requests` | HTTP client per API esterne |
| `fpdf2` | Generazione PDF |
| `python-dotenv` | Caricamento variabili `.env` |

---

## 4. Configurazione `.env`

Copiare il file di esempio e personalizzarlo:

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Aprire `.env` con un editor di testo e compilare i campi:

```ini
# ── Sicurezza (OBBLIGATORIO in produzione) ────────────────────
# Generare con: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=cambia-questo-valore-con-una-stringa-casuale-lunga

# ── Server ────────────────────────────────────────────────────
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=0          # 0 = produzione, 1 = sviluppo

# ── Sessioni ──────────────────────────────────────────────────
SESSION_LIFETIME_DAYS=7

# ── Sync automatico (globale, fallback) ───────────────────────
SYNC_INTERVAL_MIN=5
```

> **Nota:** Le credenziali MapForHam (username e API key) sono ora configurate **per ogni utente** dalla sezione Impostazioni dell'app, non nel file `.env`.

### Generare la SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Copiare l'output nel campo `SECRET_KEY` del file `.env`.

---

## 5. Inizializzazione del database

```bash
python manage_db.py init
```

Output atteso:
```
Database: /percorso/logbook.db
Creazione schema... OK
Applicazione migrazioni... OK
✓ Database inizializzato correttamente.
```

### Comandi disponibili di `manage_db.py`

```bash
python manage_db.py init      # Crea schema e applica migrazioni
python manage_db.py migrate   # Applica solo le migrazioni pendenti
python manage_db.py info      # Mostra statistiche e cronologia migrazioni
python manage_db.py seed      # Inserisce dati di esempio (sviluppo)
python manage_db.py reset     # ⚠ Cancella tutto e ricrea (chiede conferma)
python manage_db.py backup    # Copia DB in file di backup timestampato
```

---

## 6. Primo avvio in sviluppo

### Windows
```bat
start.bat
```

### Linux/macOS
```bash
chmod +x start.sh
./start.sh
```

### Manuale
```bash
python app.py
```

L'applicazione sarà disponibile su: **http://localhost:5000**

Al primo accesso, aprire `http://localhost:5000/register` per creare il proprio account.

---

## 7. Deployment in produzione

> ⚠️ **Non usare mai il server di sviluppo Flask (`FLASK_DEBUG=1`) in produzione.**

### 7.1 Gunicorn

Installare Gunicorn:
```bash
pip install gunicorn
```

Avvio manuale (test):
```bash
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

**Parametri consigliati:**
- `-w 2` — 2 worker (per applicazione single-threaded con SQLite è sufficiente)
- `-b 127.0.0.1:5000` — bind solo su loopback (nginx fa da proxy)

---

### 7.2 Nginx come reverse proxy

Installare Nginx:
```bash
sudo apt install nginx
```

Creare il file di configurazione `/etc/nginx/sites-available/logbook`:
```nginx
server {
    listen 80;
    server_name logbook.tuo-dominio.it;  # oppure indirizzo IP del server

    # Redirect a HTTPS (abilitare dopo aver configurato SSL)
    # return 301 https://$host$request_uri;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Timeout per export PDF/CSV su logbook grandi
        proxy_read_timeout 60s;

        # File upload (import ADIF)
        client_max_body_size 10M;
    }

    # Cache degli asset statici
    location /static/ {
        proxy_pass       http://127.0.0.1:5000;
        expires          7d;
        add_header       Cache-Control "public, immutable";
    }
}
```

Abilitare il sito:
```bash
sudo ln -s /etc/nginx/sites-available/logbook /etc/nginx/sites-enabled/
sudo nginx -t         # verifica configurazione
sudo systemctl reload nginx
```

---

### 7.3 Systemd service

Creare il file `/etc/systemd/system/logbook.service`:

```ini
[Unit]
Description=Ham Radio Logbook
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/logbook
Environment="PATH=/var/www/logbook/venv/bin"
ExecStart=/var/www/logbook/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5000 \
    --timeout 60 \
    --access-logfile /var/log/logbook/access.log \
    --error-logfile /var/log/logbook/error.log \
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Abilitare e avviare:
```bash
sudo mkdir -p /var/log/logbook
sudo chown www-data:www-data /var/log/logbook
sudo systemctl daemon-reload
sudo systemctl enable logbook
sudo systemctl start logbook
sudo systemctl status logbook   # verifica
```

---

### 7.4 HTTPS con Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d logbook.tuo-dominio.it
```

Certbot configurerà automaticamente Nginx per HTTPS e imposterà il rinnovo automatico del certificato.

Verificare il rinnovo automatico:
```bash
sudo certbot renew --dry-run
```

---

## 8. Aggiornamento

```bash
# 1. Fermare il servizio
sudo systemctl stop logbook

# 2. Backup del database
python manage_db.py backup

# 3. Aggiornare il codice
git pull

# 4. Aggiornare le dipendenze
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 5. Applicare le migrazioni
python manage_db.py migrate

# 6. Riavviare il servizio
sudo systemctl start logbook
```

---

## 9. Backup e ripristino

### Backup manuale
```bash
python manage_db.py backup
# Crea: logbook_backup_YYYYMMDD_HHMMSS.db
```

### Backup automatico con cron
```bash
# Apri crontab
crontab -e

# Backup giornaliero alle 02:00
0 2 * * * cd /var/www/logbook && /var/www/logbook/venv/bin/python manage_db.py backup >> /var/log/logbook/backup.log 2>&1
```

### Ripristino
```bash
# Il DB è un singolo file SQLite — basta copiarlo
cp logbook_backup_20260101_020000.db logbook.db
sudo systemctl restart logbook
```

---

## 10. Risoluzione problemi comuni

### ❌ `python: command not found`
Su alcuni sistemi il comando è `python3`. Usare `python3 app.py` e `pip3 install`.

### ❌ `ModuleNotFoundError: No module named 'flask'`
L'ambiente virtuale non è attivo. Eseguire:
```bash
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### ❌ Database locked / OperationalError
SQLite non supporta scritture concorrenti. Con 2+ worker Gunicorn può verificarsi. Soluzione: usare 1 worker (`-w 1`) o configurare WAL mode nel database:
```python
# In db.py, in get_conn(), aggiungere:
conn.execute("PRAGMA journal_mode=WAL")
```

### ❌ Il Service Worker non si aggiorna
Svuotare la cache del browser: DevTools → Application → Storage → Clear site data.

### ❌ Login fallisce sempre
Verificare che `SECRET_KEY` sia uguale tra riavvii (non rigenerarla ad ogni avvio). Assicurarsi che `.env` sia correttamente configurato.

### ❌ L'app non è raggiungibile dall'esterno
1. Verificare che `FLASK_HOST=0.0.0.0` (non `127.0.0.1`)
2. Verificare il firewall: `sudo ufw allow 5000` (o `443` per HTTPS)
3. Verificare che il router abbia il port forwarding configurato

### ❌ Export PDF fallisce
```bash
pip install fpdf2 --upgrade
```
