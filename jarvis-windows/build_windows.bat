@echo off
REM ============================================================
REM  JARVIS - Build beider .exe-Versionen (auf WINDOWS ausfuehren)
REM  Ergebnis liegt danach im Ordner  dist\
REM    - dist\JARVIS-Portable.exe   (USB / Schule, nur Chat+Sprache)
REM    - dist\JARVIS-Desktop.exe    (daheim, Voll-Agent: Dateien+Chrome)
REM ============================================================
echo.
echo [1/3] Installiere Abhaengigkeiten...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo [2/3] Baue JARVIS-Portable.exe ...
pyinstaller --onefile --noconsole --name JARVIS-Portable ^
  --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 ^
  jarvis.py

echo.
echo [3/3] Baue JARVIS-Desktop.exe ...
pyinstaller --onefile --noconsole --name JARVIS-Desktop ^
  --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 ^
  jarvis.py

echo.
echo ============================================================
echo  FERTIG. Die .exe-Dateien liegen in:  dist\
echo.
echo  Portabel nutzen: Kopiere auf den USB-Stick:
echo    - dist\JARVIS-Portable.exe
echo    - deine config.json (Supabase, optional)
echo    Beim ersten Start daheim einrichten -> jarvis_data.json
echo    entsteht NEBEN der exe und reist auf dem Stick mit.
echo ============================================================
pause
