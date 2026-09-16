const FORWARDED_HEADER_BLOCKLIST = [
  'host',
  'connection',
  'content-length',
  'transfer-encoding',
  'forwarded',
  'x-forwarded-host',
  'x-forwarded-for',
  'x-forwarded-proto',
  // The browser talks same-origin to this Next.js route. Forwarding Origin to
  // FastAPI makes alternate frontend hostnames look like cross-origin callers.
  // Keep Sec-Fetch-Site instead so real cross-site browser requests remain
  // distinguishable and can still be rejected by FastAPI.
  'origin',
];

export function proxyHeaders(input) {
  const headers = new Headers(input);
  for (const name of FORWARDED_HEADER_BLOCKLIST) headers.delete(name);
  return headers;
}

export function canonicalGoogleConnectUrl({path, incomingUrl, canonicalOrigin}) {
  if (path.join('/') !== 'google/connect') return null;
  const incoming = new URL(incomingUrl);
  if (['localhost', '127.0.0.1', '::1'].includes(incoming.hostname)) return null;
  const canonical = new URL(canonicalOrigin);
  if (incoming.origin === canonical.origin) return null;
  return `${canonical.origin}/api/google/connect${incoming.search}`;
}
