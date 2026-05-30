#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
 J.A.R.V.I.S.  -  Portabler Iron-Man-Agent (Windows Desktop)
============================================================
 - Echtes Fenster (Tkinter) - KEIN Browser
 - Portabel: laeuft vom USB-Stick, speichert ALLES (Login +
   API-Keys) in 'jarvis_data.json' NEBEN der App -> einmal
   anmelden, reist auf dem Stick mit.
 - Reden + Schreiben: Mikrofon wartet, bis du FERTIG geredet
   hast (denkt nicht waehrend du sprichst), spricht zurueck.
 - Agent: Gemini + OpenAI + Claude arbeiten zusammen (je
   nachdem, fuer wie viele ein API-Key hinterlegt ist).
 - Optionales Supabase-Konto (einmal anmelden).

 Start:  python jarvis.py      (oder gebaute JARVIS.exe)
============================================================
"""

import os
import sys
import json
import base64
import threading
import queue
import time

import tkinter as tk
from tkinter import ttk, messagebox

# ---- HTTP (Pflicht) -----------------------------------------------------
try:
    import requests
except Exception:
    requests = None

# ---- Sprache rein (optional) -------------------------------------------
try:
    import speech_recognition as sr
    VOICE_IN = True
except Exception:
    sr = None
    VOICE_IN = False

# ---- Sprache raus (optional) -------------------------------------------
try:
    import pyttsx3
    VOICE_OUT = True
except Exception:
    pyttsx3 = None
    VOICE_OUT = False


# ============================================================
#  Speicherort (portabel -> neben der App / exe)
# ============================================================
def app_dir():
    """Ordner der App - auch wenn als PyInstaller-.exe gepackt."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_FILE = os.path.join(app_dir(), "jarvis_data.json")
CONFIG_FILE = os.path.join(app_dir(), "config.json")  # Supabase url/anon (optional)


# ============================================================
#  Modus:  "portable" (USB, nur Chat+Sprache) | "full" (Desktop,
#  voller Agent mit Dateisystem-Zugriff + Chrome).
#  Bestimmt durch: --full / --portable  oder  Datei 'jarvis_full.flag'
# ============================================================
def detect_mode():
    if "--full" in sys.argv:
        return "full"
    if "--portable" in sys.argv:
        return "portable"
    # Erkennung am Dateinamen der exe -> JARVIS-Desktop.exe = full
    name = os.path.basename(
        sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).lower()
    if "desktop" in name or "full" in name:
        return "full"
    if "portable" in name:
        return "portable"
    if os.path.exists(os.path.join(app_dir(), "jarvis_full.flag")):
        return "full"
    return "portable"


MODE = detect_mode()
FULL = MODE == "full"


# ============================================================
#  Anbieter
# ============================================================
PROVIDERS = {
    "openai":    {"label": "OpenAI",  "default_model": "gpt-4o-mini",        "icon": "O"},
    "anthropic": {"label": "Claude",  "default_model": "claude-sonnet-4-6",  "icon": "C"},
    "gemini":    {"label": "Gemini",  "default_model": "gemini-2.0-flash",   "icon": "G"},
}

JARVIS_PERSONA = (
    "Du bist J.A.R.V.I.S., der persoenliche KI-Assistent im Stil von Tony Starks Iron Man. "
    "Du bist hoeflich, trocken-britisch-charmant, extrem kompetent und kommst schnell auf den Punkt. "
    "Du sprichst Deutsch (ausser man bittet um etwas anderes), redest den Nutzer respektvoll an "
    "(z. B. 'Sir' nur sparsam, sonst neutral) und gibst klare, umsetzbare Antworten. "
    "Halte gesprochene Antworten eher kurz und natuerlich, da sie vorgelesen werden."
)

# Agenten-Team (wenn mehrere Anbieter zusammenarbeiten)
TEAM_AGENTS = [
    ("Scout", "Researcher",
     "Du bist ein gruendlicher Rechercheur. Du zerlegst die Aufgabe, sammelst Fakten, Annahmen und offene Fragen."),
    ("Forge", "Architekt",
     "Du bist Loesungs-Architekt. Du baust aus der Recherche eine konkrete, strukturierte Loesung mit klaren Schritten."),
    ("Raven", "Kritiker",
     "Du bist ein scharfer, fairer Kritiker. Du findest Schwaechen, Risiken und blinde Flecken und schlaegst konkrete Verbesserungen vor."),
    ("Echo", "Synthesizer",
     "Du bist der Synthesizer. Du verbindest die besten Ideen aller zu EINER klaren, umsetzbaren Endloesung."),
]

