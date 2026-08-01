"""Ham Radio Logbook - Flask server."""

from flask import Flask, jsonify, request, send_from_directory, Response, session, redirect
from flask_cors import CORS
import threading
import time
import datetime
import os

import requests
import config
import auth
import db
import adif as adif_mod
import mapforham as mfh

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = config.SECRET_KEY

# -- Session / cookie security ------------------------------------------------
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not config.DEBUG,   # HTTPS only in production
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=config.SESSION_LIFETIME_DAYS),
)

CORS(app)

db.init_db()

# -- Public paths (no login required) -----------------------------------------
# Add paths here to exempt from auth. Keep this list short and explicit.
_PUBLIC_PATHS = frozenset(["/login", "/logout", "/register", "/favicon.ico"])
_PUBLIC_EXTENSIONS = frozenset([".js", ".css", ".svg", ".png", ".ico", ".webmanifest"])
_PUBLIC_FILES = frozenset(["sw.js", "manifest.json", "offline.html"])


@app.before_request
def require_login():
    path = request.path
    if path in _PUBLIC_PATHS:
        return None
    if os.path.basename(path) in _PUBLIC_FILES:
        return None
    if os.path.splitext(path)[1].lower() in _PUBLIC_EXTENSIONS:
        return None
    if not session.get("user_id"):
        if path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Non autenticato"}), 401
        return redirect("/login")


def _uid() -> int:
    """Return the current session user_id."""
    return session["user_id"]


