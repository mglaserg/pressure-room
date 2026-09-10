#!/usr/bin/env python3
# Pressure Room v0.5.7 upgrade
# Combines:
#   v0.5.5 deterministic next/font typography
#   v0.5.6 screenplay Edit / Page mode + Fountain preview
#   v0.5.7 CSS split + version/deployment/repo hygiene
#
# Run from the pressure-room repository root:
#   python pressure-room-v0.5.7-upgrade.py

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
VERSION = "0.5.7"
MARKER = "Pressure Room v0.5.7"
EDITED_PATHS = [
    "frontend/app/layout.js",
    "frontend/app/globals.css",
    "frontend/components/WriteView.js",
    "frontend/package.json",
    "frontend/package-lock.json",
    "backend/pyproject.toml",
    "backend/app/main.py",
    "README.md",
    "ARCHITECTURE.md",
    "DESIGN_SYSTEM.md",
    "DEPLOY_AWS.md",
    ".gitignore",
]


def die(message: str) -> None:
    raise SystemExit(message)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        die(f"Required file not found: {rel}\nRun this from the pressure-room repository root.")
    return path.read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        die(f"{label}: expected exactly one match, found {count}. Refusing to guess.")
    return text.replace(old, new, 1)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


if not (ROOT / ".git").exists():
    die("This does not look like the pressure-room Git repository root (.git not found).")

if (ROOT / "frontend/styles/foundation.css").exists() and MARKER in read("README.md"):
    print("Pressure Room v0.5.7 is already applied; nothing to do.")
    raise SystemExit(0)

globals_css = read("frontend/app/globals.css")
if "Pressure Room design system v0.5.4" not in globals_css:
    die(
        "This upgrade expects the v0.5.4 design-system pass first. "
        "The marker was not found in frontend/app/globals.css."
    )

status = git("status", "--porcelain", "--", *EDITED_PATHS, check=False).stdout.strip()
if status:
    die(
        "One or more files this upgrade edits already have uncommitted changes.\n"
        "Commit/stash them first so this remains reversible:\n\n" + status
    )

# ---------------------------------------------------------------------------
# v0.5.5 — deterministic typography
# ---------------------------------------------------------------------------
layout = read("frontend/app/layout.js")
if "next/font/google" not in layout:
    layout = replace_once(
        layout,
        "import './globals.css';",
        '''import { Courier_Prime, Inter, Newsreader } from 'next/font/google';
import './globals.css';

const uiFont = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-pressure-ui',
  display: 'swap',
});

const displayFont = Newsreader({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  style: ['normal', 'italic'],
  variable: '--font-pressure-display',
  display: 'swap',
});

const screenplayFont = Courier_Prime({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-pressure-script',
  display: 'swap',
});''',
        "layout font imports",
    )
    layout = replace_once(
        layout,
        '<html lang="en">\n      <body>{children}</body>\n    </html>',
        '''<html lang="en" className={`${uiFont.variable} ${displayFont.variable} ${screenplayFont.variable}`}>
      <body>{children}</body>
    </html>''',
        "layout font variables",
    )
write("frontend/app/layout.js", layout)

font_replacements = {
    '--font-ui:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;':
        '--font-ui:var(--font-pressure-ui),ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;',
    '--font-display:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;':
        '--font-display:var(--font-pressure-display),Georgia,serif;',
    '--font-script:"Courier Prime","Courier New",Courier,monospace;':
        '--font-script:var(--font-pressure-script),"Courier New",Courier,monospace;',
}
for old, new in font_replacements.items():
    if old not in globals_css:
        die(f"Expected v0.5.4 font token not found: {old}")
    globals_css = globals_css.replace(old, new, 1)

