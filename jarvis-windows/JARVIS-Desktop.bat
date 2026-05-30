@echo off
REM Startet JARVIS im DESKTOP-/VOLL-Modus aus dem Quellcode (Python noetig).
REM Voll-Agent: Zugriff auf Dateisystem + kann Chrome oeffnen.
cd /d "%~dp0"
python jarvis.py --full
