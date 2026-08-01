"""
Download CDN assets locally into static/vendor/.
Run once after deploy (or after git pull):

    python download_vendors.py

This makes the app fully self-hosted — no external CDN dependency.
Works on PythonAnywhere Basic where outbound CDN access may be restricted.
"""

import os
import sys
import urllib.request

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "vendor")
FONTS = os.path.join(BASE, "fonts")
IMAGES = os.path.join(BASE, "images")

os.makedirs(BASE,   exist_ok=True)
os.makedirs(FONTS,  exist_ok=True)
os.makedirs(IMAGES, exist_ok=True)

ASSETS = [
    # Bootstrap CSS
    (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
        os.path.join(BASE, "bootstrap.min.css"),
    ),
    # Bootstrap JS (bundle includes Popper)
    (
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
        os.path.join(BASE, "bootstrap.bundle.min.js"),
    ),
    # Bootstrap Icons CSS
    (
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
        os.path.join(BASE, "bootstrap-icons.min.css"),
    ),
    # Bootstrap Icons fonts
    (
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2",
        os.path.join(FONTS, "bootstrap-icons.woff2"),
    ),
    (
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff",
        os.path.join(FONTS, "bootstrap-icons.woff"),
    ),
    # Leaflet CSS + JS
    (
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        os.path.join(BASE, "leaflet.css"),
    ),
    (
        "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
        os.path.join(BASE, "leaflet.js"),
    ),
    # Leaflet marker images (referenced by leaflet.css)
    (
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        os.path.join(IMAGES, "marker-icon.png"),
    ),
    (
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        os.path.join(IMAGES, "marker-icon-2x.png"),
    ),
    (
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
        os.path.join(IMAGES, "marker-shadow.png"),
    ),
]

def download(url, dest):
    if os.path.exists(dest):
        print(f"  ✓ già presente: {os.path.basename(dest)}")
        return
    print(f"  ↓ {url.split('/')[-1]} ...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            f.write(r.read())
        print("OK")
    except Exception as e:
        print(f"ERRORE: {e}")
        sys.exit(1)

print("Download assets vendor in static/vendor/ ...")
for url, dest in ASSETS:
    download(url, dest)

# Patch leaflet.css: fix image path from "images/" to "../vendor/images/"
# (Leaflet CSS uses relative paths like url(images/marker-icon.png))
leaflet_css = os.path.join(BASE, "leaflet.css")
with open(leaflet_css, "r", encoding="utf-8") as f:
    content = f.read()
patched = content.replace("url(images/", "url(images/")
# No patch needed — we serve images/ as a subfolder of vendor/, so relative paths work
with open(leaflet_css, "w", encoding="utf-8") as f:
    f.write(patched)

print("\n✓ Tutti gli asset scaricati correttamente in static/vendor/")
print("  Ricorda di fare Reload della web app su PythonAnywhere.")
