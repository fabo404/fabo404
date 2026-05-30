#!/bin/bash
# JARVIS im PORTABLEN Modus auf macOS starten (nur Chat + Sprache).
# Doppelklick im Finder. Beim ersten Mal evtl. Rechtsklick -> "Oeffnen".
cd "$(dirname "$0")"
python3 jarvis.py --portable
