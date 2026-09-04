export const API = '/api';
const REQUEST_TIMEOUT_MS = 12000;

export async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${API}${path}`, {
      ...options,
      cache: 'no-store',
      signal: options.signal || controller.signal,
      headers: {
        ...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({detail: res.statusText}));
      throw new Error(detail.detail || `Request failed (${res.status})`);
    }
    const type = res.headers.get('content-type') || '';
    return type.includes('application/json') ? res.json() : res;
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('Pressure Room API did not respond within 12 seconds. Open /api/health to check the server connection.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export const patch = (table, id, data) => api(`/${table}/${id}`, {method: 'PATCH', body: JSON.stringify({data})});
export const remove = (table, id) => api(`/${table}/${id}`, {method: 'DELETE'});
export const create = (path, data) => api(path, {method: 'POST', body: JSON.stringify({data})});
