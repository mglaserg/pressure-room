# Pressure Room on AWS — v0.4.4

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

v0.4.4 runs the Linux/AWS launcher in production mode (`next build` + `next start`) so remote browsers are not subject to Next.js development-origin blocking. The explicit `/api` proxy and request timeouts remain in place.

## Running on a server

For a quick direct deployment:

```bash
chmod +x run.sh
./run.sh
```

For a durable deployment, put Next.js behind nginx/Caddy on 80/443 and run both Next.js and FastAPI under systemd or another process supervisor.

## Development mode over NetBird / another remote origin

AWS should normally use `./run.sh`, which runs a production Next.js server.

If you intentionally want hot reload, use `./run-dev.sh`. Next.js protects development assets from unexpected origins, so provide the hostname/IP you use in the browser:

```bash
PRESSURE_ROOM_ALLOWED_DEV_ORIGINS=100.69.49.155 ./run-dev.sh
```

For more than one trusted dev origin, use a comma-separated list. This setting is only for `next dev`; production mode does not require it.
