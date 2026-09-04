# Pressure Room on AWS — v0.4.3

Pressure Room now uses a Next.js **Route Handler proxy** for every browser `/api/*` request.
The browser only talks to the Next.js origin. Next.js talks to FastAPI on the server.

## Expected topology

Browser -> Next.js :3000 -> Route Handler `/api/*` -> FastAPI 127.0.0.1:8000

Only port 3000 needs to be externally reachable when using the simple direct deployment.
Port 8000 should remain private.

## Three decisive checks

Run these **on the AWS machine** after starting Pressure Room:

```bash
curl --max-time 5 -i http://127.0.0.1:8000/api/health
curl --max-time 5 -i http://127.0.0.1:8000/api/projects
curl --max-time 8 -i http://127.0.0.1:3000/api/health
```

All three should return HTTP 200.

Then from your own computer/browser open:

```text
http://YOUR_SERVER:3000/api/health
```

If that returns JSON, the browser-to-Next-to-FastAPI path works.

## If the app shows “Opening the room…”

v0.4.3 adds request timeouts. It should now turn a hung startup request into a visible error within roughly 12 seconds, with a button to open `/api/health`.

## Running on a server

For a quick direct deployment:

```bash
chmod +x run.sh
./run.sh
```

For a durable deployment, put Next.js behind nginx/Caddy on 80/443 and run both Next.js and FastAPI under systemd or another process supervisor.