# Werkzeuge nur im Full-/Desktop-Modus
TOOLS_SPEC = (
    "\n\nDu hast Zugriff auf den lokalen Computer (Desktop-Modus). "
    "Wenn du eine AKTION ausfuehren willst, antworte AUSSCHLIESSLICH mit EINEM JSON-Objekt "
    "(kein weiterer Text), Form: {\"tool\":\"NAME\",\"args\":{...}}.\n"
    "Verfuegbare Tools:\n"
    "- open_chrome  {\"url\":\"https://...\"}      -> oeffnet Chrome (oder Standardbrowser).\n"
    "- open_path    {\"path\":\"C:/Ordner/datei\"} -> oeffnet Datei oder Ordner.\n"
    "- list_dir     {\"path\":\"C:/Ordner\"}        -> listet einen Ordner auf.\n"
    "- read_file    {\"path\":\"C:/.../datei.txt\"} -> liest eine Textdatei.\n"
    "- write_file   {\"path\":\"...\",\"content\":\"...\"} -> schreibt eine Datei.\n"
    "- run_command  {\"command\":\"...\"}           -> fuehrt einen Befehl aus (wird vom Nutzer bestaetigt).\n"
    "Nach der Aktion bekommst du das Ergebnis als 'Tool-Ergebnis: ...' und antwortest dann "
    "dem Nutzer normal auf Deutsch. Wenn KEIN Tool noetig ist, antworte einfach normal (kein JSON)."
)


# ============================================================
#  Persistente Daten (portabel)
# ============================================================
def _obf(s):
    """Leichte Verschleierung (KEINE echte Verschluesselung) der Keys auf dem Stick."""
    try:
        return base64.b64encode(s.encode("utf-8")).decode("ascii")
    except Exception:
        return ""


def _deobf(s):
    try:
        return base64.b64decode(s.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


DEFAULT_DATA = {
    "keys": {"openai": "", "anthropic": "", "gemini": ""},
    "models": {p: PROVIDERS[p]["default_model"] for p in PROVIDERS},
    "team_mode": True,        # mehrere Anbieter zusammenarbeiten lassen
    "voice_out": True,        # JARVIS spricht
    "voice_rate": 180,
    "session": None,          # Supabase-Session (einmal anmelden)
}


def load_data():
    data = json.loads(json.dumps(DEFAULT_DATA))  # deep copy
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # Keys entschleiern
        if "keys" in saved:
            for p, v in saved["keys"].items():
                saved["keys"][p] = _deobf(v) if v else ""
        data.update(saved)
        # sicherstellen, dass alle Felder existieren
        for k in DEFAULT_DATA:
            data.setdefault(k, DEFAULT_DATA[k])
        for p in PROVIDERS:
            data["keys"].setdefault(p, "")
            data["models"].setdefault(p, PROVIDERS[p]["default_model"])
    except Exception:
        pass
    return data


def save_data(data):
    try:
        out = json.loads(json.dumps(data))
        # Keys verschleiern, bevor sie auf den Stick geschrieben werden
        out["keys"] = {p: (_obf(v) if v else "") for p, v in data.get("keys", {}).items()}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Speichern fehlgeschlagen:", e)


def load_supabase_cfg():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            c = json.load(f)
        return c.get("supabase_url", "").rstrip("/"), c.get("supabase_anon_key", "")
    except Exception:
        return "", ""


# ============================================================
#  Supabase-Auth (optional, REST)
# ============================================================
class Supabase:
    def __init__(self):
        self.url, self.anon = load_supabase_cfg()

    @property
    def configured(self):
        return bool(self.url and self.anon and requests)

    def _headers(self):
        return {"apikey": self.anon, "Content-Type": "application/json"}

    def login(self, email, password):
        r = requests.post(
            f"{self.url}/auth/v1/token?grant_type=password",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=20,
        )
        if r.status_code >= 400:
            raise RuntimeError(self._err(r))
        return r.json()

    def signup(self, email, password):
        r = requests.post(
            f"{self.url}/auth/v1/signup",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=20,
        )
        if r.status_code >= 400:
            raise RuntimeError(self._err(r))
        return r.json()

    @staticmethod
    def _err(r):
        try:
            j = r.json()
            return j.get("msg") or j.get("error_description") or j.get("error") or r.text[:160]
        except Exception:
            return f"HTTP {r.status_code}: {r.text[:160]}"


# ============================================================
#  LLM-Aufrufe je Anbieter
# ============================================================
def call_openai(key, model, system, messages, base_url="https://api.openai.com/v1"):
    msgs = [{"role": "system", "content": system}] + messages
    r = requests.post(
        base_url + "/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        json={"model": model, "max_tokens": 1200, "messages": msgs},
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError("OpenAI " + str(r.status_code) + ": " + r.text[:160])
    return r.json()["choices"][0]["message"]["content"]


def call_anthropic(key, model, system, messages):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        json={"model": model, "max_tokens": 1200, "system": system, "messages": messages},
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError("Claude " + str(r.status_code) + ": " + r.text[:160])
    data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []))


