# Supabase durable storage

Pressure Room can use Supabase/Postgres as its durable live story store while keeping SQLite as a disposable working cache and Google Drive as the portable `.pressureroom` mirror.

## Setup

1. Create a Supabase project.
2. Run `schema.sql` in the Supabase SQL editor.
3. Set these variables on the FastAPI backend only:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role key>
PRESSURE_ROOM_SUPABASE_TABLE=pressure_room_projects
```

4. Restart the backend and check `/api/ready`. A configured deployment reports `durable: "supabase-postgres"`.

## Security

The service-role key bypasses normal RLS and must never be sent to the browser. Pressure Room only uses it from FastAPI. The table has RLS enabled and access revoked from `anon` and `authenticated` roles as defense in depth.

## Migration

No manual story conversion is required. On first authenticated use after enabling Supabase, an empty durable workspace is seeded from the user's existing Pressure Room cache/Drive workspace. Back up important stories before changing production storage, as with any storage migration.
