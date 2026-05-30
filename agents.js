/* ============================================================
 * Synapse · Multi-Agent Orchestration Engine
 * - Portable: Schlüssel nur im RAM (keine Rückstände) oder
 *   per Config-Datei auf dem USB-Stick gespeichert
 * - Mehrere Anbieter (Gemini / Claude / OpenAI) gleichzeitig
 * - Modi: Einzel (ein Anbieter) oder Agent-Modus (alle zusammen)
 * - Demo-Modus offline
 * ============================================================ */

const AVATAR_PALETTE = ["🜂", "🧭", "🏗️", "🔬", "🛡️", "✍️", "⚖️", "💡", "📊", "🎯", "🧪", "🌐"];

const AVATAR_BG = {
  "🜂": "#272c4d", "🧭": "#16324a", "🏗️": "#3a2a18", "🔬": "#15323a",
  "🛡️": "#2a1830", "✍️": "#2a2a18", "⚖️": "#1f2a18", "💡": "#3a3416",
  "📊": "#182a2a", "🎯": "#3a1820", "🧪": "#1a2a3a", "🌐": "#1a2e2a",
};

const PROVIDERS = {
  gemini:    { label: "Google · Gemini",      defaultModel: "gemini-2.0-flash", icon: "✦" },
  anthropic: { label: "Anthropic · Claude",   defaultModel: "claude-sonnet-4-6", icon: "🜂" },
  openai:    { label: "OpenAI-kompatibel",    defaultModel: "gpt-4o-mini",      icon: "◎" },
};

const DEFAULT_AGENTS = [
  { id: "scout", name: "Scout", role: "Researcher", avatar: "🧭",
    persona: "Du bist ein gründlicher Rechercheur. Du zerlegst die Aufgabe, sammelst Fakten, Annahmen und offene Fragen. Du bist präzise und nennst konkrete Beispiele." },
  { id: "forge", name: "Forge", role: "Architekt", avatar: "🏗️",
    persona: "Du bist ein Lösungs-Architekt. Du baust aus der Recherche eine konkrete, strukturierte Lösung mit klaren Schritten und Begründungen." },
  { id: "raven", name: "Raven", role: "Kritiker", avatar: "⚖️",
    persona: "Du bist ein scharfer, fairer Kritiker. Du findest Schwächen, Risiken und blinde Flecken im Vorschlag und machst konkrete Verbesserungsvorschläge. Konstruktiv, nicht destruktiv." },
  { id: "echo", name: "Echo", role: "Synthesizer", avatar: "💡",
    persona: "Du bist der Synthesizer. Du verbindest die besten Ideen aller Agenten zu einer einzigen, klaren, umsetzbaren Endlösung. Du strukturierst sauber und triffst Entscheidungen." },
];

/* ============================================================
 * Config (Portable)
 *   config = {
 *     portable: true,                       // true => kein localStorage
 *     accounts: { gemini:{apiKey,model}, ... },
 *     mode: "agent" | "single",
 *     single: "gemini",                     // aktiver Anbieter im Einzelmodus
 *     agents: [...]
 *   }
 * Im Portable-Modus lebt alles nur im RAM (= keine Spuren auf dem PC).
 * Persistenz erfolgt ausschließlich über Export/Import einer Datei
 * auf dem USB-Stick.
 * ============================================================ */
const Config = (() => {
  const DEFAULTS = () => ({
    portable: true,
    accounts: {},
    mode: "agent",
    single: "gemini",
    agents: structuredClone(DEFAULT_AGENTS),
  });

  let state = DEFAULTS();

  // Beim Start: wenn früher NICHT portable gespeichert wurde, laden.
  try {
    const saved = JSON.parse(localStorage.getItem("synapse.config"));
    if (saved && saved.portable === false) state = { ...DEFAULTS(), ...saved };
  } catch {}

  function persistIfAllowed() {
    if (state.portable) {
      // Portable: niemals auf den PC schreiben, evtl. Altlasten entfernen
      try { localStorage.removeItem("synapse.config"); } catch {}
    } else {
      try { localStorage.setItem("synapse.config", JSON.stringify(state)); } catch {}
    }
  }

  return {
    get: () => state,
    set(patch) { state = { ...state, ...patch }; persistIfAllowed(); },
    setAccount(provider, data) {
      state.accounts = { ...state.accounts, [provider]: data };
      persistIfAllowed();
    },
    removeAccount(provider) {
      const a = { ...state.accounts }; delete a[provider];
      state.accounts = a; persistIfAllowed();
    },
    setAgents(agents) { state.agents = agents; persistIfAllowed(); },
    enabledProviders() {
      return Object.keys(state.accounts).filter((p) => state.accounts[p] && state.accounts[p].apiKey);
    },
    // Export für USB-Stick
    exportBlob() {
      return new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    },
    importObject(obj) {
      state = { ...DEFAULTS(), ...obj };
      persistIfAllowed();
    },
    // Alles aus dem Browser entfernen (Panik-/Aufräum-Knopf in der Schule)
    wipe() {
      try { localStorage.removeItem("synapse.config"); } catch {}
      try { sessionStorage.clear(); } catch {}
      state = DEFAULTS();
    },
  };
})();