# Remove texture and hover-lift accessories.
globals_css = re.sub(r'^body:before\{.*?\}\n', '', globals_css, count=1, flags=re.M)
globals_css = globals_css.replace(
    'transition:transform .15s ease,background .15s ease,border-color .15s ease,opacity .15s ease;',
    'transition:background .15s ease,border-color .15s ease,opacity .15s ease;',
    1,
)
globals_css = globals_css.replace(
    '.button:hover{transform:translateY(-1px);background:var(--accent-strong)}',
    '.button:hover{background:var(--accent-strong)}',
    1,
)
globals_css = globals_css.replace('.button:active{transform:translateY(0)}\n', '', 1)

# ---------------------------------------------------------------------------
# v0.5.6 — dependency-free Fountain renderer + Page mode
# ---------------------------------------------------------------------------
write(
    "frontend/lib/fountain.mjs",
    r'''const SCENE_HEADING = /^(INT\.|EXT\.|EST\.|INT\/EXT\.|I\/E\.)/i;
const TRANSITION = /^(FADE (IN|OUT)\.?|CUT TO:|DISSOLVE TO:|SMASH CUT TO:|MATCH CUT TO:|.+ TO:)$/;

function cleanForced(text, marker) {
  return text.startsWith(marker) ? text.slice(marker.length).trim() : text;
}

export function parseFountain(source = '') {
  const lines = String(source).replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let inDialogue = false;
  let previousBlank = true;

  for (let index = 0; index < lines.length; index += 1) {
    const raw = lines[index].replace(/\s+$/, '');
    const text = raw.trim();
    const next = (lines[index + 1] || '').trim();

    if (!text) {
      blocks.push({type: 'blank', text: ''});
      inDialogue = false;
      previousBlank = true;
      continue;
    }

    if (text.startsWith('[[') && text.endsWith(']]')) {
      blocks.push({type: 'note', text: text.slice(2, -2).trim()});
      previousBlank = false;
      continue;
    }

    if (/^#{1,6}\s/.test(text) || text.startsWith('=')) {
      blocks.push({type: 'note', text});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    if (text.startsWith('>') && text.endsWith('<') && text.length > 2) {
      blocks.push({type: 'centered', text: text.slice(1, -1).trim()});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    if (text.startsWith('.') || SCENE_HEADING.test(text)) {
      blocks.push({type: 'scene', text: cleanForced(text, '.')});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    if ((text.startsWith('>') && !text.endsWith('<')) || TRANSITION.test(text)) {
      blocks.push({type: 'transition', text: cleanForced(text, '>')});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    const forcedCharacter = text.startsWith('@');
    const characterCandidate =
      previousBlank &&
      Boolean(next) &&
      text.length <= 42 &&
      /^[A-Z0-9][A-Z0-9 .'"()#\-]+(?:\^)?$/.test(text);

    if (forcedCharacter || characterCandidate) {
      blocks.push({
        type: 'character',
        text: cleanForced(text, '@').replace(/\^$/, '').trim(),
      });
      inDialogue = true;
      previousBlank = false;
      continue;
    }

    if (inDialogue && /^\(.*\)$/.test(text)) {
      blocks.push({type: 'parenthetical', text});
      previousBlank = false;
      continue;
    }

    if (inDialogue) {
      blocks.push({type: 'dialogue', text: cleanForced(text, '~')});
      previousBlank = false;
      continue;
    }

    blocks.push({type: 'action', text: cleanForced(text, '!')});
    previousBlank = false;
  }

  return blocks;
}
''',
)

write(
    "frontend/lib/fountain.test.mjs",
    r'''import test from 'node:test';
import assert from 'node:assert/strict';
import {parseFountain} from './fountain.mjs';

test('parses a normal character cue and dialogue', () => {
  const blocks = parseFountain('MAYA\nI am not leaving.\n\nCUT TO:');
  assert.deepEqual(
    blocks.map(block => block.type),
    ['character', 'dialogue', 'blank', 'transition'],
  );
});

test('supports forced Fountain markers', () => {
  const blocks = parseFountain('.MONTAGE - NIGHT\n\n!THE CITY HOLDS ITS BREATH.\n\n@NORA\n(quietly)\nDo it.');
  assert.deepEqual(
    blocks.map(block => block.type),
    ['scene', 'blank', 'action', 'blank', 'character', 'parenthetical', 'dialogue'],
  );
  assert.equal(blocks[0].text, 'MONTAGE - NIGHT');
  assert.equal(blocks[2].text, 'THE CITY HOLDS ITS BREATH.');
});

test('keeps centered text and marks structural notes as non-page content', () => {
  const blocks = parseFountain('>THE END<\n[[private note]]\n# Sequence');
  assert.deepEqual(
    blocks.map(block => block.type),
    ['centered', 'note', 'note'],
  );
});
''',
)

