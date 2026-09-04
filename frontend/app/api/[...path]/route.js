const API_ORIGIN = (process.env.PRESSURE_ROOM_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const TIMEOUT_MS = 10000;

export const dynamic = 'force-dynamic';

async function proxy(request, context) {
  const {path = []} = await context.params;
  const incoming = new URL(request.url);
  const target = `${API_ORIGIN}/api/${path.map(encodeURIComponent).join('/')}${incoming.search}`;

  const headers = new Headers(request.headers);
  for (const name of ['host', 'connection', 'content-length', 'transfer-encoding']) headers.delete(name);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const hasBody = !['GET', 'HEAD'].includes(request.method);
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: 'manual',
      cache: 'no-store',
      signal: controller.signal,
    });

    const responseHeaders = new Headers(response.headers);
    for (const name of ['connection', 'transfer-encoding', 'content-encoding']) responseHeaders.delete(name);

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const timedOut = error?.name === 'AbortError';
    return Response.json(
      {
        detail: timedOut
          ? `Pressure Room API timed out after ${TIMEOUT_MS / 1000}s.`
          : `Pressure Room web server could not reach FastAPI at ${API_ORIGIN}.`,
      },
      {status: 502},
    );
  } finally {
    clearTimeout(timer);
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const HEAD = proxy;
export const OPTIONS = proxy;
