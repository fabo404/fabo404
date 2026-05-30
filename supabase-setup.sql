-- ============================================================
-- Freezy AI · Supabase-Einrichtung
-- Führe dieses SQL einmal aus:
--   Supabase Dashboard → SQL Editor → New query → einfügen → Run
-- Es legt die Tabelle für den verschlüsselten Schlüssel-Tresor an
-- und schützt sie so, dass jeder Nutzer NUR seine eigenen Daten sieht.
-- ============================================================

create table if not exists public.vaults (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  data       text,                       -- verschlüsselter JSON-Tresor (Base64)
  updated_at timestamptz not null default now()
);

alter table public.vaults enable row level security;

-- Nur die eigenen Daten lesen
create policy "vault_select_own" on public.vaults
  for select using (auth.uid() = user_id);

-- Nur die eigenen Daten anlegen
create policy "vault_insert_own" on public.vaults
  for insert with check (auth.uid() = user_id);

-- Nur die eigenen Daten ändern
create policy "vault_update_own" on public.vaults
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
