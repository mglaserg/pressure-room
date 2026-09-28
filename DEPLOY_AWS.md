# Pressure Room on AWS — durable storage pass

Pressure Room uses **Amplify for the Next.js frontend** and **Amazon ECS Express Mode for the FastAPI backend**. For production, configure **Supabase/Postgres as durable live story state**. SQLite inside the container remains a disposable working cache, and Google Drive remains the visible `.pressureroom` mirror/export path.

## Production topology

```text
Browser
  ↓
AWS Amplify / Next.js
  ↓ same-origin /api/*
Next.js Route Handler proxy
  ↓ PRESSURE_ROOM_API_URL
Amazon ECS Express Mode
  ↓
FastAPI :8000
  ↓
ephemeral SQLite working cache
  ↕
Supabase/Postgres              ← durable live state
  ↕
Google Drive / Pressure Room/*.pressureroom  ← portable mirror/export
```

The browser never receives the Supabase service-role key and never needs to call ECS directly.

## Supabase / Postgres

Run [`backend/supabase/schema.sql`](backend/supabase/schema.sql) once in the Supabase SQL editor, then configure the backend with:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only service role key>
PRESSURE_ROOM_SUPABASE_TABLE=pressure_room_projects
```

The backend uses Supabase PostgREST over HTTPS, so this pass adds no Python database-driver dependency. Each story row stores the existing portable project payload, a content revision, and Drive mirror state. Story mutations compare-and-swap the previous revision; a stale worker receives a conflict instead of overwriting newer content.

Do **not** expose `SUPABASE_SERVICE_ROLE_KEY` to Amplify/browser environment variables.

## Amplify

Set this environment variable on the `main` branch:

```text
PRESSURE_ROOM_API_URL=https://<ecs-application-url>
```

`amplify.yml` writes it into `.env.production` during the Next.js build.

After deployment, verify the complete proxy path:

```powershell
curl.exe https://main.d23277cgmbx1g0.amplifyapp.com/api/health
```

A configured production response reports `durable: "supabase-postgres"`.

## ECS Express Mode

Backend contract:

```text
container port:    8000
health check path: /api/health
minimum tasks:     1
maximum tasks:     1 (recommended for now)
```

Supabase removes the container filesystem as the story source of truth. One task is still recommended until Drive mirror draining is moved from the current process-level lock to a distributed queue/lock.

Direct backend check:

```powershell
curl.exe https://<ecs-application-url>/api/health
```

## Google Drive configuration

Ordinary ECS environment variables:

```text
GOOGLE_CLIENT_ID
PRESSURE_ROOM_PUBLIC_URL=https://main.d23277cgmbx1g0.amplifyapp.com
PRESSURE_ROOM_ALLOWED_EMAIL=<your Google account>
```

Secrets Manager values injected into the task:

```text
GOOGLE_CLIENT_SECRET
PRESSURE_ROOM_SESSION_KEY
SUPABASE_SERVICE_ROLE_KEY
```

`SUPABASE_URL` is not secret, but the service-role key absolutely is. The ECS task execution role must be able to call `secretsmanager:GetSecretValue` for configured secret ARNs. If a customer-managed KMS key protects them, add the corresponding `kms:Decrypt` permission.

OAuth callback:

```text
https://main.d23277cgmbx1g0.amplifyapp.com/api/google/callback
```

Pressure Room requests `openid`, `email`, and `drive.file`. A partial Drive grant is rejected and the reconnect path starts a fresh Google authorization. Disconnect revokes the active Google token where possible and invalidates the Pressure Room session.

## Persistence and migration behavior

With Supabase configured:

1. The per-user SQLite cache is hydrated from Supabase first.
2. If Supabase is empty for that user but the existing cache/Drive workspace contains stories, those projects are seeded into Supabase.
3. Each mutation is written to Supabase with optimistic concurrency before the local transaction commits.
4. Google Drive is drained afterward as a portable mirror. Drive ETags continue to protect conditional overwrites.
5. If an ephemeral cache loses the Drive file ID after a restart, Pressure Room recovers the existing sidecar by its `pressure_room_project_id` app property rather than creating a duplicate.

Without Supabase variables, Pressure Room retains the prior Drive-canonical behavior for compatibility/local use.

## Deployment automation

`.github/workflows/deploy-backend-ecs-express.yml` builds the backend image, pushes it to ECR, and updates the ECS Express service when backend files change on `main`.

The frontend continues to deploy through Amplify.
