# Supabase durable state

Pressure Room uses Supabase Auth (magic links) for identity and Postgres JSONB project snapshots for durable data. The FastAPI backend holds service credentials server-side, hydrates an isolated SQLite working cache for each signed-in user, and writes changed stories with optimistic revision checking.

Apply `supabase/migrations/` or `backend/supabase/schema.sql` before deploying. Existing rows and compatibility schema columns remain intact. No external sync runs; import/export is user-initiated. Trash preserves payloads and membership until an owner permanently deletes a project.

Required production environment variables: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `PRESSURE_ROOM_AUTH_ENABLED=true`, `PRESSURE_ROOM_PUBLIC_URL`, and `PRESSURE_ROOM_SESSION_KEY`.
