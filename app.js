/* ============================================================
 * Synapse · UI-Controller (Portable Edition)
 * ============================================================ */

const $ = (s) => document.querySelector(s);
const el = (tag, cls) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };

let running = false;
let editingAgentId = null;
let selectedAvatar = AVATAR_PALETTE[0];

/* ---------------- Init ---------------- */
function init() {
  renderRoster();
  renderProviderList();
  renderModeUI();
  updateModePill();
  bindComposer();
  bindControls();
  bindModals();
  bindPortable();
}

/* ---------------- Roster ---------------- */
function renderRoster() {
  const list = $("#rosterList");
  list.innerHTML = "";
  Config.get().agents.forEach((a) => {
    const card = el("div", "agent-card");
    card.dataset.id = a.id;
    card.style.setProperty("--avatar-bg", AVATAR_BG[a.avatar] || "#1b1e2e");
    card.innerHTML = `
      <div class="av">${a.avatar}</div>
      <div class="meta">
        <div class="nm">${esc(a.name)}</div>
        <div class="rl">${esc(a.role)}</div>
      </div>
      <div class="pulse"></div>`;
    card.onclick = () => openAgentEditor(a.id);
    list.appendChild(card);
  });
}

function renderProviderList() {
  const wrap = $("#providerList");
  wrap.innerHTML = "";
  const enabled = Config.enabledProviders();
  if (!enabled.length) {
    const e = el("div", "provider-empty");
    e.textContent = "Noch keiner angemeldet — Demo-Modus aktiv.";
    wrap.appendChild(e);
    return;
  }
  Object.keys(PROVIDERS).forEach((p) => {
    const on = enabled.includes(p);
    const chip = el("div", "provider-chip " + (on ? "on" : "off"));
    chip.innerHTML = `
      <div class="pic">${PROVIDERS[p].icon}</div>
      <div class="pname">${esc(PROVIDERS[p].label)}</div>
      <div class="pstate"></div>`;
    if (on) wrap.appendChild(chip);
  });
}

function setThinking(agentId, on) {
  const card = document.querySelector(`.agent-card[data-id="${agentId}"]`);
  if (card) card.classList.toggle("thinking", on);
}

/* ---------------- Mode UI ---------------- */
function renderModeUI() {
  const cfg = Config.get();
  const single = cfg.mode === "single";
  $("#modeSingle").classList.toggle("active", single);
  $("#modeAgent").classList.toggle("active", !single);
  $("#singleProvider").hidden = !single;
  $("#roundsCtrl").hidden = single;

  // populate single-provider dropdown
  const sel = $("#singleProvider");
  sel.innerHTML = "";
  const enabled = Config.enabledProviders();
  if (!enabled.length) {
    const o = el("option"); o.value = "demo"; o.textContent = "Demo (offline)"; sel.appendChild(o);
  } else {
    enabled.forEach((p) => {
      const o = el("option"); o.value = p; o.textContent = PROVIDERS[p].label;
      if (p === cfg.single) o.selected = true;
      sel.appendChild(o);
    });
  }
}

/* ---------------- Composer ---------------- */
function bindComposer() {
  const input = $("#taskInput");
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 180) + "px";
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); }
  });
  $("#sendBtn").onclick = start;
  $("#suggestions").querySelectorAll("button").forEach((b) => {
    b.onclick = () => { input.value = b.textContent; input.dispatchEvent(new Event("input")); input.focus(); };
  });
}

function bindControls() {
  const slider = $("#roundsSlider");
  slider.oninput = () => ($("#roundsVal").textContent = slider.value);

  $("#modeSingle").onclick = () => { Config.set({ mode: "single" }); renderModeUI(); updateModePill(); };
  $("#modeAgent").onclick = () => { Config.set({ mode: "agent" }); renderModeUI(); updateModePill(); };
  $("#singleProvider").onchange = (e) => { Config.set({ single: e.target.value }); updateModePill(); };
}

