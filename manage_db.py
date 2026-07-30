#!/usr/bin/env python3
"""
Database management CLI for Ham Radio Logbook.

Usage:
  python manage_db.py init             — Create/update schema and run migrations
  python manage_db.py migrate          — Show and apply pending migrations only
  python manage_db.py reset            — Drop all data and recreate (asks confirmation)
  python manage_db.py seed             — Insert sample QSO and equipment data
  python manage_db.py info             — Show database statistics and migration history
  python manage_db.py backup [FILE]    — Copy the database to a timestamped backup
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

# Make sure we can import project modules regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db

# ── Helpers ───────────────────────────────────────────────────────────────────

def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [s/N] ").strip().lower()
    return answer in ("s", "si", "y", "yes")


def _conn():
    return db.get_conn()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(_args):
    """Initialize schema and apply all pending migrations."""
    print(f"Database: {db.DB_PATH}")
    print("Creazione schema...", end=" ", flush=True)
    with _conn() as conn:
        conn.executescript(db.SCHEMA)
        conn.executescript(db._MIGRATION_TABLE)
    print("OK")
    print("Applicazione migrazioni...", end=" ", flush=True)
    db.run_migrations()
    print("OK")
    print("✓ Database inizializzato correttamente.")


def cmd_migrate(_args):
    """Show pending migrations and apply them."""
    print(f"Database: {db.DB_PATH}")
    with _conn() as conn:
        conn.executescript(db._MIGRATION_TABLE)
        applied = {r[0] for r in conn.execute("SELECT version FROM _migrations").fetchall()}

    pending = [(v, d, s) for v, d, s in db.MIGRATIONS if v not in applied]

    if not pending:
        print("✓ Nessuna migrazione pendente — database aggiornato.")
        return

    print(f"\nMigrazioni pendenti ({len(pending)}):")
    for v, d, _ in pending:
        print(f"  [{v:03d}] {d}")

    if not _confirm("\nApplicare le migrazioni?"):
        print("Annullato.")
        return

    db.run_migrations()
    print(f"✓ {len(pending)} migrazione/i applicata/e.")


def cmd_reset(_args):
    """Drop all data and recreate the database from scratch."""
    print(f"Database: {db.DB_PATH}")
    print("\n⚠️  ATTENZIONE: questa operazione elimina TUTTI i QSO e l'attrezzatura!")

    if not _confirm("Sei sicuro di voler resettare il database?"):
        print("Annullato.")
        return

    nominativo = input("Digita il tuo nominativo per confermare: ").strip().upper()
    if not nominativo:
        print("Nominativo non inserito — operazione annullata.")
        return

    # Backup automatico prima del reset
    if os.path.exists(db.DB_PATH):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db.DB_PATH.replace(".db", f"_backup_{ts}.db")
        shutil.copy2(db.DB_PATH, backup_path)
        print(f"Backup salvato: {backup_path}")
        os.remove(db.DB_PATH)

    db.init_db()
    print(f"✓ Database resettato. Backup automatico creato prima del reset.")


def cmd_seed(_args):
    """Insert sample QSO and equipment records for testing."""
    print(f"Database: {db.DB_PATH}")

    if not os.path.exists(db.DB_PATH):
        print("Database non trovato — esegui prima: python manage_db.py init")
        return

    # Ensure at least one user exists for seed data
    users = db.get_all_users()
    if not users:
        print("  Nessun utente trovato — creo utente demo (IU8VBG / demo1234)...")
        db.create_user("IU8VBG", "demo1234", "demo@example.com", "Utente Demo")
        users = db.get_all_users()
    seed_user_id = users[0]["id"]
    print(f"  Seed utente: {users[0]['username']} (id={seed_user_id})")

    with _conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM qso WHERE user_id=?", (seed_user_id,)).fetchone()[0]

    if existing > 0:
        if not _confirm(f"Ci sono già {existing} QSO per questo utente. Aggiungere i dati di esempio comunque?"):
            print("Annullato.")
            return

    # Sample equipment
    equipment_samples = [
        {"type": "radio",     "name": "ICOM IC-7300",       "brand": "ICOM",      "model": "IC-7300",   "band_coverage": "HF 160-6m",     "power_w": 100},
        {"type": "radio",     "name": "Yaesu FT-817ND",     "brand": "Yaesu",     "model": "FT-817ND",  "band_coverage": "HF/VHF/UHF QRP","power_w": 5},
        {"type": "antenna",   "name": "Dipolo 40m",         "brand": "",          "model": "",          "band_coverage": "40m, 15m",       "gain_dbi": 2.15, "height_m": 8.0},
        {"type": "antenna",   "name": "Vertical GP 10-40m", "brand": "Cushcraft", "model": "R7",        "band_coverage": "10-40m",         "gain_dbi": 3.0,  "height_m": 7.0},
        {"type": "accessory", "name": "MFJ-949E Tuner",     "brand": "MFJ",       "model": "949E",      "band_coverage": "HF 160-10m",     "power_w": 300},
    ]
    eq_ids = []
    for eq in equipment_samples:
        eq_id = db.insert_equipment(eq, 1)  # seed to first user
        eq_ids.append(eq_id)
    print(f"  + {len(equipment_samples)} attrezzature di esempio inserite")

    # Sample QSOs
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = datetime.now().replace(day=max(1, datetime.now().day - 1)).strftime("%Y-%m-%d")
    qso_samples = [
        {"qso_date": today,     "time_on": "09:14", "callsign": "IK2YCK", "name": "Mario",  "band": "20m", "mode": "SSB", "rst_sent": "59",  "rst_rcvd": "58",  "qth": "Milano",  "gridsquare": "JN45", "dxcc": "248", "cq_zone": "15", "itu_zone": "28", "antenna_id": eq_ids[2] if len(eq_ids) > 2 else None},
        {"qso_date": today,     "time_on": "09:42", "callsign": "EA5ISD", "name": "Jose",   "band": "20m", "mode": "FT8", "rst_sent": "-10", "rst_rcvd": "-12", "qth": "Valencia","gridsquare": "IM98", "dxcc": "281", "cq_zone": "14", "itu_zone": "37", "antenna_id": eq_ids[3] if len(eq_ids) > 3 else None},
        {"qso_date": today,     "time_on": "10:05", "callsign": "DL5KAT", "name": "Klaus",  "band": "40m", "mode": "CW",  "rst_sent": "579", "rst_rcvd": "569", "qth": "Berlin",  "gridsquare": "JO62", "dxcc": "230", "cq_zone": "14", "itu_zone": "28"},
        {"qso_date": yesterday, "time_on": "17:33", "callsign": "G4ABC",  "name": "John",   "band": "15m", "mode": "SSB", "rst_sent": "59",  "rst_rcvd": "57",  "qth": "London",  "gridsquare": "IO91", "dxcc": "223", "cq_zone": "14", "itu_zone": "27"},
        {"qso_date": yesterday, "time_on": "18:11", "callsign": "F5JFU",  "name": "Pierre", "band": "10m", "mode": "FM",  "rst_sent": "59",  "rst_rcvd": "59",  "qth": "Paris",   "gridsquare": "JN03", "dxcc": "227", "cq_zone": "14", "itu_zone": "27"},
        {"qso_date": yesterday, "time_on": "14:22", "callsign": "ON4UN",  "name": "John",   "band": "80m", "mode": "SSB", "rst_sent": "55",  "rst_rcvd": "54",  "qth": "Ghent",   "gridsquare": "JO10", "dxcc": "209", "cq_zone": "14", "itu_zone": "27"},
    ]
    for q in qso_samples:
        db.insert_qso(q, 1)  # seed to first user
    print(f"  + {len(qso_samples)} QSO di esempio inseriti")
    print(f"✓ Seed completato.")


def cmd_info(_args):
    """Show database statistics and migration history."""
    if not os.path.exists(db.DB_PATH):
        print(f"Database non trovato: {db.DB_PATH}")
        print("Esegui: python manage_db.py init")
        return

    size_kb = os.path.getsize(db.DB_PATH) / 1024
    print(f"Database: {db.DB_PATH}  ({size_kb:.1f} KB)\n")

    with _conn() as conn:
        # QSO stats
        qso_total   = conn.execute("SELECT COUNT(*) FROM qso").fetchone()[0]
        qso_synced  = conn.execute("SELECT COUNT(*) FROM qso WHERE synced=1").fetchone()[0]
        qso_pending = qso_total - qso_synced
        last_qso    = conn.execute("SELECT callsign, qso_date, time_on FROM qso ORDER BY qso_date DESC, time_on DESC LIMIT 1").fetchone()

        print("── QSO ─────────────────────────────────────────")
        print(f"  Totale:        {qso_total}")
        print(f"  Sincronizzati: {qso_synced}")
        print(f"  In attesa:     {qso_pending}")
        if last_qso:
            print(f"  Ultimo QSO:    {last_qso[0]} il {last_qso[1]} alle {last_qso[2]}")

        # Equipment stats
        eq_total = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
        print(f"\n── Attrezzatura ────────────────────────────────")
        print(f"  Totale: {eq_total}")
        for t in ("radio", "antenna", "accessory"):
            n = conn.execute("SELECT COUNT(*) FROM equipment WHERE type=?", (t,)).fetchone()[0]
            print(f"  {t.capitalize():<12}: {n}")

        # Migrations
        print(f"\n── Migrazioni ──────────────────────────────────")
        try:
            rows = conn.execute("SELECT version, description, applied_at FROM _migrations ORDER BY version").fetchall()
            applied_versions = {r[0] for r in rows}
            for v, d, t in rows:
                print(f"  [{v:03d}] {d:<45}  {t}")
        except Exception:
            applied_versions = set()
            print("  (tabella migrazioni non trovata — esegui init)")

        pending_mig = [(v, d) for v, d, _ in db.MIGRATIONS if v not in applied_versions]
        if pending_mig:
            print(f"\n  ⚠  {len(pending_mig)} migrazione/i pendente/i — esegui: python manage_db.py migrate")


def cmd_backup(args):
    """Copy the database to a timestamped backup file."""
    if not os.path.exists(db.DB_PATH):
        print(f"Database non trovato: {db.DB_PATH}")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_out = db.DB_PATH.replace(".db", f"_backup_{ts}.db")
    dest = getattr(args, "output", None) or default_out

    shutil.copy2(db.DB_PATH, dest)
    size_kb = os.path.getsize(dest) / 1024
    print(f"✓ Backup salvato: {dest}  ({size_kb:.1f} KB)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gestione database Ham Radio Logbook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("init",    help="Crea schema e applica tutte le migrazioni")
    sub.add_parser("migrate", help="Mostra e applica le migrazioni pendenti")
    sub.add_parser("reset",   help="⚠ Cancella tutto e ricrea il database (con backup)")
    sub.add_parser("seed",    help="Inserisce QSO e attrezzatura di esempio")
    sub.add_parser("info",    help="Mostra statistiche e cronologia migrazioni")

    bk = sub.add_parser("backup", help="Copia il database in un file di backup")
    bk.add_argument("output", nargs="?", metavar="FILE",
                    help="Percorso di destinazione (default: logbook_backup_TIMESTAMP.db)")

    args = parser.parse_args()

    commands = {
        "init":    cmd_init,
        "migrate": cmd_migrate,
        "reset":   cmd_reset,
        "seed":    cmd_seed,
        "info":    cmd_info,
        "backup":  cmd_backup,
    }

    if args.command not in commands:
        parser.print_help()
        sys.exit(0)

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nAnnullato.")


if __name__ == "__main__":
    main()
