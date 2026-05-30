<div align="center">

# ❄️ Freezy AI

### Portabler Multi-Agent-Hub — verbinde KI-Agenten, die miteinander kommunizieren (auch mit Bildern), um das beste Ergebnis zu liefern

</div>

Freezy AI ist eine elegante Web-App im Stil von **Google Antigravity** / **Claude Code**.
Du stellst eine Aufgabe (optional **mit Bild**) — entweder antwortet **ein einzelnes Modell**
(z. B. nur Gemini), oder im **Agent-Modus** arbeitet ein ganzes Team aus KI-Agenten zusammen:
sie teilen die Aufgabe auf, **diskutieren über alle angemeldeten Anbieter hinweg** und
**synthetisieren** am Ende die stärkste gemeinsame Lösung.

## ✨ Features

- **🔌 Portable — keine Rückstände**: Schlüssel bleiben standardmäßig **nur im Arbeitsspeicher**.
  Schließt du den Tab (z. B. am Schul-PC), ist alles weg. Null Spuren.
- **💾 USB-Konfiguration**: Einmal bei allen Anbietern angemeldet? Speichere die Config als
  `freezy-config.json` auf deinen **USB-Stick** und lade sie beim nächsten Mal mit einem Klick.
- **📷 Bild-Eingabe (Vision)**: Häng ein Bild an — die Modelle/Agenten analysieren es mit.
- **📱 Handytauglich**: responsives Layout mit ausklappbarem Menü.
- **☁️ Cloud-Konto (optional)**: Login mit Benutzername + Passwort. Deine Anbieter-Schlüssel
  werden **Ende-zu-Ende verschlüsselt** gespeichert und sind nach dem Login auf **jedem Gerät**
  (z. B. Schul-PC) sofort verfügbar. Keine Sitzung bleibt zurück.

## ☁️ Cloud-Konto einrichten (einmalig, kostenlos)

Damit du dich überall nur mit **Benutzername + Passwort** anmelden kannst, brauchst du ein
kostenloses [Supabase](https://supabase.com)-Projekt (kostenloser „Free"-Tarif reicht):

1. Auf **supabase.com** registrieren → **New project** anlegen (Region & Passwort wählen, ~2 Min. warten).
2. **SQL Editor** öffnen → Inhalt von [`supabase-setup.sql`](supabase-setup.sql) einfügen → **Run**.
3. **Authentication → Sign In / Providers → E-Mail**: die Option **„Confirm email" ausschalten**
   (damit Login ohne echte E-Mail-Bestätigung sofort funktioniert).
4. **Project Settings → API**: kopiere **Project URL** und den **anon public**-Key.
5. In diesem Repo die Datei [`config.js`](config.js) bearbeiten und beide Werte eintragen:
   ```js
   window.SUPABASE_CONFIG = {
     url: "https://DEINPROJEKT.supabase.co",
     anonKey: "DEIN_ANON_PUBLIC_KEY"
   };
   ```
6. Speichern → GitHub Pages baut neu → fertig. Beim nächsten Öffnen erscheint der **Login-Bildschirm**.

> 🔒 **Sicherheit:** Der anon-Key darf öffentlich sein (Schutz über Row-Level-Security).
> Deine API-Schlüssel werden **im Browser mit deinem Passwort verschlüsselt** (AES-GCM) —
> der Server speichert nur unlesbaren Chiffretext. Verlierst du dein Passwort, sind die
> gespeicherten Schlüssel nicht wiederherstellbar (du trägst sie dann einfach neu ein).
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
| `auth.js` | Cloud-Login (Supabase) & verschlüsselter Schlüssel-Tresor |
| `config.js` | Deine Supabase-Zugangsdaten (URL + anon-Key) |
| `supabase-setup.sql` | Einmaliges DB-Setup (Tabelle + Row-Level-Security) |
| `app.js` | UI-Steuerung & Rendering |

---

<div align="center"><sub>Gebaut mit 🜂 — alle Agenten, ein Ergebnis. Portable. Spurlos.</sub></div>