/* ---------------- Run ---------------- */
async function start() {
  if (running) return;
  const task = $("#taskInput").value.trim();
  if (!task) return;

  running = true;
  $("#sendBtn").disabled = true;
  $("#emptyState").hidden = true;
  $("#taskInput").value = "";
  $("#taskInput").style.height = "auto";

  addUserMessage(task);

  const hooks = {
    onPhase: (label) => addDivider(label),
    onThinkStart: (agent) => { setThinking(agent.id, true); showTyping(agent); },
    onThinkEnd: (agent) => { setThinking(agent.id, false); hideTyping(); },
    onMessage: (agent, text, opts) => addAgentMessage(agent, text, opts),
  };

  const cfg = Config.get();
  try {
    if (cfg.mode === "single") {
      await runSingle(task, cfg.single || "demo", hooks);
    } else {
      const rounds = parseInt($("#roundsSlider").value, 10);
      await orchestrate(task, rounds, hooks);
    }
  } catch (e) {
    addDivider("Fehler");
    const err = el("div", "user-msg");
    err.style.alignSelf = "center";
    err.textContent = "Fehler: " + e.message;
    $("#thread").appendChild(err);
  }

  running = false;
  $("#sendBtn").disabled = false;
  scrollDown();
}

/* ---------------- Thread rendering ---------------- */
function addUserMessage(text) {
  const m = el("div", "user-msg");
  m.textContent = text;
  $("#thread").appendChild(m);
  scrollDown();
}
function addDivider(label) {
  const d = el("div", "round-divider");
  d.textContent = label;
  $("#thread").appendChild(d);
  scrollDown();
}

let typingNode = null;
function showTyping(agent) {
  hideTyping();
  const m = el("div", "msg");
  m.style.setProperty("--avatar-bg", AVATAR_BG[agent.avatar] || "#1b1e2e");
  m.innerHTML = `
    <div class="av">${agent.avatar}</div>
    <div class="bubble">
      <div class="bubble-head"><span class="nm">${esc(agent.name)}</span><span class="role-tag">${esc(agent.role)}</span></div>
      <div class="typing"><span></span><span></span><span></span></div>
    </div>`;
  typingNode = m;
  $("#thread").appendChild(m);
  scrollDown();
}
function hideTyping() { if (typingNode) { typingNode.remove(); typingNode = null; } }

function addAgentMessage(agent, text, opts = {}) {
  hideTyping();
  const m = el("div", "msg" + (opts.final ? " final" : "") + (opts.ref ? " ref" : ""));
  m.style.setProperty("--avatar-bg", AVATAR_BG[agent.avatar] || "#1b1e2e");
  const badge = agent.provider ? `<span class="provider-badge">${esc(agent.provider)}</span>` : "";
  const phase = opts.final ? "ERGEBNIS" : "";
  m.innerHTML = `
    <div class="av">${agent.avatar}</div>
    <div class="bubble">
      <div class="bubble-head">
        <span class="nm">${esc(agent.name)}</span>
        <span class="role-tag">${esc(agent.role)}</span>
        ${badge}
        ${phase ? `<span class="phase">${phase}</span>` : ""}
      </div>
      <div class="body">${renderMarkdown(text)}</div>
    </div>`;
  $("#thread").appendChild(m);
  scrollDown();
}

function scrollDown() {
  const b = $("#board");
  requestAnimationFrame(() => (b.scrollTop = b.scrollHeight));
}

/* ---------------- Minimal markdown ---------------- */
function renderMarkdown(src) {
  let s = esc(src);
  s = s.replace(/```([\s\S]*?)```/g, (_, c) => `<pre>${c.replace(/^\n/, "")}</pre>`);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  s = s.replace(/_([^_\n]+)_/g, "<em>$1</em>");
  s = s.replace(/^&gt; (.+)$/gm, '<p style="border-left:3px solid var(--accent-2);padding-left:12px;color:var(--text-dim)">$1</p>');
  s = s.replace(/(?:^|\n)((?:[-*] .+(?:\n|$))+)/g, (_, block) => {
    const items = block.trim().split("\n").map((l) => "<li>" + l.replace(/^[-*]\s+/, "") + "</li>").join("");
    return "\n<ul>" + items + "</ul>";
  });
  s = s.replace(/(?:^|\n)((?:\d+\. .+(?:\n|$))+)/g, (_, block) => {
    const items = block.trim().split("\n").map((l) => "<li>" + l.replace(/^\d+\.\s+/, "") + "</li>").join("");
    return "\n<ol style='margin:4px 0 9px 20px'>" + items + "</ol>";
  });
  s = s.split(/\n{2,}/).map((p) => (/^\s*<(ul|ol|pre|p)/.test(p.trim()) ? p : "<p>" + p.replace(/\n/g, "<br>") + "</p>")).join("");
  return s;
}

