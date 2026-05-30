#!/bin/bash
# JARVIS im DESKTOP-/VOLL-Modus auf macOS starten (Voll-Agent: Dateien + Browser).
# Doppelklick im Finder. Beim ersten Mal evtl. Rechtsklick -> "Oeffnen".
cd "$(dirname "$0")"
python3 jarvis.py --full
