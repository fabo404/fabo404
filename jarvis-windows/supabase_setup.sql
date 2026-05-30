-- ============================================================
--  JARVIS  ·  Supabase-Setup fuer geraeteuebergreifende Chats
--  EINMAL ausfuehren:  Supabase-Projekt -> SQL Editor -> einfuegen -> Run
-- ============================================================

-- Tabelle: pro Nutzer eine Zeile mit dem kompletten Chat-Verlauf (als JSON)
create table if not exists public.jarvis_chats (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  messages   jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

-- Sicherheit: jeder darf NUR seine eigene Zeile sehen/aendern
alter table public.jarvis_chats enable row level security;

drop policy if exists "jarvis own select" on public.jarvis_chats;
create policy "jarvis own select" on public.jarvis_chats
  for select using (auth.uid() = user_id);

drop policy if exists "jarvis own insert" on public.jarvis_chats;
create policy "jarvis own insert" on public.jarvis_chats
  for insert with check (auth.uid() = user_id);

drop policy if exists "jarvis own update" on public.jarvis_chats;
create policy "jarvis own update" on public.jarvis_chats
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
