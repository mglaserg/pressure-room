# Pressure Room on AWS — v0.5.7

Pressure Room uses **Amplify for the Next.js frontend** and **Amazon ECS Express Mode for the FastAPI backend**. Google Drive is the canonical production story store; SQLite inside the container is a disposable working cache.

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
ephemeral SQLite cache
  ↕
Google Drive / Pressure Room/*.pressureroom
```

The browser never needs to call ECS directly, so normal app traffic remains same-origin.

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

## ECS Express Mode

Backend contract:

```text
container port:    8000
health check path: /api/health
minimum tasks:     1
maximum tasks:     1
```

The single-task cap is deliberate for the current Drive + SQLite single-writer model.

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
```

The ECS task execution role must be able to call `secretsmanager:GetSecretValue` for those secret ARNs. If a customer-managed KMS key protects them, add the corresponding `kms:Decrypt` permission.

OAuth callback:

```text
https://main.d23277cgmbx1g0.amplifyapp.com/api/google/callback
```

## Deployment automation

`.github/workflows/deploy-backend-ecs-express.yml` builds the backend image, pushes it to ECR, and updates the ECS Express service when backend files change on `main`.

The frontend continues to deploy through Amplify.

## Persistence rule

Do not treat the ECS container filesystem as durable storage. A replacement task can start with an empty local SQLite cache. Once Drive is configured, Pressure Room hydrates that cache from the user's Drive files and writes project changes back to Drive.

If multi-writer collaboration is added later, move canonical live state to PostgreSQL or another concurrency-safe store; keep Drive as export / backup / sharing.
