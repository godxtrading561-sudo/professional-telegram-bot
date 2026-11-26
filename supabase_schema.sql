-- Run once in the Supabase SQL Editor.
-- The bot should use the service_role API key stored only in GitHub Actions Secrets.
create table if not exists public.bot_state (
    session_id text primary key,
    state jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.bot_state enable row level security;

-- No public/anon policies are created. The server-side service_role key bypasses RLS.
