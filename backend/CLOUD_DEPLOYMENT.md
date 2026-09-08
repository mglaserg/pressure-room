# Pressure Room Cloud Deployment — Google Drive Canonical Storage

Pressure Room v0.5.3 uses Google Drive as its cloud source of truth.

The backend still uses SQLite, but only as a local / App Runner working cache.
Each story is stored in a visible Google Drive `Pressure Room` folder as a
portable `.pressureroom` package. Mutations save the full project back to Drive
before the API returns.

## Architecture

```text
Browser
  ↓
AWS Amplify / Next.js
  ↓ /api/*
AWS App Runner / FastAPI
  ↓
ephemeral SQLite working cache
  ↕
Google Drive / Pressure Room/*.pressureroom   ← canonical
```

There is no RDS or PostgreSQL in v0.5.3.

## Local development

Google Drive is optional locally. With no `GOOGLE_CLIENT_ID`, Pressure Room
keeps its existing SQLite-only behavior.

```powershell
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --reload --port 8000
```

## Google Cloud setup

1. Create or choose a Google Cloud project.
2. Enable **Google Drive API**.
3. Configure the OAuth consent screen.
4. For an External app that is still in testing, add your Google account as a
   test user.
5. Create an OAuth Client ID of type **Web application**.
6. Add this authorized redirect URI:

```text
https://YOUR-AMPLIFY-DOMAIN/api/google/callback
```

Pressure Room requests these scopes:

```text
openid
email
https://www.googleapis.com/auth/drive.file
```

`drive.file` lets Pressure Room manage files/folders it creates or files the
user explicitly opens with the app, rather than granting broad access to the
entire Drive.

## Generate the session encryption key

```powershell
cd backend
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Save that value securely. Do not commit it.

## App Runner

Create the service from:

- repository: `mglaserg/pressure-room`
- branch: `main`
- source directory: `backend`
- configuration: `apprunner.yaml`

Set runtime environment variables:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
PRESSURE_ROOM_SESSION_KEY=...
PRESSURE_ROOM_PUBLIC_URL=https://YOUR-AMPLIFY-DOMAIN
PRESSURE_ROOM_ALLOWED_EMAIL=you@example.com
```

`PRESSURE_ROOM_ALLOWED_EMAIL` is optional but strongly recommended for this
single-writer deployment.

Do **not** attach a VPC connector. This version needs App Runner's normal public
outbound access to reach Google OAuth and Google Drive.

For v0.5.x, set App Runner autoscaling maximum size to **1 instance**. Drive is
a document store, not a realtime transaction database. This avoids two
ephemeral SQLite workers racing to write the same Drive project.

Recommended health check:

```text
/api/health
```

## Amplify

Set the `main` environment variable:

```text
PRESSURE_ROOM_API_URL=https://YOUR-APP-RUNNER-SERVICE.awsapprunner.com
```

The existing `amplify.yml` writes this server-only value into `.env.production`
for the Next.js SSR proxy.

## First connection

Open the Amplify Pressure Room URL and choose **Connect Google Drive**.

On first connection:
- Pressure Room creates a visible `Pressure Room` folder in My Drive.
- If it is empty, the current local cache is pushed into Drive.
- On later boots, Drive rehydrates the ephemeral SQLite cache.
- Every edit autosaves the changed project back to Drive.

## Existing Windows stories

Your local SQLite file remains untouched. Export a `.pressureroom` package from
your local app and import it into the cloud app; the imported project is then
saved to Drive automatically.

## Why no PostgreSQL yet?

This is intentionally a single-writer architecture. When realtime multi-writer
collaboration becomes a V2 requirement, use PostgreSQL for transactional state
and keep Drive as export, backup, and sharing.
