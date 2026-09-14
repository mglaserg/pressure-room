// Serialize saves per scene, including across component remounts.
const chains = new Map();

export function createDraftSaver({key, storage, send, onState = () => {}}) {
  let pending = null;
  let revision = 0;
  let timer;
  let cached = true;

  function recover() {
    try {
      const raw = storage.getItem(key);
      if (!raw) return null;
      const value = JSON.parse(raw);
      return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
    } catch { return null; }
  }

  function update(payload) {
    revision += 1;
    pending = {...payload};
    try { storage.setItem(key, JSON.stringify(pending)); cached = true; }
    catch { cached = false; }
    onState(cached ? 'saving' : 'uncached');
    clearTimeout(timer);
    timer = setTimeout(flush, 700);
  }

  function flush() {
    clearTimeout(timer);
    if (!pending) return chains.get(key) || Promise.resolve();
    const payload = pending;
    const version = revision;
    const serialized = JSON.stringify(payload);
    pending = null;
    const job = (chains.get(key) || Promise.resolve()).then(async () => {
      try {
        await send(payload);
        // An older response must never erase a newer recoverable draft.
        try { if (storage.getItem(key) === serialized) storage.removeItem(key); } catch {}
        if (version === revision) onState('saved');
      } catch {
        if (version === revision) {
          pending = payload;
          onState(cached ? 'offline' : 'uncached');
        }
      }
    });
    chains.set(key, job);
    job.finally(() => { if (chains.get(key) === job) chains.delete(key); });
    return job;
  }

  return {recover, update, flush, isPending: () => Boolean(pending || chains.has(key))};
}
