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
-- Supabase service-role key. Browser clients never receive that key.
revoke all on table public.pressure_room_projects from anon, authenticated;
