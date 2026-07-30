#!/usr/bin/env bash
# Ham Radio Logbook — launcher for Linux/macOS

set -e
cd "$(dirname "$0")"

echo "Avvio Ham Radio Logbook..."

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERRORE: python3 non trovato. Installa Python 3.9+."
    exit 1
fi

# Install dependencies if needed
echo "Verifica dipendenze..."
python3 -m pip install -q -r requirements.txt

# Detect LAN IP
if command -v ip &>/dev/null; then
    LAN_IP=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}')
elif command -v ipconfig &>/dev/null; then
    LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || true)
else
    LAN_IP=""
fi

echo ""
echo "============================================"
echo " Ham Radio Logbook avviato!"
echo " Apri nel browser: http://localhost:5000"
if [ -n "$LAN_IP" ]; then
    echo " Accesso LAN / smartphone: http://$LAN_IP:5000"
fi
echo " Premi Ctrl+C per fermare il server"
echo "============================================"
echo ""

# Open browser (best effort)
(sleep 2 && (open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null)) &

python3 app.py
