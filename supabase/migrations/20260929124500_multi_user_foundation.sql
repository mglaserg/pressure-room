-- Pressure Room multi-user foundation.
-- Supabase Auth provides identity; FastAPI remains the only database writer.

alter table public.project_members
  add column if not exists email text;

create index if not exists project_members_project_idx
  on public.project_members (project_id);

create table if not exists public.project_invites (
  id text primary key,
  project_id text not null,
  email text not null,
  role text not null check (role in ('editor', 'viewer')),
  token_hash text not null unique,
  invited_by uuid not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  accepted_at timestamptz,
  accepted_by uuid
);

create index if not exists project_invites_project_idx
  on public.project_invites (project_id, created_at desc);
create index if not exists project_invites_email_idx
  on public.project_invites (lower(email));

create table if not exists public.project_presence (
  project_id text not null,
  user_id uuid not null,
  email text,
  seen_at timestamptz not null default now(),
  primary key (project_id, user_id)
);

create index if not exists project_presence_seen_idx
  on public.project_presence (project_id, seen_at desc);

create table if not exists public.project_events (
  id text primary key,
  project_id text not null,
  actor_id uuid not null,
  actor_email text,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists project_events_project_idx
  on public.project_events (project_id, created_at desc);

alter table public.project_invites enable row level security;
alter table public.project_presence enable row level security;
alter table public.project_events enable row level security;

-- These tables are deliberately server-only. FastAPI performs membership checks
-- using the server-side Supabase secret key. Browser roles get no direct table access.
revoke all on table public.project_members from anon, authenticated;
revoke all on table public.project_invites from anon, authenticated;
revoke all on table public.project_presence from anon, authenticated;
revoke all on table public.project_events from anon, authenticated;
