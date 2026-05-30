/* ============================================================
 * Freezy AI · Cloud-Konto Konfiguration
 * ------------------------------------------------------------
 * Trage hier die zwei Werte aus deinem KOSTENLOSEN Supabase-Projekt ein:
 *   Supabase Dashboard → Project Settings → API
 *     • Project URL      → url
 *     • anon public key  → anonKey
 *
 * Der anon-Key ist für den Browser gedacht und DARF öffentlich sein
 * (der Schutz läuft über "Row Level Security" in der Datenbank).
 *
 * Solange die Felder leer sind, läuft Freezy AI ganz normal OHNE Login
 * (lokal / Portable). Sobald du beide Werte einträgst, erscheint der
 * Login-Bildschirm und du kannst dich von überall anmelden.
 * ============================================================ */
window.SUPABASE_CONFIG = {
  url: "",       // z. B. "https://abcdefgh.supabase.co"
  anonKey: ""    // der lange "anon public" Schlüssel
};
