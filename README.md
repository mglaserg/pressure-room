# Pressure Room v0.5.7

**Stories reveal character under pressure.**

Pressure Room is a local-first screenwriting environment for developing stories through **pressure, choice, consequence, and moral movement**.

> **Want → Pressure → Choice → Consequence → Bill → Change**

V0.5.7 consolidates the product-design pass: a token-enforced visual system, deterministic self-hosted typography, and an Edit / Page screenplay workflow on top of the same story engine.

## V0.5 design principles

- **Editorial, not dashboard.** Screenplay and story language get visual priority over controls.
- **Power underneath, calm on the surface.** Deep structure stays available without crowding the writer.
- **Aesthetics are functional.** Typography, spacing, motion, and visual hierarchy are part of the writing experience.
- **No runtime font dependency.** `next/font` fetches the chosen fonts at build time and serves them with the app; the browser does not depend on a font CDN.
- **Mobile is intentional.** Navigation, scene selection, structure disclosure, causal mapping, and forms reflow for touch rather than merely shrinking.

## The workspace

Pressure Room keeps only four top-level areas:

- **Write** — screenplay text is the primary surface; scene structure stays tucked away until opened.
- **Structure** — Story, Characters, Causality, Bills, Branches.
- **Diagnose** — Story MRI, Pressure Lab, optional Room Questions.
- **How to use** — onboarding designed to introduce Pressure Room to friends and collaborators.

## Highlights

### Write
- Edit / Page toggle over the same screenplay source
- typeset Fountain preview with screenplay spacing and dialogue indentation
- paper-like screenplay canvas
- editorial scene rail on desktop / swipeable scene strip on mobile
- local draft preservation
- debounced autosave
- progressive-disclosure scene structure
- Want / Pressure / Choice as the first structural layer
- deeper scene mechanics hidden until needed

### Characters
- character-dossier layout instead of a generic form
- visual moral-compromise gauge
- Want and Moral Boundary elevated as the core pair
- Need, Core Belief, Fear, and Temptation remain progressively disclosed

### Causality
- redesigned story-wall view
- scene cards connected by visible THEREFORE / BUT ribbons
- causal notes shown directly in the chain
- unconnected gaps are visible without being treated as errors
- focused connection builder with a full-size “Why does this follow?” field

### Bill Ledger
- restrained ledger cards
- external and moral costs separated clearly
- status remains visible without dominating the writing experience

### Diagnose
- more readable Story MRI
- calmer Pressure Lab
- optional Room Questions remain supplementary
- diagnostics are framed as lenses, never quality scores

### Share
- complete `.pressureroom` project package
- import as copy
- restore / replace
- PDF story packet
- Markdown story packet
- Fountain screenplay export

The visual rules are documented in [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## Run it on Windows

Double-click:

```text
run.bat
```

This opens the API and web frontend in separate terminal windows, then opens `http://localhost:3000`.

### Test the production frontend locally

```powershell
cd frontend
npm install
npm run build
npm run start
```

Then open `http://localhost:3000`.

## Run manually for development

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Existing data

Keep your existing `data/pressure_room.db` in the repo. The backend continues to use the same database and UUID-based story model.

The git tag `v0.1.0` remains the clean Streamlit checkpoint.

## Remote / AWS hosting

Production is intentionally split:

```text
Browser
  → AWS Amplify / Next.js
  → same-origin /api/* Route Handler proxy
  → Amazon ECS Express Mode
  → FastAPI
  → ephemeral SQLite working cache
  ↔ Google Drive / Pressure Room/*.pressureroom (canonical)
```

Amplify receives `PRESSURE_ROOM_API_URL=https://<ecs-application-url>` at build time. ECS listens on port `8000` and uses `/api/health` for its health check. Production keeps one ECS task because Drive + SQLite is currently a single-writer architecture.

See [`DEPLOY_AWS.md`](DEPLOY_AWS.md) for the deployment contract.

## Sharing with friends

See [QUICK_START.md](QUICK_START.md), or open **How to use** inside Pressure Room.

## GitHub

GitHub sync remains optional. The portable `.pressureroom` package is the future unit of snapshot/version sync.

## Development checks

Backend:

```bash
cd backend
pytest -q
```

Frontend dependencies remain deliberately small: Next, React, React DOM.
