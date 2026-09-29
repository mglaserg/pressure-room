-- Prepare Pressure Room for Supabase Auth and collaboration.
-- This migration intentionally adds identity fields without enforcing ownership yet.

alter table public.pressure_room_projects
  add column if not exists owner_id uuid,
  add column if not exists created_by uuid,
  add column if not exists updated_by uuid;

create table if not exists public.project_members (
  project_id text not null,
  user_id uuid not null,
  role text not null default 'viewer' check (role in ('owner', 'editor', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (project_id, user_id)
);

create index if not exists project_members_user_idx
  on public.project_members (user_id);

alter table public.project_members enable row level security;
revoke all on table public.project_members from anon, authenticated;
