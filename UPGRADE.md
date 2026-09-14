# Upgrade to 0.6.1

Base: `72c9197fe6a0001156c9dc0204a2812fc0df5143` (uploaded September 14, 2026 bundle).

1. Before upgrading, let all writing finish saving. Export any Drive projects you want as independent backups. Browser-local stories remain in the same browser storage key; preserve that browser profile and origin. Existing legacy recovery keys are retained, but are not automatically applied across account boundaries by the new scoped recovery mechanism.
2. Apply the supplied patch from the repository root with `git apply --check <patch-path>`, then `git apply <patch-path>`. If the check fails, use the full bundle or ZIP in a fresh directory; do not force the patch over another version.
3. Run `uv sync --project backend --locked`. In `frontend`, run `npm ci`, `npm test`, and `npm run build`.
4. Restart the backend and web server together. Browser-local mode continues to work without Google. Google Drive requires the existing OAuth client configuration and `PRESSURE_ROOM_PUBLIC_URL` set to the exact HTTPS web origin. Localhost HTTP remains supported.
5. The old unauthenticated server-SQLite API is now off by default. Only if intentionally using that legacy API behind trusted access, set `PRESSURE_ROOM_ALLOW_LOCAL_API=true` in the backend process environment. This is not needed for the browser's “Continue on this device” workflow. If a trusted development origin differs from localhost:3000, set `PRESSURE_ROOM_ALLOWED_ORIGINS` to its exact origin. Do not turn on the anonymous API on a public server.

The backend's Docker build now uses `backend/requirements.lock`, exported from `uv.lock`, and a non-root account. The writable default database directory is `/app/data`. A custom cache directory or mounted volume must be writable by UID 10001. Update locked dependencies with uv, then regenerate the requirements file using the command at its top. Docker itself was not available for a container build in the audit environment.

Google disconnect now uses POST; the shipped interface was updated. Existing valid encrypted sessions continue to work until their server-enforced 90-day lifetime expires. Disconnect removes the browser cookie; it does not revoke Google consent or every previously copied session. Revoke the app in Google account settings when revocation is needed.

Portable package uploads intentionally drop embedded external file links; importing someone else's package no longer authorizes automatic writes to file IDs inside it. Snapshot restores preserve current project linkage, not untrusted historical linkage. Snapshot history survives restores. Oversized imports are rejected at 10 MiB compressed / 32 MiB project JSON; the HTTP request ceiling is 11 MiB including multipart overhead.

No production deployment, remote repository push, Google account action, or live data migration was performed during this review. Keep the current single-instance deployment constraint until Drive conflict handling is implemented.
