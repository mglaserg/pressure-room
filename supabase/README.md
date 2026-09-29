# Supabase deployment

Pressure Room's GitHub integration deploys database changes from `supabase/migrations/`.

The migrations now create:

- `public.pressure_room_projects` — durable story snapshots
- `public.project_members` — owner/editor/viewer access
- `public.project_invites` — hashed, expiring email invitations
- `public.project_presence` — lightweight collaborator presence
- `public.project_events` — collaboration/activity event plumbing
- `pressure_room_projects.trashed_at` — owner-controlled soft deletion and restore

All of these tables have RLS enabled and browser roles revoked. Runtime reads/writes go through FastAPI using the server-only `SUPABASE_SECRET_KEY` (`sb_secret_...`); no Supabase secret belongs in this directory or in Git.

After the migrations deploy, configure **Authentication → URL Configuration** in Supabase. Set the Site URL to the public Pressure Room frontend origin and allow that same origin as a redirect URL. Magic-link redirects return to `/?auth_callback=1`.
