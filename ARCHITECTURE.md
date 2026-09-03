# Pressure Room — Architecture Notes

## Product rule

The application must remain valuable with the Writers' Room assistant completely disabled.

The durable domain model is:

**Project → Branch → Episode → Scene → Choice/Change**

with linked **Characters**, **Causal Links**, and **Bills**.

## V1

- Streamlit UI
- SQLite
- Stable UUID primary keys
- UTC timestamps
- optimistic-version counters
- normalized relationships
- main branch pre-created for every story

## Collaboration seam for V2

V1 intentionally avoids storing essential story state inside Streamlit session state. Durable state lives in the database.

A collaborative implementation can replace SQLite with PostgreSQL and add:

1. authenticated users / room membership
2. `created_by` and `updated_by`
3. comments / pitches as first-class records
4. proposed vs accepted changes
5. revision/event log
6. presence and active-editor state
7. WebSocket/realtime subscriptions
8. conflict handling for simultaneous edits
9. branch comparison and merge semantics

The story vocabulary does not need to change.

## Suggested V2 stack

- FastAPI API
- PostgreSQL
- React / Next.js
- WebSockets or a hosted realtime layer
- optional CRDT only for simultaneous screenplay-text editing

For structured objects such as scenes, bills, and causal links, ordinary optimistic concurrency is likely simpler than a CRDT.

## AI boundary

The Writers' Room assistant is a supplementary reader/interrogator. It can:
- question causality
- surface unpaid bills
- challenge easy exits
- identify untransformed scenes
- ask whether moral turns are earned

It should not be required to create, edit, navigate, or analyze a project.
