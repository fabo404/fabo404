@echo off
REM Startet JARVIS im PORTABLEN Modus aus dem Quellcode (Python noetig).
REM Fuer die Schule/USB ohne Python: stattdessen die gebaute JARVIS-Portable.exe nutzen.
cd /d "%~dp0"
python jarvis.py --portable
