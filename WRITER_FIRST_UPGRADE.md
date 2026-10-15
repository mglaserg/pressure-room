# Writer-first upgrade (v0.8.0)

This release is the first deliberately small implementation increment of the approved Pressure Room overhaul. It keeps the existing project → branch → episode → scene model, UUIDs, snapshot format, authentication path, Supabase JSONB persistence and branch-aware PDF exporters.

## Audit findings and decisions

The findings below come from the repository at `3423af0`; they are code observations, not claims about production traffic or user behavior.

| Observed problem | Primary evidence | Decision | Observable check |
| --- | --- | --- | --- |
| The editable surface was a fixed-height scene textarea and the page-shaped view was read-only. | `WriteView.js` used `viewMode` to choose between a textarea and `ScreenplayPage`; `write.css` gave the textarea its own minimum height and resize behavior. | Make the paper itself the default editable surface, grow it with the document and retain typeset screenplay preview as an optional view. | Production build plus manual desktop/mobile acceptance checks listed below. |
| Screenplay assumptions were embedded in labels and typography. | `WriteView.js`, the episode selector and new-story flow had screenplay-only nouns and controls. | Add one project-level `writing_mode`; share storage/autosave while varying presentation and optional tools. | Mode/text round-trip backend test and portable-backup test. |
| Browser-local branch deletion could destroy any branch through the generic table delete path; the server had the same generic route. | Generic DELETE implementations accepted `branches`; neither checked `is_main` nor `parent_branch_id`. | Remove branches from generic deletion and add a dedicated, confirmed operation with Main and descendant guards. | Server and browser-local branch-safety tests. |
| The branch hierarchy was not preserved by browser-local cloning or portable backups. | Local clone omitted `parent_branch_id`; the portable whitelist omitted it. | Persist/remap the existing parent relation; do not introduce a second hierarchy. | Portable relationship validation and descendant-delete tests. |
| Autosave already had useful recovery behavior. | `draft-saver.mjs` caches every pending payload before its 700 ms save, serializes saves, flushes on navigation and pauses on version conflicts. | Preserve it, expand its payload whitelist and add Ctrl/Cmd+S; do not introduce another editor state store. | Existing draft-saver tests remain green. |

## User experience in this increment

- The writing page is directly editable, grows with the document and avoids an inner scrolling box.
- Screenplay mode retains Fountain-compatible source and branch PDF behavior, adds quick element insertion and keeps typeset preview optional.
- Sketch mode uses the same free writing page. Optional Game Lab and Tension Lab notes cover premise, rule, restriction, escalation and consequence without gating the document.
- Novel mode uses prose typography and maps the existing episode/scene hierarchy to parts and chapters. No screenplay controls are shown.
- The primary navigation uses the simpler labels Write, Plan, Tools and Help.
- Story-path deletion requires the exact branch name. Main cannot be deleted. A branch with descendants cannot be deleted. Deleting the active alternate path returns the next workspace load to Main.

## Data migration and compatibility

SQLite migration is automatic and additive on startup:

- `projects.writing_mode` defaults to `screenplay`;
- five nullable/default-empty sketch-lab text columns are added to `scenes`;
- missing branch `updated_at` and `version` columns are repaired.

No existing IDs or text columns are rewritten. Existing projects therefore open in screenplay mode and their content is unchanged. Supabase continues storing the canonical project payload as JSONB, so no Supabase table migration is required. New fields are included in `.pressureroom` browser backups; older backups default to screenplay mode when imported. Snapshot records remain project-owned and are not removed with a branch.

## Performance and reliability budget

This increment adds no editor framework or runtime dependency. The existing 700 ms debounced, serialized autosave remains the only network write path. Editor state remains local to the selected scene, and the full workspace is updated only after a successful save. Mode changes and navigation flush pending drafts first.

Recommended acceptance budgets for the next measured browser pass:

- typing: no visible dropped input during a 10,000-word document test;
- autosave: one trailing save after a normal burst, with no data loss across scene/mode navigation;
- load: no new network requests per keystroke;
- mobile: no horizontal document overflow at 390 px;
- branch deletion: Main, descendants and unrelated snapshots/content remain untouched.

These are budgets, not measured production results. The automated suite proves data behavior; device-level latency still needs browser profiling on target hardware.

## Deliberately deferred

The following are not claimed as complete in v0.8.0:

- a structured rich-text screenplay editor that hides every Fountain marker while preserving full round-trip fidelity;
- drag-and-drop scene/chapter rearrangement and scene cards;
- a dedicated manuscript/PDF exporter for novel mode;
- search and replace, comments/annotations and live collaborative cursors;
- physical iPhone Safari verification and formal accessibility testing with assistive technology;
- production performance traces or database query plans (no production environment was supplied).

These should be implemented only after realistic document fixtures and browser traces identify the next bottleneck. The current architecture intentionally leaves one shared editor/autosave core rather than three isolated editors.

## Verification

Automated checks for this patch:

- backend API/data suite, including writing-mode and branch-deletion regressions;
- frontend draft saver, Fountain parser, portable backup and local branch-deletion tests;
- Next.js production build;
- existing branch-specific PDF tests, including standard and mobile PDFs.

Suggested manual acceptance pass:

1. Open an old project and confirm its text and Main path are unchanged.
2. Type several pages, switch scenes and modes, reload, and confirm save/recovery state.
3. In sketch mode, write without opening a lab; then add lab notes and export/import a backup.
4. In novel mode, verify prose typography and that screenplay controls are absent.
5. Create a parent and child branch. Confirm Main and the parent are protected, then delete child followed by parent.
6. Export both branch screenplay PDFs and confirm each still includes only the requested path.
