# Pressure Room on AWS — durable multi-user deployment

Pressure Room uses **Amplify for the Next.js frontend** and **Amazon ECS Express Mode for the FastAPI backend**. For production, configure **Supabase/Postgres as durable live story state**. SQLite inside the container remains a disposable working cache, and Google Drive remains an optional owner-controlled `.pressureroom` mirror/export path.

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

The browser never receives the Supabase secret key and never needs to call ECS directly. The browser talks same-origin to Next.js; FastAPI handles Supabase Auth and database access.

## Supabase / Postgres

Run [`backend/supabase/schema.sql`](backend/supabase/schema.sql) once in the Supabase SQL editor, then configure the backend with:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<server-only sb_secret_... key>
PRESSURE_ROOM_SUPABASE_TABLE=pressure_room_projects
PRESSURE_ROOM_AUTH_ENABLED=true
```

The backend uses Supabase PostgREST over HTTPS, so this adds no Python database-driver dependency. Each story row stores the existing portable project payload, a content revision, ownership metadata and Drive mirror state. Story mutations compare-and-swap the previous revision; a stale worker receives a conflict instead of overwriting newer content.

In Supabase **Authentication → URL Configuration**, set the Site URL and allowed Redirect URL to the public Amplify origin. Magic-link auth uses that origin and returns through the same-origin Next.js API proxy. Configure custom SMTP before sending magic links to users outside the Supabase organization.

Do **not** expose `SUPABASE_SECRET_KEY` to Amplify/browser environment variables.

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

## Google Drive configuration (optional in magic-link mode)

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
SUPABASE_SECRET_KEY
```

`SUPABASE_URL` is not secret, but the secret key absolutely is. The ECS task execution role must be able to call `secretsmanager:GetSecretValue` for configured secret ARNs. If a customer-managed KMS key protects them, add the corresponding `kms:Decrypt` permission.

OAuth callback:

```text
https://main.d23277cgmbx1g0.amplifyapp.com/api/google/callback
```

Pressure Room requests `openid`, `email`, and `drive.file`. A partial Drive grant is rejected and the reconnect path starts a fresh Google authorization. Disconnect revokes the active Google token where possible and invalidates the Pressure Room session.

## Persistence and migration behavior

With Supabase + magic-link auth configured:

1. Supabase Auth identifies the user; a per-user SQLite cache is hydrated only with projects the user can access.
2. Existing Google-partitioned rows can be claimed on first sign-in when the Google and magic-link emails match.
3. Every project has owner/editor/viewer membership metadata; removed members are pruned from their local cache on the next request.
4. Each mutation is written to Supabase with optimistic concurrency before the local transaction commits.
5. Only the project owner drains the optional Google Drive mirror. Drive ETags continue to protect conditional overwrites.
6. Presence heartbeats and project events provide the collaboration transport seam; simultaneous screenplay text editing remains a later CRDT/Yjs milestone.

Without Supabase variables, Pressure Room retains the prior Drive-canonical behavior for compatibility/local use.

## Deployment automation

`.github/workflows/deploy-backend-ecs-express.yml` builds the backend image, pushes it to ECR, and updates the ECS Express service when backend files change on `main`.

The workflow expects these GitHub Actions repository variables in addition to the existing AWS/Google values:

```text
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY_ARN=arn:aws:secretsmanager:...:secret:<secret-name>:SUPABASE_SECRET_KEY::
```

The deploy action injects `PRESSURE_ROOM_AUTH_ENABLED=true`, the Supabase URL, and the secret-backed Supabase key into each new ECS task definition so automated deployments do not silently fall back to SQLite.

The frontend continues to deploy through Amplify. Its production build uses local/system font stacks and does not fetch Google Fonts during CI.
