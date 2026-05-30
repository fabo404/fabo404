#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
 J.A.R.V.I.S.  -  Portabler Iron-Man-Agent
 Laeuft mit DEMSELBEN Code auf  Windows / macOS / Linux.
============================================================
 - Echtes Fenster (Tkinter) - KEIN Browser
 - Animierter Arc-Reactor, Karten-Chat, Live-Streaming (flott!)
 - Portabel: speichert ALLES (Login + API-Keys) in
   'jarvis_data.json' NEBEN der App -> einmal anmelden,
   reist auf dem USB-Stick mit.
 - Reden + Schreiben: Mikrofon wartet, bis du FERTIG geredet
   hast (denkt NICHT waehrend du sprichst), spricht zurueck.
 - Agent: Gemini + OpenAI + Claude arbeiten zusammen.
 - Modi: portable (nur Chat+Sprache) | full (Dateien+Browser)
============================================================
"""

import os
import sys
import json
import math
import base64
import threading
import queue

import tkinter as tk
from tkinter import ttk, messagebox

try:
    import requests
except Exception:
    requests = None

try:
    import speech_recognition as sr
    VOICE_IN = True
except Exception:
    sr = None
    VOICE_IN = False

try:
    import pyttsx3
    VOICE_OUT = True
except Exception:
    pyttsx3 = None
    VOICE_OUT = False

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


# ============================================================
#  Speicherort (portabel -> neben der App / exe)
# ============================================================
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_FILE = os.path.join(app_dir(), "jarvis_data.json")
CONFIG_FILE = os.path.join(app_dir(), "config.json")


# ============================================================
#  Modus: "portable" (nur Chat+Sprache) | "full" (Voll-Agent)
# ============================================================
def detect_mode():
    if "--full" in sys.argv:
        return "full"
    if "--portable" in sys.argv:
        return "portable"
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
#  Anbieter & Persona
# ============================================================
PROVIDERS = {
    "openai":    {"label": "OpenAI",  "default_model": "gpt-4o-mini",        "icon": "O"},
    "anthropic": {"label": "Claude",  "default_model": "claude-sonnet-4-6",  "icon": "C"},
    "gemini":    {"label": "Gemini",  "default_model": "gemini-2.0-flash",   "icon": "G"},
}

JARVIS_PERSONA = (
    "Du bist J.A.R.V.I.S., der persoenliche KI-Assistent im Stil von Tony Starks Iron Man. "
    "Du bist hoeflich, trocken-britisch-charmant, extrem kompetent und kommst schnell auf den Punkt. "
    "Du sprichst Deutsch (ausser man bittet um etwas anderes) und gibst klare, umsetzbare Antworten. "
    "Halte gesprochene Antworten eher kurz und natuerlich, da sie vorgelesen werden."
)

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

TOOLS_SPEC = (
    "\n\nDu hast Zugriff auf den lokalen Computer (Desktop-Modus). "
    "Wenn du eine AKTION ausfuehren willst, antworte AUSSCHLIESSLICH mit EINEM JSON-Objekt "
    "(kein weiterer Text), Form: {\"tool\":\"NAME\",\"args\":{...}}.\n"
    "Verfuegbare Tools:\n"
    "- open_chrome  {\"url\":\"https://...\"}      -> oeffnet Chrome (oder Standardbrowser).\n"
    "- open_path    {\"path\":\"/Pfad/datei\"}     -> oeffnet Datei oder Ordner.\n"
    "- list_dir     {\"path\":\"/Pfad\"}            -> listet einen Ordner auf.\n"
    "- read_file    {\"path\":\"/.../datei.txt\"}   -> liest eine Textdatei.\n"
    "- write_file   {\"path\":\"...\",\"content\":\"...\"} -> schreibt eine Datei.\n"
    "- run_command  {\"command\":\"...\"}           -> fuehrt einen Befehl aus (wird vom Nutzer bestaetigt).\n"
    "Nach der Aktion bekommst du das Ergebnis als 'Tool-Ergebnis: ...' und antwortest dann "
    "dem Nutzer normal auf Deutsch. Wenn KEIN Tool noetig ist, antworte einfach normal (kein JSON)."
)


# ============================================================
#  Persistente Daten (portabel)
# ============================================================
def _obf(s):
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
    "team_mode": True,
    "voice_out": True,
    "voice_rate": 180,
    "session": None,
}


def load_data():
    data = json.loads(json.dumps(DEFAULT_DATA))
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if "keys" in saved:
            for p, v in saved["keys"].items():
                saved["keys"][p] = _deobf(v) if v else ""
        data.update(saved)
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
        r = requests.post(f"{self.url}/auth/v1/token?grant_type=password",
                          headers=self._headers(),
                          json={"email": email, "password": password}, timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(self._err(r))
        return r.json()

    def signup(self, email, password):
        r = requests.post(f"{self.url}/auth/v1/signup", headers=self._headers(),
                          json={"email": email, "password": password}, timeout=20)
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
#  LLM-Aufrufe (mit Verlauf) - nicht-streamend
# ============================================================
def call_openai(key, model, system, messages, base_url="https://api.openai.com/v1"):
    msgs = [{"role": "system", "content": system}] + messages
    r = requests.post(base_url + "/chat/completions",
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
                      json={"model": model, "max_tokens": 1200, "messages": msgs}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("OpenAI " + str(r.status_code) + ": " + r.text[:160])
    return r.json()["choices"][0]["message"]["content"]


def call_anthropic(key, model, system, messages):
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers={"Content-Type": "application/json", "x-api-key": key,
                               "anthropic-version": "2023-06-01"},
                      json={"model": model, "max_tokens": 1200, "system": system,
                            "messages": messages}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Claude " + str(r.status_code) + ": " + r.text[:160])
    return "".join(b.get("text", "") for b in r.json().get("content", []))


def call_gemini(key, model, system, messages):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":generateContent?key=" + key)
    contents = [{"role": ("user" if m["role"] == "user" else "model"),
                 "parts": [{"text": m["content"]}]} for m in messages]
    r = requests.post(url, headers={"Content-Type": "application/json"},
                      json={"systemInstruction": {"parts": [{"text": system}]},
                            "contents": contents,
                            "generationConfig": {"maxOutputTokens": 1200}}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError("Gemini " + str(r.status_code) + ": " + r.text[:160])
    parts = (r.json().get("candidates", [{}])[0].get("content", {}) or {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def call_provider(provider, key, model, system, messages):
    if provider == "openai":
        return call_openai(key, model, system, messages)
    if provider == "anthropic":
        return call_anthropic(key, model, system, messages)
    if provider == "gemini":
        return call_gemini(key, model, system, messages)
    raise RuntimeError("Unbekannter Anbieter: " + provider)


# ============================================================
#  LLM-Aufrufe - STREAMING (Antwort kommt live, Wort fuer Wort)
# ============================================================
def stream_openai(key, model, system, messages, on_token, base_url="https://api.openai.com/v1"):
    msgs = [{"role": "system", "content": system}] + messages
    full = ""
    with requests.post(base_url + "/chat/completions",
                       headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
                       json={"model": model, "max_tokens": 1200, "stream": True, "messages": msgs},
                       stream=True, timeout=120) as r:
        if r.status_code >= 400:
            raise RuntimeError("OpenAI " + str(r.status_code) + ": " + r.text[:160])
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                delta = json.loads(payload)["choices"][0]["delta"].get("content")
            except Exception:
                continue
            if delta:
                full += delta
                on_token(delta)
    return full


def stream_anthropic(key, model, system, messages, on_token):
    full = ""
    with requests.post("https://api.anthropic.com/v1/messages",
                       headers={"Content-Type": "application/json", "x-api-key": key,
                                "anthropic-version": "2023-06-01"},
                       json={"model": model, "max_tokens": 1200, "system": system,
                             "messages": messages, "stream": True},
                       stream=True, timeout=120) as r:
        if r.status_code >= 400:
            raise RuntimeError("Claude " + str(r.status_code) + ": " + r.text[:160])
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except Exception:
                continue
            if obj.get("type") == "content_block_delta":
                t = obj.get("delta", {}).get("text", "")
                if t:
                    full += t
                    on_token(t)
    return full


def stream_gemini(key, model, system, messages, on_token):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":streamGenerateContent?alt=sse&key=" + key)
    contents = [{"role": ("user" if m["role"] == "user" else "model"),
                 "parts": [{"text": m["content"]}]} for m in messages]
    full = ""
    with requests.post(url, headers={"Content-Type": "application/json"},
                       json={"systemInstruction": {"parts": [{"text": system}]},
                             "contents": contents,
                             "generationConfig": {"maxOutputTokens": 1200}},
                       stream=True, timeout=120) as r:
        if r.status_code >= 400:
            raise RuntimeError("Gemini " + str(r.status_code) + ": " + r.text[:160])
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except Exception:
                continue
            parts = (obj.get("candidates", [{}])[0].get("content", {}) or {}).get("parts", [])
            for p in parts:
                t = p.get("text", "")
                if t:
                    full += t
                    on_token(t)
    return full


def stream_provider(provider, key, model, system, messages, on_token):
    if provider == "openai":
        return stream_openai(key, model, system, messages, on_token)
    if provider == "anthropic":
        return stream_anthropic(key, model, system, messages, on_token)
    if provider == "gemini":
        return stream_gemini(key, model, system, messages, on_token)
    raise RuntimeError("Unbekannter Anbieter: " + provider)


# ============================================================
#  Agent-Engine
# ============================================================
class Brain:
    def __init__(self, data):
        self.data = data

    def active_providers(self):
        order = ["anthropic", "openai", "gemini"]
        return [p for p in order if self.data["keys"].get(p, "").strip()]

    def _km(self, provider):
        key = self.data["keys"][provider].strip()
        model = self.data["models"].get(provider) or PROVIDERS[provider]["default_model"]
        return key, model

    def complete(self, provider, system, messages):
        key, model = self._km(provider)
        return call_provider(provider, key, model, system, messages)

    def complete_stream(self, provider, system, messages, on_token):
        key, model = self._km(provider)
        return stream_provider(provider, key, model, system, messages, on_token)

    def respond_team(self, prompt, providers, emit):
        transcript = []

        def ctx():
            if not transcript:
                return "(noch keine Beitraege)"
            return "Bisheriger Verlauf des Teams:\n\n" + "\n\n".join(
                f"[{t[0]} - {t[1]}]\n{t[2]}" for t in transcript)

        workers = TEAM_AGENTS[:-1]
        synth = TEAM_AGENTS[-1]
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

        provider = providers[0]
        system = (JARVIS_PERSONA + " " + synth[2] +
                  " Fasse die Diskussion zu EINER klaren, umsetzbaren Endloesung zusammen.")
        usr = (f"AUFGABE DES NUTZERS:\n{prompt}\n\n{ctx()}\n\n"
               "DEINE AUFGABE JETZT: Liefere die finale, beste gemeinsame Antwort.")
        try:
            return self.complete(provider, system, [{"role": "user", "content": usr}])
        except Exception as e:
            return f"Entschuldigung, die Synthese ist fehlgeschlagen: {e}"


# ============================================================
#  Theme (Iron-Man)
# ============================================================
BG      = "#070a10"
HEADER  = "#0b0f18"
PANEL   = "#0d111b"
INPUT   = "#141926"
CARD_U  = "#1a1410"   # User-Bubble (warm/gold-getoent)
CARD_J  = "#0c1a24"   # JARVIS-Bubble (arc-reactor-getoent)
CARD_A  = "#15151f"   # Agenten
GOLD    = "#ffc24b"
CYAN    = "#4cc9ff"
RED     = "#ff5a4d"
TEXT    = "#eaf2fb"
DIM     = "#93a0b8"
FAINT   = "#5d6884"
LINE    = "#1d2638"

UIFONT = "Segoe UI" if IS_WIN else ("Helvetica Neue" if IS_MAC else "DejaVu Sans")
MONO   = "Consolas" if IS_WIN else ("Menlo" if IS_MAC else "DejaVu Sans Mono")


class JarvisApp:
    def __init__(self, root):
        self.root = root
        self.data = load_data()
        self.brain = Brain(self.data)
        self.supa = Supabase()

        self.busy = False
        self.listening = False
        self.ui_queue = queue.Queue()
        self.history = []
        self._phase = 0

        self.tts = None
        if VOICE_OUT:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty("rate", self.data.get("voice_rate", 180))
            except Exception:
                self.tts = None
        self.can_speak = (self.tts is not None) or IS_MAC

        self._build_ui()
        self._poll_queue()
        self._animate()
        self._greet()

    # ---------- UI ----------
    def _build_ui(self):
        mode_label = "DESKTOP · Voll-Agent" if FULL else "PORTABLE · USB"
        self.root.title("J.A.R.V.I.S.  —  Iron Man Assistant  [" + mode_label + "]")
        self.root.configure(bg=BG)
        self.root.geometry("900x720")
        self.root.minsize(680, 540)

        # ===== Kopfzeile =====
        top = tk.Frame(self.root, bg=HEADER)
        top.pack(fill="x")
        inner = tk.Frame(top, bg=HEADER)
        inner.pack(fill="x", padx=18, pady=12)

        self.reactor = tk.Canvas(inner, width=46, height=46, bg=HEADER, highlightthickness=0)
        self.reactor.pack(side="left")

        title = tk.Frame(inner, bg=HEADER)
        title.pack(side="left", padx=12)
        tk.Label(title, text="J . A . R . V . I . S .", fg=TEXT, bg=HEADER,
                 font=(UIFONT, 17, "bold")).pack(anchor="w")
        self.status = tk.Label(title, text="initialisiere…", fg=DIM, bg=HEADER, font=(MONO, 9))
        self.status.pack(anchor="w")

        self.team_var = tk.BooleanVar(value=self.data.get("team_mode", True))
        self.voice_var = tk.BooleanVar(value=self.data.get("voice_out", True) and self.can_speak)

        self._mk_btn(inner, "⚙", self.open_settings, GOLD).pack(side="right")
        self._chk(inner, "Team", self.team_var, self._toggle_team, GOLD).pack(side="right", padx=10)
        self._chk(inner, "Stimme", self.voice_var, self._toggle_voice, CYAN).pack(side="right")

        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x")

        # ===== Chat =====
        mid = tk.Frame(self.root, bg=PANEL)
        mid.pack(fill="both", expand=True)
        self.chat = tk.Text(mid, bg=PANEL, fg=TEXT, wrap="word", bd=0, padx=20, pady=18,
                            font=(UIFONT, 11), state="disabled", insertbackground=TEXT,
                            spacing2=3, cursor="arrow")
        sb = ttk.Scrollbar(mid, command=self.chat.yview)
        self.chat.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.chat.pack(side="left", fill="both", expand=True)
        self._init_tags()

        # ===== Eingabe =====
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill="x", padx=16, pady=14)

        self.mic_btn = tk.Button(bottom, text="🎤", command=self.toggle_listen,
                                 bg=INPUT, fg=CYAN, activebackground=INPUT, activeforeground=CYAN,
                                 bd=0, font=(UIFONT, 16), width=3, cursor="hand2",
                                 highlightthickness=1, highlightbackground=LINE)
        self.mic_btn.pack(side="left", padx=(0, 10), ipady=6)
        if not VOICE_IN:
            self.mic_btn.config(state="disabled", fg=FAINT)

        wrap = tk.Frame(bottom, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        wrap.pack(side="left", fill="x", expand=True)
        self.entry = tk.Text(wrap, bg=INPUT, fg=TEXT, height=2, bd=0, wrap="word",
                             font=(UIFONT, 11), padx=14, pady=11, insertbackground=GOLD)
        self.entry.pack(fill="x", expand=True)
        self.entry.bind("<Return>", self._on_return)

        self.send_btn = tk.Button(bottom, text="Senden  ➤", command=self.on_send, bg=CYAN,
                                  fg="#04121c", activebackground="#7ad7ff", activeforeground="#04121c",
                                  bd=0, font=(UIFONT, 11, "bold"), padx=18, cursor="hand2")
        self.send_btn.pack(side="left", padx=(10, 0), ipady=8)

        hint = "Enter = senden   ·   Shift+Enter = neue Zeile"
        if VOICE_IN:
            hint += "   ·   🎤 = ich warte, bis du fertig geredet hast"
        tk.Label(self.root, text=hint, fg=FAINT, bg=BG, font=(MONO, 8)).pack(pady=(0, 8))

    def _init_tags(self):
        c = self.chat
        c.tag_config("you_name", foreground=GOLD, font=(UIFONT, 10, "bold"),
                     spacing1=12, lmargin1=14, lmargin2=14)
        c.tag_config("you_body", foreground=TEXT, background=CARD_U, font=(UIFONT, 11),
                     lmargin1=14, lmargin2=14, rmargin=80, spacing1=3, spacing3=10)
        c.tag_config("jarvis_name", foreground=CYAN, font=(UIFONT, 10, "bold"),
                     spacing1=12, lmargin1=14, lmargin2=14)
        c.tag_config("jarvis_body", foreground=TEXT, background=CARD_J, font=(UIFONT, 11),
                     lmargin1=14, lmargin2=14, rmargin=50, spacing1=3, spacing3=10)
        c.tag_config("agent_name", foreground="#c3cbe2", font=(UIFONT, 10, "bold"),
                     spacing1=10, lmargin1=14, lmargin2=14)
        c.tag_config("agent_body", foreground=DIM, background=CARD_A, font=(UIFONT, 10),
                     lmargin1=14, lmargin2=14, rmargin=60, spacing1=2, spacing3=8)
        c.tag_config("sys", foreground=FAINT, font=(MONO, 9), spacing1=4, lmargin1=14, lmargin2=14)
        c.tag_config("gap", font=(UIFONT, 4))

    def _mk_btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd, bg=HEADER, fg=color,
                         activebackground=HEADER, activeforeground=color, bd=0,
                         font=(UIFONT, 14), cursor="hand2")

    def _chk(self, parent, text, var, cmd, color):
        return tk.Checkbutton(parent, text=text, variable=var, command=cmd, fg=color, bg=HEADER,
                              selectcolor=PANEL, activebackground=HEADER, activeforeground=color,
                              font=(UIFONT, 10), bd=0, highlightthickness=0)

    # ---------- Animation ----------
    def _animate(self):
        self._phase += 1
        self._draw_reactor()
        if self.listening:
            self.mic_btn.config(fg=RED if (self._phase // 2) % 2 else "#ff9d95")
        self.root.after(110, self._animate)

    def _draw_reactor(self):
        c = self.reactor
        c.delete("all")
        cx = cy = 23
        active = self.busy or self.listening
        speed = 0.5 if active else 0.18
        pulse = (math.sin(self._phase * speed) + 1) / 2  # 0..1
        col = RED if self.listening else CYAN
        c.create_oval(cx - 20, cy - 20, cx + 20, cy + 20, outline=LINE, width=2)
        r = 9 + pulse * 8
        glow = "#16465f" if not self.listening else "#5c1f1c"
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=glow, width=2)
        c.create_oval(cx - 13, cy - 13, cx + 13, cy + 13, outline=col, width=2)
        # 3 Speichen
        for k in range(3):
            a = self._phase * 0.05 + k * (2 * math.pi / 3)
            x, y = cx + 13 * math.cos(a), cy + 13 * math.sin(a)
            c.create_line(cx, cy, x, y, fill=col, width=2)
        core = 5 + pulse * 2
        c.create_oval(cx - core, cy - core, cx + core, cy + core, fill=col, outline="")
        c.create_oval(cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5, fill="#eafdff", outline="")

    # ---------- Begruessung ----------
    def _greet(self):
        prov = self.brain.active_providers()
        self._sys("● Modus: " + ("DESKTOP — Voll-Agent (Dateisystem + Browser)" if FULL
                                 else "PORTABLE — Chat + Sprache (kein Systemzugriff)")
                  + f"   ·   System: {'macOS' if IS_MAC else 'Windows' if IS_WIN else 'Linux'}")
        if not requests:
            self._sys("Achtung: 'requests' fehlt — bitte requirements installieren.")
        if not prov:
            self.bubble("jarvis", "JARVIS",
                        "Guten Tag. Ich bin online, aber mir fehlen noch die API-Schluessel. "
                        "Oeffne ⚙ und trage mindestens einen Schluessel ein (OpenAI, Claude oder Gemini).")
        else:
            names = ", ".join(PROVIDERS[p]["label"] for p in prov)
            extra = " Wir arbeiten im Team." if (len(prov) > 1 and self.team_var.get()) else ""
            caps = " Ich kann Dateien und den Browser oeffnen." if FULL else ""
            self.bubble("jarvis", "JARVIS",
                        f"Guten Tag. Alle Systeme bereit. Aktiv: {names}.{extra}{caps} Womit kann ich helfen?")
        self.set_status("bereit", DIM)

    # ---------- Chat-Ausgabe ----------
    def bubble(self, kind, who, text):
        self.chat.config(state="normal")
        self.chat.insert("end", " " + who + "\n", kind + "_name")
        self.chat.insert("end", " " + text + " \n", kind + "_body")
        self.chat.insert("end", "\n", "gap")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _stream_begin(self):
        self.chat.config(state="normal")
        self.chat.insert("end", " JARVIS\n", "jarvis_name")
        self.chat.insert("end", " ", "jarvis_body")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _stream_token(self, t):
        self.chat.config(state="normal")
        self.chat.insert("end", t, "jarvis_body")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _stream_end(self):
        self.chat.config(state="normal")
        self.chat.insert("end", " \n", "jarvis_body")
        self.chat.insert("end", "\n", "gap")
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
                self.ui_queue.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(33, self._poll_queue)

    def post(self, fn):
        self.ui_queue.put(fn)

    # ---------- Eingabe ----------
    def _on_return(self, event):
        if event.state & 0x0001:  # Shift -> neue Zeile
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
                        "Mir fehlt noch ein API-Schluessel. Bitte unter ⚙ eintragen.")
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
                self.post(lambda: self.bubble("jarvis", "JARVIS", final))
            else:
                final = self._agent_stream(prov[0], text)
        except Exception as e:
            final = f"Es ist ein Fehler aufgetreten: {e}"
            self.post(lambda f=final: self.bubble("jarvis", "JARVIS", f))

        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": final})
        self.history = self.history[-16:]

        def idle():
            self.busy = False
            self.send_btn.config(state="normal")
            self.set_status("bereit", DIM)
        self.post(idle)

        if self.voice_var.get() and self.can_speak:
            self._speak(final)

    # ---------- Agent (Streaming + Werkzeuge) ----------
    def _agent_stream(self, provider, user_text):
        system = JARVIS_PERSONA + (TOOLS_SPEC if FULL else "")
        msgs = list(self.history[-12:]) + [{"role": "user", "content": user_text}]

        if FULL:
            # Erst pruefen, ob ein Werkzeug noetig ist (Tool-Schleife)
            reply = self.brain.complete(provider, system, msgs)
            steps = 0
            while True:
                tool = self._parse_tool(reply)
                if not tool or steps >= 6:
                    break
                steps += 1
                name, args = tool
                self.post(lambda n=name: self.set_status(f"⚙ {n}…", GOLD))
                self.post(lambda n=name, a=args: self._sys(
                    f"Aktion: {n}  {json.dumps(a, ensure_ascii=False)}"))
                result = self._exec_tool(name, args)
                self.post(lambda r=result: self._sys(
                    "Ergebnis: " + (r[:280] + ("…" if len(r) > 280 else ""))))
                msgs.append({"role": "assistant", "content": reply})
                msgs.append({"role": "user", "content": "Tool-Ergebnis: " + result})
                reply = self.brain.complete(provider, system, msgs)
            self.post(lambda r=reply: self.bubble("jarvis", "JARVIS", r))
            return reply

        # Portable: direktes Live-Streaming in eine Bubble
        self.post(self._stream_begin)
        self.post(lambda: self.set_status("antwortet…", CYAN))

        def on_token(t):
            self.post(lambda t=t: self._stream_token(t))
        full = self.brain.complete_stream(provider, system, msgs, on_token)
        self.post(self._stream_end)
        return full

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
            res["ok"] = messagebox.askyesno("JARVIS — Aktion bestaetigen", text)
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
        if IS_MAC:
            try:
                subprocess.Popen(["open", "-a", "Google Chrome", url])
                return f"Chrome geoeffnet: {url}"
            except Exception:
                webbrowser.open(url)
                return f"Standardbrowser geoeffnet: {url}"
        if IS_WIN:
            for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                      r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
                if os.path.exists(c):
                    subprocess.Popen([c, url])
                    return f"Chrome geoeffnet: {url}"
        exe = shutil.which("google-chrome") or shutil.which("chrome")
        if exe:
            subprocess.Popen([exe, url])
            return f"Chrome geoeffnet: {url}"
        webbrowser.open(url)
        return f"Standardbrowser geoeffnet: {url}"

    def _open_path(self, path):
        if not path or not os.path.exists(path):
            return f"Pfad nicht gefunden: {path}"
        import subprocess
        if IS_MAC:
            subprocess.Popen(["open", path])
        elif IS_WIN:
            os.startfile(path)  # type: ignore[attr-defined]
        else:
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
        return res[:4000] or "(kein Output)"

    # ---------- Sprache raus ----------
    def _speak(self, text):
        clean = self._strip_md(text)
        if self.tts is not None:
            try:
                self.tts.setProperty("rate", self.data.get("voice_rate", 180))
                self.tts.say(clean)
                self.tts.runAndWait()
                return
            except Exception:
                pass
        if IS_MAC:
            try:
                import subprocess
                subprocess.run(["say", clean], timeout=120)
            except Exception:
                pass

    @staticmethod
    def _strip_md(s):
        for ch in ("*", "`", "#", "_", ">"):
            s = s.replace(ch, "")
        return s

    # ---------- Sprache rein (wartet, bis du fertig bist) ----------
    def toggle_listen(self):
        if not VOICE_IN:
            messagebox.showinfo("Mikrofon", "Sprach-Eingabe nicht verfuegbar.\n"
                                "Bitte 'SpeechRecognition' und 'PyAudio' installieren.")
            return
        if self.busy or self.listening:
            return
        self.listening = True
        self.set_status("🎤 ich hoere… sprich, ich warte bis du fertig bist", RED)
        threading.Thread(target=self._listen_once, daemon=True).start()

    def _listen_once(self):
        recog = sr.Recognizer()
        recog.pause_threshold = 1.3  # erst nach Sprechpause -> denkt NICHT waehrend du redest
        recog.dynamic_energy_threshold = True
        transcript, err = None, None
        try:
            with sr.Microphone() as source:
                recog.adjust_for_ambient_noise(source, duration=0.4)
                audio = recog.listen(source, timeout=12, phrase_time_limit=40)
            self.post(lambda: self.set_status("verstehe…", CYAN))
            transcript = self._transcribe(recog, audio)
        except sr.WaitTimeoutError:
            err = "Ich habe nichts gehoert."
        except Exception as e:
            err = f"Mikrofon-Fehler: {e}"

        def finish():
            self.listening = False
            self.mic_btn.config(fg=CYAN, text="🎤")
            self.set_status("bereit", DIM)
            if err:
                self._sys(err)
            elif transcript:
                self._handle_input(transcript)
            else:
                self._sys("Nichts verstanden.")
        self.post(finish)

    def _transcribe(self, recog, audio):
        okey = self.data["keys"].get("openai", "").strip()
        if okey and requests:
            try:
                r = requests.post("https://api.openai.com/v1/audio/transcriptions",
                                  headers={"Authorization": "Bearer " + okey},
                                  files={"file": ("speech.wav", audio.get_wav_data(), "audio/wav")},
                                  data={"model": "whisper-1", "language": "de"}, timeout=90)
                if r.status_code < 400:
                    return r.json().get("text", "").strip()
            except Exception:
                pass
        try:
            return recog.recognize_google(audio, language="de-DE").strip()
        except Exception:
            return ""

    # ---------- Schalter ----------
    def _toggle_team(self):
        self.data["team_mode"] = self.team_var.get()
        save_data(self.data)

    def _toggle_voice(self):
        if self.voice_var.get() and not self.can_speak:
            self.voice_var.set(False)
            messagebox.showinfo("Stimme", "Sprachausgabe nicht verfuegbar (pyttsx3 fehlt).")
            return
        self.data["voice_out"] = self.voice_var.get()
        save_data(self.data)

    # ============================================================
    #  Einstellungen (Keys + Supabase-Login)
    # ============================================================
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Einstellungen")
        win.configure(bg=BG)
        win.geometry("560x620")
        win.transient(self.root)

        tk.Label(win, text="API-Schluessel", fg=GOLD, bg=BG,
                 font=(UIFONT, 13, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(win, text="Trage 1–3 Schluessel ein. Mehrere = sie arbeiten im Team zusammen.",
                 fg=DIM, bg=BG, font=(UIFONT, 9)).pack(anchor="w", padx=18)

        key_vars, model_vars = {}, {}
        for p in ("openai", "anthropic", "gemini"):
            box = tk.Frame(win, bg=PANEL)
            box.pack(fill="x", padx=18, pady=6)
            tk.Label(box, text=PROVIDERS[p]["label"], fg=CYAN, bg=PANEL, font=(UIFONT, 11, "bold"),
                     width=10, anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=8)
            kv = tk.StringVar(value=self.data["keys"].get(p, ""))
            key_vars[p] = kv
            tk.Entry(box, textvariable=kv, show="•", bg=INPUT, fg=TEXT, bd=0, insertbackground=GOLD,
                     font=(MONO, 10)).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
            mv = tk.StringVar(value=self.data["models"].get(p, PROVIDERS[p]["default_model"]))
            model_vars[p] = mv
            tk.Entry(box, textvariable=mv, bg=INPUT, fg=DIM, bd=0, insertbackground=GOLD,
                     font=(MONO, 9), width=22).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
            box.columnconfigure(1, weight=1)

        tk.Label(win, text="Konto (optional, Supabase)", fg=GOLD, bg=BG,
                 font=(UIFONT, 13, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        if not self.supa.configured:
            tk.Label(win, text="Kein Supabase konfiguriert. Lege config.json mit supabase_url + "
                               "supabase_anon_key an, um Konten zu nutzen.",
                     fg=DIM, bg=BG, font=(UIFONT, 9), wraplength=500, justify="left").pack(anchor="w", padx=18)
        else:
            sess = self.data.get("session")
            if sess and sess.get("user"):
                tk.Label(win, text="Angemeldet als: " + sess["user"].get("email", "?"),
                         fg=CYAN, bg=BG, font=(UIFONT, 10)).pack(anchor="w", padx=18, pady=4)
                tk.Button(win, text="Abmelden", command=lambda: self._logout(win), bg=INPUT, fg=RED,
                          bd=0, font=(UIFONT, 10), cursor="hand2").pack(anchor="w", padx=18)
            else:
                lf = tk.Frame(win, bg=BG)
                lf.pack(fill="x", padx=18, pady=4)
                tk.Label(lf, text="E-Mail", fg=DIM, bg=BG, font=(UIFONT, 9)).pack(anchor="w")
                em_entry = tk.Entry(lf, bg=INPUT, fg=TEXT, bd=0, insertbackground=GOLD, font=(UIFONT, 10))
                em_entry.pack(fill="x", pady=(0, 6), ipady=4)
                tk.Label(lf, text="Passwort", fg=DIM, bg=BG, font=(UIFONT, 9)).pack(anchor="w")
                pe = tk.Entry(lf, show="•", bg=INPUT, fg=TEXT, bd=0, insertbackground=GOLD, font=(UIFONT, 10))
                pe.pack(fill="x", pady=(0, 6), ipady=4)
                brow = tk.Frame(lf, bg=BG)
                brow.pack(fill="x", pady=4)
                tk.Button(brow, text="Anmelden",
                          command=lambda: self._login(em_entry.get().strip(), pe.get(), win),
                          bg=CYAN, fg="#04121c", bd=0, font=(UIFONT, 10, "bold"),
                          cursor="hand2", padx=12).pack(side="left")
                tk.Button(brow, text="Registrieren",
                          command=lambda: self._signup(em_entry.get().strip(), pe.get(), win),
                          bg=INPUT, fg=GOLD, bd=0, font=(UIFONT, 10), cursor="hand2",
                          padx=12).pack(side="left", padx=8)

        def save_and_close():
            for p in PROVIDERS:
                self.data["keys"][p] = key_vars[p].get().strip()
                self.data["models"][p] = model_vars[p].get().strip() or PROVIDERS[p]["default_model"]
            save_data(self.data)
            win.destroy()
            self.set_status("Einstellungen gespeichert", GOLD)
            self.root.after(1500, lambda: self.set_status("bereit", DIM))

        tk.Button(win, text="Speichern", command=save_and_close, bg=GOLD, fg="#1a1205", bd=0,
                  font=(UIFONT, 11, "bold"), cursor="hand2", padx=18, pady=6).pack(pady=18)

    def _login(self, email, pw, win):
        if not email or not pw:
            messagebox.showinfo("Login", "Bitte E-Mail und Passwort eingeben.")
            return
        try:
            res = self.supa.login(email, pw)
            self.data["session"] = {"access_token": res.get("access_token"),
                                    "refresh_token": res.get("refresh_token"),
                                    "user": res.get("user", {})}
            save_data(self.data)
            messagebox.showinfo("Login", "Angemeldet. Du bleibst jetzt eingeloggt.")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Login fehlgeschlagen", str(e))

    def _signup(self, email, pw, win):
        if not email or not pw:
            messagebox.showinfo("Registrieren", "Bitte E-Mail und Passwort eingeben.")
            return
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
    if IS_WIN:
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    JarvisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
