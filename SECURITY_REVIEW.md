<<<<<<< HEAD
# Pressure Room 0.7.0 — security, cleanup and design review

Reviewed September 14–15, 2026. Source: `pressure-room-2026-09-14_154506-72c9197.bundle`, base commit `72c9197fe6a0001156c9dc0204a2812fc0df5143`. Updated package version: **0.7.0**.

The cleanup addresses concrete security and data-preservation defects while retaining the current writing interface. Dependency audits now return **zero known vulnerabilities**. This is a source review and local verification, not a production penetration test or a guarantee that the application is vulnerability-free. Drive conflict handling is implemented in this follow-up; live integration and durable deployment storage still require verification.
=======
# Pressure Room — security, cleanup and design review

Reviewed September 14, 2026. Source: `pressure-room-2026-09-14_154506-72c9197.bundle`, base commit `72c9197fe6a0001156c9dc0204a2812fc0df5143`. Updated package version: **0.6.1**.

The cleanup addresses concrete security and data-preservation defects while retaining the current writing interface. Dependency audits now return **zero known vulnerabilities**. This is a source review and local verification, not a production penetration test or a guarantee that the application is vulnerability-free. **Drive conflict handling remains the main unresolved data-loss risk.**
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020

## Findings and changes

Severity reflects the conditions below; reliability defects are distinguished from exploitable security issues.

| Priority | Finding in the uploaded version | Change / status |
|---|---|---|
| High, when exposed publicly | With Google configuration absent, the server accepted anonymous reads and writes against one SQLite database. The browser-local option did not remove those backend endpoints. | Server-local API now fails closed unless `PRESSURE_ROOM_ALLOW_LOCAL_API=true` is explicitly enabled. Browser-local mode still works without Google. Existing Google authentication remains in place. |
| High, dependency advisory; application exposure conditional | Locked PostCSS had multiple advisories, including arbitrary source-map reads when processing attacker-controlled CSS. No user-controlled CSS compilation route was found in this application. npm reported PostCSS high and its dependent Next.js moderate. | Pinned an npm override to PostCSS 8.5.28, updated the lock, and verified the production build. Retained Next.js 15.5.24. Audit is now clear. |
| High, data preservation | Replace import deleted the original project before all incoming rows were validated; Drive refresh cleared the cache before all packages were imported. A later failure could leave partial data. | Shared transactional connection rolls back the entire import or Drive refresh. Regression tests confirm preservation after malformed input. |
| High, data preservation | Autosave timers were cancelled on view unmount. Only screenplay text was cached, empty cached text was ignored, and an old request could clear a newer draft. | Saves now serialize by scene, persist the full draft, flush on scene/view exit, retain failed drafts, preserve deliberate empty text, and avoid deleting newer recovery data. Successful saves update the in-memory workspace. Save destination is captured rather than changed by a later mode switch. |
| Medium, resource exhaustion | File upload and ZIP JSON decompression had no application limit. | Requests bounded to 11 MiB before backend parsing and at the frontend proxy; package bytes to 10 MiB and decompressed project JSON to 32 MiB. Duplicate project.json entries and encrypted/oversized project data are rejected. This does not replace edge rate limiting. |
| Medium, trust boundary | Portable packages could carry external Drive file IDs and historical links later used for automatic Fountain writes. | Uploaded packages discard external linkage; snapshot restores preserve only the current project's link and cannot target another project. Drive-linked project cache retrieval remains a distinct trusted-account workflow. |
| Medium, session hardening | Session cookie browser expiry was 90 days, but decrypting a copied cookie imposed no server expiry. | Fernet validates the same 90-day lifetime. Non-local OAuth origins require HTTPS. Disabled Google routes report that Google is unconfigured. |
| Medium, request hardening | No explicit origin guard for cookie-authenticated writes; disconnect changed state through GET; sensitive API responses lacked consistent no-store headers. | Browser-origin checks for mutations, POST disconnect, no-store API responses, no-referrer and nosniff. Browser cookie SameSite remains Lax for OAuth callback compatibility. |
| Medium, input integrity | Imported column names entered SQL construction without schema validation; some PATCH operations could connect records across story/episode boundaries. | Schema allowlists on inserts/updates/deletes, same-story relationship checks, same-episode causal-link checks, and clean missing-record responses. This is defensive hardening; no successful arbitrary-SQL exploit is claimed. |
| Medium, reliability | Generic insert added `id` to `project_sources`, whose primary key is `project_id`, preventing link creation. Snapshot restore deleted its own history. | Corrected source-table insertion and retained snapshot history during restore. |
| Low / medium, hardening | Export titles entered Content-Disposition directly; Unicode and control characters could break responses. Docker copied broadly and installed floating dependencies as root. | Safe ASCII fallback plus encoded Unicode filename; explicit application copy, hashed lock export, and non-root container user. |
| Low, maintenance / usability | Tracked backup files duplicated the codebase. The modal lacked native dialog/focus behavior. Proxy timeouts were shorter than a single Drive call. | Removed tracked .bak files; ignored credentials/nested databases/backups; native modal with Escape, focus return and background inertness; visible focus styles, reduced-motion support, screenplay label, live save status and retry. Proxy/client timeouts adjusted to 60/65 seconds with an ambiguous-completion warning. |

