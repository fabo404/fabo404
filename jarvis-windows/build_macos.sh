#!/bin/bash
# ============================================================
#  JARVIS - Build beider Mac-Apps (auf macOS ausfuehren)
#  Ergebnis im Ordner  dist/
#    - dist/JARVIS-Portable.app  (USB / Schule, nur Chat+Sprache)
#    - dist/JARVIS-Desktop.app   (daheim, Voll-Agent: Dateien+Browser)
# ============================================================
set -e
cd "$(dirname "$0")"

echo "[1/4] PortAudio fuer das Mikrofon (via Homebrew, falls noetig)..."
command -v brew >/dev/null 2>&1 && brew list portaudio >/dev/null 2>&1 || \
  { command -v brew >/dev/null 2>&1 && brew install portaudio || echo "  (Homebrew/portaudio uebersprungen)"; }

echo "[2/4] Python-Abhaengigkeiten..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

echo "[3/4] Baue JARVIS-Portable.app ..."
pyinstaller --windowed --name JARVIS-Portable \
  --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.nsss jarvis.py

echo "[4/4] Baue JARVIS-Desktop.app ..."
pyinstaller --windowed --name JARVIS-Desktop \
  --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.nsss jarvis.py

echo ""
echo "FERTIG. Die .app-Dateien liegen in:  dist/"
echo "Portabel nutzen: dist/JARVIS-Portable.app + deine config.json auf den Stick."
