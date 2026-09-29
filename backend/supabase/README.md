# Supabase durable storage + magic-link identity

Pressure Room uses Supabase/Postgres as the durable live story store while SQLite remains a disposable per-user working cache. With magic-link auth enabled, Google Drive is an optional owner-controlled `.pressureroom` mirror/export rather than the account identity.

## Setup

1. Create a Supabase project.
2. Apply `supabase/migrations/` through the GitHub integration, or run `schema.sql` manually for a fresh setup.
3. Set these variables on the FastAPI backend only:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<sb_secret_... key>
PRESSURE_ROOM_SUPABASE_TABLE=pressure_room_projects
PRESSURE_ROOM_AUTH_ENABLED=true
```

`PRESSURE_ROOM_PUBLIC_URL` and `PRESSURE_ROOM_SESSION_KEY` are also required for magic-link sessions.

Pressure Room still does **not** need `SUPABASE_PUBLISHABLE_KEY`: the browser talks only to the same-origin FastAPI API. FastAPI asks Supabase Auth to send magic links, validates the returned Supabase access token once, then issues an encrypted HttpOnly Pressure Room session cookie. Durable database access remains server-side.

4. In Supabase **Authentication → URL Configuration**, set the Site URL to your public Pressure Room frontend origin and add that origin to Redirect URLs.
5. Restart the backend and check `/api/ready`. A configured deployment reports:

```json
{
  "ok": true,
  "durable": "supabase-postgres",
  "auth": "supabase-magic-link"
}
```

## Email delivery

Supabase's built-in SMTP is intended for testing and, by default, only sends to pre-authorized organization addresses. Configure custom SMTP before inviting arbitrary external collaborators.

## Security

The secret key bypasses RLS and must never be sent to the browser. RLS remains enabled and `anon`/`authenticated` table grants are revoked as defense in depth. The API enforces owner/editor/viewer permissions before story writes or sharing actions. Invitation bearer tokens are stored only as SHA-256 hashes.

## Existing projects

When magic-link auth is first enabled, a user who still has the matching Google Drive session can automatically claim the older Google-partitioned durable workspace when the Google email matches the magic-link email. Existing project IDs are preserved. If the old Google session is gone, reconnect that same Google account once so Pressure Room can prove and migrate the legacy partition.


## Project Trash

Cloud project deletion is two-stage. Moving a project to Trash sets `pressure_room_projects.trashed_at`; the story payload and collaboration metadata remain durable, normal project queries hide it, and collaborators cannot access it until the owner restores it. Permanent deletion is owner-only and removes the durable project plus membership, invitation, presence and event rows. Google Drive mirror deletion is optional and never deletes an original linked Fountain file.
