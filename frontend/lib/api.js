export const API = '/api';

export async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({detail: res.statusText}));
    throw new Error(detail.detail || 'Request failed');
  }
  const type = res.headers.get('content-type') || '';
  return type.includes('application/json') ? res.json() : res;
}

export const patch = (table, id, data) => api(`/${table}/${id}`, {method: 'PATCH', body: JSON.stringify({data})});
export const remove = (table, id) => api(`/${table}/${id}`, {method: 'DELETE'});
export const create = (path, data) => api(path, {method: 'POST', body: JSON.stringify({data})});