/* ---------------- Settings / Accounts modal ---------------- */
function bindModals() {
  $("#settingsBtn").onclick = openSettings;
  $("#closeSettings").onclick = $("#cancelSettings").onclick = () => ($("#settingsModal").hidden = true);
  $("#saveSettings").onclick = saveSettingsFromModal;

  $("#addAgentBtn").onclick = () => openAgentEditor(null);
  $("#closeAgent").onclick = () => ($("#agentModal").hidden = true);
  $("#saveAgent").onclick = saveAgentFromModal;
  $("#deleteAgent").onclick = deleteCurrentAgent;

  const row = $("#avatarRow");
  AVATAR_PALETTE.forEach((a) => {
    const o = el("div", "opt");
    o.textContent = a; o.dataset.av = a;
    o.onclick = () => { selectedAvatar = a; row.querySelectorAll(".opt").forEach((x) => x.classList.remove("sel")); o.classList.add("sel"); };
    row.appendChild(o);
  });

  document.querySelectorAll(".modal-backdrop").forEach((bd) => {
    bd.addEventListener("click", (e) => { if (e.target === bd) bd.hidden = true; });
  });
}

function openSettings() {
  const cfg = Config.get();
  $("#portableToggle").checked = !!cfg.portable;
  renderAccounts();
  $("#settingsModal").hidden = false;
}

function renderAccounts() {
  const cfg = Config.get();
  const wrap = $("#accountsContainer");
  wrap.innerHTML = "";
  Object.keys(PROVIDERS).forEach((p) => {
    const acc = cfg.accounts[p] || {};
    const on = !!acc.apiKey;
    const card = el("div", "account" + (on ? " active open" : ""));
    card.dataset.provider = p;
    const showBase = p !== "gemini";
    card.innerHTML = `
      <div class="account-head">
        <div class="pic">${PROVIDERS[p].icon}</div>
        <div class="info">
          <div class="t">${esc(PROVIDERS[p].label)}</div>
          <div class="s">${esc(acc.model || PROVIDERS[p].defaultModel)}</div>
        </div>
        <span class="status ${on ? "on" : "off"}">${on ? "angemeldet" : "offen"}</span>
        <span class="chev">▸</span>
      </div>
      <div class="account-body ${on ? "" : "collapsed"}">
        <div class="row">
          <label class="field"><span>Modell</span>
            <input type="text" data-f="model" placeholder="${PROVIDERS[p].defaultModel}" value="${esc(acc.model || "")}" /></label>
          ${showBase ? `<label class="field"><span>Basis-URL <small>(optional)</small></span>
            <input type="text" data-f="baseUrl" placeholder="Standard" value="${esc(acc.baseUrl || "")}" /></label>` : ""}
        </div>
        <label class="field"><span>API-Schlüssel</span>
          <input type="password" data-f="apiKey" placeholder="hier einfügen…" value="${esc(acc.apiKey || "")}" /></label>
      </div>`;
    card.querySelector(".account-head").onclick = () => {
      card.classList.toggle("open");
      card.querySelector(".account-body").classList.toggle("collapsed");
    };
    wrap.appendChild(card);
  });
}

function saveSettingsFromModal() {
  Config.set({ portable: $("#portableToggle").checked });
  document.querySelectorAll("#accountsContainer .account").forEach((card) => {
    const p = card.dataset.provider;
    const get = (f) => { const i = card.querySelector(`[data-f="${f}"]`); return i ? i.value.trim() : ""; };
    const apiKey = get("apiKey");
    if (apiKey) Config.setAccount(p, { apiKey, model: get("model"), baseUrl: get("baseUrl") });
    else Config.removeAccount(p);
  });
  // sicherstellen, dass single-provider gültig ist
  const enabled = Config.enabledProviders();
  if (enabled.length && !enabled.includes(Config.get().single)) Config.set({ single: enabled[0] });

  renderProviderList();
  renderModeUI();
  updateModePill();
  $("#settingsModal").hidden = true;
}

