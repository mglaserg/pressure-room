-- Pressure Room durable story state for Supabase/Postgres.
-- Run once in the Supabase SQL editor before setting backend credentials.

create table if not exists public.pressure_room_projects (
  user_sub text not null,
  project_id text not null,
  payload jsonb not null,
  revision text not null,
  sync_state jsonb,
  updated_at timestamptz not null default now(),
  primary key (user_sub, project_id)
);

-- Safe to rerun after upgrading an early draft of the table.
alter table public.pressure_room_projects
  add column if not exists sync_state jsonb;

create index if not exists pressure_room_projects_updated_idx
  on public.pressure_room_projects (user_sub, updated_at desc);

alter table public.pressure_room_projects enable row level security;

-- Pressure Room talks to this table only from the FastAPI backend with the
-- Supabase `sb_secret_...` key. Browser clients never receive that key.
revoke all on table public.pressure_room_projects from anon, authenticated;

-- Multi-user identity/collaboration metadata. Safe to rerun.
alter table public.pressure_room_projects
  add column if not exists owner_id uuid,
  add column if not exists created_by uuid,
  add column if not exists updated_by uuid,
  add column if not exists trashed_at timestamptz;

create index if not exists pressure_room_projects_owner_trash_idx
  on public.pressure_room_projects (owner_id, trashed_at, updated_at desc);

create table if not exists public.project_members (
  project_id text not null,
  user_id uuid not null,
  email text,
  role text not null default 'viewer' check (role in ('owner', 'editor', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (project_id, user_id)
);

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

create table if not exists public.project_presence (
  project_id text not null,
  user_id uuid not null,
  email text,
  seen_at timestamptz not null default now(),
  primary key (project_id, user_id)
);

create table if not exists public.project_events (
  id text primary key,
  project_id text not null,
  actor_id uuid not null,
  actor_email text,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists project_members_user_idx on public.project_members (user_id);
create index if not exists project_members_project_idx on public.project_members (project_id);
create index if not exists project_invites_project_idx on public.project_invites (project_id, created_at desc);
create index if not exists project_presence_seen_idx on public.project_presence (project_id, seen_at desc);
create index if not exists project_events_project_idx on public.project_events (project_id, created_at desc);

alter table public.project_members enable row level security;
alter table public.project_invites enable row level security;
alter table public.project_presence enable row level security;
alter table public.project_events enable row level security;

revoke all on table public.project_members from anon, authenticated;
revoke all on table public.project_invites from anon, authenticated;
revoke all on table public.project_presence from anon, authenticated;
revoke all on table public.project_events from anon, authenticated;
