import sqlite3
import os
import re as _re

# ── DXCC prefix helpers ──────────────────────────────────────────────────────
def _callsign_prefix(callsign: str) -> str:
    """Extract DXCC entity prefix from a callsign (e.g. DL5KAT → DL)."""
    cs = callsign.upper().split('/')[0]
    m = _re.match(r'^(.*)\d[A-Z]+$', cs)
    return m.group(1) if m else cs[:2]

_DXCC_NAMES = {
    'I':'Italia','IK':'Italia','IU':'Italia','IZ':'Italia','IW':'Italia',
    'IN':'Italia','IO':'Italia','II':'Italia','IS':'Sardegna',
    'DL':'Germania','DK':'Germania','DJ':'Germania','DF':'Germania',
    'DB':'Germania','DC':'Germania','DG':'Germania','DH':'Germania',
    'DD':'Germania','DE':'Germania','DM':'Germania',
    'EA':'Spagna','EB':'Spagna','EC':'Spagna','ED':'Spagna',
    'EE':'Spagna','EF':'Spagna','EG':'Spagna','EH':'Spagna',
    'F':'Francia',
    'G':'UK','M':'UK','GW':'Galles','GM':'Scozia',
    'GI':'N.Irlanda','GJ':'Jersey','GU':'Guernsey','GD':'I.of Man',
    'ON':'Belgio','OO':'Belgio','OP':'Belgio','OR':'Belgio',
    'PA':'Olanda','PB':'Olanda','PC':'Olanda','PD':'Olanda',
    'PE':'Olanda','PF':'Olanda','PG':'Olanda','PH':'Olanda',
    'HB':'Svizzera','OE':'Austria',
    'SM':'Svezia','SA':'Svezia','SB':'Svezia','SC':'Svezia',
    'SD':'Svezia','SE':'Svezia','SG':'Svezia','SI':'Svezia',
    'OH':'Finlandia','LA':'Norvegia','OZ':'Danimarca',
    'SP':'Polonia','SQ':'Polonia','SR':'Polonia',
    'OK':'Rep. Ceca','OL':'Rep. Ceca','OM':'Slovacchia',
    'HA':'Ungheria','HG':'Ungheria','YO':'Romania','LZ':'Bulgaria',
    'SV':'Grecia','TA':'Turchia',
    'UA':'Russia','RA':'Russia','RK':'Russia','RM':'Russia',
    'RN':'Russia','RU':'Russia','RV':'Russia','RW':'Russia',
    'RX':'Russia','RZ':'Russia',
    'K':'USA','W':'USA','N':'USA','AA':'USA','AB':'USA',
    'AC':'USA','AD':'USA','AE':'USA','AF':'USA','AG':'USA','AK':'USA',
    'VE':'Canada','VA':'Canada','VO':'Canada','VY':'Canada',
    'JA':'Giappone','JH':'Giappone','JR':'Giappone',
    'VK':'Australia','ZL':'N. Zelanda',
    'PY':'Brasile','PP':'Brasile','PU':'Brasile',
    'LU':'Argentina','CE':'Cile','XE':'Messico',
    'BY':'Cina','BG':'Cina','BA':'Cina','BD':'Cina',
    'HL':'Corea del Sud','VU':'India','ZS':'Sud Africa',
    '9A':'Croazia','YU':'Serbia','E7':'Bosnia',
    'S5':'Slovenia','YL':'Lettonia','LY':'Lituania','ES':'Estonia',
    '4X':'Israele','4Z':'Israele',
}

# On Render (or any server with a persistent disk), set DATABASE_PATH to the
# volume mount path, e.g. DATABASE_PATH=/var/data/logbook.db
# Falls back to the app directory for local development.
_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logbook.db")
DB_PATH = os.environ.get("DATABASE_PATH", _default_db)

