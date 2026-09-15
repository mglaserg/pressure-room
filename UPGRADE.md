<<<<<<< HEAD
# Upgrade to Pressure Room 0.7.0

This release includes the 0.6.1 security cleanup and completes the code/design follow-up. The incremental patch applies to `703792ea2f6653d836336fe07d2ac9e47d96e1bc` (0.6.1). The full bundle and source ZIP include both rounds and can be used independently of that patch.

1. Download independent backups of existing stories and any failed scene recovery drafts. Stop the old backend before replacing its code or copying its SQLite files. Retain the browser profile and web origin used for browser-local stories.
2. For an existing 0.6.1 checkout, run `git apply --check <patch-path>` and then `git apply <patch-path>`. Otherwise clone the supplied full bundle into a fresh directory or extract the source ZIP. Do not force an incremental patch over the original uploaded version.
3. Run `uv sync --project backend --locked`, `uv run --project backend pytest backend/tests`, then `npm ci`, `npm test` and `npm run build` in `frontend`.
4. Run **one backend worker / one active instance per cache volume**. Give it persistent, backed-up storage for both `PRESSURE_ROOM_DB` and `PRESSURE_ROOM_USER_CACHE_DIR`. Docker defaults to `/app/data/pressure_room.db` and `/app/data/users`; mount `/app/data` with ownership allowing UID 10001 to write. The included ECS workflow does not provision persistent storage. An ephemeral container filesystem does not preserve pending uploads or session revocations across task replacement.
5. Restart frontend and backend together. Database initialization adds the sync queue, revocation table and Fountain source fields. Existing story and browser-local storage identifiers are retained. Do not roll back to old code against the migrated cache without restoring its pre-upgrade copy.
6. Check a disposable Google account/project before production use: OAuth connect and Picker, normal sidecar and Fountain writes, two-device conflict, failed/ambiguous upload followed by retry, recovery copy and external Fountain reload, copied-cookie rejection after disconnect, and persistence after a process restart. These live checks were not possible in this workspace.

## Sync and recovery behavior

Each story mutation and its exact pending upload are committed together in SQLite. Remote writes then run in stages: story sidecar, linked Fountain, final sidecar metadata. The files cannot be updated atomically together. Pending/conflict status stays visible until those stages complete. Refresh skips queued stories. A process restart retains pending work when the database volume survives; use **Retry sync** to resume it. This is not a background sync daemon.

Updates require the revision loaded by the browser and a strong Drive ETag. Before the first conditional overwrite per account/process, and after an hour, the backend creates a disposable text file, attempts an impossible `If-Match` update, then deletes it. It proceeds only if Drive rejects that update. If the check or cleanup fails, the real story overwrite remains blocked. An interrupted probe can leave a harmless file named “Pressure Room sync capability check”; it contains no story content. The v2 Drive endpoint supplies ETags and receives conditional content updates; listing and creates continue to use v3.

For a conflict, download a backup, **Keep mine as a new story**, or **Load Drive + keep recovery**. The latter creates a separate recovery story before replacement. If the conflict is in linked Fountain, it rebuilds the linked path from the current external screenplay and keeps other paths. Rich structural annotations for the rebuilt path remain in the recovery story. Recovery copies are not automatically deleted or uploaded unless explicitly saved/copied through the sync flow.

**Room → Export & backup** works in browser-local mode too. Backups include snapshots and story notes; copy import remaps identities and disconnects external Drive linkage. Restore replaces the story identified inside the file, not merely the currently selected story. Local restore retains a pre-restore snapshot. A conflicting scene draft must be downloaded/resolved before export can claim that the latest edit is included. Browser storage is neither encrypted nor a device-loss backup; old scoped recovery drafts are not merged blindly.

Only one selected path is written to a linked Fountain file. Existing links use the main path until changed under **Room**. Independent full-story exports can still contain multiple paths; use the editable backup to preserve the complete project.

## Security/deployment compatibility

The legacy anonymous server-SQLite API remains disabled by default. `PRESSURE_ROOM_ALLOW_LOCAL_API=true` is only for trusted single-user development; the browser-local workflow does not need it. Preserve the exact HTTPS `PRESSURE_ROOM_PUBLIC_URL`, OAuth callbacks and allowed origins. Disconnect is POST and revokes the current session identifier, including a copied cookie, through the persistent default database. It does not revoke Google consent or other independently issued sessions.

The backend deployment job now depends on the verification workflow, including tests, production build and npm/Python audits. Repository branch protection, Amplify/frontend deployment gates, IAM, WAF, OAuth restrictions and durable ECS storage still require configuration in the actual environment. No production deployment or account changes were performed.
=======
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
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
