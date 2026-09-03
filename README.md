# Pressure Room

**A causal story-development workspace.**

Pressure Room is a Streamlit app for developing character-driven stories through **pressure, choice, consequence, and moral change** rather than forcing a screenplay into a generic beat sheet.

Its core loop is:

> **Character wants something → makes a choice → consequence → pressure narrows options → harder choice → bill comes due → moral boundary moves.**

## V0.1 features

- **Story Bible / Moral Spine**
  - Want
  - Need
  - Core belief
  - Moral boundary
  - Fear
  - Temptation
  - Moral-compromise tracker
- **Therefore / But Causal Map**
- **Scene Builder**
  - Opening behavior/image
  - Want
  - Obstacle
  - Tactic
  - Pressure
  - Choice
  - Starting/ending state
  - Cut-on beat
- **Bill Ledger**
  - External consequence
  - Internal / moral cost
  - Outstanding, escalating, paid, abandoned
- **Pressure Lab**
  - Remove an option
  - Add a deadline
  - Conflicting obligations
  - Expose prior behavior
  - Reverse status
  - Force commitment
  - Create a witness
  - Attach collateral
- **Story MRI**
  - Pressure
  - Moral compromise
  - Character option-space
- **Writers’ Room**
  - Optional, rule-based structural questions
  - The app does **not** depend on AI

## Run it

Python 3.11+ recommended.

### Windows shortcut

Double-click:

```text
run.bat
```

It uses `uv` when available and falls back to a local virtual environment + pip.

### With `uv`

```bash
cd pressure-room
uv sync
uv run streamlit run app.py
```

### With pip

```bash
cd pressure-room
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

The app creates `data/pressure_room.db` automatically and seeds a small fictional demo story so the interface is not empty on first launch.

## Why the data model already looks a little “bigger” than V1

V1 uses SQLite and is intended for a single writer, but important records already have:

- stable UUIDs
- timestamps
- version counters
- a branch table
- normalized project / episode / scene / character / causal-link / bill records

That is deliberate. A future collaborative version can move the same conceptual model to PostgreSQL + a realtime backend instead of redesigning the story system.

## V2 collaboration direction

A natural V2 architecture is:

- PostgreSQL
- FastAPI
- React / Next.js
- WebSockets or a realtime provider
- presence (“X is editing Scene 14”)
- comments and pitches
- accepted vs proposed causal changes
- version history
- branches / alternate story directions
- permissions
- live causal-graph updates

## Philosophy

Pressure Room should never answer “what should I write?” before the writer has a chance to make a choice.

Its job is to keep asking:

- What does the character want?
- Why can’t they simply get it?
- What are they relying on?
- How does the story make that stop working?
- What do they choose?
- Therefore what must now be true?
- What bill did that choice create?
- What did it do to the character?
- What options are no longer available?
- Has their moral boundary moved?

**The writer remains the writer.**
