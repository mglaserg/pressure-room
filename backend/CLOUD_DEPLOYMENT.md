# Cloud architecture

Production uses Supabase Auth and Postgres for durable project content; per-user SQLite is only an ephemeral FastAPI working cache. Browser-local stories remain device-local. See [DEPLOY_AWS.md](../../DEPLOY_AWS.md) for variables, pipeline, and post-deployment checks.

External file synchronization is not supported. Portable export/import remains available for `.pressureroom`, Fountain, PDF and Markdown formats.
