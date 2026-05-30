<div align="center">

# 🜂 Synapse

### Portable Multi-Agent-App — verbinde KI-Agenten, die miteinander kommunizieren, um das beste Ergebnis zu liefern

</div>

Synapse ist eine elegante Web-App im Stil von **Google Antigravity** / **Claude Code**.
Du stellst eine Aufgabe — entweder antwortet **ein einzelnes Modell** (z. B. nur Gemini),
oder im **Agent-Modus** arbeitet ein ganzes Team aus KI-Agenten zusammen: sie teilen die
Aufgabe auf, **diskutieren über alle angemeldeten Anbieter hinweg** und **synthetisieren**
am Ende die stärkste gemeinsame Lösung.

## ✨ Features

- **🔌 Portable — keine Rückstände**: Schlüssel bleiben standardmäßig **nur im Arbeitsspeicher**.
  Schließt du den Tab (z. B. am Schul-PC), ist alles weg. Null Spuren.
- **💾 USB-Konfiguration**: Einmal bei allen Anbietern angemeldet? Speichere die Config als
  `synapse-config.json` auf deinen **USB-Stick** und lade sie beim nächsten Mal mit einem Klick.
- **🧠 Mehrere Anbieter gleichzeitig**: **Google Gemini**, **Anthropic Claude**, **OpenAI-kompatibel**.
- **🎛️ Zwei Modi**:
  - **Einzel** — wähle genau einen Anbieter (z. B. nur Gemini).
  - **Agent-Modus** — alle angemeldeten Anbieter arbeiten als Team zusammen.
- **🤖 Anpassbares Agenten-Team**: Researcher, Architekt, Kritiker & Synthesizer — eigene Agenten mit eigener Spezialität hinzufügbar.
- **⌫ Wipe-Knopf**: löscht auf Wunsch alle Spuren auf dem aktuellen PC sofort.
- **🎨 Schönes UI**: dunkles Design, Glassmorphism, animiertes „Denken", Live-Status, Anbieter-Badges.
- **📴 Demo-Modus**: funktioniert sofort offline, ganz ohne API-Schlüssel.

## 🚀 Starten

Statische App — kein Build, keine Installation nötig. Perfekt für den USB-Stick:

```bash
# Einfach die Datei im Browser öffnen
index.html

# Oder lokaler Server (empfohlen für echte API-Aufrufe)
python3 -m http.server 8000   →   http://localhost:8000
```

Tipp für die Schule: Kopiere den ganzen Ordner auf den USB-Stick und öffne `index.html`
direkt im Browser. Nach dem Anmelden einmal **„⤓ USB"** klicken — fertig.

## 🔑 Anbieter verbinden

Klicke unten links auf **„Anbieter & Schlüssel"**, klappe einen Anbieter auf und trage
deinen API-Schlüssel ein. Schlüssel werden **nur lokal** verwendet und ausschließlich
direkt an den jeweiligen Anbieter gesendet — niemals an einen Dritt-Server.

| Anbieter | Schlüssel bekommen |
|----------|--------------------|
| Google Gemini | aistudio.google.com → API Key |
| Anthropic Claude | console.anthropic.com |
| OpenAI-kompatibel | platform.openai.com (oder eigene Basis-URL) |

## 🗂️ Aufbau

| Datei | Zweck |
|-------|-------|
| `index.html` | Struktur & Layout |
| `styles.css` | Design / Theme |
| `agents.js` | Anbieter-Anbindung, Portable-Config & Orchestrierungs-Engine |
| `app.js` | UI-Steuerung & Rendering |

---

<div align="center"><sub>Gebaut mit 🜂 — alle Agenten, ein Ergebnis. Portable. Spurlos.</sub></div>
