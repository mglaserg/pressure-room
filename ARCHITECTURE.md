# Pressure Room — Architecture

## Product rule

**Power underneath. Calm on the surface.**

Every screen has one obvious primary job. The rich story model is preserved, but advanced structure is progressively disclosed rather than presented all at once.

The durable domain model remains:

**Project → Branch → Episode → Scene → Choice / Change**

linked to **Characters**, **Causal Links**, **Bills**, **Notes**, and **Snapshots**.

## V0.5 stack

### Frontend
- Next.js 16 App Router
- React 19
- responsive CSS without a component-framework dependency
- PWA manifest / mobile-safe viewport
- local screenplay draft preservation plus debounced API autosave

### Backend
- FastAPI
- SQLite for local-first V0.x
- normalized UUID-based schema inherited from V0.1
- export/import service
- diagnostic service

### Data migration

The backend opens the existing `data/pressure_room.db` location and performs additive migrations. V0.1 scene rows receive a `screenplay_text` column; existing project/character/episode/scene/bill IDs remain intact.

## Information architecture

Top level is intentionally limited to four areas:

1. **Write** — screenplay + optional per-scene structure disclosure
2. **Structure** — Story, Characters, Causality, Bills, Branches
3. **Diagnose** — Story MRI, Pressure Lab, optional Room Questions
4. **How to use** — onboarding / friend-friendly guide

The former standalone Writers' Room page is no longer top-level. It is supplementary by design.

## Portable project format

A `.pressureroom` file is a ZIP package containing:

- `project.json` — lossless structured project state
- `story-packet.md`
- `screenplay.fountain`
- a small package README

Import supports:
- **copy** — remap UUIDs and create a distinct project
- **replace** — restore the exact canonical UUID/state

## Story laboratory

V0.5 includes:
- story branches
- branch cloning
- named project snapshots
- snapshot restore API

These remain behind **Structure → Branches** so they do not clutter writing.

## V2 collaboration seam

The conceptual model is already collaboration-friendly: stable UUIDs, timestamps, version counters, normalized entities, and portable snapshots.

The expected V2 migration is:
- PostgreSQL
- authenticated users / room membership
- FastAPI remains the domain API
- WebSockets or a realtime layer for presence and structured updates
- comments / pitches / proposed vs accepted changes
- optimistic concurrency for structured story objects
- CRDT only if simultaneous screenplay-text editing actually requires it

## GitHub

GitHub is optional. The `.pressureroom` package is the boundary: future GitHub sync can version these snapshots without making Git knowledge a requirement for normal writing.

Recommended progression:
1. connect a repository
2. push a named project snapshot
3. pull latest snapshot with preview
4. compare before restore
5. keep creative story branches distinct from Git branches


## V0.5 visual system

V0.5 formalizes design as part of product behavior. The application uses:

- warm graphite surfaces instead of generic black dashboard panels
- an editorial serif stack for story hierarchy and a restrained sans-serif UI stack
- a paper-toned screenplay canvas with monospaced screenplay typography
- brass as a limited interaction/accent color rather than a decorative wash
- fewer visible borders and more whitespace
- progressively disclosed forms
- mobile-specific navigation and scene selection
- a visual causality wall rather than a database-like link list

No external font or design-system CDN is required, reducing local/remote rendering differences.