# Ensure the parent directory exists (important when using a volume mount)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email             TEXT,
    password_hash     TEXT NOT NULL,
    full_name         TEXT,
    mfh_username      TEXT DEFAULT '',
    mfh_api_key       TEXT DEFAULT '',
    my_gridsquare     TEXT DEFAULT '',
    sync_interval_min INTEGER DEFAULT 5,
    is_active         INTEGER DEFAULT 1,
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qso (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    qso_date        TEXT NOT NULL,
    qso_date_off    TEXT,
    time_on         TEXT NOT NULL,
    time_off        TEXT,
    callsign        TEXT NOT NULL,
    name            TEXT,
    mode            TEXT,
    freq            TEXT,
    band            TEXT,
    rst_sent        TEXT,
    rst_rcvd        TEXT,
    gridsquare      TEXT,
    my_gridsquare   TEXT,
    qth             TEXT,
    state           TEXT,
    dxcc            TEXT,
    cq_zone         TEXT,
    itu_zone        TEXT,
    tx_pwr          TEXT,
    my_pota_ref     TEXT,
    pota_ref        TEXT,
    comment         TEXT,
    notes           TEXT,
    mfh_id          TEXT,
    antenna_id      INTEGER,
    synced          INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS equipment (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    type          TEXT NOT NULL DEFAULT 'radio',
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
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        run_migrations(conn)


# ── Versioned migrations ──────────────────────────────────────────────────────
# Each entry: (version: int, description: str, sql: str)
# Add new migrations at the END of the list — never change existing ones.
MIGRATIONS = [
    (1, "Initial schema (qso + equipment tables)", None),
    (2, "Add antenna_id to qso",  "ALTER TABLE qso ADD COLUMN antenna_id INTEGER"),
    (3, "Add dxcc to qso",        "ALTER TABLE qso ADD COLUMN dxcc TEXT"),
    (4, "Add cq_zone to qso",     "ALTER TABLE qso ADD COLUMN cq_zone TEXT"),
    (5, "Add itu_zone to qso",    "ALTER TABLE qso ADD COLUMN itu_zone TEXT"),
    (6, "Add user_id to qso",     "ALTER TABLE qso ADD COLUMN user_id INTEGER"),
    (7, "Add user_id to equipment", "ALTER TABLE equipment ADD COLUMN user_id INTEGER"),
]

_MIGRATION_TABLE = """
CREATE TABLE IF NOT EXISTS _migrations (
    version     INTEGER PRIMARY KEY,
    description TEXT,
    applied_at  TEXT DEFAULT (datetime('now'))
);
"""


def run_migrations(conn=None):
    """Apply any pending migrations; safe to call on both new and existing DBs."""
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    try:
        conn.executescript(_MIGRATION_TABLE)
        applied = {r[0] for r in conn.execute("SELECT version FROM _migrations").fetchall()}
        for version, desc, sql in MIGRATIONS:
            if version in applied:
                continue
            if sql:
                try:
                    conn.execute(sql)
                except Exception:
                    pass  # column/object already exists from a manual schema change
            conn.execute(
                "INSERT OR IGNORE INTO _migrations (version, description) VALUES (?, ?)",
                (version, desc)
            )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


# ── User management ───────────────────────────────────────────────────────────

def create_user(username: str, password: str, email: str = "", full_name: str = "") -> int:
    """Create a new user. Raises ValueError on duplicate username."""
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash(password)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash, full_name) VALUES (?,?,?,?)",
                (username.strip(), email.strip(), pw_hash, full_name.strip()),
            )
            return cur.lastrowid
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            raise ValueError(f"Il nominativo '{username}' è già registrato.")
        raise


def get_user_by_id(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username.strip(),)
        ).fetchone()
        return dict(row) if row else None


def verify_user_password(username: str, password: str) -> dict | None:
    """Return the user dict if credentials are valid, else None."""
    from werkzeug.security import check_password_hash
    user = get_user_by_username(username)
    if not user or not user.get("is_active"):
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None


def username_exists(username: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username.strip(),)
        ).fetchone()
        return row is not None


def update_user_settings(user_id: int, data: dict) -> bool:
    """Update per-user settings (mfh_username, mfh_api_key, my_gridsquare, sync_interval_min)."""
    allowed = ["mfh_username", "mfh_api_key", "my_gridsquare", "sync_interval_min", "full_name", "email"]
    cols = [f for f in allowed if f in data]
    if not cols:
        return False
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    values = [data[c] for c in cols] + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    return True


def get_all_users() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, email, full_name, is_active, created_at FROM users ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def insert_qso(data: dict, user_id: int) -> int:
    fields = [
        "user_id", "qso_date", "qso_date_off", "time_on", "time_off", "callsign", "name",
        "mode", "freq", "band", "rst_sent", "rst_rcvd", "gridsquare",
        "my_gridsquare", "qth", "state", "dxcc", "cq_zone", "itu_zone",
        "tx_pwr", "my_pota_ref", "pota_ref",
        "comment", "notes", "mfh_id", "antenna_id", "synced",
    ]
    row = dict(data)
    row["user_id"] = user_id
    cols = [f for f in fields if f in row]
    placeholders = ", ".join("?" for _ in cols)
    values = [row[c] for c in cols]
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO qso ({', '.join(cols)}) VALUES ({placeholders})", values
        )
        return cur.lastrowid


