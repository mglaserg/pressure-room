# Verification evidence

The September 15, 2026 follow-up was checked with 43 Python tests, 14 JavaScript tests, the Next.js production build, locked npm/Python dependency audits, a headless Chromium browser pass and a browser/backend package round trip. See `SECURITY_REVIEW.md` at repository root for findings and limits. Earlier audit artifacts are retained as historical evidence.

To repeat the browser pass after installing backend dependencies and building the frontend:

```sh
# Install Playwright and its Chromium browser in your development environment.
node scripts/browser-check.cjs
```

`PRESSURE_ROOM_PLAYWRIGHT_MODULE` may name an absolute Playwright module directory; `PRESSURE_ROOM_CHROMIUM` may name an existing compatible Chromium executable. Otherwise normal Playwright module/browser resolution is used. Run from the repository root. The script starts temporary servers on loopback ports 3137 and 8137, seeds a sample story and writes screenshots/results to ignored `qa/`. It does not connect to Google or modify production stories.

The saved screenshots show the desktop writer, focus mode, Room dialog, 390 px mobile writer/dialog and progressive diagnosis. Browser results cover local edits, backup/copy import, reload, stale-scene rejection, recovery and focus handling. They do not establish live Google or physical-device compatibility.
