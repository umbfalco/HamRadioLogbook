"""
WSGI entry point for PythonAnywhere.

In the PythonAnywhere Web tab:
  Source code:   /home/<USERNAME>/ham-radio-logbook
  Working dir:   /home/<USERNAME>/ham-radio-logbook
  WSGI file:     /var/www/<USERNAME>_pythonanywhere_com_wsgi.py
                 (or point it directly to this file)
  Virtualenv:    /home/<USERNAME>/.virtualenvs/logbook

Replace the contents of the PA-generated WSGI file with:

    import sys, os
    sys.path.insert(0, '/home/<USERNAME>/ham-radio-logbook')
    os.chdir('/home/<USERNAME>/ham-radio-logbook')
    from wsgi import application

Or simply import from here.
"""

import sys
import os

# ── Adjust this path to your PythonAnywhere home directory ───────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Set working directory so relative paths (e.g. logbook.db) resolve correctly
os.chdir(PROJECT_DIR)

# Load .env variables before importing app
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_DIR, ".env"))
except ImportError:
    pass

# Import the Flask app — PythonAnywhere expects the WSGI callable as 'application'
from app import app as application  # noqa: F401