def get_all_qso(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM qso WHERE user_id = ? ORDER BY qso_date DESC, time_on DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_qso(qso_id: int, user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM qso WHERE id = ? AND user_id = ?", (qso_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def update_qso(qso_id: int, user_id: int, data: dict) -> bool:
    allowed = [
        "qso_date", "qso_date_off", "time_on", "time_off", "callsign", "name",
        "mode", "freq", "band", "rst_sent", "rst_rcvd", "gridsquare",
        "my_gridsquare", "qth", "state", "dxcc", "cq_zone", "itu_zone",
        "tx_pwr", "my_pota_ref", "pota_ref",
        "comment", "notes", "mfh_id", "antenna_id", "synced",
    ]
    cols = [f for f in allowed if f in data]
    if not cols:
        return False
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    values = [data[c] for c in cols] + [qso_id, user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE qso SET {set_clause} WHERE id = ? AND user_id = ?", values)
    return True


def delete_qso(qso_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM qso WHERE id = ? AND user_id = ?", (qso_id, user_id))
        return cur.rowcount > 0


def get_unsynced_qso(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM qso WHERE synced = 0 AND user_id = ? ORDER BY qso_date, time_on",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_unsynced_qso() -> list:
    """Return all unsynced QSOs across all users (for background sync thread)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT q.*, u.mfh_username, u.mfh_api_key "
            "FROM qso q JOIN users u ON q.user_id = u.id "
            "WHERE q.synced = 0 ORDER BY q.qso_date, q.time_on"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_synced(qso_id: int, mfh_id=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE qso SET synced = 1, mfh_id = ? WHERE id = ?", (mfh_id, qso_id)
        )


def qso_exists(callsign: str, qso_date: str, time_on: str, user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM qso WHERE callsign = ? AND qso_date = ? AND time_on = ? AND user_id = ?",
            (callsign.upper(), qso_date, time_on, user_id),
        ).fetchone()
        return row is not None


def get_report_stats(user_id: int) -> dict:
    """Return aggregated stats for the report page, scoped to user."""
    import datetime as _dt

    with get_conn() as conn:
        uid = (user_id,)

        total = conn.execute("SELECT COUNT(*) FROM qso WHERE user_id=?", uid).fetchone()[0]

        last_row = conn.execute(
            "SELECT * FROM qso WHERE user_id=? ORDER BY qso_date DESC, time_on DESC LIMIT 1", uid
        ).fetchone()
        last_qso = dict(last_row) if last_row else None

        band_rows = conn.execute(
            "SELECT band, COUNT(*) AS n FROM qso WHERE user_id=? AND band != '' AND band IS NOT NULL "
            "GROUP BY band ORDER BY n DESC", uid
        ).fetchall()
        bands_all = [{"band": r["band"], "count": r["n"]} for r in band_rows]
        top_band = bands_all[0] if bands_all else None

        mode_rows = conn.execute(
            "SELECT mode, COUNT(*) AS n FROM qso WHERE user_id=? AND mode != '' AND mode IS NOT NULL "
            "GROUP BY mode ORDER BY n DESC", uid
        ).fetchall()
        modes_all = [{"mode": r["mode"], "count": r["n"]} for r in mode_rows]
        top_mode = modes_all[0] if modes_all else None

        first_of_month = _dt.date.today().replace(day=1).isoformat()
        month_total = conn.execute(
            "SELECT COUNT(*) FROM qso WHERE user_id=? AND qso_date >= ?", (user_id, first_of_month)
        ).fetchone()[0]

        month_days = conn.execute(
            "SELECT qso_date, COUNT(*) AS n FROM qso WHERE user_id=? AND qso_date >= ? "
            "GROUP BY qso_date ORDER BY qso_date", (user_id, first_of_month)
        ).fetchall()
        qso_per_day = [{"date": r["qso_date"], "count": r["n"]} for r in month_days]

        six_months_ago = (
            _dt.date.today().replace(day=1) - _dt.timedelta(days=150)
        ).isoformat()
        monthly_rows = conn.execute(
            "SELECT substr(qso_date,1,7) AS month, COUNT(*) AS n FROM qso "
            "WHERE user_id=? AND qso_date >= ? GROUP BY month ORDER BY month",
            (user_id, six_months_ago)
        ).fetchall()
        monthly_totals = [{"month": r["month"], "count": r["n"]} for r in monthly_rows]

        time_rows = conn.execute(
            "SELECT time_on, time_off FROM qso WHERE user_id=? "
            "AND time_on IS NOT NULL AND time_off IS NOT NULL "
            "AND time_on != '' AND time_off != ''", uid
        ).fetchall()
        total_minutes = 0
        for r in time_rows:
            try:
                on_h,  on_m  = int(r["time_on"][:2]),  int(r["time_on"][3:5])
                off_h, off_m = int(r["time_off"][:2]), int(r["time_off"][3:5])
                diff = (off_h * 60 + off_m) - (on_h * 60 + on_m)
                if diff < 0:
                    diff += 24 * 60
                total_minutes += diff
            except Exception:
                pass

        antenna_rows = conn.execute(
            "SELECT e.name AS antenna, COUNT(q.id) AS n "
            "FROM qso q JOIN equipment e ON q.antenna_id = e.id "
            "WHERE e.type = 'antenna' AND q.user_id=? "
            "GROUP BY e.id, e.name ORDER BY n DESC", uid
        ).fetchall()
        qso_per_antenna = [{"antenna": r["antenna"], "count": r["n"]} for r in antenna_rows]

        all_calls = conn.execute("SELECT callsign FROM qso WHERE user_id=?", uid).fetchall()
        prefix_counts: dict = {}
        for row in all_calls:
            pfx = _callsign_prefix(row["callsign"])
            prefix_counts[pfx] = prefix_counts.get(pfx, 0) + 1
        top_dxcc = sorted(prefix_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_dxcc = [
            {"prefix": pfx, "country": _DXCC_NAMES.get(pfx, pfx), "count": cnt}
            for pfx, cnt in top_dxcc
        ]

        unique_calls = conn.execute(
            "SELECT COUNT(DISTINCT callsign) FROM qso WHERE user_id=?", uid
        ).fetchone()[0]

    return {
        "total": total,
        "unique_callsigns": unique_calls,
        "last_qso": last_qso,
        "top_band": top_band,
        "top_mode": top_mode,
        "bands_all": bands_all,
        "modes_all": modes_all,
        "month_total": month_total,
        "qso_per_day": qso_per_day,
        "monthly_totals": monthly_totals,
        "total_tx_minutes": total_minutes,
        "top_dxcc": top_dxcc,
        "qso_per_antenna": qso_per_antenna,
    }


def get_qso_for_map(period: str, user_id: int) -> list:
    """Return QSOs with gridsquare for the given period, scoped to user."""
    today = __import__("datetime").date.today().isoformat()
    if period == "today":
        extra = f"AND qso_date = '{today}'"
    elif period == "week":
        extra = "AND qso_date >= date('now', '-7 days')"
    elif period == "month":
        extra = "AND qso_date >= date('now', '-30 days')"
    else:
        extra = ""
    sql = f"""
        SELECT id, qso_date, time_on, callsign, name, band, mode,
               gridsquare, my_gridsquare, qth, rst_sent, rst_rcvd
        FROM qso WHERE user_id = ? {extra}
        ORDER BY qso_date DESC, time_on DESC
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()
        return [dict(r) for r in rows]


# ── Equipment CRUD ────────────────────────────────────────────────────────────

EQ_FIELDS = ["user_id", "type", "name", "brand", "model", "band_coverage",
             "power_w", "gain_dbi", "height_m", "connector", "notes", "active"]


def get_all_equipment(user_id: int, eq_type=None) -> list:
    with get_conn() as conn:
        if eq_type:
            rows = conn.execute(
                "SELECT * FROM equipment WHERE user_id=? AND type=? ORDER BY active DESC, name",
                (user_id, eq_type)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM equipment WHERE user_id=? ORDER BY type, active DESC, name",
                (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_equipment(eq_id: int, user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM equipment WHERE id=? AND user_id=?", (eq_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def insert_equipment(data: dict, user_id: int) -> int:
    row = dict(data)
    row["user_id"] = user_id
    cols = [f for f in EQ_FIELDS if f in row]
    placeholders = ", ".join("?" for _ in cols)
    values = [row[c] for c in cols]
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO equipment ({', '.join(cols)}) VALUES ({placeholders})", values
        )
        return cur.lastrowid


def update_equipment(eq_id: int, user_id: int, data: dict) -> bool:
    allowed = ["type", "name", "brand", "model", "band_coverage",
               "power_w", "gain_dbi", "height_m", "connector", "notes", "active"]
    cols = [f for f in allowed if f in data]
    if not cols:
        return False
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    values = [data[c] for c in cols] + [eq_id, user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE equipment SET {set_clause} WHERE id=? AND user_id=?", values)
    return True


def delete_equipment(eq_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM equipment WHERE id=? AND user_id=?", (eq_id, user_id))
        return cur.rowcount > 0