write_view = read("frontend/components/WriteView.js")
if "parseFountain" not in write_view:
    write_view = replace_once(
        write_view,
        "import {create, patch} from '@/lib/api';",
        "import {create, patch} from '@/lib/api';\nimport {parseFountain} from '@/lib/fountain.mjs';",
        "WriteView Fountain import",
    )
    write_view = replace_once(
        write_view,
        "  const [saveState, setSaveState] = useState('saved');\n  const timer = useRef(null);",
        "  const [saveState, setSaveState] = useState('saved');\n  const [viewMode, setViewMode] = useState('edit');\n  const timer = useRef(null);",
        "WriteView view mode state",
    )
    write_view = replace_once(
        write_view,
        "  useEffect(()=>()=>clearTimeout(timer.current),[]);",
        '''  useEffect(()=>{
    const saved = typeof window !== 'undefined' ? localStorage.getItem('pressure-room-write-view') : null;
    if (saved === 'page') setViewMode('page');
  },[]);

  useEffect(()=>()=>clearTimeout(timer.current),[]);

  function chooseView(nextMode) {
    setViewMode(nextMode);
    if (typeof window !== 'undefined') localStorage.setItem('pressure-room-write-view', nextMode);
  }''',
        "WriteView persisted mode",
    )

    old_editor = '''          <div className="writer-toolbar">
            <div className="writer-location"><span className="eyebrow">Episode {episode.number}</span><b>Scene {String(selected.scene_no).padStart(2,'0')}</b></div>
            <div className={`save-state ${saveState}`}><i/>{saveState==='saving'?'Saving':saveState==='offline'?'Saved on this device':'Saved'}</div>
          </div>

          <section className="writer-paper">
            <input className="slugline-input" value={draft.slugline || ''} onChange={e=>change('slugline', e.target.value)} aria-label="Scene heading" placeholder="INT. LOCATION — DAY"/>
            <div className="paper-rule"/>
            <textarea className="screenplay-editor" value={draft.screenplay_text || ''} onChange={e=>change('screenplay_text', e.target.value)} placeholder="Write the scene…" spellCheck="true"/>
          </section>'''

    new_editor = '''          <div className="writer-toolbar">
            <div className="writer-location"><span className="eyebrow">Episode {episode.number}</span><b>Scene {String(selected.scene_no).padStart(2,'0')}</b></div>
            <div className="writer-toolbar-actions">
              <div className="writer-view-switch" role="group" aria-label="Writing view">
                <button type="button" className={viewMode==='edit'?'active':''} aria-pressed={viewMode==='edit'} onClick={()=>chooseView('edit')}>Edit</button>
                <button type="button" className={viewMode==='page'?'active':''} aria-pressed={viewMode==='page'} onClick={()=>chooseView('page')}>Page</button>
              </div>
              <div className={`save-state ${saveState}`}><i/>{saveState==='saving'?'Saving':saveState==='offline'?'Saved on this device':'Saved'}</div>
            </div>
          </div>

          {viewMode==='edit'
            ? <section className="writer-paper">
                <input className="slugline-input" value={draft.slugline || ''} onChange={e=>change('slugline', e.target.value)} aria-label="Scene heading" placeholder="INT. LOCATION — DAY"/>
                <div className="paper-rule"/>
                <textarea className="screenplay-editor" value={draft.screenplay_text || ''} onChange={e=>change('screenplay_text', e.target.value)} placeholder="Write the scene…" spellCheck="true"/>
              </section>
            : <ScreenplayPage slugline={draft.slugline || ''} text={draft.screenplay_text || ''}/>}'''

    write_view = replace_once(write_view, old_editor, new_editor, "WriteView toolbar/editor")

    helper_anchor = "\nfunction StructurePanel({draft, change, characters}) {"
    if helper_anchor not in write_view:
        die("WriteView helper anchor was not found. Refusing to guess.")

    helper = r'''
function ScreenplayPage({slugline, text}) {
  const blocks = useMemo(()=>parseFountain(text), [text]);
  const visible = blocks.filter(block=>block.type!=='note');

  return <section className="screenplay-page-frame" aria-label="Typeset screenplay page preview">
    <div className="screenplay-page">
      <div className="fountain-line fountain-scene">{slugline || 'INT. LOCATION — DAY'}</div>
      {visible.length
        ? visible.map((block,index)=>{
            if(block.type==='blank') return <div key={index} className="fountain-blank" aria-hidden="true"/>;
            return <div key={index} className={`fountain-line fountain-${block.type}`}>{block.text}</div>;
          })
        : <div className="fountain-empty">The page is waiting for the scene.</div>}
    </div>
  </section>;
}
'''
    write_view = write_view.replace(helper_anchor, helper + helper_anchor, 1)

