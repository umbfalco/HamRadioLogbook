"""
Application configuration.
Values are read from environment variables; use a .env file for local dev
(see .env.example). Never hardcode secrets here.
"""
import os

# Load .env file if present (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional; env vars can be set directly in the shell

# ── MapForHam ────────────────────────────────────────────────────────────────
MFH_USERNAME = os.environ.get("MFH_USERNAME", "")
MFH_API_KEY  = os.environ.get("MFH_API_KEY",  "")
MY_GRIDSQUARE = os.environ.get("MY_GRIDSQUARE", "")

# ── Flask ────────────────────────────────────────────────────────────────────
HOST      = os.environ.get("HOST", "0.0.0.0")
PORT      = int(os.environ.get("PORT", 5000))
DEBUG     = os.environ.get("DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# ── Authentication ───────────────────────────────────────────────────────────
# Run: python set_password.py  to generate the hash.
AUTH_USERNAME        = os.environ.get("AUTH_USERNAME", "admin")
AUTH_PASSWORD_HASH   = os.environ.get("AUTH_PASSWORD_HASH", "")
SESSION_LIFETIME_DAYS = int(os.environ.get("SESSION_LIFETIME_DAYS", "30"))

# ── Background sync ──────────────────────────────────────────────────────────
SYNC_INTERVAL_MIN = int(os.environ.get("SYNC_INTERVAL_MIN", "5"))