### Dependency evidence

The original npm scan reported **2 affected packages: 1 high, 1 moderate; 0 critical**. These represent PostCSS plus its dependent Next.js, not two independent runtime exploits. The updated scan reports zero. The resolved Python dependency scan reports zero known vulnerabilities.

The [PostCSS maintainer advisory](https://github.com/postcss/postcss/security/advisories/GHSA-fxqj-rqcc-2cmp) describes the source-map disclosure condition and identifies 8.5.23 as the fix for that advisory; the installed override is 8.5.28. The other advisories and exact ranges returned by npm are retained in `audit/npm-before.json`.

The [Next.js release blog](https://nextjs.org/blog) identifies 15.5.24 as the August 2026 maintenance security release. React's [server-component advisory](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components) concerns `react-server-dom-*` implementations; the presence of `react: 19.2.0` alone does not establish that this already-patched Next.js bundle is vulnerable. No React RCE finding is asserted here.

Machine-readable audit output is included under `audit/`. These are point-in-time registry results, not future guarantees.

<<<<<<< HEAD
## Follow-up completed — September 15, 2026

The 0.7.0 follow-up addresses the code and interface work left by 0.6.1. It does not certify a running deployment or a Google account. The findings above remain the record of the original cleanup; the status below supersedes that iteration's remaining-work list.

| Area | Implemented and checked |
|---|---|
| Durable saves | Atomic local mutation plus exact SQLite upload intent; staged sidecar/Fountain completion; pending work survives reopening the database; failed refresh leaves cached stories accessible. Network writes occur after the local transaction commits. |
| Concurrent edits | Browser project-revision checks, local scene-version checks and Drive ETag preconditions. Changed remote content is retained as a conflict. Lost successful responses are acknowledged only when the complete remote payload matches the intended one. Stable pre-generated file IDs prevent duplicate creates on retry. |
| Conditional-write safety | A disposable-file capability probe verifies rejection of an impossible `If-Match` before real story overwrites. Missing/weak ETags or failed capability checks block overwrites. Tests cover both an enforcing service and a service that ignores the header. Live Google behavior remains untested here. |
| Recovery | Retry, independent recovery-copy creation and loading Drive with a preserved recovery story. Fountain-conflict reload rebuilds only the linked path from external text. Copied snapshots retain a remapped, restorable story identity. |
| Browser drafts | Full draft caching; stale recovered drafts and HTTP 409 failures pause autosave instead of overwriting the saved scene. Recovery download and explicit load-saved controls. Backup/account actions stop if the current scene remains unsaved. Pending remote jobs can still be backed up from the committed local story. |
| Fountain paths | One explicit branch controls the linked screenplay. Alternate branches are excluded from that file; main is the compatibility default. The complete editable package preserves all branches. |
| Local portability | Bounded ZIP encode/decode, schema field filtering, reference checks, copy import, explicit replacement, snapshots and story notes. Original identifiers survive replace; copies remap relationships. Imports strip external Drive linkage. |
| Sessions | Disconnect revokes the current session ID in SQLite, so replaying that cookie is rejected. Legacy encrypted cookies receive a stable fingerprint. Account-scoped browser recovery drafts can be explicitly cleared. Google consent and separately issued sessions remain independent. |
| Resource limits | Streamed Drive media capped before buffering the whole response: project ZIP 10 MiB, Fountain 8 MiB. Portable project JSON is capped at 32 MiB; export cannot produce an oversized package that the importer rejects. Browser package parsing checks expansion size before decompression. |
| Deployment gate | Backend deployment depends on the reusable verification job. The job runs Python/JavaScript tests, lock consistency, npm/Python vulnerability audits and the production web build. |

Google's [Drive v2 File reference](https://developers.google.com/workspace/drive/api/reference/rest/v2/files) exposes the ETag, and its [update reference](https://developers.google.com/workspace/drive/api/reference/rest/v2/files/update) defines the content-update endpoint. The implementation deliberately verifies conditional-write enforcement at runtime rather than treating generic HTTP semantics as proof of live Drive behavior.

## Design work

The dark surrounding interface and warm screenplay paper remain. **Room** now collects paths, new-story actions, storage/account controls and **Export & backup**. Focus mode removes the scene rail and optional structure, while retaining scene navigation and save status. Diagnose leads with one revision question and reveals its full tools on request.

Save language distinguishes browser storage, Drive completion, pending upload, failure and conflict. Recovery actions appear beside the problem. The mobile pass removed a legacy rule that hid save status, reduced header crowding, fixed wrapping navigation labels and kept native dialogs inside a 390 px viewport. Google Picker temporarily suspends the native modal so its external picker can be interactive.

Desktop and mobile screenshots are under `audit/screenshots/`. Native dialog Escape/focus return, focus mode, autosave persistence, browser export/copy import and mobile containment were exercised in Chromium. This is not a WCAG certification, a screen-reader review or a physical iOS/Android test.

## Verification and limits

- **43 Python tests** and **14 JavaScript tests** passed. Coverage includes failed-import rollback, session expiry/revocation, bounded imports, relationship integrity, durable pending state, conditional requests, lost acknowledgements, external conflicts, snapshot-copy restoration and selected-path rendering.
- Next.js production build succeeded, including all seven generated pages.
- `npm audit`: **0 known vulnerabilities** across the locked npm dependency graph, including new `fflate@0.8.3`. `pip-audit 2.10.1`: **0 known vulnerabilities** among 29 resolved production Python packages. Registry results dated September 15 are in `audit/npm-after.json` and `audit/python-after.json`; these do not cover container OS packages or unknown vulnerabilities.
- Browser test results are in `audit/browser-results.json`; browser/backend package interoperability was also checked. The test uses a seeded sample story, not user production data.
- The earlier limited reachable-Git-object secret-pattern scan found no matches for the tested key/token formats. No additional claim of exhaustive history/secret-store coverage is made.
- Two test-library deprecation warnings remain in Starlette/httpx and AnyIO test integration.

### Operational work still requiring the real environment

1. **Persistent storage and one active writer process.** The queue and revocation database survive only as long as their backing volume. The included ECS deployment does not provision a persistent volume. Configure and restore-test durable storage before relying on task-replacement recovery. Keep one backend worker/instance per cache volume; the in-process lock is not a distributed lock. Independent cache instances cannot coordinate revocation through isolated databases.
2. **Live Google and deployment validation.** OAuth/Picker, real ETag enforcement, two-device conflicts, ambiguous network responses, durable restart, IAM, TLS, edge rate limiting, Google app restrictions and container execution/scanning were not verified. The runtime probe fails closed, but does not replace a complete integration test. No production push, deploy or remote migration was performed.
3. **Scale and parity.** Full-story packaging/hashing and full snapshots remain expensive for very large projects. Snapshot retention, per-account queues and delta saves are future work. The browser and Python engines share a tested portable format, not a single implementation; broader feature parity is still a maintenance concern. Browser-local mode provides editable backups, while PDF/Markdown/Fountain downloads remain server features.
4. **Platform protection.** Repository branch protection and frontend hosting gates must be configured separately. The existing limited CSP is not a full nonce-based script policy. Shared-browser storage remains readable to another person using that profile; disconnect does not encrypt or erase browser-local stories.

See `UPGRADE.md` for migration, recovery behavior and required deployment settings. The full bundle retains Git history. The ZIP excludes installed dependencies and runtime databases.
=======
## Remaining risks and architecture considerations

1. **Drive synchronization and external edits — high data-loss priority.** `ensure_local()` can rehydrate the cache after 15 seconds; writes and refreshes do not form one durable operation. Sidecar and Fountain writes are separate, and linked Fountain uploads do not use a remote precondition to reject conflicting modifications. Two tabs/devices or another editor can overwrite work. The in-process lock does not coordinate processes or containers. The current deployment specifies one task, but that does not solve concurrent browser/device edits. Add a per-project durable write queue, revision checks/conditional updates where supported, recoverable conflict copies, and explicit conflict UI before enabling multi-instance deployment. API timeouts still cannot prove a write did not complete. Do not blindly retry destructive or create operations.
2. **Linked Fountain branch semantics.** The current renderer walks all project episodes, including alternate branches; cloning a branch can cause alternatives to appear in a single linked script. Decide which branch is authoritative for a linked Fountain file and require an explicit export choice for alternatives. This iteration does not change that behavior silently.
3. **Browser-local backup and parity.** Browser-local stories still lack the existing Drive-only import/export UI. Clearing site data, changing origin/browser/profile, or device failure can lose that store. Add a one-click local project backup and validated restore before making browser-only storage the preferred durable workflow. Local and Python data engines duplicate behavior and have different feature coverage; move toward a shared contract and parity tests. Corrupt/unreadable browser JSON now produces an error rather than being silently replaced with an empty store.
4. **Session revocation and shared devices.** The Google session is still a client-held encrypted token. Logout deletes the current cookie; it does not revoke copied cookies or Google consent. Tokens are cached in process, and browser recovery drafts remain on the device. New recovery keys include storage mode/account, but this is not encryption or protection against someone using the same browser profile. Plan server-side revocation and an explicit account/draft cleanup policy if multi-user/shared-device use grows.
5. **Production protection still needs inspection.** No live AWS/Amplify/ECS configuration, IAM policies, WAF/rate limiting, TLS termination, Google OAuth/Picker restrictions, logs, container OS scan, or backup recovery drill was examined. The CSP added here covers framing, base URIs and objects; it is not a complete script policy. A nonce-based policy must account for Next.js hydration and Google Picker. CI is added as a separate verification workflow; make it a required branch/deployment check in repository settings. Existing deployment is not automatically blocked by this independent workflow.
6. **Large projects.** Full-project packages and repeated snapshots amplify upload volume, decompression and parsing costs. Quotas, snapshot retention, delta saves, and streaming bounded Drive downloads remain useful future work. Backend Drive downloads currently buffer their bodies before package validation; the upload limits do not cap all upstream downloads.

Positive controls already present: per-Google-account cache paths are derived from stable account identity; SQL values are parameterized; editable PATCH fields are explicitly constrained; PDF content is escaped; React renders screenplay text as text; OAuth uses a random state cookie and an HttpOnly encrypted session; Drive uses the narrower `drive.file` scope. These are useful foundations and were retained.

## Design considerations

This assessment is based on component and stylesheet inspection. Automated browser installation failed, so no rendered desktop/mobile or assistive-technology verification is claimed.

The strongest existing choices are the restrained dark chrome, warm writing paper, separate UI/display/screenplay typography, clear Write / Structure / Diagnose modes, and collapsed deeper scene structure. Preserve those. The best next iteration should make writing feel safer and calmer, rather than add another dashboard.

| Priority | Design action | Why it matters |
|---|---|---|
| First | One truthful save indicator with distinct states: saving, saved locally, synced to Drive, failed, conflict. Provide retry/recovery close to the editor. | Writers should never infer durability from a green label. This pass corrects failed-save language and retains full drafts; conflict states still need backend support. |
| First | A visible Backup action in browser-local mode; account/storage settings with clear location and recovery information. | Storage choice is a meaningful user decision; users need a way out of the browser before a failure. |
| Next | Reduce mobile header actions to story/episode context and one overflow menu. Put path switching, storage management, import/export and new-story actions there. | The top bar currently combines navigation, creation, account state and file actions; fewer simultaneous controls give the page more space. |
| Next | Focus mode: collapse scene rail and optional structure while retaining scene navigation and save status. | The existing progressive disclosure is good; extend it without hiding essential save state. |
| Next | Diagnose should lead with one actionable observation, then reveal the full check list. | Treat diagnostics as help for the next revision, not a scorecard the writer must clear. |
| Next | Label the current Share menu “Export & backup,” with genuine collaboration separated if introduced later. Put disconnect inside account settings. | Current exports are downloads; the naming should communicate what will happen. The previous Drive status link also logged the user out unexpectedly. |
| Verify | Keyboard flow, native modal behavior, narrow screens, 200% zoom, touch targets and actual text contrast. | Source-level fixes were added, but visual and accessibility checks still need a real browser/device pass. |

## Verification

- Existing baseline: 10 backend tests passed before edits.
- Updated backend: **24 tests passed**, including failed-import and failed-Drive-pull rollback, snapshot history, source-table insertion, imported link stripping, cross-story snapshot rejection, server-side session expiry, body/ZIP limits, safe Unicode exports, cross-origin writes, anonymous API denial, and relationship validation.
- Frontend: **7 tests passed** (3 existing Fountain parser tests plus 4 autosave/recovery tests).
- Next.js production build compiled and generated all 7 pages successfully; no major Next.js upgrade required.
- Production HTTP smoke check: web page and proxied health returned 200, anonymous project API returned 403, and response security headers were present.
- npm audit after dependency update: **0 known vulnerabilities**. Python resolved dependency audit: **0 known vulnerabilities**.
- A limited pattern scan of 330 reachable Git objects found no matches for private-key blocks, AWS access-key IDs, GitHub token formats, or Google client-secret format. This is not an exhaustive secret scan and does not inspect external secret stores.
- Two test-library deprecation warnings remain (Starlette/httpx and AnyIO test integration); they did not affect results.
- Live Google authentication, live Drive mutations, multi-device conflict behavior, Docker image execution, deployment and visual browser QA were not verified.

See `UPGRADE.md` for compatibility changes, patch application, cache permissions, and storage expectations. The full bundle retains Git history; the source ZIP excludes history, installed dependencies and runtime data.
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
