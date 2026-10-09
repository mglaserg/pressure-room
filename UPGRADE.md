# Upgrade notes — October 9, 2026

## Removed external sync

Cloud authentication and persistence now use **Supabase only**. The previous third-party file connection, OAuth callback, picker, status UI and mirror/synchronization endpoints have been removed. Do not configure their old environment variables in ECS or Amplify. Files already stored outside Pressure Room are **not** deleted or imported by this change. If you have an old project stored exclusively outside Supabase, back it up and use **Export & backup → Restore a backup** after signing in.

No destructive database migration is required. The current schema retains compatibility columns and historical project metadata; these do not trigger network synchronization. We preserve previously stored revision calculations to avoid invalidating existing Supabase projects.

## Existing data and auth

Existing Supabase project IDs, branches, episodes, scenes, memberships and invites are retained. Existing Supabase email magic-link authentication remains unchanged. Browser-local workspaces are still separate; signing in does not automatically import browser-local data.

## Smoke test before production

Run `python -m pytest -q backend/tests` and `npm ci && npm test && npm run build` from `frontend`. Verify a new story, an episode, a scene autosave, cross-device reload, Trash/restore, share invitations, and manual package import/export. Ensure `/api/ready` reports `supabase-postgres` for durable cloud state.
