// Serialize saves per scene, including across component remounts.
const chains = new Map();
<<<<<<< HEAD
const activeSavers = new Set();
export async function flushDrafts(){
  const savers=[...activeSavers];
  await Promise.all(savers.map(s=>s.flush()));
  if(savers.some(s=>s.isPending()))throw Error('A scene draft has not been saved. Download its recovery draft or resolve it before continuing.');
}
=======
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020

export function createDraftSaver({key, storage, send, onState = () => {}}) {
  let pending = null;
  let revision = 0;
  let timer;
  let cached = true;
<<<<<<< HEAD
  let paused = false;
=======
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020

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
<<<<<<< HEAD
    onState(paused ? 'conflict' : cached ? 'saving' : 'uncached');
    clearTimeout(timer);
    if(!paused)timer = setTimeout(flush, 700);
=======
    onState(cached ? 'saving' : 'uncached');
    clearTimeout(timer);
    timer = setTimeout(flush, 700);
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
  }

  function flush() {
    clearTimeout(timer);
<<<<<<< HEAD
    if (paused || !pending) return chains.get(key) || Promise.resolve();
=======
    if (!pending) return chains.get(key) || Promise.resolve();
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
    const payload = pending;
    const version = revision;
    const serialized = JSON.stringify(payload);
    pending = null;
    const job = (chains.get(key) || Promise.resolve()).then(async () => {
      try {
<<<<<<< HEAD
        const result=await send(payload);
        if(result?.sync && !['synced','local'].includes(result.sync.status)){
          if(version===revision)onState(result.sync.status);
          return;
        }
        // An older response must never erase a newer recoverable draft.
        try { if (storage.getItem(key) === serialized) storage.removeItem(key); } catch {}
        if (version === revision) onState('saved');
      } catch (error) {
        if (version === revision) {
          pending = payload;
          if(error.status===409)paused=true;
          onState(error.status===409?'conflict':cached?'offline':'uncached');
=======
        await send(payload);
        // An older response must never erase a newer recoverable draft.
        try { if (storage.getItem(key) === serialized) storage.removeItem(key); } catch {}
        if (version === revision) onState('saved');
      } catch {
        if (version === revision) {
          pending = payload;
          onState(cached ? 'offline' : 'uncached');
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
        }
      }
    });
    chains.set(key, job);
    job.finally(() => { if (chains.get(key) === job) chains.delete(key); });
    return job;
  }

<<<<<<< HEAD
  const api={recover,update,flush,pause:()=>{paused=true;clearTimeout(timer)},isPending:()=>Boolean(pending||chains.has(key)),
    discard:()=>{clearTimeout(timer);pending=null;paused=false;revision+=1;try{storage.removeItem(key)}catch{}},
    release:()=>{activeSavers.delete(api);return flush();}};
  activeSavers.add(api);
  return api;
=======
  return {recover, update, flush, isPending: () => Boolean(pending || chains.has(key))};
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
}
