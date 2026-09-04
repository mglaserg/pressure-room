# Pressure Room v0.4

**Writers, under pressure.**

Pressure Room is a local-first screenwriting environment for developing stories through **pressure, choice, consequence, and moral movement**.

V0.4 moves Pressure Room from its Streamlit prototype into a proper web application while preserving the original V0.1 story model.

> **Want → Pressure → Choice → Consequence → Bill → Change**

## What changed from v0.1

The biggest change is not more theory. It is **less interface**.

The application now has only four top-level areas:

- **Write** — screenplay text is the primary surface; scene structure is hidden until opened.
- **Structure** — Story, Characters, Causality, Bills, Branches.
- **Diagnose** — Story MRI, Pressure Lab, optional Room Questions.
- **How to use** — onboarding designed to introduce Pressure Room to friends and collaborators.

## v0.4 features

### Write
- actual screenplay text per scene
- clean paper-like editor
- mobile scene strip / desktop scene rail
- local draft preservation
- debounced autosave
- progressive-disclosure scene structure
- Want / Pressure / Choice first; advanced fields stay tucked away

### Structure
- Story Bible / Moral Spine
- THEREFORE / BUT causality
- Bill Ledger
- story branches
- branch cloning
- named snapshots

### Diagnose
- Story MRI
- Pressure Lab
- optional Writers' Room interrogation questions
- AI is **not** required

### Share
- complete `.pressureroom` project package
- import as copy
- restore / replace
- PDF story packet
- Markdown story packet
- Fountain screenplay export

### Mobile
- responsive layout
- bottom navigation
- swipeable scene rail
- touch-sized controls
- PWA manifest foundation

## Run it on Windows

Double-click:

```text
run.bat
```

This opens the API and web frontend in separate terminal windows, then opens `http://localhost:3000`.

## Run manually

### 1. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Existing v0.1 data

Keep your existing `data/pressure_room.db` in the repo. The new backend uses the same location and performs an additive migration for screenplay text and snapshots.

The git tag `v0.1.0` remains the clean Streamlit checkpoint.

## Sharing with friends

See [QUICK_START.md](QUICK_START.md), or open **How to use** inside Pressure Room.

## GitHub

GitHub sync is intentionally not required for v0.4. The portable `.pressureroom` format is now stable enough to become the unit of future GitHub snapshot/version sync.

## Development checks

Backend:

```bash
cd backend
pytest -q
```

Frontend dependencies are deliberately small: Next, React, React DOM.
