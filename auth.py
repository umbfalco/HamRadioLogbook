"""
Authentication module for Ham Radio Logbook — multi-user, DB-backed.

Credentials are stored in the `users` table (Werkzeug PBKDF2 hashes).
Rate limiting is in-memory per IP (resets on server restart).
"""

import time
from collections import defaultdict
from functools import wraps

from flask import jsonify, redirect, request, session
from werkzeug.security import generate_password_hash

import db

# ── Rate limiting ─────────────────────────────────────────────────────────────
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300

_attempts: dict = defaultdict(list)


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else request.remote_addr


def _rate_ok(ip: str) -> bool:
    now = time.time()
    _attempts[ip] = [t for t in _attempts[ip] if now - t < WINDOW_SECONDS]
    return len(_attempts[ip]) < MAX_ATTEMPTS


def _record_failure(ip: str) -> None:
    _attempts[ip].append(time.time())


def _clear_failures(ip: str) -> None:
    _attempts.pop(ip, None)


def remaining_lockout(ip: str) -> int:
    now = time.time()
    recent = [t for t in _attempts.get(ip, []) if now - t < WINDOW_SECONDS]
    if len(recent) < MAX_ATTEMPTS:
        return 0
    return max(0, int(WINDOW_SECONDS - (now - min(recent))))


# ── Credential helpers ────────────────────────────────────────────────────────

def verify(username: str, password: str) -> dict | None:
    """Return user dict on success, None on failure."""
    return db.verify_user_password(username, password)


def make_hash(password: str) -> str:
    return generate_password_hash(password)


# ── Session helpers ───────────────────────────────────────────────────────────

def get_session_user_id() -> int | None:
    return session.get("user_id")


def get_session_username() -> str:
    return session.get("username", "")


# ── Flask decorator ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Non autenticato"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

