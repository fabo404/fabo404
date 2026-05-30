/* ============================================================
 * Freezy AI · Cloud-Konto (Supabase) + verschlüsselter Tresor
 * ------------------------------------------------------------
 * - Login mit Benutzername + Passwort
 * - Anbieter-Keys werden client-seitig mit dem Passwort verschlüsselt
 *   (AES-GCM, Schlüssel via PBKDF2). Der Server sieht nie Klartext.
 * - persistSession:false → an fremden PCs bleibt nichts zurück.
 * ============================================================ */
const Auth = (() => {
  const cfg = window.SUPABASE_CONFIG || {};
  const isConfigured = !!(cfg.url && cfg.anonKey && !/DEIN|EXAMPLE|xxxx/i.test(cfg.url));

  let sb = null;
  if (isConfigured && window.supabase) {
    sb = window.supabase.createClient(cfg.url, cfg.anonKey, {
      auth: { persistSession: false, autoRefreshToken: true },
    });
  }

  let user = null;      // Supabase user
  let encKey = null;    // CryptoKey (nur im RAM)
  let salt = null;      // Uint8Array
  let pw = null;        // Passwort nur im RAM für diese Sitzung

  /* ---- Krypto-Helfer (WebCrypto) ---- */
  const b64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
  const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

  async function deriveKey(password, saltBytes) {
    const km = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: saltBytes, iterations: 150000, hash: "SHA-256" },
      km, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]
    );
  }
  async function encryptObj(obj) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, encKey, new TextEncoder().encode(JSON.stringify(obj)));
    return { v: 1, salt: b64(salt), iv: b64(iv), ct: b64(ct) };
  }
  async function decryptPayload(payload) {
    const iv = unb64(payload.iv);
    const ct = unb64(payload.ct);
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, encKey, ct);
    return JSON.parse(new TextDecoder().decode(pt));
  }

  /* ---- Fehlertexte ---- */
  function translate(msg) {
    msg = msg || "";
    if (/Invalid login credentials/i.test(msg)) return "Benutzername oder Passwort falsch.";
    if (/already registered|already exists/i.test(msg)) return "Dieses Konto gibt es schon — bitte einloggen.";
    if (/Password should be at least/i.test(msg)) return "Passwort zu kurz (mind. 6 Zeichen).";
    if (/Email.*invalid|invalid.*email/i.test(msg)) return "Benutzername ungültig (nur Buchstaben/Zahlen).";
    return msg;
  }

  function userToEmail(u) {
    u = (u || "").trim();
    return u.includes("@") ? u.toLowerCase() : `${u.toLowerCase().replace(/[^a-z0-9._-]/g, "")}@freezy.local`;
  }

  /* ---- Tresor laden / speichern ---- */
  async function loadVault() {
    const { data, error } = await sb.from("vaults").select("data").eq("user_id", user.id).maybeSingle();
    if (error) throw new Error(error.message);
    if (!data || !data.data) {
      // Noch kein Tresor → frisches Salz anlegen
      salt = crypto.getRandomValues(new Uint8Array(16));
      encKey = await deriveKey(pw, salt);
      return null;
    }
    const payload = JSON.parse(data.data);
    salt = unb64(payload.salt);
    encKey = await deriveKey(pw, salt);
    try {
      return await decryptPayload(payload);
    } catch {
      throw new Error("Der Tresor ließ sich nicht entschlüsseln (Passwort?).");
    }
  }

  async function pushVault(state) {
    if (!user || !encKey) return;
    const payload = await encryptObj(state);
    const { error } = await sb.from("vaults")
      .upsert({ user_id: user.id, data: JSON.stringify(payload), updated_at: new Date().toISOString() });
    if (error) throw new Error(error.message);
  }

  /* ---- Auth ---- */
  async function signIn(username, password) {
    const { data, error } = await sb.auth.signInWithPassword({ email: userToEmail(username), password });
    if (error) throw new Error(translate(error.message));
    user = data.user; pw = password;
    return loadVault();
  }

  async function signUp(username, password) {
    const { data, error } = await sb.auth.signUp({ email: userToEmail(username), password });
    if (error) throw new Error(translate(error.message));
    if (!data.session) {
      // E-Mail-Bestätigung ist noch aktiv → mit @freezy.local unmöglich
      throw new Error("Bitte in Supabase die E-Mail-Bestätigung deaktivieren (Authentication → Sign In / Providers → \"Confirm email\" aus).");
    }
    user = data.user; pw = password;
    salt = crypto.getRandomValues(new Uint8Array(16));
    encKey = await deriveKey(pw, salt);
    return null; // frisches Konto, noch keine Daten
  }

  async function signOut() {
    try { if (sb) await sb.auth.signOut(); } catch {}
    user = null; encKey = null; salt = null; pw = null;
  }

  return {
    configured: () => isConfigured && !!sb,
    loggedIn: () => !!user,
    username: () => (user ? (user.email || "").replace(/@freezy\.local$/, "") : ""),
    signIn, signUp, signOut, pushVault,
  };
})();
