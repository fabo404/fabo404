# 🤖 J.A.R.V.I.S. — Portabler Iron-Man-Agent

Ein echter Desktop-Assistent im Iron-Man-Stil — **kein Browser**, echtes Fenster mit
animiertem Arc-Reactor und **Live-Streaming** (die Antwort kommt Wort für Wort, fühlt sich
sofort an). Du kannst mit ihm **reden** und **schreiben**, und **Gemini + OpenAI + Claude**
arbeiten zusammen (je nachdem, für wie viele du einen API-Key hinterlegst).

> 🎤 **Wichtig:** Beim Reden **wartet** JARVIS, bis du **fertig** gesprochen hast —
> er fängt nicht an zu „denken", während du noch redest.

**Ein Code — drei Systeme:** dasselbe `jarvis.py` läuft auf **Windows, macOS und Linux**.

---

## Versionen & Modi

Zwei Modi (über den Dateinamen bzw. `--full` / `--portable` gesteuert):

| | **Portable** | **Desktop / Full** |
|---|---|---|
| Wofür | Schule / fremder PC / USB | Eigener Rechner |
| Kann | **Chat + Sprechen** | **Voll-Agent:** Chat + Sprechen **+ Dateisystem + Browser** |
| Sicherheit | kein Systemzugriff | voller Zugriff (mit Bestätigung) |

Pro System gibt es passende Start-Dateien:

| System | Portable starten | Desktop starten | App bauen |
|--------|------------------|------------------|-----------|
| **Windows** | `JARVIS-Portable.bat` | `JARVIS-Desktop.bat` | `build_windows.bat` → `.exe` |
| **macOS** | `JARVIS-Portable.command` | `JARVIS-Desktop.command` | `build_macos.sh` → `.app` |
| **Linux** | `python3 jarvis.py --portable` | `python3 jarvis.py --full` | PyInstaller |

> ⚠️ `.bat` läuft **nur auf Windows**, `.command` **nur auf macOS**. Pro System die richtige nehmen.

---

## 1) Einmalig daheim einrichten

1. **Python 3.10+** installieren (https://python.org).
   - macOS hat oft schon `python3`. Sonst per python.org oder `brew install python`.
2. Abhängigkeiten installieren (Terminal in diesem Ordner):
   ```bash
   pip install -r requirements.txt        # Windows
   pip3 install -r requirements.txt       # macOS / Linux
   ```
   - **macOS-Mikrofon:** vorher `brew install portaudio` (für PyAudio).
3. (Optional) **Supabase-Konto:** `config.example.json` → zu `config.json` kopieren und
   `supabase_url` + `supabase_anon_key` eintragen.
4. **Starten & einrichten:**
   - Windows: `JARVIS-Desktop.bat`  ·  macOS: `JARVIS-Desktop.command` (1. Mal evtl. Rechtsklick → „Öffnen")
   - In **⚙** deine **API-Keys** eintragen (1–3 Stück), optional bei Supabase anmelden.
   - Alles wird in **`jarvis_data.json` NEBEN der App** gespeichert.

---

## 2) Portabel für die Schule (USB-Stick)

1. Daheim die App **bauen** (siehe unten) oder den Ordner mit Python nutzen.
2. Auf den USB-Stick kopieren:
   - Windows: `JARVIS-Portable.exe` · macOS: `JARVIS-Portable.app`
   - `jarvis_data.json` (entsteht nach dem Einrichten — enthält Keys + Login)
   - optional `config.json`
3. **In der Schule:** Stick einstecken → Portable-App doppelklicken → sofort Chat + Sprechen.
   Keine Installation, alles liegt auf dem Stick.

> Im Portable-Modus hat JARVIS **keinen** Zugriff aufs Dateisystem und startet **keine**
> Programme — bewusst sicher für fremde PCs.

---

## 3) App bauen (einmal)

- **Windows:** `build_windows.bat` → `dist\JARVIS-Portable.exe` + `dist\JARVIS-Desktop.exe`
- **macOS:** `bash build_macos.sh` → `dist/JARVIS-Portable.app` + `dist/JARVIS-Desktop.app`

„Installiert daheim" = die `JARVIS-Desktop`-App nach Programme/Applications kopieren und
eine Verknüpfung anlegen.

---

## Bedienung

- **Schreiben:** unten tippen, **Enter** sendet (**Shift+Enter** = neue Zeile).
- **Reden:** 🎤 anklicken → sprechen → **Pause machen, wenn du fertig bist**. JARVIS
  transkribiert **erst dann**, streamt die Antwort live und spricht sie (wenn „Stimme" an).
- **Team-Modus:** an = mehrere Anbieter diskutieren und liefern eine gemeinsame Antwort.
  *(Für Aktionen wie Datei/Browser im Desktop-Modus den Team-Modus ausschalten.)*
- **Desktop-Aktionen** (nur Voll-Agent): „Öffne Chrome und such…", „Lies die Datei …",
  „Schreib eine Datei …". Schreiben/Befehle musst du per Klick **bestätigen**.

---

## Chats geräteübergreifend (Cloud-Sync)

- **Ohne Anmeldung:** Chats werden lokal in `jarvis_data.json` gespeichert (bleiben nach
  Neustart da und wandern auf dem USB-Stick mit).
- **Mit Supabase-Login:** Chats werden zusätzlich in der **Cloud** gespeichert und auf
  **jedem Gerät** (Windows, Mac, USB) beim Start automatisch geladen — überall derselbe Verlauf.

**Was du dafür einmal ausführen musst:**
1. Kostenloses Projekt auf https://supabase.com anlegen.
2. In **Supabase → SQL Editor** den Inhalt von **`supabase_setup.sql`** einfügen und **Run** klicken
   (legt die Tabelle `jarvis_chats` + Sicherheitsregeln an).
3. `config.example.json` → `config.json` kopieren und aus **Supabase → Project Settings → API**
   die **Project URL** und den **anon public key** eintragen.
4. In JARVIS unter **⚙** auf **Registrieren** und dann **Anmelden** — fertig.

---

## Sprache (Details)

- **Erkennung (Sprache → Text):** mit OpenAI-Key → **Whisper** (beste Qualität), sonst
  kostenlose Google-Web-Erkennung (Internet nötig).
- **Ausgabe (Text → Sprache):** Windows = SAPI5 · macOS = NSSpeechSynthesizer bzw. der
  eingebaute `say`-Befehl als Fallback · Linux = espeak (über pyttsx3).

---

## Sicherheit & Hinweise

- API-Keys liegen in `jarvis_data.json` (leicht verschleiert, **keine** echte
  Verschlüsselung). Behandle den USB-Stick wie deinen Schlüsselbund.
- `jarvis_data.json` und `config.json` sind in `.gitignore` — **nie hochladen**.
- Eine **einzige Datei für Desktop UND iPhone ohne Browser gibt es technisch nicht**
  (iOS lässt nur signierte Apps via Xcode/App-Store zu). Diese App deckt
  **Windows + macOS + Linux** ab. Für iOS wäre ein separates Swift-Projekt nötig.