/* ============================================================
 * LLM-Aufruf je Anbieter
 * ============================================================ */
async function callLLM(provider, account, systemPrompt, userText) {
  if (provider === "gemini") {
    const model = account.model || PROVIDERS.gemini.defaultModel;
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(account.apiKey)}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: systemPrompt }] },
        contents: [{ role: "user", parts: [{ text: userText }] }],
        generationConfig: { maxOutputTokens: 1024 },
      }),
    });
    if (!res.ok) throw new Error("Gemini " + res.status + ": " + (await res.text()).slice(0, 160));
    const data = await res.json();
    return (data.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("");
  }

  if (provider === "anthropic") {
    const res = await fetch((account.baseUrl || "https://api.anthropic.com") + "/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": account.apiKey,
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model: account.model || PROVIDERS.anthropic.defaultModel,
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: "user", content: userText }],
      }),
    });
    if (!res.ok) throw new Error("Anthropic " + res.status + ": " + (await res.text()).slice(0, 160));
    const data = await res.json();
    return data.content.map((c) => c.text || "").join("");
  }

  // OpenAI-kompatibel
  const res = await fetch((account.baseUrl || "https://api.openai.com/v1") + "/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: "Bearer " + account.apiKey },
    body: JSON.stringify({
      model: account.model || PROVIDERS.openai.defaultModel,
      max_tokens: 1024,
      messages: [{ role: "system", content: systemPrompt }, { role: "user", content: userText }],
    }),
  });
  if (!res.ok) throw new Error("OpenAI " + res.status + ": " + (await res.text()).slice(0, 160));
  const data = await res.json();
  return data.choices[0].message.content;
}

/* ============================================================
 * EINZEL-MODUS: direkte Antwort von genau einem Anbieter
 * ============================================================ */
async function runSingle(task, provider, hooks) {
  const cfg = Config.get();
  const account = cfg.accounts[provider];
  const live = account && account.apiKey;

  const agent = {
    id: "single",
    name: live ? (PROVIDERS[provider]?.label || provider) : "Demo-Assistent",
    role: live ? "Einzelmodell" : "Demo",
    avatar: PROVIDERS[provider]?.icon === "✦" ? "🌐" : "🜂",
  };

  hooks.onPhase("Einzel-Modus · " + agent.name);
  hooks.onThinkStart(agent);

  let text;
  if (live) {
    const sys = "Du bist ein hilfreicher, präziser Assistent. Antworte klar und gut strukturiert.";
    try { text = await callLLM(provider, account, sys, task); }
    catch (e) { text = "⚠️ API-Fehler: " + e.message + "\n\n" + demoSingle(task); }
  } else {
    await wait(700 + Math.random() * 500);
    text = demoSingle(task);
  }

  hooks.onThinkEnd(agent);
  hooks.onMessage(agent, text, { final: true });
  return text;
}

/* ============================================================
 * AGENT-MODUS: alle angemeldeten Anbieter arbeiten zusammen.
 * Agenten werden reihum auf die aktiven Anbieter verteilt,
 * damit wirklich "alle, bei denen du angemeldet bist" mitreden.
 * ============================================================ */
async function orchestrate(task, rounds, hooks) {
  const cfg = Config.get();
  const agents = cfg.agents;
  const enabled = Config.enabledProviders();
  const transcript = [];

  const synthesizer = agents.find((a) => a.role.toLowerCase().includes("synth")) || agents[agents.length - 1];
  const workers = agents.filter((a) => a !== synthesizer);

  // Anbieter-Zuweisung pro Agent (round-robin über aktive Accounts)
  const providerFor = {};
  agents.forEach((a, i) => {
    providerFor[a.id] = enabled.length ? enabled[i % enabled.length] : null;
  });

  const contextBlock = () =>
    transcript.length
      ? "Bisheriger Verlauf des Teams:\n\n" +
        transcript.map((t) => `[${t.agent.name} · ${t.agent.role}]\n${t.text}`).join("\n\n")
      : "(noch keine Beiträge)";

  async function speak(agent, instruction, opts = {}) {
    const provider = providerFor[agent.id];
    const account = provider ? cfg.accounts[provider] : null;
    const live = account && account.apiKey;

    // Anbieter-Badge fürs UI mitgeben
    const tagged = { ...agent, provider: live ? (PROVIDERS[provider]?.label || provider) : "Demo" };
    hooks.onThinkStart(tagged);

    let text;
    if (live) {
      const sys = `${agent.persona}\n\nDu arbeitest in einem Team aus mehreren KI-Agenten (teils auf unterschiedlichen Modellen) an einer gemeinsamen Aufgabe. Antworte fokussiert (max ~180 Wörter), beziehe dich wo sinnvoll auf die Beiträge der anderen.`;
      const userMsg = `AUFGABE DES NUTZERS:\n${task}\n\n${contextBlock()}\n\nDEINE AUFGABE JETZT:\n${instruction}`;
      try { text = await callLLM(provider, account, sys, userMsg); }
      catch (e) { text = `⚠️ API-Fehler (${tagged.provider}) — Demo-Antwort:\n\n` + demoResponse(agent, task, transcript, opts); }
    } else {
      await wait(600 + Math.random() * 650);
      text = demoResponse(agent, task, transcript, opts);
    }

    hooks.onThinkEnd(tagged);
    transcript.push({ agent, text });
    hooks.onMessage(tagged, text, opts);
    return text;
  }

  hooks.onPhase("Runde 1 · Analyse & Planung");
  for (const agent of workers) {
    const isFirst = transcript.length === 0;
    await speak(agent,
      isFirst ? "Analysiere die Aufgabe aus deiner Rolle heraus und lege den Grundstein für die Lösung."
              : "Baue auf den bisherigen Beiträgen auf und ergänze deine Perspektive.",
      { ref: !isFirst });
  }

  for (let r = 2; r <= rounds; r++) {
    hooks.onPhase(`Runde ${r} · Verfeinerung & Kritik`);
    for (const agent of workers) {
      await speak(agent, "Reagiere auf die Beiträge der anderen: stärke gute Ideen, widerlege schwache, und verbessere die Lösung konkret.", { ref: true });
    }
  }

  hooks.onPhase("Synthese · Bestes gemeinsames Ergebnis");
  return speak(synthesizer, "Fasse die gesamte Diskussion zu EINER klaren, vollständigen und umsetzbaren Endlösung zusammen. Triff Entscheidungen, wo das Team uneinig war. Strukturiere das Ergebnis übersichtlich.", { ref: true, final: true });
}

