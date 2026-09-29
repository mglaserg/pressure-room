-- Project lifecycle: soft-delete to Trash before permanent deletion.

alter table public.pressure_room_projects
  add column if not exists trashed_at timestamptz;

create index if not exists pressure_room_projects_owner_trash_idx
  on public.pressure_room_projects (owner_id, trashed_at, updated_at desc);
