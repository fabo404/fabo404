# 🤖 J.A.R.V.I.S. — Portabler Iron-Man-Agent (Windows)

Ein echter Desktop-Assistent im Iron-Man-Stil — **kein Browser**, echtes Fenster.
Du kannst mit ihm **reden** und **schreiben**, und **Gemini + OpenAI + Claude**
arbeiten zusammen (je nachdem, für wie viele du einen API-Key hinterlegst).

> 🎤 **Wichtig:** Beim Reden **wartet** JARVIS, bis du **fertig** gesprochen hast —
> er fängt nicht an zu „denken", während du noch redest.

---

## Es gibt ZWEI Versionen (beide vorher **daheim einrichten**)

| | **Portable (USB)** | **Desktop (daheim)** |
|---|---|---|
| Wofür | Schule / fremder PC | Eigener Rechner |
| Installation | keine — eine Datei klicken | als App / Verknüpfung |
| Kann | **Chat + Sprechen** | **Voll-Agent:** Chat + Sprechen **+ Dateisystem + Chrome öffnen** |
| Datei | `JARVIS-Portable.exe` | `JARVIS-Desktop.exe` |

Beide nutzen denselben Code; der **Dateiname** entscheidet den Modus
(`...-Desktop.exe` = Voll-Agent, `...-Portable.exe` = sicher/eingeschränkt).

---

## 1) Einmalig daheim einrichten

1. **Python 3.10+** installieren (https://python.org, Haken „Add to PATH").
2. In diesem Ordner ein Terminal öffnen und Abhängigkeiten installieren:
   ```bat
   pip install -r requirements.txt
   ```
3. (Optional) **Supabase-Konto-System**: `config.example.json` → zu `config.json`
   kopieren und deine `supabase_url` + `supabase_anon_key` eintragen.
4. **Starten & einrichten:**
   ```bat
   JARVIS-Desktop.bat      ::  Voll-Agent daheim
   JARVIS-Portable.bat     ::  so wie es auf dem USB läuft
   ```
   - In **⚙ Einstellungen** deine **API-Keys** eintragen (1–3 Stück).
   - Optional bei **Supabase anmelden** → du bleibst eingeloggt.
   - Alles wird in **`jarvis_data.json` NEBEN der App** gespeichert.

---

## 2) Portabel für die Schule (USB-Stick)

1. Daheim die **`.exe`** bauen (siehe unten) **oder** den ganzen Ordner mit Python nutzen.
2. Auf den USB-Stick kopieren:
   - `JARVIS-Portable.exe`
   - `jarvis_data.json` (entsteht nach dem Einrichten — enthält Keys + Login)
   - optional `config.json`
3. **In der Schule:** Stick einstecken → **`JARVIS-Portable.exe` doppelklicken** →
   sofort Chat + Sprechen. Keine Installation, keine Spuren am Schul-PC nötig
   (alles liegt auf dem Stick).

> Im Portable-Modus hat JARVIS **keinen** Zugriff aufs Dateisystem und kann
> **keine** Programme starten — bewusst sicher für fremde PCs.

---

## 3) `.exe` bauen (einmal, auf Windows)

```bat
build_windows.bat
```
Danach liegen im Ordner `dist\`:
- `JARVIS-Portable.exe` → USB / Schule
- `JARVIS-Desktop.exe` → daheim (Voll-Agent)

„Installiert daheim" = `JARVIS-Desktop.exe` z. B. nach `C:\Program Files\JARVIS\`
kopieren und eine Verknüpfung auf den Desktop legen.

---

## Bedienung

- **Schreiben:** unten tippen, **Enter** sendet (**Shift+Enter** = neue Zeile).
- **Reden:** 🎤 anklicken → sprechen → **Pause machen, wenn du fertig bist**.
  JARVIS transkribiert **erst dann** und antwortet (und spricht zurück, wenn „Stimme" an).
- **Team-Modus:** an = mehrere Anbieter diskutieren und liefern eine gemeinsame Antwort.
  *(Für Aktionen wie Datei/Chrome im Desktop-Modus den Team-Modus ausschalten.)*
- **Desktop-Aktionen** (nur Voll-Agent): „Öffne Chrome und such…", „Lies die Datei …",
  „Schreib eine Datei …". Schreiben/Befehle musst du per Klick **bestätigen**.

---

## Sprache (Details)

- **Erkennung (Sprache → Text):** mit OpenAI-Key → **Whisper** (beste Qualität),
  sonst kostenlose Google-Web-Erkennung (Internet nötig).
- **Ausgabe (Text → Sprache):** Windows-Stimme (offline, SAPI5) über `pyttsx3`.

---

## Sicherheit & Hinweise

- API-Keys liegen in `jarvis_data.json` (leicht verschleiert, **keine** echte
  Verschlüsselung). Behandle den USB-Stick wie deinen Schlüsselbund.
- `jarvis_data.json` und `config.json` sind in `.gitignore` — **nie hochladen**.
- Eine **einzige Datei für Windows UND iPhone ohne Browser gibt es technisch nicht**
  (iOS lässt nur signierte Apps via Xcode/App-Store zu). Diese App ist die
  **Windows-Variante**. Für iOS wäre ein separates Swift-Projekt nötig.
