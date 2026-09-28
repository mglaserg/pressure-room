# Pressure Room Cloud Deployment — Supabase durable state + Google Drive mirror

The production backend now supports three layers with deliberately different jobs:

```text
FastAPI
  ↓
per-user SQLite working cache          ← disposable
  ↕
Supabase/Postgres project snapshots    ← durable live state
  ↕
Google Drive .pressureroom files       ← portable mirror/export
```

Supabase is optional so local development remains zero-config. When it is absent, the established Google-Drive-canonical flow remains available.

## 1. Supabase setup

Create a Supabase project and run `backend/supabase/schema.sql` in its SQL editor. Then set these **backend-only** values:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role key>
PRESSURE_ROOM_SUPABASE_TABLE=pressure_room_projects
```

The FastAPI server talks to Postgres through Supabase PostgREST using the already-installed `httpx` package. No browser code receives the service-role key.

The table is intentionally simple: one row per Google user + story, containing the existing portable project payload as JSONB, the project revision hash, Drive mirror state, and update timestamp. This gives the current domain model durable storage without prematurely rewriting every entity into a new relational collaboration schema.

## 2. Google Cloud setup

1. Create or choose a Google Cloud project.
2. Enable **Google Drive API**.
3. Configure the OAuth consent screen.
4. For an External app that is still in testing, add your Google account as a test user.
5. Create an OAuth Client ID of type **Web application**.
6. Add the production callback: `https://YOUR-AMPLIFY-DOMAIN/api/google/callback`.

Pressure Room requests:

```text
openid
email
https://www.googleapis.com/auth/drive.file
```

A connection that does not actually grant `drive.file` is rejected rather than leaving the app in a half-authorized state.

## 3. Session key

```powershell
cd backend
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep `PRESSURE_ROOM_SESSION_KEY`, `GOOGLE_CLIENT_SECRET`, and `SUPABASE_SERVICE_ROLE_KEY` in the backend secret store. Do not commit them or expose them through Next.js public variables.

## 4. Backend variables

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
PRESSURE_ROOM_SESSION_KEY=...
PRESSURE_ROOM_PUBLIC_URL=https://YOUR-AMPLIFY-DOMAIN
PRESSURE_ROOM_ALLOWED_EMAIL=you@example.com
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
PRESSURE_ROOM_SUPABASE_TABLE=pressure_room_projects
```

`PRESSURE_ROOM_ALLOWED_EMAIL` remains optional, but it is useful while the deployment is private.

The service needs normal public outbound HTTPS access to Google and Supabase.

## 5. Frontend

Set:

```text
PRESSURE_ROOM_API_URL=https://YOUR-BACKEND
```

The Next.js server-side proxy keeps normal app traffic same-origin.

## 6. Boot and save behavior

On an authenticated request, Pressure Room binds the user's local cache and hydrates it from Supabase. If the durable table is empty during an upgrade, existing cache/Drive projects are seeded into Supabase. Thereafter, Supabase is consulted before editing.

For a normal story mutation:

1. SQLite starts the request transaction.
2. The endpoint changes the working model and records the exact Drive upload intent.
3. Supabase is updated with a compare-and-swap against the story revision the request started from.
4. If that durable write conflicts or fails, the local edit is not committed.
5. After commit, the Drive mirror is drained using its strong ETag protections.
6. Updated Drive mirror metadata is persisted back to Supabase without replacing newer story content.

This separates **story durability** from **Drive synchronization**. A temporary Drive failure can leave the mirror pending without making the successfully persisted story disappear.

## 7. Scaling note

The story store now has cross-worker optimistic concurrency, but Drive mirror draining still uses a process-level `SYNC_LOCK`. Keep one backend task/instance for now. Multi-task deployment should wait for a distributed sync queue/lock or equivalent job ownership.

That is a much smaller future job than migrating the whole story model out of ephemeral SQLite because durable content is already in Postgres.