function updateModePill() {
  const cfg = Config.get();
  const pill = $("#modePill");
  const enabled = Config.enabledProviders();
  const base = cfg.portable ? "Portable" : "Gespeichert";
  if (!enabled.length) {
    pill.textContent = base + " · Demo";
    pill.classList.remove("live");
  } else if (cfg.mode === "single") {
    pill.textContent = base + " · " + (PROVIDERS[cfg.single]?.label.split("·").pop().trim() || "Einzel");
    pill.classList.add("live");
  } else {
    pill.textContent = base + " · " + enabled.length + " Anbieter";
    pill.classList.add("live");
  }
}

/* ---------------- Portable: USB save/load + wipe ---------------- */
function bindPortable() {
  $("#saveUsbBtn").onclick = () => {
    const url = URL.createObjectURL(Config.exportBlob());
    const a = el("a"); a.href = url; a.download = "synapse-config.json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("Konfiguration gespeichert — leg die Datei auf deinen USB-Stick.");
  };
  $("#loadUsbBtn").onclick = () => $("#usbFile").click();
  $("#usbFile").onchange = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    try {
      const obj = JSON.parse(await file.text());
      Config.importObject(obj);
      renderRoster(); renderProviderList(); renderModeUI(); updateModePill();
      toast("Konfiguration vom USB-Stick geladen ✓");
    } catch { toast("Datei konnte nicht gelesen werden."); }
    e.target.value = "";
  };
  $("#wipeBtn").onclick = () => {
    if (!confirm("Alle Schlüssel & Spuren auf DIESEM PC löschen?\n(Deine USB-Datei bleibt erhalten.)")) return;
    Config.wipe();
    renderRoster(); renderProviderList(); renderModeUI(); updateModePill();
    toast("Bereinigt — keine Rückstände auf diesem PC.");
  };
}

let toastTimer = null;
function toast(msg) {
  let t = $("#toast");
  if (!t) { t = el("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}

/* ---------------- Agent editor ---------------- */
function openAgentEditor(id) {
  editingAgentId = id;
  const agents = Config.get().agents;
  const a = id ? agents.find((x) => x.id === id) : null;
  $("#agentModalTitle").textContent = a ? "Agent bearbeiten" : "Agent hinzufügen";
  $("#agentName").value = a ? `${a.name} · ${a.role}` : "";
  $("#agentPersona").value = a ? a.persona : "";
  selectedAvatar = a ? a.avatar : AVATAR_PALETTE[Math.floor(Math.random() * AVATAR_PALETTE.length)];
  $("#avatarRow").querySelectorAll(".opt").forEach((o) => o.classList.toggle("sel", o.dataset.av === selectedAvatar));
  $("#deleteAgent").hidden = !a || agents.length <= 2;
  $("#agentModal").hidden = false;
}

function saveAgentFromModal() {
  const raw = $("#agentName").value.trim();
  if (!raw) return;
  const [name, role] = raw.includes("·") ? raw.split("·").map((s) => s.trim()) : [raw, "Agent"];
  const persona = $("#agentPersona").value.trim() || `Du bist ${name}, ein spezialisierter Agent (${role}).`;
  const agents = [...Config.get().agents];

  if (editingAgentId) {
    const a = agents.find((x) => x.id === editingAgentId);
    Object.assign(a, { name, role: role || "Agent", persona, avatar: selectedAvatar });
  } else {
    agents.push({ id: "a" + Date.now(), name, role: role || "Agent", persona, avatar: selectedAvatar });
  }
  Config.setAgents(agents);
  renderRoster();
  $("#agentModal").hidden = true;
}

function deleteCurrentAgent() {
  Config.setAgents(Config.get().agents.filter((a) => a.id !== editingAgentId));
  renderRoster();
  $("#agentModal").hidden = true;
}

/* ---------------- utils ---------------- */
function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

init();
