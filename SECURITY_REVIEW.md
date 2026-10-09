# Pressure Room security review — current architecture

Cloud stories use Supabase Auth magic-link sessions and Postgres durable snapshots. FastAPI is the only service that holds Supabase server credentials. Next.js proxies browser requests under the same origin. Authenticated story mutation requires project access rights and an optimistic revision check. Browser-local storage is separate; anonymous server-SQLite access is disabled unless explicitly enabled for trusted development.

## Protective boundaries

- Cross-origin write attempts are rejected by FastAPI security middleware.
- Session cookies are HttpOnly and encrypted using the configured Fernet session key.
- Content-changing writes use an `X-Project-Revision` precondition to prevent silent stale overwrites.
- Cloud project roles are owner/editor/viewer; Trash restoration and final deletion are owner-restricted.
- User caches are isolated; Postgres is authoritative and the cache is rebuilt from the user's accessible projects.
- Portable imports strip historical external source links, preserving the boundary between archive content and storage authority.

## Outstanding operational validation

Live production verification must cover real Supabase session and SMTP delivery, concurrent edits across devices, deployment secrets, AWS IAM, HTTPS ingress and data backup/recovery. Tests in the repository do not substitute for live integration tests. Browser-local device data remains the user's responsibility to back up. External provider authorization and files were not modified by this code change.