write("frontend/components/WriteView.js", write_view)

page_css = r'''
/* Screenplay Edit / Page mode */
.writer-toolbar-actions{display:flex;align-items:center;gap:.75rem}
.writer-view-switch{display:flex;align-items:center;padding:3px;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--overlay-faint)}
.writer-view-switch button{border:0;background:transparent;color:var(--text-muted);border-radius:var(--radius-sm);padding:.38rem .64rem;font-size:var(--type-xs);font-weight:var(--weight-bold);line-height:1;min-height:28px}
.writer-view-switch button:hover{color:var(--text-primary)}
.writer-view-switch button.active{background:var(--surface-panel-3);color:var(--text-primary);box-shadow:inset 0 0 0 1px var(--overlay-soft)}
.screenplay-page-frame{display:flex;justify-content:center;overflow:auto;padding:.35rem 0 1rem}
.screenplay-page{box-sizing:border-box;width:min(8.5in,100%);min-height:11in;background:var(--paper);color:var(--paper-ink);padding:.9in 1in 1in 1.5in;box-shadow:var(--shadow-paper);font-family:var(--font-script);font-size:12pt;line-height:1;letter-spacing:0}
.fountain-line{white-space:pre-wrap;overflow-wrap:break-word}
.fountain-scene{text-transform:uppercase;font-weight:var(--weight-bold);margin:0 0 1em}
.fountain-action{margin:0 0 1em}
.fountain-character{width:2.2in;margin:1em 0 0 2.15in;text-transform:uppercase}
.fountain-parenthetical{width:2.1in;margin:0 0 0 1.65in}
.fountain-dialogue{width:3.5in;margin:0 0 0 1in;line-height:1.08}
.fountain-transition{text-align:right;text-transform:uppercase;margin:1em 0}
.fountain-centered{text-align:center;margin:1em 0}
.fountain-blank{height:1em}
.fountain-empty{color:var(--paper-muted);padding-top:1em}

@media(max-width:680px){
  .writer-toolbar{align-items:center}
  .writer-toolbar-actions{gap:.45rem}
  .save-state{display:none}
  .writer-view-switch button{padding:.38rem .55rem}
  .screenplay-page-frame{margin:0 -.05rem;padding:0}
  .screenplay-page{width:100%;min-height:70vh;padding:1.35rem 1rem 2rem;font-size:11.5pt}
  .fountain-character{width:auto;margin-left:38%}
  .fountain-parenthetical{width:auto;margin-left:24%;margin-right:12%}
  .fountain-dialogue{width:auto;margin-left:14%;margin-right:8%}
}
'''

