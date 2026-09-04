# Deploy Pressure Room on AWS

Pressure Room v0.4.2 uses a same-origin web architecture:

```text
Browser -> Next.js :3000 -> internal proxy -> FastAPI 127.0.0.1:8000
```

The FastAPI port does **not** need to be public.

## Quick start on the server

From the repository root:

```bash
chmod +x run.sh
./run.sh
```

The frontend now binds to `0.0.0.0:3000`; FastAPI remains private on `127.0.0.1:8000`.

## Verify on the AWS instance

In another shell:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:3000/api/health
```

Both should return JSON with `"ok": true`. The second request proves that Next.js is successfully proxying to FastAPI.

## AWS Security Group

For direct access during development, allow inbound TCP **3000** from your IP (or from the network/VPN you use). You do not need to expose port 8000.

Then browse to:

```text
http://YOUR_AWS_PUBLIC_IP:3000
```

If you use NetBird/Tailscale/a VPN, use the server's VPN address instead and allow that traffic in the host firewall as needed.

## Recommended later: HTTPS / reverse proxy

For a durable deployment, put nginx/Caddy/your AWS load balancer in front of Next.js and expose only 80/443. Proxy all traffic to `127.0.0.1:3000`; Next.js will continue proxying `/api/*` internally to FastAPI.

## If the page still does not open

Check listeners:

```bash
ss -ltnp | grep -E ':3000|:8000'
```

Expected:
- `0.0.0.0:3000` (Next.js)
- `127.0.0.1:8000` (FastAPI)

Then check the app itself:

```bash
curl -I http://127.0.0.1:3000
curl http://127.0.0.1:3000/api/health
```

If those work on the server but not from your computer, the remaining issue is AWS Security Group / host firewall / routing rather than Pressure Room.