def call_gemini(key, model, system, messages):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":generateContent?key=" + key)
    contents = [{"role": ("user" if m["role"] == "user" else "model"),
                 "parts": [{"text": m["content"]}]} for m in messages]
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 1200},
        },
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError("Gemini " + str(r.status_code) + ": " + r.text[:160])
    data = r.json()
    parts = (data.get("candidates", [{}])[0].get("content", {}) or {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def call_provider(provider, key, model, system, messages):
    """messages = Liste von {'role':'user'|'assistant','content':str}."""
    if provider == "openai":
        return call_openai(key, model, system, messages)
    if provider == "anthropic":
        return call_anthropic(key, model, system, messages)
    if provider == "gemini":
        return call_gemini(key, model, system, messages)
    raise RuntimeError("Unbekannter Anbieter: " + provider)


# ============================================================
#  Agent-Engine (denkt erst NACH der Eingabe)
# ============================================================
class Brain:
    def __init__(self, data):
        self.data = data

    def active_providers(self):
        """Anbieter, fuer die ein Key hinterlegt ist (Reihenfolge: Claude, OpenAI, Gemini)."""
        order = ["anthropic", "openai", "gemini"]
        return [p for p in order if self.data["keys"].get(p, "").strip()]

    def complete(self, provider, system, messages):
        """Ein Anbieter-Aufruf mit Gespraechs-Verlauf."""
        key = self.data["keys"][provider].strip()
        model = self.data["models"].get(provider) or PROVIDERS[provider]["default_model"]
        return call_provider(provider, key, model, system, messages)

    # ---- Team-Modus: mehrere Anbieter arbeiten zusammen ----
    def respond_team(self, prompt, providers, emit):
        """providers = Liste aktiver Anbieter; emit(name, role, text) zeigt Zwischenbeitraege."""
        transcript = []

        def ctx():
            if not transcript:
                return "(noch keine Beitraege)"
            return "Bisheriger Verlauf des Teams:\n\n" + "\n\n".join(
                f"[{t[0]} - {t[1]}]\n{t[2]}" for t in transcript
            )

        workers = TEAM_AGENTS[:-1]
        synth = TEAM_AGENTS[-1]

        # Anbieter reihum den Agenten zuweisen
        for i, (name, role, persona) in enumerate(workers):
            provider = providers[i % len(providers)]
            system = (persona + " Du arbeitest in einem Team aus mehreren KI-Agenten "
                      "(auf verschiedenen Modellen). Antworte fokussiert (max ~150 Woerter).")
            usr = (f"AUFGABE DES NUTZERS:\n{prompt}\n\n{ctx()}\n\n"
                   "DEINE AUFGABE JETZT: Bringe deine Perspektive ein und baue auf den anderen auf.")
            try:
                text = self.complete(provider, system, [{"role": "user", "content": usr}])
            except Exception as e:
                text = f"[Fehler bei {PROVIDERS[provider]['label']}: {e}]"
            transcript.append((name, role, text))
            emit(name, f"{role} - {PROVIDERS[provider]['label']}", text)

        # Synthese durch den faehigsten verfuegbaren Anbieter
        provider = providers[0]
        system = (JARVIS_PERSONA + " " + synth[2] +
                  " Fasse die Diskussion zu EINER klaren, umsetzbaren Endloesung zusammen.")
        usr = (f"AUFGABE DES NUTZERS:\n{prompt}\n\n{ctx()}\n\n"
               "DEINE AUFGABE JETZT: Liefere die finale, beste gemeinsame Antwort.")
        try:
            final = self.complete(provider, system, [{"role": "user", "content": usr}])
        except Exception as e:
            final = f"Entschuldigung, die Synthese ist fehlgeschlagen: {e}"
        return final


# ============================================================
#  GUI
# ============================================================
BG = "#0a0c12"
PANEL = "#11141d"
PANEL2 = "#161a26"
GOLD = "#ffc24b"
CYAN = "#4cc9ff"
RED = "#ff5a4d"
TEXT = "#e9ecf5"
DIM = "#9aa1b8"
FAINT = "#5d6480"


class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.data = load_data()
        self.brain = Brain(self.data)
        self.supa = Supabase()

        self.busy = False
        self.listening = False
        self.ui_queue = queue.Queue()
        self.history = []  # Gespraechs-Gedaechtnis: [{role, content}, ...]

        # TTS-Engine (im Hauptthread initialisiert, im Worker benutzt)
        self.tts = None
        if VOICE_OUT:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty("rate", self.data.get("voice_rate", 180))
            except Exception:
                self.tts = None

        self._build_ui()
        self._poll_queue()
        self._greet()

    # ---------- UI-Aufbau ----------
    def _build_ui(self):
        mode_label = "Desktop · Voll-Agent" if FULL else "Portable · USB"
        self.root.title("J.A.R.V.I.S.  -  Iron Man Assistant  [" + mode_label + "]")
        self.root.configure(bg=BG)
        self.root.geometry("860x680")
        self.root.minsize(640, 520)

        # Kopf
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(top, text="◉", fg=CYAN, bg=BG, font=("Segoe UI", 20, "bold")).pack(side="left")
        title = tk.Frame(top, bg=BG)
        title.pack(side="left", padx=8)
        tk.Label(title, text="J.A.R.V.I.S.", fg=TEXT, bg=BG,
                 font=("Segoe UI Semibold", 16)).pack(anchor="w")
        self.status = tk.Label(title, text="bereit", fg=DIM, bg=BG, font=("Consolas", 9))
        self.status.pack(anchor="w")

        # Team-Schalter
        self.team_var = tk.BooleanVar(value=self.data.get("team_mode", True))
        team = tk.Checkbutton(top, text="Team-Modus", variable=self.team_var,
                              command=self._toggle_team, fg=GOLD, bg=BG, selectcolor=PANEL,
                              activebackground=BG, activeforeground=GOLD, font=("Segoe UI", 10),
                              bd=0, highlightthickness=0)
        team.pack(side="right")

        self.voice_var = tk.BooleanVar(value=self.data.get("voice_out", True))
        voice = tk.Checkbutton(top, text="Stimme", variable=self.voice_var,
                               command=self._toggle_voice, fg=CYAN, bg=BG, selectcolor=PANEL,
                               activebackground=BG, activeforeground=CYAN, font=("Segoe UI", 10),
                               bd=0, highlightthickness=0)
        voice.pack(side="right", padx=(0, 12))

        self._mk_btn(top, "⚙ Einstellungen", self.open_settings, GOLD).pack(side="right", padx=(0, 12))

        # Chat-Bereich
        mid = tk.Frame(self.root, bg=PANEL, highlightbackground="#222838", highlightthickness=1)
        mid.pack(fill="both", expand=True, padx=16, pady=8)

        self.chat = tk.Text(mid, bg=PANEL, fg=TEXT, wrap="word", bd=0,
                            font=("Segoe UI", 11), padx=16, pady=14,
                            spacing1=2, spacing3=8, state="disabled",
                            insertbackground=TEXT)
        sb = ttk.Scrollbar(mid, command=self.chat.yview)
        self.chat.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.chat.pack(side="left", fill="both", expand=True)

        self.chat.tag_config("you", foreground=GOLD, font=("Segoe UI Semibold", 11))
        self.chat.tag_config("jarvis", foreground=CYAN, font=("Segoe UI Semibold", 11))
        self.chat.tag_config("agent", foreground="#b9c0d6", font=("Segoe UI Semibold", 10))
        self.chat.tag_config("body", foreground=TEXT)
        self.chat.tag_config("sys", foreground=FAINT, font=("Consolas", 9))

        # Eingabe
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill="x", padx=16, pady=(4, 14))

        self.mic_btn = tk.Button(bottom, text="\U0001F3A4", command=self.toggle_listen,
                                 bg=PANEL2, fg=CYAN, activebackground=PANEL2,
                                 activeforeground=CYAN, bd=0, font=("Segoe UI", 16),
                                 width=3, cursor="hand2")
        self.mic_btn.pack(side="left", padx=(0, 8), ipady=4)
        if not VOICE_IN:
            self.mic_btn.config(state="disabled", fg=FAINT)

        self.entry = tk.Text(bottom, bg=PANEL2, fg=TEXT, height=2, bd=0, wrap="word",
                             font=("Segoe UI", 11), padx=12, pady=10, insertbackground=GOLD)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Shift-Return>", lambda e: None)

        self.send_btn = self._mk_btn(bottom, "Senden ➤", self.on_send, CYAN, solid=True)
        self.send_btn.pack(side="left", padx=(8, 0), ipady=6)

        hint = "Enter = senden  -  Shift+Enter = neue Zeile"
        if VOICE_IN:
            hint += "  -  \U0001F3A4 klicken: ich warte, bis du fertig geredet hast"
        tk.Label(self.root, text=hint, fg=FAINT, bg=BG, font=("Consolas", 8)).pack(pady=(0, 8))

    def _mk_btn(self, parent, text, cmd, color, solid=False):
        if solid:
            return tk.Button(parent, text=text, command=cmd, bg=color, fg="#08111a",
                             activebackground=color, activeforeground="#08111a", bd=0,
                             font=("Segoe UI Semibold", 10), padx=14, cursor="hand2")
        return tk.Button(parent, text=text, command=cmd, bg=BG, fg=color,
                         activebackground=BG, activeforeground=color, bd=0,
                         font=("Segoe UI", 10), cursor="hand2")

    # ---------- Begruessung ----------
    def _greet(self):
        prov = self.brain.active_providers()
        self._sys("Modus: " + ("DESKTOP - Voll-Agent (Dateisystem + Chrome)" if FULL
                               else "PORTABLE - Chat + Sprache (kein Systemzugriff)"))
        if not requests:
            self._sys("Achtung: 'requests' fehlt - bitte requirements installieren.")
        if not prov:
            self.bubble("jarvis", "JARVIS",
                        "Guten Tag. Ich bin online, aber mir fehlen noch die API-Schluessel. "
                        "Oeffne ⚙ Einstellungen und trage mindestens einen Schluessel ein "
                        "(OpenAI, Claude oder Gemini).")
        else:
            names = ", ".join(PROVIDERS[p]["label"] for p in prov)
            extra = " Wir arbeiten im Team." if (len(prov) > 1 and self.team_var.get()) else ""
            caps = " Ich kann Dateien oeffnen und Chrome starten." if FULL else ""
            self.bubble("jarvis", "JARVIS",
                        f"Guten Tag. Alle Systeme bereit. Aktiv: {names}.{extra}{caps} Womit kann ich helfen?")

    # ---------- Chat-Ausgabe ----------
    def bubble(self, tag, who, text):
        self.chat.config(state="normal")
        self.chat.insert("end", who + "\n", tag)
        self.chat.insert("end", text + "\n\n", "body")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _sys(self, text):
        self.chat.config(state="normal")
        self.chat.insert("end", "  " + text + "\n\n", "sys")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def set_status(self, text, color=DIM):
        self.status.config(text=text, fg=color)

    # ---------- Thread -> UI ----------
    def _poll_queue(self):
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.root.after(60, self._poll_queue)

    def post(self, fn):
        self.ui_queue.put(fn)

    # ---------- Eingabe ----------
    def _on_return(self, event):
        if event.state & 0x0001:  # Shift gedrueckt -> neue Zeile
            return
        self.on_send()
        return "break"

    def on_send(self):
        if self.busy:
            return
        text = self.entry.get("1.0", "end").strip()
        if not text:
            return
        self.entry.delete("1.0", "end")
        self._handle_input(text)

    def _handle_input(self, text):
        self.bubble("you", "Du", text)
        prov = self.brain.active_providers()
        if not prov:
            self.bubble("jarvis", "JARVIS",
                        "Mir fehlt noch ein API-Schluessel. Bitte unter ⚙ Einstellungen eintragen.")
            return
        self.busy = True
        self.send_btn.config(state="disabled")
        self.set_status("denkt nach…", CYAN)
        threading.Thread(target=self._think, args=(text, prov), daemon=True).start()

    def _think(self, text, prov):
        team = self.team_var.get() and len(prov) > 1
        try:
            if team:
                def emit(name, role, body):
                    self.post(lambda n=name, r=role, b=body: self.bubble("agent", f"{n} ({r})", b))
                final = self.brain.respond_team(text, prov, emit)
            else:
                final = self._agent_loop(prov[0], text)
        except Exception as e:
            final = f"Es ist ein Fehler aufgetreten: {e}"

        # Gedaechtnis aktualisieren (auf die letzten Runden begrenzt)
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": final})
        self.history = self.history[-16:]

        def done():
            self.bubble("jarvis", "JARVIS", final)
            self.busy = False
            self.send_btn.config(state="normal")
            self.set_status("bereit", DIM)
        self.post(done)

        if self.voice_var.get() and self.tts is not None:
            self._speak(final)

    # ---------- Agent-Schleife (mit Werkzeugen im Full-Modus) ----------
    def _agent_loop(self, provider, user_text):
        system = JARVIS_PERSONA + (TOOLS_SPEC if FULL else "")
        msgs = list(self.history[-12:]) + [{"role": "user", "content": user_text}]
        reply = ""
        for _ in range(6):
            reply = self.brain.complete(provider, system, msgs)
            tool = self._parse_tool(reply) if FULL else None
            if not tool:
                return reply
            name, args = tool
            self.post(lambda n=name: self.set_status(f"⚙ {n}…", GOLD))
            self.post(lambda n=name, a=args: self._sys(f"Aktion: {n}  {json.dumps(a, ensure_ascii=False)}"))
            result = self._exec_tool(name, args)
            self.post(lambda r=result: self._sys("Ergebnis: " + (r[:300] + ("…" if len(r) > 300 else ""))))
            msgs.append({"role": "assistant", "content": reply})
            msgs.append({"role": "user", "content": "Tool-Ergebnis: " + result})
        # Falls nach mehreren Schritten noch kein Klartext: Zusammenfassung erzwingen
        return self.brain.complete(provider, JARVIS_PERSONA,
                                   msgs + [{"role": "user", "content": "Fasse das Ergebnis kurz fuer den Nutzer zusammen."}])

    @staticmethod
    def _parse_tool(reply):
        s = (reply or "").strip()
        if s.startswith("```"):
            s = s.strip("`")
            if s.lower().startswith("json"):
                s = s[4:]
            s = s.strip()
        if not s.startswith("{"):
            return None
        try:
            obj = json.loads(s)
        except Exception:
            return None
        if isinstance(obj, dict) and "tool" in obj:
            return obj["tool"], (obj.get("args") or {})
        return None

    # ---------- Werkzeuge (nur Full-/Desktop-Modus) ----------
    def _confirm(self, text):
        ev = threading.Event()
        res = {"ok": False}

        def ask():
            res["ok"] = messagebox.askyesno("JARVIS - Aktion bestaetigen", text)
            ev.set()
        self.post(ask)
        ev.wait()
        return res["ok"]

    def _exec_tool(self, name, args):
        if not FULL:
            return "Aktionen sind nur in der Desktop-Version erlaubt."
        try:
            if name == "open_chrome":
                return self._open_chrome(args.get("url", ""))
            if name == "open_path":
                return self._open_path(args.get("path", ""))
            if name == "list_dir":
                return self._list_dir(args.get("path", "."))
            if name == "read_file":
                return self._read_file(args.get("path", ""))
            if name == "write_file":
                return self._write_file(args.get("path", ""), args.get("content", ""))
            if name == "run_command":
                return self._run_command(args.get("command", ""))
            return f"Unbekanntes Tool: {name}"
        except Exception as e:
            return f"Fehler: {e}"

    def _open_chrome(self, url):
        if not url:
            return "Keine URL angegeben."
        import subprocess
        import shutil
        import webbrowser
        for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
            if os.path.exists(c):
                subprocess.Popen([c, url])
                return f"Chrome geoeffnet: {url}"
        exe = shutil.which("chrome") or shutil.which("google-chrome")
        if exe:
            subprocess.Popen([exe, url])
            return f"Chrome geoeffnet: {url}"
        webbrowser.open(url)
        return f"Standardbrowser geoeffnet: {url}"

    def _open_path(self, path):
        if not path or not os.path.exists(path):
            return f"Pfad nicht gefunden: {path}"
        try:
            os.startfile(path)  # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", path])
        return f"Geoeffnet: {path}"

    def _list_dir(self, path):
        path = path or "."
        if not os.path.isdir(path):
            return f"Kein Ordner: {path}"
        items = sorted(os.listdir(path))[:200]
        return f"Inhalt von {path} ({len(items)} Eintraege):\n" + "\n".join(items)

    def _read_file(self, path):
        if not os.path.isfile(path):
            return f"Keine Datei: {path}"
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(8000)

    def _write_file(self, path, content):
        if not self._confirm(f"JARVIS moechte schreiben:\n{path}\n({len(content)} Zeichen)\n\nErlauben?"):
            return "Vom Nutzer abgelehnt."
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Geschrieben: {path}"

    def _run_command(self, command):
        if not command:
            return "Kein Befehl."
        if not self._confirm(f"JARVIS moechte ausfuehren:\n\n{command}\n\nErlauben?"):
            return "Vom Nutzer abgelehnt."
        import subprocess
        out = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        res = (out.stdout or "")
        if out.stderr:
            res += "\n[stderr] " + out.stderr
        return (res[:4000] or "(kein Output)")

    # ---------- Sprache raus ----------
    def _speak(self, text):
        clean = self._strip_md(text)
        try:
            self.tts.setProperty("rate", self.data.get("voice_rate", 180))
            self.tts.say(clean)
            self.tts.runAndWait()
        except Exception:
            pass

    @staticmethod
    def _strip_md(s):
        for ch in ("*", "`", "#", "_", ">"):
            s = s.replace(ch, "")
        return s

    # ---------- Sprache rein (wartet bis du fertig bist) ----------
    def toggle_listen(self):
        if not VOICE_IN:
            messagebox.showinfo("Mikrofon", "Sprach-Eingabe nicht verfuegbar.\n"
                                "Bitte 'SpeechRecognition' und 'PyAudio' installieren.")
            return
        if self.busy or self.listening:
            return
        self.listening = True
        self.mic_btn.config(fg=RED, text="●")
        self.set_status("\U0001F3A4 ich hoere… sprich, ich warte bis du fertig bist", RED)
        threading.Thread(target=self._listen_once, daemon=True).start()

    def _listen_once(self):
        recog = sr.Recognizer()
        # WICHTIG: erst nach einer Sprechpause zurueckgeben ->
        # JARVIS denkt NICHT, waehrend du noch redest.
        recog.pause_threshold = 1.3
        recog.dynamic_energy_threshold = True
        transcript, err = None, None
        try:
            with sr.Microphone() as source:
                recog.adjust_for_ambient_noise(source, duration=0.5)
                audio = recog.listen(source, timeout=12, phrase_time_limit=40)
            # Erst JETZT (du bist fertig) wird transkribiert:
            self.post(lambda: self.set_status("verstehe…", CYAN))
            transcript = self._transcribe(recog, audio)
        except sr.WaitTimeoutError:
            err = "Ich habe nichts gehoert."
        except Exception as e:
            err = f"Mikrofon-Fehler: {e}"

        def finish():
            self.listening = False
            self.mic_btn.config(fg=CYAN, text="\U0001F3A4")
            self.set_status("bereit", DIM)
            if err:
                self._sys(err)
            elif transcript:
                self._handle_input(transcript)
            else:
                self._sys("Nichts verstanden.")
        self.post(finish)

    def _transcribe(self, recog, audio):
        # Beste Qualitaet: OpenAI Whisper, falls Key vorhanden
        okey = self.data["keys"].get("openai", "").strip()
        if okey and requests:
            try:
                wav = audio.get_wav_data()
                r = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": "Bearer " + okey},
                    files={"file": ("speech.wav", wav, "audio/wav")},
                    data={"model": "whisper-1", "language": "de"},
                    timeout=90,
                )
                if r.status_code < 400:
                    return r.json().get("text", "").strip()
            except Exception:
                pass
        # Fallback: kostenlose Google-Web-Erkennung (Internet noetig, kein Key)
        try:
            return recog.recognize_google(audio, language="de-DE").strip()
        except Exception:
            return ""

    # ---------- Schalter ----------
    def _toggle_team(self):
        self.data["team_mode"] = self.team_var.get()
        save_data(self.data)

    def _toggle_voice(self):
        self.data["voice_out"] = self.voice_var.get()
        save_data(self.data)

    # ============================================================
    #  Einstellungen (Keys + Supabase-Login)
    # ============================================================
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Einstellungen")
        win.configure(bg=BG)
        win.geometry("560x600")
        win.transient(self.root)

        pad = {"padx": 18, "pady": 6}

        tk.Label(win, text="API-Schluessel", fg=GOLD, bg=BG,
                 font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(win, text="Trage 1-3 Schluessel ein. Mehrere = sie arbeiten im Team zusammen.",
                 fg=DIM, bg=BG, font=("Segoe UI", 9)).pack(anchor="w", padx=18)

        key_vars, model_vars = {}, {}
        for p in ("openai", "anthropic", "gemini"):
            box = tk.Frame(win, bg=PANEL)
            box.pack(fill="x", **pad)
            tk.Label(box, text=PROVIDERS[p]["label"], fg=CYAN, bg=PANEL,
                     font=("Segoe UI Semibold", 11), width=10, anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=8)
            kv = tk.StringVar(value=self.data["keys"].get(p, ""))
            key_vars[p] = kv
            tk.Entry(box, textvariable=kv, show="*", bg=PANEL2, fg=TEXT, bd=0,
                     insertbackground=GOLD, font=("Consolas", 10)).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
            mv = tk.StringVar(value=self.data["models"].get(p, PROVIDERS[p]["default_model"]))
            model_vars[p] = mv
            tk.Entry(box, textvariable=mv, bg=PANEL2, fg=DIM, bd=0,
                     insertbackground=GOLD, font=("Consolas", 9), width=22).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
            box.columnconfigure(1, weight=1)

        # Supabase-Konto
        tk.Label(win, text="Konto (optional, Supabase)", fg=GOLD, bg=BG,
                 font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=18, pady=(14, 2))
        if not self.supa.configured:
            tk.Label(win, text="Kein Supabase konfiguriert. Lege config.json mit "
                               "supabase_url + supabase_anon_key an, um Konten zu nutzen.",
                     fg=DIM, bg=BG, font=("Segoe UI", 9), wraplength=500, justify="left").pack(anchor="w", padx=18)
        else:
            sess = self.data.get("session")
            if sess and sess.get("user"):
                tk.Label(win, text="Angemeldet als: " + sess["user"].get("email", "?"),
                         fg=CYAN, bg=BG, font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=4)
                tk.Button(win, text="Abmelden", command=lambda: self._logout(win),
                          bg=PANEL2, fg=RED, bd=0, font=("Segoe UI", 10), cursor="hand2").pack(anchor="w", padx=18)
            else:
                lf = tk.Frame(win, bg=BG)
                lf.pack(fill="x", padx=18, pady=4)
                tk.Label(lf, text="E-Mail", fg=DIM, bg=BG, font=("Segoe UI", 9)).pack(anchor="w")
                em_entry = tk.Entry(lf, bg=PANEL2, fg=TEXT, bd=0, insertbackground=GOLD,
                                    font=("Segoe UI", 10))
                em_entry.pack(fill="x", pady=(0, 6), ipady=4)
                tk.Label(lf, text="Passwort", fg=DIM, bg=BG, font=("Segoe UI", 9)).pack(anchor="w")
                pe = tk.Entry(lf, show="*", bg=PANEL2, fg=TEXT, bd=0,
                              insertbackground=GOLD, font=("Segoe UI", 10))
                pe.pack(fill="x", pady=(0, 6), ipady=4)
                brow = tk.Frame(lf, bg=BG); brow.pack(fill="x", pady=4)
                tk.Button(brow, text="Anmelden",
                          command=lambda: self._login(em_entry.get().strip(), pe.get(), win),
                          bg=CYAN, fg="#08111a", bd=0, font=("Segoe UI Semibold", 10),
                          cursor="hand2", padx=12).pack(side="left")
                tk.Button(brow, text="Registrieren",
                          command=lambda: self._signup(em_entry.get().strip(), pe.get(), win),
                          bg=PANEL2, fg=GOLD, bd=0, font=("Segoe UI", 10),
                          cursor="hand2", padx=12).pack(side="left", padx=8)

        # Speichern
        def save_and_close():
            for p in PROVIDERS:
                self.data["keys"][p] = key_vars[p].get().strip()
                self.data["models"][p] = model_vars[p].get().strip() or PROVIDERS[p]["default_model"]
            save_data(self.data)
            win.destroy()
            self.set_status("Einstellungen gespeichert", GOLD)
            self.root.after(1500, lambda: self.set_status("bereit", DIM))

        tk.Button(win, text="Speichern", command=save_and_close, bg=GOLD, fg="#08111a",
                  bd=0, font=("Segoe UI Semibold", 11), cursor="hand2", padx=18, pady=6).pack(pady=18)

    def _login(self, email, pw, win):
        if not email or not pw:
            messagebox.showinfo("Login", "Bitte E-Mail und Passwort eingeben."); return
        try:
            res = self.supa.login(email, pw)
            self.data["session"] = {
                "access_token": res.get("access_token"),
                "refresh_token": res.get("refresh_token"),
                "user": res.get("user", {}),
            }
            save_data(self.data)
            messagebox.showinfo("Login", "Angemeldet. Du bleibst jetzt eingeloggt.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Login fehlgeschlagen", str(e))

    def _signup(self, email, pw, win):
        if not email or not pw:
            messagebox.showinfo("Registrieren", "Bitte E-Mail und Passwort eingeben."); return
        try:
            self.supa.signup(email, pw)
            messagebox.showinfo("Registrieren",
                                "Konto erstellt. Falls noetig E-Mail bestaetigen, dann anmelden.")
        except Exception as e:
            messagebox.showerror("Registrieren fehlgeschlagen", str(e))

    def _logout(self, win):
        self.data["session"] = None
        save_data(self.data)
        win.destroy()
        self.set_status("abgemeldet", DIM)


def main():
    root = tk.Tk()
    try:
        # etwas schaerfer auf Windows-HiDPI
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    JarvisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
