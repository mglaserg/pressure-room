# Pressure Room Cloud Backend

Pressure Room keeps SQLite for local development and switches to PostgreSQL
when `DATABASE_URL` is present.

## Local development

No new environment variables are required:

```powershell
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --reload --port 8000
```

`uv sync` will refresh `uv.lock` after the PostgreSQL dependency is added.

## Production database

Create a PostgreSQL database and expose its connection string to the backend as:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/pressure_room?sslmode=require
```

For Amazon RDS, keep the DB private and allow inbound TCP/5432 only from the
security group used by the App Runner VPC Connector.

## App Runner

Create an App Runner service from the GitHub repository:

- Repository: `mglaserg/pressure-room`
- Branch: `main`
- Source directory: `backend`
- Deployment: automatic
- Configuration: use `apprunner.yaml`

The managed runtime is Python 3.11. App Runner executes the service on port
8000.

Configure a VPC Connector using subnets in the same VPC as RDS. Attach a
security group dedicated to the App Runner connector, then allow that security
group into the RDS security group on PostgreSQL port 5432.

Store the production database URL in AWS Secrets Manager and expose it to the
App Runner service as the runtime secret `DATABASE_URL`.

Recommended App Runner health check path:

```text
/api/health
```

After deployment:

```bash
curl -i https://YOUR-SERVICE.awsapprunner.com/api/health
curl -i https://YOUR-SERVICE.awsapprunner.com/api/ready
```

`health` proves the API process is alive. `ready` also verifies the database
connection.

## Amplify

In the Amplify `main` branch environment variables, set:

```text
PRESSURE_ROOM_API_URL=https://YOUR-SERVICE.awsapprunner.com
```

The repository `amplify.yml` writes that server-side value into
`.env.production` before `next build`. It is not a `NEXT_PUBLIC_` variable and
is consumed by the Next.js `/api/*` proxy.

Redeploy Amplify and verify:

```bash
curl -i https://YOUR-AMPLIFY-DOMAIN/api/health
```

## Existing local stories

Do not copy the SQLite file into App Runner. Use Pressure Room's existing
project package export/import flow to move stories into the PostgreSQL-backed