/* ============================================================
 * Demo-Antworten (offline)
 * ============================================================ */
function demoSingle(task) {
  const topic = task.length > 70 ? task.slice(0, 67).trim() + "…" : task;
  return (
    `**Antwort** zu *"${topic}"* _(Demo-Modus)_\n\n` +
    `Hier würde das gewählte Modell direkt antworten. Trage unter **Anbieter & Schlüssel** ` +
    `einen API-Key ein, um echte Antworten zu erhalten.\n\n` +
    `- Punkt 1: Kern der Lösung\n- Punkt 2: konkrete Umsetzung\n- Punkt 3: nächster Schritt`
  );
}

function demoResponse(agent, task, transcript, opts) {
  const topic = task.length > 70 ? task.slice(0, 67).trim() + "…" : task;
  const role = agent.role.toLowerCase();
  const round = transcript.filter((x) => x.agent === agent).length;
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

  if (opts.final || role.includes("synth")) {
    return (
      `**Gemeinsames Ergebnis** zu *"${topic}"*\n\n` +
      `Nach ${transcript.length} Beiträgen hat das Team konvergiert:\n\n` +
      `1. **Kern-Ansatz** — Scouts Analyse + Forges Struktur.\n` +
      `2. **Umsetzung** — klare Schritte, größter Hebel zuerst.\n` +
      `3. **Risiken** — Ravens Einwände eingearbeitet.\n` +
      `4. **Nächster Schritt** — bestes Aufwand/Wirkung-Verhältnis.\n\n` +
      `> Konsens: stärkste Variante, die alle Perspektiven vereint. ✅`
    );
  }
  if (role.includes("research") || role.includes("scout")) {
    if (round === 0)
      return `Ich zerlege *"${topic}"*:\n\n- **Ziel:** Was soll herauskommen?\n- **Annahmen:** ${pick(["Zielgruppe","Budget","Zeitrahmen"])} ist offen.\n- **Hebel:** Klarheit & Priorisierung.\n\nForge, übernimm die Struktur.`;
    return `Ich habe Forges Struktur geprüft — beim Punkt "${pick(["Priorisierung","Messbarkeit","Zielgruppe"])}" fehlt noch ein Detail.`;
  }
  if (role.includes("archi") || role.includes("forge")) {
    if (round === 0)
      return `Struktur-Vorschlag:\n\n\`\`\`\n1. Fundament  → ${pick(["Anforderungen","Setup","Datenbasis"])}\n2. Kernlösung → schrittweise\n3. Feinschliff → testen\n\`\`\`\n\nRaven, wo siehst du Schwächen?`;
    return `Ich passe die Architektur an Ravens Kritik an: Schritt 2 wird in zwei testbare Teile gesplittet — geringeres Risiko.`;
  }
  if (role.includes("krit") || role.includes("raven") || role.includes("critic")) {
    if (round === 0)
      return `Einwände:\n\n- ⚠️ Schritt 2 ist zu groß.\n- ⚠️ **${pick(["Edge-Cases","Skalierung","Akzeptanz"])}** fehlt.\n- ✅ Schrittweise Struktur ist stark.\n\nVorschlag: aufteilen + Mess-Punkt.`;
    return `Die Anpassungen überzeugen mich. Letzter Punkt: ein klares Erfolgskriterium definieren, dann ist es rund.`;
  }
  return `Aus Sicht von **${agent.name}** (${agent.role}): Ich bringe meine Spezialität ein und achte besonders auf **${pick(["Qualität","Machbarkeit","Wirkung"])}**.`;
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