if "/* Screenplay Edit / Page mode */" not in globals_css:
    story_marker = "\n/* Story */"
    if story_marker not in globals_css:
        die("Could not find the Story CSS marker after the Write section.")
    globals_css = globals_css.replace(
        story_marker,
        "\n" + page_css.strip() + "\n\n/* Story */",
        1,
    )

# ---------------------------------------------------------------------------
# v0.5.7 — split the CSS by product surface while preserving source order.
# ---------------------------------------------------------------------------
markers = [
    "/* Brand + shell */",
    "/* Write */",
    "/* Story */",
    "/* Diagnose */",
    "/* Help */",
    "/* Modal + sharing */",
    "/* Responsive */",
]
for marker in markers:
    if marker not in globals_css:
        die(f"CSS split: required section marker missing: {marker}")

positions = {marker: globals_css.index(marker) for marker in markers}

foundation = globals_css[:positions["/* Brand + shell */"]].rstrip() + "\n"
shell = globals_css[positions["/* Brand + shell */"]:positions["/* Write */"]].rstrip() + "\n"
write_css = globals_css[positions["/* Write */"]:positions["/* Story */"]].rstrip() + "\n"
structure_css = globals_css[positions["/* Story */"]:positions["/* Diagnose */"]].rstrip() + "\n"
diagnose_css = globals_css[positions["/* Diagnose */"]:positions["/* Help */"]].rstrip() + "\n"
help_css = globals_css[positions["/* Help */"]:positions["/* Modal + sharing */"]].rstrip() + "\n"
chrome_css = globals_css[positions["/* Modal + sharing */"]:positions["/* Responsive */"]].rstrip() + "\n"
responsive_css = globals_css[positions["/* Responsive */"]:].rstrip() + "\n"

write("frontend/styles/foundation.css", foundation)
write("frontend/styles/shell.css", shell)
write("frontend/styles/write.css", write_css)
write("frontend/styles/structure.css", structure_css)
write("frontend/styles/diagnose.css", diagnose_css)
write("frontend/styles/help.css", help_css)
write("frontend/styles/chrome.css", chrome_css)
write("frontend/styles/responsive.css", responsive_css)

write(
    "frontend/app/globals.css",
    '''@import "../styles/foundation.css";
@import "../styles/shell.css";
@import "../styles/write.css";
@import "../styles/structure.css";
@import "../styles/diagnose.css";
@import "../styles/help.css";
@import "../styles/chrome.css";
@import "../styles/responsive.css";
''',
)

# ---------------------------------------------------------------------------
# Version alignment
# ---------------------------------------------------------------------------
package = json.loads(read("frontend/package.json"))
package["version"] = VERSION
package.setdefault("scripts", {})["test:fountain"] = "node --test lib/fountain.test.mjs"
write("frontend/package.json", json.dumps(package, indent=2) + "\n")

lock = json.loads(read("frontend/package-lock.json"))
lock["version"] = VERSION
if isinstance(lock.get("packages"), dict) and "" in lock["packages"]:
    lock["packages"][""]["version"] = VERSION
write("frontend/package-lock.json", json.dumps(lock, indent=2) + "\n")

pyproject = read("backend/pyproject.toml")
pyproject, n = re.subn(r'(?m)^version = "0\.5\.3"$', f'version = "{VERSION}"', pyproject, count=1)
if n != 1:
    die("backend/pyproject.toml version was not the expected 0.5.3.")
write("backend/pyproject.toml", pyproject)

backend_main = read("backend/app/main.py")
backend_main = replace_once(
    backend_main,
    'version="0.5.3"',
    f'version="{VERSION}"',
    "FastAPI application version",
)
backend_main = replace_once(
    backend_main,
    '"version": "0.5.3"',
    f'"version": "{VERSION}"',
    "health endpoint version",
)
write("backend/app/main.py", backend_main)

# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------
readme = read("README.md")
readme = re.sub(r'^# Pressure Room v[^\n]+', f'# Pressure Room v{VERSION}', readme, count=1)
readme = readme.replace(
    "V0.5 is the major product-design pass: the same story engine now feels like a **premium creative writing workspace rather than a development dashboard**.",
    "V0.5.7 consolidates the product-design pass: a token-enforced visual system, deterministic self-hosted typography, and an Edit / Page screenplay workflow on top of the same story engine.",
    1,
)
readme = readme.replace(
    "- **No fragile design dependencies.** The visual system uses native font stacks and local CSS—no external font/CDN requirement.",
    "- **No runtime font dependency.** `next/font` fetches the chosen fonts at build time and serves them with the app; the browser does not depend on a font CDN.",
    1,
)
readme = readme.replace(
    "### Write\n- paper-like screenplay canvas",
    "### Write\n- Edit / Page toggle over the same screenplay source\n- typeset Fountain preview with screenplay spacing and dialogue indentation\n- paper-like screenplay canvas",
    1,
)

remote_re = re.compile(r"## Remote / AWS hosting\n.*?(?=\n## Sharing with friends)", re.S)
remote_block = '''## Remote / AWS hosting

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

See [`DEPLOY_AWS.md`](DEPLOY_AWS.md) for the deployment contract.'''
if not remote_re.search(readme):
    die("README remote/AWS section was not found.")
readme = remote_re.sub(remote_block + "\n", readme, count=1)
write("README.md", readme)

architecture = read("ARCHITECTURE.md")
architecture = architecture.replace("## V0.5 stack", f"## V{VERSION} stack", 1)
architecture = architecture.replace("- Next.js 16 App Router", "- Next.js 15.5.24 App Router", 1)
architecture = architecture.replace(
    "- responsive CSS without a component-framework dependency",
    "- responsive CSS without a component-framework dependency\n- build-time self-hosted typography via `next/font` (Inter / Newsreader / Courier Prime)\n- CSS split by product surface so design drift stays visible in diffs",
    1,
)
architecture = architecture.replace(
    "- SQLite for local-first V0.x",
    "- SQLite as the local / ephemeral working cache\n- Google Drive `.pressureroom` files as the canonical production store",
    1,
)
architecture = architecture.replace("## V0.5 visual system", f"## V{VERSION} visual system", 1)
architecture = architecture.replace(
    "No external font or design-system CDN is required, reducing local/remote rendering differences.",
    "`next/font` downloads typography during the build and serves it with the application, so production has deterministic fonts without runtime font-CDN requests.",
    1,
)
write("ARCHITECTURE.md", architecture)

design = read("DESIGN_SYSTEM.md")
typography_re = re.compile(r"## Typography\n.*?(?=\n## Interaction hierarchy)", re.S)
typography_block = '''## Typography

Typography is deterministic across platforms and has no runtime font-CDN dependency. Next.js `next/font` downloads the files during the build and serves them with the application.

- UI: **Inter**
- Story hierarchy: **Newsreader**
- Screenplay: **Courier Prime**
- UI sizing uses the seven-step token scale; meaningful interface text does not drop below `--type-xs` (`0.75rem`).
- Font weights use real 400 / 500 / 600 / 700 / 800 steps instead of synthetic in-between values.

## Token discipline

Components consume semantic surface, text, status, radius, and type tokens. New one-off hex colors, font sizes, and radii should be treated as design-system exceptions that need an explicit reason.

The screenplay is the intentional exception: Page mode follows screenplay conventions rather than the general UI type scale.'''
if not typography_re.search(design):
    die("DESIGN_SYSTEM typography section was not found.")
design = typography_re.sub(typography_block + "\n", design, count=1)
write("DESIGN_SYSTEM.md", design)

