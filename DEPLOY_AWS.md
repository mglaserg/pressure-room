# Pressure Room production deployment

Pressure Room uses **AWS Amplify / Next.js** for the UI, **FastAPI on ECS** for its backend, and **Supabase Auth + Postgres** as the authenticated project's sole durable store. SQLite in the backend is a disposable, per-user cache. Browser-local mode remains a separate on-device option.

```text
Browser → Amplify/Next.js → same-origin /api proxy → FastAPI/ECS
                                                    ↕
                                        Supabase Auth + Postgres
                                                    ↕
                                        per-user SQLite cache (ephemeral)
```

## Supabase

Apply `supabase/migrations/` or `backend/supabase/schema.sql` before production launch. Configure `SUPABASE_URL`, server-only `SUPABASE_SECRET_KEY`, `PRESSURE_ROOM_AUTH_ENABLED=true`, `PRESSURE_ROOM_SESSION_KEY` (a valid Fernet key), and `PRESSURE_ROOM_PUBLIC_URL` (the production HTTPS frontend origin). Set the appropriate redirect URL in Supabase Authentication. Existing Supabase email authentication is used for magic links.

Never expose `SUPABASE_SECRET_KEY` or `PRESSURE_ROOM_SESSION_KEY` in browser or Amplify public variables. The backend accesses Supabase through PostgREST; project writes perform optimistic concurrency checks against revisions.

## Amplify

`PRESSURE_ROOM_API_URL=https://<ecs-application-url>` is needed by the Next.js API proxy. The browser uses same-origin `/api` and never needs direct ECS access. The API proxy strips browser-supplied `Origin` and lets FastAPI enforce cross-site write restrictions via fetch metadata.

## ECS

Container port: `8000`. Health check: `/api/health`; readiness: `/api/ready`. Deployment automation: `.github/workflows/deploy-backend-ecs-express.yml`. The deploy job waits for **backend** tests, lockfile verification and audit; frontend checks run independently in `.github/workflows/check.yml`. A frontend-only failure does not prevent a backend fix from shipping. A failure of a backend test or security check still blocks deployment. The workflow requires AWS role variables, `PRESSURE_ROOM_PUBLIC_URL`, `SUPABASE_URL`, `PRESSURE_ROOM_SESSION_KEY_ARN`, and `SUPABASE_SECRET_KEY_ARN`.

Deploy with `PRESSURE_ROOM_ALLOW_LOCAL_API=false` (default). Authenticated data must not depend on ECS filesystem persistence. The existing Postgres schema retains legacy nullable columns for backward compatibility; they are not used for synchronization.

## Verification

1. Confirm `/api/ready` reports `durable: supabase-postgres` and `auth: supabase-magic-link`. Inspect `/api/health` for `build_sha` matching the successfully deployed Git commit, and `export_kinds` containing `screenplay-pdf` and `screenplay-mobile-pdf`. If those fields are absent, the running ECS service is on old code; fixing the frontend will not fix the export endpoint.
2. Sign in via an email magic link, create/edit a story, then reopen it on another device.
3. Check episode and scene persistence, invite permissions, export/import, Trash and restore.
4. Confirm old `/api/google/*` endpoints no longer provide integration functions.
5. Download a `.pressureroom` backup before migrating any data that was never in Supabase. Deployment does not delete existing external files or revoke provider-side consent.