@app.after_request
def add_security_headers(response):
    """Add defensive HTTP headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
        "connect-src 'self' https://api.hamdb.org http://api.hamdb.org "
        "https://www.mapforham.com;"
    )
    return response


# â”€â”€ Background sync state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_sync_lock = threading.Lock()
_sync_state = {
    "last_sync": None,
    "next_sync": None,
    "last_result": None,
}


def _background_sync_loop():
    interval = config.SYNC_INTERVAL_MIN * 60
    while True:
        time.sleep(interval)
        pending = db.get_all_unsynced_qso()
        synced, failed = 0, 0
        for q in pending:
            mfh_user = q.get("mfh_username") or ""
            mfh_key  = q.get("mfh_api_key") or ""
            if not mfh_user or not mfh_key:
                continue
            resp = mfh.insert_qso(mfh_user, mfh_key, q)
            if resp["ok"]:
                try:
                    mfh_id = str(resp["data"].get("id", ""))
                except Exception:
                    mfh_id = None
                db.mark_synced(q["id"], mfh_id)
                synced += 1
            else:
                failed += 1
        now = datetime.datetime.utcnow().isoformat() + "Z"
        nxt = (datetime.datetime.utcnow() + datetime.timedelta(seconds=interval)).isoformat() + "Z"
        with _sync_lock:
            _sync_state["last_sync"] = now
            _sync_state["next_sync"] = nxt
            _sync_state["last_result"] = {"synced": synced, "failed": failed, "total": len(pending)}


_sync_thread = threading.Thread(target=_background_sync_loop, daemon=True)
_sync_thread.start()


# â”€â”€ SPA entry point â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# -- Login / Logout -----------------------------------------------------------

@app.route("/login", methods=["GET"])
def login_page():
    if session.get("user_id"):
        return redirect("/")
    return send_from_directory(app.static_folder, "login.html")


@app.route("/login", methods=["POST"])
def login_post():
    ip = auth._client_ip()
    if not auth._rate_ok(ip):
        wait = auth.remaining_lockout(ip)
        return jsonify({"ok": False, "error": f"Troppi tentativi. Riprova tra {wait}s."}), 429

    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = auth.verify(username, password)
    if user:
        auth._clear_failures(ip)
        session.permanent = True
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"ok": True, "username": user["username"]})
    else:
        auth._record_failure(ip)
        remaining = auth.MAX_ATTEMPTS - len(auth._attempts.get(ip, []))
        return jsonify({
            "ok": False,
            "error": f"Credenziali errate. Tentativi rimasti: {max(0, remaining)}",
        }), 401


@app.route("/register", methods=["GET"])
def register_page():
    if session.get("user_id"):
        return redirect("/")
    return send_from_directory(app.static_folder, "register.html")


@app.route("/register", methods=["POST"])
def register_post():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip().upper()
    password = data.get("password", "")
    confirm  = data.get("confirm", "")
    email    = data.get("email", "").strip()
    full_name = data.get("full_name", "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "Nominativo e password sono obbligatori."}), 400
    if len(username) < 3:
        return jsonify({"ok": False, "error": "Il nominativo deve avere almeno 3 caratteri."}), 400
    if len(password) < 8:
        return jsonify({"ok": False, "error": "La password deve avere almeno 8 caratteri."}), 400
    if password != confirm:
        return jsonify({"ok": False, "error": "Le password non corrispondono."}), 400
    if db.username_exists(username):
        return jsonify({"ok": False, "error": f"Il nominativo '{username}' è già registrato."}), 409

    try:
        user_id = db.create_user(username, password, email, full_name)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 409

    # Auto-login after registration
    session.permanent = True
    session["user_id"] = user_id
    session["username"] = username
    return jsonify({"ok": True, "username": username}), 201


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# â”€â”€ Health / ping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True, "ts": datetime.datetime.utcnow().isoformat() + "Z"})


# â”€â”€ Settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/settings", methods=["GET"])
def get_settings():
    user = db.get_user_by_id(_uid())
    if not user:
        return jsonify({"ok": False, "error": "Utente non trovato"}), 404
    return jsonify({
        "username": user.get("mfh_username") or "",
        "has_key": bool(user.get("mfh_api_key")),
        "sync_interval_min": user.get("sync_interval_min") or config.SYNC_INTERVAL_MIN,
        "my_gridsquare": user.get("my_gridsquare") or "",
        "full_name": user.get("full_name") or "",
        "email": user.get("email") or "",
        "callsign": user.get("username") or "",
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.get_json(force=True)
    update = {}
    if "username" in data:
        update["mfh_username"] = data["username"].strip()
    if "api_key" in data and data["api_key"]:
        update["mfh_api_key"] = data["api_key"].strip()
    if "sync_interval_min" in data:
        try:
            update["sync_interval_min"] = max(1, int(data["sync_interval_min"]))
        except (ValueError, TypeError):
            pass
    if "my_gridsquare" in data:
        update["my_gridsquare"] = data["my_gridsquare"].strip().upper()
    if "full_name" in data:
        update["full_name"] = data["full_name"].strip()
    if "email" in data:
        update["email"] = data["email"].strip()
    db.update_user_settings(_uid(), update)
    return jsonify({"ok": True})


# â”€â”€ Local QSO CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/qso", methods=["GET"])
def list_qso():
    return jsonify(db.get_all_qso(_uid()))


@app.route("/api/qso", methods=["POST"])
def create_qso():
    data = request.get_json(force=True)
    required = {"qso_date", "time_on", "callsign"}
    missing = required - set(data.keys())
    if missing:
        return jsonify({"ok": False, "error": f"Campi obbligatori mancanti: {missing}"}), 400

    uid = _uid()
    if db.qso_exists(data["callsign"], data["qso_date"], data["time_on"], uid):
        return jsonify({"ok": False, "error": "QSO duplicato (stessa callsign, data e ora)"}), 409

    qso_id = db.insert_qso(data, uid)
    result = {"ok": True, "id": qso_id, "mfh": None}

    user = db.get_user_by_id(uid)
    mfh_user = (user or {}).get("mfh_username") or ""
    mfh_key  = (user or {}).get("mfh_api_key") or ""
    if mfh_user and mfh_key:
        resp = mfh.insert_qso(mfh_user, mfh_key, data)
        mfh_id = None
        if resp["ok"]:
            try:
                mfh_id = str(resp["data"].get("id", ""))
            except Exception:
                pass
            db.mark_synced(qso_id, mfh_id)
            result["mfh"] = {"ok": True, "mfh_id": mfh_id}
        else:
            result["mfh"] = {"ok": False, "error": resp["error"]}

    return jsonify(result), 201


@app.route("/api/qso/<int:qso_id>", methods=["GET"])
def get_qso(qso_id):
    q = db.get_qso(qso_id, _uid())
    if not q:
        return jsonify({"ok": False, "error": "QSO non trovato"}), 404
    return jsonify(q)


@app.route("/api/qso/<int:qso_id>", methods=["PUT"])
def update_qso(qso_id):
    data = request.get_json(force=True)
    if not db.update_qso(qso_id, _uid(), data):
        return jsonify({"ok": False, "error": "Aggiornamento fallito"}), 400
    return jsonify({"ok": True})


@app.route("/api/qso/<int:qso_id>", methods=["DELETE"])
def delete_qso_local(qso_id):
    uid = _uid()
    q = db.get_qso(qso_id, uid)
    if not q:
        return jsonify({"ok": False, "error": "QSO non trovato"}), 404

    result = {"ok": True, "mfh": None}

    user = db.get_user_by_id(uid)
    mfh_user = (user or {}).get("mfh_username") or ""
    mfh_key  = (user or {}).get("mfh_api_key") or ""
    if q.get("synced") and q.get("mfh_id") and mfh_user and mfh_key:
        resp = mfh.delete_qso(mfh_user, mfh_key, q["mfh_id"])
        result["mfh"] = resp

    db.delete_qso(qso_id, uid)
    return jsonify(result)


# â”€â”€ Sync â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/sync", methods=["POST"])
def sync_all():
    uid = _uid()
    user = db.get_user_by_id(uid)
    mfh_user = (user or {}).get("mfh_username") or ""
    mfh_key  = (user or {}).get("mfh_api_key") or ""
    if not mfh_user or not mfh_key:
        return jsonify({"ok": False, "error": "Credenziali MFH non configurate"}), 400

    pending = db.get_unsynced_qso(uid)
    synced, failed = 0, 0
    for q in pending:
        resp = mfh.insert_qso(mfh_user, mfh_key, q)
        if resp["ok"]:
            try:
                mfh_id = str(resp["data"].get("id", ""))
            except Exception:
                mfh_id = None
            db.mark_synced(q["id"], mfh_id)
            synced += 1
        else:
            failed += 1

    now = datetime.datetime.utcnow().isoformat() + "Z"
    nxt = (datetime.datetime.utcnow() +
           datetime.timedelta(minutes=config.SYNC_INTERVAL_MIN)).isoformat() + "Z"
    with _sync_lock:
        _sync_state["last_sync"] = now
        _sync_state["next_sync"] = nxt
        _sync_state["last_result"] = {"synced": synced, "failed": failed, "total": len(pending)}

    return jsonify({"ok": True, "synced": synced, "failed": failed, "pending": len(pending)})


@app.route("/api/sync/status")
def sync_status():
    uid = _uid()
    with _sync_lock:
        state = dict(_sync_state)
    state["pending"] = len(db.get_unsynced_qso(uid))
    user = db.get_user_by_id(uid)
    state["configured"] = bool((user or {}).get("mfh_username") and (user or {}).get("mfh_api_key"))
    state["sync_interval_min"] = config.SYNC_INTERVAL_MIN
    return jsonify(state)


# â”€â”€ Remote logbook from MFH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/mfh/logbook", methods=["GET"])
def mfh_logbook():
    user = db.get_user_by_id(_uid())
    mfh_user = (user or {}).get("mfh_username") or ""
    mfh_key  = (user or {}).get("mfh_api_key") or ""
    if not mfh_user or not mfh_key:
        return jsonify({"ok": False, "error": "Credenziali MFH non configurate"}), 400
    return jsonify(mfh.read_logbook(mfh_user, mfh_key))


@app.route("/api/lookup/<callsign>", methods=["GET"])
def lookup_callsign(callsign):
    """Cascade callsign lookup: MapForHam → HamDB.org (free fallback)."""
    callsign = callsign.upper().strip()

    # 1. Try MapForHam callbook
    user = db.get_user_by_id(_uid())
    mfh_key = (user or {}).get("mfh_api_key") or ""
    if mfh_key:
        res = mfh.lookup_callsign(callsign, mfh_key)
        if res.get("ok"):
            data = res.get("data")
            if isinstance(data, list) and data:
                data = data[0]
            if data:
                fname = (data.get("first_name") or "").strip()
                lname = (data.get("name") or "").strip()
                return jsonify({
                    "ok": True, "callsign": callsign,
                    "name": f"{fname} {lname}".strip(),
                    "qth": data.get("qth") or data.get("city", ""),
                    "gridsquare": data.get("gridsquare") or data.get("locator", ""),
                    "country": data.get("country", ""),
                    "dxcc": str(data.get("dxcc") or ""),
                    "cq_zone": str(data.get("cq_zone") or data.get("cq") or ""),
                    "itu_zone": str(data.get("itu_zone") or data.get("itu") or ""),
                    "source": "MapForHam",
                })

    # 2. Fallback: HamDB.org — free, no API key required
    try:
        r = requests.get(
            f"http://api.hamdb.org/{callsign}/json/hamlogbook",
            timeout=5
        )
        h = r.json().get("hamdb", {})
        if h.get("message") == "OK":
            fname = (h.get("fname") or "").strip()
            lname = (h.get("name") or "").strip()
            return jsonify({
                "ok": True, "callsign": callsign,
                "name": f"{fname} {lname}".strip(),
                "qth": (h.get("addr2") or "").strip(),
                "gridsquare": h.get("grid", ""),
                "country": h.get("country", ""),
                "dxcc": "", "cq_zone": "", "itu_zone": "",
                "source": "HamDB",
            })
    except Exception:
        pass

    return jsonify({"ok": False, "callsign": callsign})


@app.route("/api/mfh/callbook/<callsign>", methods=["GET"])
def mfh_callbook(callsign):
    user = db.get_user_by_id(_uid())
    mfh_key = (user or {}).get("mfh_api_key") or ""
    if not mfh_key:
        return jsonify({"ok": False, "error": "API key MFH non configurata"}), 400
    return jsonify(mfh.lookup_callsign(callsign, mfh_key))


# â”€â”€ ADIF export / import â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/export/adif", methods=["GET"])
def export_adif():
    qso_list = db.get_all_qso(_uid())
    content = adif_mod.logbook_to_adif(qso_list)
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=logbook.adi"},
    )


@app.route("/api/import/adif", methods=["POST"])
def import_adif():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Nessun file inviato"}), 400
    text = request.files["file"].read().decode("utf-8", errors="ignore")
    records = adif_mod.parse_adif(text)
    uid = _uid()
    imported, skipped = 0, 0
    for rec in records:
        if db.qso_exists(rec["callsign"], rec["qso_date"], rec["time_on"], uid):
            skipped += 1
        else:
            db.insert_qso(rec, uid)
            imported += 1
    return jsonify({"ok": True, "imported": imported, "skipped": skipped})


# ── CSV export ────────────────────────────────────────────────────────────────

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    import csv, io
    qso_list = db.get_all_qso(_uid())
    columns = [
        "qso_date", "qso_date_off", "time_on", "time_off", "callsign", "name",
        "mode", "freq", "band", "rst_sent", "rst_rcvd", "gridsquare",
        "my_gridsquare", "qth", "state", "dxcc", "cq_zone", "itu_zone",
        "tx_pwr", "my_pota_ref", "pota_ref", "comment", "notes",
        "antenna_id", "synced", "mfh_id",
    ]
    buf = io.StringIO()
    # UTF-8 BOM for Excel compatibility
    buf.write("\ufeff")
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for q in qso_list:
        writer.writerow({c: q.get(c, "") for c in columns})
    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=logbook.csv"},
    )


# â”€â”€ PDF export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/export/pdf", methods=["GET"])
def export_pdf():
    from fpdf import FPDF
    import io as _io

    qso_list = db.get_all_qso(_uid())

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.set_fill_color(26, 58, 92)
            self.set_text_color(240, 180, 41)
            self.cell(0, 12, "Ham Radio Logbook", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(100, 100, 100)
            self.set_font("Helvetica", "", 8)
            user = db.get_user_by_id(session.get("user_id", 0)) or {}
            owner = user.get("username") or "—"
            self.cell(0, 6, f"Operatore: {owner}    Totale QSO: {len(qso_list)}    Generato: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                      align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, f"Pag. {self.page_no()}", align="C")

    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # Column definitions: (header, width, align)
    cols = [
        ("Data",      22, "C"),
        ("Ora ON",    16, "C"),
        ("Nominativo",26, "C"),
        ("Banda",     14, "C"),
        ("Modo",      16, "C"),
        ("Freq MHz",  20, "R"),
        ("RST →",     14, "C"),
        ("RST ←",     14, "C"),
        ("Nome",      26, "L"),
        ("QTH",       26, "L"),
        ("DXCC",      14, "C"),
        ("CQZ",       10, "C"),
        ("Pwr W",     13, "R"),
        ("Sync",      10, "C"),
    ]

    # Table header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(26, 58, 92)
    pdf.set_text_color(255, 255, 255)
    for hdr, w, a in cols:
        pdf.cell(w, 7, hdr, border=1, align=a, fill=True)
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 30, 30)
    for i, q in enumerate(qso_list):
        fill = (i % 2 == 0)
        pdf.set_fill_color(240, 245, 252) if fill else pdf.set_fill_color(255, 255, 255)
        synced_label = "âœ“" if q.get("synced") else "â€¦"
        row = [
            q.get("qso_date", ""),
            q.get("time_on", ""),
            q.get("callsign", ""),
            q.get("band", ""),
            q.get("mode", ""),
            q.get("freq", ""),
            q.get("rst_sent", ""),
            q.get("rst_rcvd", ""),
            q.get("name", ""),
            q.get("qth", ""),
            q.get("dxcc", ""),
            q.get("cq_zone", ""),
            str(q.get("tx_pwr", "")),
            synced_label,
        ]
        for val, (_, w, a) in zip(row, cols):
            pdf.cell(w, 6, str(val)[:20], border=1, align=a, fill=fill)
        pdf.ln()

    buf = _io.BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return Response(
        buf.read(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=logbook.pdf"},
    )


# â”€â”€ Map data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route("/api/map/qso", methods=["GET"])
def map_qso():
    uid = _uid()
    period = request.args.get("period", "today")
    qsos = db.get_qso_for_map(period, uid)

    user = db.get_user_by_id(uid)
    my_gs = (user or {}).get("my_gridsquare") or ""
    if not my_gs:
        for q in qsos:
            if q.get("my_gridsquare"):
                my_gs = q["my_gridsquare"]
                break

    bands = {}
    modes = {}
    countries = set()
    for q in qsos:
        if q.get("band"):
            bands[q["band"]] = bands.get(q["band"], 0) + 1
        if q.get("mode"):
            modes[q["mode"]] = modes.get(q["mode"], 0) + 1
        cs = q.get("callsign", "")
        prefix = ""
        for ch in cs:
            if ch.isdigit():
                break
            prefix += ch
        if prefix:
            countries.add(prefix)

    return jsonify({
        "ok": True,
        "my_gridsquare": my_gs,
        "period": period,
        "qsos": qsos,
        "stats": {
            "total": len(qsos),
            "with_grid": sum(1 for q in qsos if q.get("gridsquare")),
            "countries": len(countries),
            "top_band": max(bands, key=bands.get) if bands else None,
            "top_mode": max(modes, key=modes.get) if modes else None,
            "bands": bands,
        },
    })


# ── Equipment CRUD ────────────────────────────────────────────────────────────

@app.route("/api/equipment", methods=["GET"])
def list_equipment():
    eq_type = request.args.get("type")
    return jsonify(db.get_all_equipment(_uid(), eq_type))


@app.route("/api/equipment", methods=["POST"])
def create_equipment():
    data = request.get_json(force=True)
    if not data.get("name"):
        return jsonify({"ok": False, "error": "Il campo 'name' è obbligatorio"}), 400
    eq_id = db.insert_equipment(data, _uid())
    return jsonify({"ok": True, "id": eq_id}), 201


@app.route("/api/equipment/<int:eq_id>", methods=["GET"])
def get_equipment_item(eq_id):
    eq = db.get_equipment(eq_id, _uid())
    if not eq:
        return jsonify({"ok": False, "error": "Non trovato"}), 404
    return jsonify(eq)


@app.route("/api/equipment/<int:eq_id>", methods=["PUT"])
def update_equipment_item(eq_id):
    data = request.get_json(force=True)
    if not db.update_equipment(eq_id, _uid(), data):
        return jsonify({"ok": False, "error": "Aggiornamento fallito"}), 400
    return jsonify({"ok": True})


@app.route("/api/equipment/<int:eq_id>", methods=["DELETE"])
def delete_equipment_item(eq_id):
    if not db.delete_equipment(eq_id, _uid()):
        return jsonify({"ok": False, "error": "Non trovato"}), 404
    return jsonify({"ok": True})


# ── Report ────────────────────────────────────────────────────────────────────

@app.route("/api/report")
def report():
    return jsonify(db.get_report_stats(_uid()))


# ── Current user info ─────────────────────────────────────────────────────────

@app.route("/api/me")
def me():
    user = db.get_user_by_id(_uid())
    if not user:
        return jsonify({"ok": False}), 404
    return jsonify({
        "ok": True,
        "id": user["id"],
        "username": user["username"],
        "full_name": user.get("full_name") or "",
        "email": user.get("email") or "",
    })


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