deploy = f'''# Pressure Room on AWS — v{VERSION}

Pressure Room uses **Amplify for the Next.js frontend** and **Amazon ECS Express Mode for the FastAPI backend**. Google Drive is the canonical production story store; SQLite inside the container is a disposable working cache.

## Production topology

```text
Browser
  ↓
AWS Amplify / Next.js
  ↓ same-origin /api/*
Next.js Route Handler proxy
  ↓ PRESSURE_ROOM_API_URL
Amazon ECS Express Mode
  ↓
FastAPI :8000
  ↓
ephemeral SQLite cache
  ↕
Google Drive / Pressure Room/*.pressureroom
```

The browser never needs to call ECS directly, so normal app traffic remains same-origin.

## Amplify

Set this environment variable on the `main` branch:

```text
PRESSURE_ROOM_API_URL=https://<ecs-application-url>
```

`amplify.yml` writes it into `.env.production` during the Next.js build.

After deployment, verify the complete proxy path:

```powershell
curl.exe https://main.d23277cgmbx1g0.amplifyapp.com/api/health
```

## ECS Express Mode

Backend contract:

```text
container port:    8000
health check path: /api/health
minimum tasks:     1
maximum tasks:     1
```

The single-task cap is deliberate for the current Drive + SQLite single-writer model.

Direct backend check:

```powershell
curl.exe https://<ecs-application-url>/api/health
```

## Google Drive configuration

Ordinary ECS environment variables:

```text
GOOGLE_CLIENT_ID
PRESSURE_ROOM_PUBLIC_URL=https://main.d23277cgmbx1g0.amplifyapp.com
PRESSURE_ROOM_ALLOWED_EMAIL=<your Google account>
```

Secrets Manager values injected into the task:

```text
GOOGLE_CLIENT_SECRET
PRESSURE_ROOM_SESSION_KEY
```

The ECS task execution role must be able to call `secretsmanager:GetSecretValue` for those secret ARNs. If a customer-managed KMS key protects them, add the corresponding `kms:Decrypt` permission.

OAuth callback:

```text
https://main.d23277cgmbx1g0.amplifyapp.com/api/google/callback
```

## Deployment automation

`.github/workflows/deploy-backend-ecs-express.yml` builds the backend image, pushes it to ECR, and updates the ECS Express service when backend files change on `main`.

The frontend continues to deploy through Amplify.

## Persistence rule

Do not treat the ECS container filesystem as durable storage. A replacement task can start with an empty local SQLite cache. Once Drive is configured, Pressure Room hydrates that cache from the user's Drive files and writes project changes back to Drive.

If multi-writer collaboration is added later, move canonical live state to PostgreSQL or another concurrency-safe store; keep Drive as export / backup / sharing.
'''
write("DEPLOY_AWS.md", deploy)

gitignore = read(".gitignore")
if "*.patch" not in gitignore:
    gitignore = gitignore.replace("*.bundle\n", "*.bundle\n*.patch\n", 1)
write(".gitignore", gitignore)

# Remove the tracked bundle from Git while preserving the local file.
if git("ls-files", "--error-unmatch", "pressure-room-current.bundle", check=False).returncode == 0:
    git("rm", "--cached", "--", "pressure-room-current.bundle")

print(f'''
{MARKER} upgrade applied.

Implemented:
  ✓ deterministic Inter / Newsreader / Courier Prime via next/font
  ✓ Edit / Page screenplay switch
  ✓ dependency-free Fountain page renderer
  ✓ Fountain parser tests
  ✓ CSS split into 8 surface-oriented files
  ✓ version alignment to {VERSION}
  ✓ current Amplify + ECS Express + Drive deployment docs
  ✓ tracked .bundle removed from Git index; local copy preserved
  ✓ generated *.patch files ignored

Run:

  cd frontend
  npm run test:fountain
  npm run build
  cd ..
  cd backend
  uv run pytest -q
  cd ..
  git diff --check
  git status
  git diff HEAD --stat

Then commit:

  git add -A
  git commit -m "Add deterministic typography and screenplay page mode"
  git push
''')
