# Supabase deployment

Pressure Room's GitHub integration deploys database changes from `supabase/migrations/`.

The initial migration creates `public.pressure_room_projects`, enables RLS, and revokes browser roles. Runtime durable writes still come from the FastAPI backend using `SUPABASE_SECRET_KEY` (`sb_secret_...`). No Supabase secret belongs in this directory or in Git.
