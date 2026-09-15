import {TABLES, encodeProject, decodeProject, copyProject, validateProject} from './portable.mjs';
export const API = '/api';
const REQUEST_TIMEOUT_MS = 65000;
const STORAGE_MODE_KEY = 'pressure-room-storage-mode';
const LOCAL_DB_KEY = 'pressure-room-local-db';

function nowIso() { return new Date().toISOString(); }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function safeWindow() { return typeof window !== 'undefined' ? window : null; }

function uid() {
  const w = safeWindow();
  if (w?.crypto?.randomUUID) return w.crypto.randomUUID();
  return `pr_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

export function getStorageMode() {
  const w = safeWindow();
  return w?.localStorage.getItem(STORAGE_MODE_KEY) || '';
}

export function setStorageMode(mode) {
  const w = safeWindow();
  if (!w) return;
  if (!mode) w.localStorage.removeItem(STORAGE_MODE_KEY);
  else w.localStorage.setItem(STORAGE_MODE_KEY, mode);
}

export function clearStorageMode() {
  setStorageMode('');
}

export function isLocalMode() {
  return getStorageMode() === 'local';
}

function blankDb() {
  return {
    projects: [],
    branches: [],
    episodes: [],
    scenes: [],
    characters: [],
    bills: [],
    causal_links: [],
    snapshots: [],
    story_notes: [],
  };
}

function readDb() {
  const w = safeWindow();
  if (!w) return blankDb();
  try {
    const raw = w.localStorage.getItem(LOCAL_DB_KEY);
    if (!raw) return blankDb();
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) ||
        Object.keys(blankDb()).some(key => key in parsed && !Array.isArray(parsed[key]))) {
      throw new Error('Invalid browser database');
    }
    return {...blankDb(), ...parsed};
  } catch {
    throw new Error("This browser’s story data could not be read. It has been left untouched; export or recover the browser data before creating new stories.");
  }
}

function writeDb(db) {
  const w = safeWindow();
  if (!w) return;
  w.localStorage.setItem(LOCAL_DB_KEY, JSON.stringify(db));
}

function touchVersion(row) {
  row.updated_at = nowIso();
  row.version = Number(row.version || 0) + 1;
}

function touchProject(db, projectId) {
  const project = db.projects.find(p => p.id === projectId);
  if (project) touchVersion(project);
}

function parseJsonBody(options = {}) {
  if (!options.body) return {};
  if (options.body instanceof FormData) return options.body;
  try {
    const parsed = JSON.parse(options.body);
    return parsed?.data ?? parsed;
  } catch {
    return {};
  }
}

function findProjectIdForTable(db, table, id) {
  if (table === 'projects') return id;
  const row = db[table]?.find(item => item.id === id);
  if (!row) return null;
  if (row.project_id) return row.project_id;
  if (table === 'scenes' || table === 'causal_links') {
    const ep = db.episodes.find(e => e.id === row.episode_id);
    return ep?.project_id || null;
  }
  if (table === 'branches') return row.project_id || null;
  return null;
}

function sceneHealth(scene) {
  const notes = [];
  const start = (scene.start_state || '').trim();
  const end = (scene.end_state || '').trim();
  if (!start || !end) notes.push('Define both the starting and ending state.');
  else if (start.toLowerCase() === end.toLowerCase()) notes.push('The scene appears to reset rather than transform the story.');
  if (!(scene.choice || '').trim()) notes.push('No decisive choice is recorded.');
  if (!(scene.pressure || '').trim()) notes.push("Pressure is undefined; ask what narrows the character's options.");
  if (!(scene.cut_on || '').trim()) notes.push('Consider ending on a decision, reveal, or irreversible change.');
  return notes;
}

const PRESSURE_MOVES = [
  {name: 'Remove an option', description: "Take away the protagonist's easiest escape route."},
  {name: 'Add a deadline', description: 'Make delay itself costly.'},
  {name: 'Conflicting obligations', description: 'Force two values or promises to collide.'},
  {name: 'Expose prior behavior', description: 'Let an earlier choice become evidence.'},
  {name: 'Reverse status', description: 'Give leverage to someone the protagonist underestimated.'},
  {name: 'Force commitment', description: 'Make half-measures impossible.'},
  {name: 'Create a witness', description: 'Let someone see what was supposed to remain private.'},
  {name: 'Attach collateral', description: 'Make solving the problem hurt someone the character values.'},
];

function storyMri(scenes, bills) {
  const outstanding = bills.filter(b => ['Outstanding', 'Escalating'].includes(b.status)).length;
  let runningPressure = 0;
  let runningMoral = 0;
  return scenes
    .slice()
    .sort((a, b) => Number(a.scene_no || 0) - Number(b.scene_no || 0))
    .map((scene, index) => {
      const i = index + 1;
      const components = ['obstacle', 'pressure', 'choice'].filter(k => (scene[k] || '').trim()).length;
      runningPressure = Math.min(10, Math.max(1, Math.round((runningPressure * 0.55) + components * 1.6 + i * 0.3)));
      runningMoral = Math.max(0, Math.min(10, runningMoral + Number(scene.moral_delta || 0)));
      const optionSpace = Math.max(1, 10 - Math.round(runningPressure * 0.55) - Math.min(3, Math.floor(outstanding / 2)));
      return {
        scene: `S${scene.scene_no}`,
        pressure: runningPressure,
        moral_compromise: runningMoral,
        option_space: optionSpace,
      };
    });
}

function writersRoomQuestions(character, scenes, bills) {
  const q = [];
  const outstanding = bills.filter(b => ['Outstanding', 'Escalating'].includes(b.status));
  if (character) {
    const boundary = character.moral_boundary || 'their stated boundary';
    q.push(`What pressure would make ${character.name} seriously consider violating: ‘${boundary}’?`);
    q.push(`Why can't ${character.name} simply tell the truth or walk away?`);
  }
  if (outstanding.length) q.push(`Could the outstanding bill ‘${outstanding.at(-1).title}’ complicate the next solution instead of introducing a new problem?`);
  if (scenes.length) {
    const last = scenes.at(-1);
    q.push(`Because Scene ${last.scene_no} ends with ‘${last.choice || 'a choice'}’, what must now be true?`);
    if (sceneHealth(last).length) q.push('What is concretely different at the end of the latest scene—knowledge, status, relationship, danger, objective, or moral state?');
  }
  q.push('Which current solution is working too well, and how can the story make that solution stop working?');
  q.push('What choice would be surprising to the audience but inevitable for this character?');
  return q.slice(0, 6);
}

function workspace(db, projectId) {
  const project = db.projects.find(p => p.id === projectId);
  if (!project) throw new Error('Project not found');
  const branches = db.branches.filter(b => b.project_id === projectId);
  const episodes = db.episodes.filter(e => e.project_id === projectId);
  const episodeIds = new Set(episodes.map(e => e.id));
  const scenes = db.scenes.filter(s => episodeIds.has(s.episode_id));
  const characters = db.characters.filter(c => c.project_id === projectId);
  const bills = db.bills.filter(b => b.project_id === projectId);
  const causal_links = db.causal_links.filter(l => episodeIds.has(l.episode_id));
  const snapshots = db.snapshots.filter(s => s.project_id === projectId).map(({payload, ...rest}) => rest);
  return {project, branches, episodes, scenes, characters, bills, causal_links, snapshots, story_notes:db.story_notes.filter(n=>n.project_id===projectId)};
}

function snapshotPayload(db, projectId) {
  const ws = workspace(db, projectId);
  return clone({
    project: ws.project,
    branches: ws.branches,
    episodes: ws.episodes,
    scenes: ws.scenes,
    characters: ws.characters,
    bills: ws.bills,
    causal_links: ws.causal_links,
    story_notes: ws.story_notes,
  });
}

function restoreProjectFromPayload(db, payload) {
  const incoming = clone(payload);
  if (!incoming?.project?.id) throw new Error('Snapshot payload is missing a project id');
  const projectId = incoming.project.id;

  const existingEpisodeIds = new Set(db.episodes.filter(e => e.project_id === projectId).map(e => e.id));

  db.projects = db.projects.filter(p => p.id !== projectId);
  db.branches = db.branches.filter(b => b.project_id !== projectId);
  db.episodes = db.episodes.filter(e => e.project_id !== projectId);
  db.scenes = db.scenes.filter(s => !existingEpisodeIds.has(s.episode_id));
  db.causal_links = db.causal_links.filter(l => !existingEpisodeIds.has(l.episode_id));
  db.characters = db.characters.filter(c => c.project_id !== projectId);
  db.bills = db.bills.filter(b => b.project_id !== projectId);
  db.story_notes = db.story_notes.filter(n => n.project_id !== projectId);

  const ts = nowIso();

  db.projects.push({...incoming.project, updated_at: ts, version: Number(incoming.project.version || 0) + 1});
  for (const b of incoming.branches || []) db.branches.push({...b, updated_at: ts, version: Number(b.version || 0) + 1});
  for (const e of incoming.episodes || []) db.episodes.push({...e, updated_at: ts, version: Number(e.version || 0) + 1});
  for (const s of incoming.scenes || []) db.scenes.push({...s, updated_at: ts, version: Number(s.version || 0) + 1});
  for (const c of incoming.characters || []) db.characters.push({...c, updated_at: ts, version: Number(c.version || 0) + 1});
  for (const b of incoming.bills || []) db.bills.push({...b, updated_at: ts, version: Number(b.version || 0) + 1});
  for (const l of incoming.causal_links || []) db.causal_links.push({...l, version: Number(l.version || 0) + 1});

  db.story_notes.push(...(incoming.story_notes||[]));
  touchProject(db, projectId);
  writeDb(db);
  return projectId;
}

export async function localApi(path, options = {}) {
  const run=()=>localRequest(path,options);
  if (typeof navigator!=='undefined' && navigator.locks) return navigator.locks.request('pressure-room-db',run);
  return run();
}

async function localRequest(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const db = readDb();
  const [pathname] = path.split('?');

  if (pathname === '/projects' && method === 'GET') {
    return clone([...db.projects].sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || '')));
  }

  if (pathname === '/projects' && method === 'POST') {
    const d = parseJsonBody(options);
    const ts = nowIso();
    const id = uid();
    db.projects.push({
      id,
      title: (d.title || 'Untitled Story').trim() || 'Untitled Story',
      premise: d.premise || '',
      theme: d.theme || '',
      created_at: ts,
      updated_at: ts,
      version: 1,
    });
    db.branches.push({
      id: uid(),
      project_id: id,
      name: 'Main',
      is_main: 1,
      created_at: ts,
      updated_at: ts,
      version: 1,
    });
    writeDb(db);
    return {id};
  }

  const projectMatch = pathname.match(/^\/projects\/([^/]+)$/);
  if (projectMatch && method === 'GET') return clone(workspace(db, projectMatch[1]));

  const createCharacterMatch = pathname.match(/^\/projects\/([^/]+)\/characters$/);
  if (createCharacterMatch && method === 'POST') {
    const project_id = createCharacterMatch[1];
    const d = parseJsonBody(options);
    const ts = nowIso();
    const id = uid();
    db.characters.push({
      id, project_id,
      name: d.name || 'New Character',
      role: d.role || '',
      want: d.want || '',
      need: d.need || '',
      core_belief: d.core_belief || '',
      moral_boundary: d.moral_boundary || '',
      fear: d.fear || '',
      temptation: d.temptation || '',
      moral_score: Number(d.moral_score || 0),
      created_at: ts, updated_at: ts, version: 1,
    });
    touchProject(db, project_id);
    writeDb(db);
    return {id};
  }

  const createEpisodeMatch = pathname.match(/^\/projects\/([^/]+)\/episodes$/);
  if (createEpisodeMatch && method === 'POST') {
    const project_id = createEpisodeMatch[1];
    const d = parseJsonBody(options);
    const ts = nowIso();
    const id = uid();
    const mainBranch = db.branches.find(b => b.project_id === project_id && Number(b.is_main) === 1);
    db.episodes.push({
      id,
      project_id,
      branch_id: d.branch_id || mainBranch?.id || '',
      number: Number(d.number || 1),
      title: d.title || 'Untitled Episode',
      logline: d.logline || '',
      status: d.status || 'Outline',
      created_at: ts,
      updated_at: ts,
      version: 1,
    });
    touchProject(db, project_id);
    writeDb(db);
    return {id};
  }

  const createSceneMatch = pathname.match(/^\/episodes\/([^/]+)\/scenes$/);
  if (createSceneMatch && method === 'POST') {
    const episode_id = createSceneMatch[1];
    const episode = db.episodes.find(e => e.id === episode_id);
    if (!episode) throw new Error('Episode not found');
    const d = parseJsonBody(options);
    const ts = nowIso();
    const id = uid();
    db.scenes.push({
      id,
      episode_id,
      scene_no: Number(d.scene_no || 1),
      slugline: d.slugline || '',
      pov_character_id: d.pov_character_id || null,
      opening_behavior: d.opening_behavior || '',
      scene_want: d.scene_want || '',
      obstacle: d.obstacle || '',
      tactic: d.tactic || '',
      pressure: d.pressure || '',
      choice: d.choice || '',
      start_state: d.start_state || '',
      end_state: d.end_state || '',
      cut_on: d.cut_on || '',
      notes: d.notes || '',
      screenplay_text: d.screenplay_text || '',
      moral_delta: Number(d.moral_delta || 0),
      created_at: ts,
      updated_at: ts,
      version: 1,
    });
    touchProject(db, episode.project_id);
    writeDb(db);
    return {id};
  }

  const createLinkMatch = pathname.match(/^\/episodes\/([^/]+)\/links$/);
  if (createLinkMatch && method === 'POST') {
    const episode_id = createLinkMatch[1];
    const episode = db.episodes.find(e => e.id === episode_id);
    if (!episode) throw new Error('Episode not found');
    const d = parseJsonBody(options);
    const relation = String(d.relation || '').toUpperCase();
    if (!d.from_scene_id || !d.to_scene_id) throw new Error('Choose both a source and destination scene');
    if (d.from_scene_id === d.to_scene_id) throw new Error('A scene cannot cause itself');
    if (!['THEREFORE', 'BUT'].includes(relation)) throw new Error('Relationship must be THEREFORE or BUT');
    const existing = db.causal_links.find(
      item => item.episode_id === episode_id && item.from_scene_id === d.from_scene_id && item.relation === relation && item.to_scene_id === d.to_scene_id
    );
    if (existing) throw new Error('That causal connection already exists');
    const id = uid();
    db.causal_links.push({
      id,
      episode_id,
      from_scene_id: d.from_scene_id,
      relation,
      to_scene_id: d.to_scene_id,
      note: String(d.note || '').trim(),
      created_at: nowIso(),
      version: 1,
    });
    touchProject(db, episode.project_id);
    writeDb(db);
    return {id};
  }

  const createBillMatch = pathname.match(/^\/projects\/([^/]+)\/bills$/);
  if (createBillMatch && method === 'POST') {
    const project_id = createBillMatch[1];
    const d = parseJsonBody(options);
    const ts = nowIso();
    const id = uid();
    db.bills.push({
      id,
      project_id,
      episode_id: d.episode_id || null,
      scene_id: d.scene_id || null,
      character_id: d.character_id || null,
      title: d.title || 'Untitled Bill',
      external_cost: d.external_cost || '',
      moral_cost: d.moral_cost || '',
      status: d.status || 'Outstanding',
      payoff_scene_id: d.payoff_scene_id || null,
      created_at: ts,
      updated_at: ts,
      version: 1,
    });
    touchProject(db, project_id);
    writeDb(db);
    return {id};
  }

  const cloneBranchMatch = pathname.match(/^\/projects\/([^/]+)\/branches\/([^/]+)\/clone$/);
  if (cloneBranchMatch && method === 'POST') {
    const [_, project_id, branch_id] = cloneBranchMatch;
    const source = db.branches.find(b => b.id === branch_id && b.project_id === project_id);
    if (!source) throw new Error('Branch not found');
    const body = parseJsonBody(options);
    const ts = nowIso();
    const newBranchId = uid();
    db.branches.push({
      id: newBranchId,
      project_id,
      name: body.name || 'Alternate path',
      is_main: 0,
      created_at: ts,
      updated_at: ts,
      version: 1,
    });

    const eps = db.episodes.filter(e => e.project_id === project_id && e.branch_id === branch_id);
    const epMap = new Map();
    const scMap = new Map();

    for (const ep of eps) {
      const newEpId = uid();
      epMap.set(ep.id, newEpId);
      db.episodes.push({...clone(ep), id: newEpId, branch_id: newBranchId, created_at: ts, updated_at: ts, version: 1});
    }

    for (const sc of db.scenes.filter(s => epMap.has(s.episode_id))) {
      const newSceneId = uid();
      scMap.set(sc.id, newSceneId);
      db.scenes.push({...clone(sc), id: newSceneId, episode_id: epMap.get(sc.episode_id), created_at: ts, updated_at: ts, version: 1});
    }

    for (const link of db.causal_links.filter(l => epMap.has(l.episode_id))) {
      db.causal_links.push({
        ...clone(link),
        id: uid(),
        episode_id: epMap.get(link.episode_id),
        from_scene_id: scMap.get(link.from_scene_id) || link.from_scene_id,
        to_scene_id: scMap.get(link.to_scene_id) || link.to_scene_id,
        created_at: ts,
        version: 1,
      });
    }

    touchProject(db, project_id);
    writeDb(db);
    return {id: newBranchId};
  }

  const createSnapshotMatch = pathname.match(/^\/projects\/([^/]+)\/snapshots$/);
  if (createSnapshotMatch && method === 'POST') {
    const project_id = createSnapshotMatch[1];
    const body = parseJsonBody(options);
    const id = uid();
    db.snapshots.push({
      id,
      project_id,
      label: body.label || 'Snapshot',
      created_at: nowIso(),
      payload: snapshotPayload(db, project_id),
      version: 1,
    });
    touchProject(db, project_id);
    writeDb(db);
    return {id};
  }

  const restoreSnapshotMatch = pathname.match(/^\/snapshots\/([^/]+)\/restore$/);
  if (restoreSnapshotMatch && method === 'POST') {
    const snapshot = db.snapshots.find(s => s.id === restoreSnapshotMatch[1]);
    if (!snapshot) throw new Error('Snapshot not found');
    const project_id = restoreProjectFromPayload(db, snapshot.payload);
    return {project_id};
  }

  const diagnosticsMatch = pathname.match(/^\/episodes\/([^/]+)\/diagnostics$/);
  if (diagnosticsMatch && method === 'GET') {
    const episode = db.episodes.find(e => e.id === diagnosticsMatch[1]);
    if (!episode) throw new Error('Episode not found');
    const scenes = db.scenes.filter(s => s.episode_id === episode.id).sort((a, b) => Number(a.scene_no || 0) - Number(b.scene_no || 0));
    const bills = db.bills.filter(b => b.project_id === episode.project_id);
    const characters = db.characters.filter(c => c.project_id === episode.project_id);
    const protagonist = characters.find(c => String(c.role || '').toLowerCase() === 'protagonist') || characters[0] || null;
    return {
      mri: storyMri(scenes, bills),
      pressure_moves: PRESSURE_MOVES,
      questions: writersRoomQuestions(protagonist, scenes, bills),
    };
  }

  const patchMatch = pathname.match(/^\/([^/]+)\/([^/]+)$/);
  if (patchMatch && method === 'PATCH') {
    const table = patchMatch[1];
    const id = patchMatch[2];
    if (!db[table]) throw new Error('Unsupported table');
    const row = db[table].find(item => item.id === id);
    if (!row) throw new Error('Object not found');
    const expected=options.headers?.['X-Record-Version'];
    if(expected!=null && Number(expected)!==Number(row.version||1)) {
      const error=new Error('This scene changed in another tab. Download your draft before loading the latest scene.');error.status=409;throw error;
    }
    const data=parseJsonBody(options);
    if(Object.keys(data).some(k=>['id','project_id','episode_id','created_at','version','__proto__','constructor','prototype'].includes(k)))throw Error('Record metadata cannot be edited.');
    Object.assign(row,data);
    touchVersion(row);
    const projectId = findProjectIdForTable(db, table, id);
    if (projectId) touchProject(db, projectId);
    writeDb(db);
    return {ok: true, record_version:row.version};
  }

  if (patchMatch && method === 'DELETE') {
    const table = patchMatch[1];
    const id = patchMatch[2];
    if (!db[table]) throw new Error('Unsupported table');
    const projectId = findProjectIdForTable(db, table, id);

    if (table === 'episodes') {
      const removedSceneIds = new Set(db.scenes.filter(s => s.episode_id === id).map(s => s.id));
      db.scenes = db.scenes.filter(s => s.episode_id !== id);
      db.causal_links = db.causal_links.filter(l => l.episode_id !== id);
      db.bills = db.bills.map(b => removedSceneIds.has(b.scene_id) ? {...b, scene_id: null} : b);
    }

    if (table === 'scenes') {
      db.causal_links = db.causal_links.filter(l => l.from_scene_id !== id && l.to_scene_id !== id);
      db.bills = db.bills.map(b => b.scene_id === id ? {...b, scene_id: null} : b);
    }

    if (table === 'branches') {
      const episodeIds = new Set(db.episodes.filter(e => e.branch_id === id).map(e => e.id));
      const sceneIds = new Set(db.scenes.filter(s => episodeIds.has(s.episode_id)).map(s => s.id));
      db.episodes = db.episodes.filter(e => e.branch_id !== id);
      db.scenes = db.scenes.filter(s => !episodeIds.has(s.episode_id));
      db.causal_links = db.causal_links.filter(l => !episodeIds.has(l.episode_id));
      db.bills = db.bills.map(b => sceneIds.has(b.scene_id) ? {...b, scene_id: null} : b);
    }

    db[table] = db[table].filter(item => item.id !== id);
    if (projectId) touchProject(db, projectId);
    writeDb(db);
    return {ok: true};
  }

  const exportMatch=pathname.match(/^\/projects\/([^/]+)\/export\/package$/);
  if(exportMatch){
    const projectId=exportMatch[1];
    const payload={...snapshotPayload(db,projectId),format:'pressure-room',format_version:2,
      story_notes:db.story_notes.filter(n=>n.project_id===projectId),
      snapshots:db.snapshots.filter(n=>n.project_id===projectId)};
    return new Response(encodeProject(payload),{headers:{'Content-Type':'application/zip'}});
  }
  if(pathname==='/import'&&method==='POST'){
    const file=options.body.get('file');
    if(!file||file.size>10*1024*1024)throw Error('Choose a backup no larger than 10 MiB.');
    let incoming=decodeProject(new Uint8Array(await file.arrayBuffer()));
    const mode=new URLSearchParams(path.split('?')[1]).get('mode')||'copy';
    if(mode==='copy')incoming=copyProject(incoming,uid);
    else if(mode!=='replace')throw Error('Unsupported import mode.');
    const pid=incoming.project.id;
    // Keep a recovery snapshot of the old story before a deliberate replacement.
    const retained=db.projects.some(p=>p.id===pid)?{id:uid(),project_id:pid,label:'Before backup restore',created_at:nowIso(),payload:snapshotPayload(db,pid)}:null;
    const oldEpisodes=new Set(db.episodes.filter(e=>e.project_id===pid).map(e=>e.id));
    const otherIds=new Set([...db.projects,...TABLES.flatMap(t=>db[t]||[]),...db.snapshots]
      .filter(r=>r.project_id!==pid&&r.id!==pid&&!oldEpisodes.has(r.episode_id)).map(r=>r.id));
    if([incoming.project,...TABLES.flatMap(t=>incoming[t]),...incoming.snapshots].some(r=>otherIds.has(r.id)))throw Error('Backup IDs collide with another story. Import as a copy.');
    db.snapshots=db.snapshots.filter(s=>s.project_id!==pid);
    db.snapshots.push(...incoming.snapshots,...(retained?[retained]:[]));
    restoreProjectFromPayload(db,incoming);
    return {project_id:pid};
  }

  throw new Error(`Unsupported local request: ${method} ${pathname}`);
}

const revisions=new Map();
const owners=new Map();
export function forgetRevision(projectId){revisions.delete(projectId);}

export async function remoteApi(path, options = {}) {
  const isWrite=!['GET','HEAD','OPTIONS'].includes(options.method||'GET');
  const segments=path.split('?')[0].split('/').filter(Boolean);
  let pid=segments[0]==='projects'?segments[1]:owners.get(segments[1]);
  if(path.startsWith('/import')&&options.body instanceof FormData)pid=options.projectId;
  const revision=options.revision||revisions.get(pid);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${API}${path}`, {
      ...options,
      cache: 'no-store',
      credentials: 'include',
      signal: options.signal || controller.signal,
      headers: {
        ...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
        ...(isWrite&&revision?{'X-Project-Revision':revision}:{}),
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({detail: res.statusText}));
      const message=detail.detail?.message||detail.detail||`Request failed (${res.status})`;
      const error=new Error(message);error.status=res.status;error.code=detail.detail?.code;throw error;
    }
    const type = res.headers.get('content-type') || '';
    if(!type.includes('application/json'))return res;
    const data=await res.json();
    if(data.project){
      pid=data.project.id;
      for(const table of ['projects',...TABLES,'snapshots'])for(const row of table==='projects'?[data.project]:(data[table]||[]))owners.set(row.id,pid);
    }
    if(data.revision&&(data.project_id||pid))revisions.set(data.project_id||pid,data.revision);
    return data;
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('Pressure Room API did not respond in time. Your request may still have completed; check the saved story before retrying.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function shouldForceRemote(path) {
  return path.startsWith('/google/') || path === '/health' || path === '/ready';
}

export async function api(path, options = {}) {
  if (isLocalMode() && !shouldForceRemote(path)) {
    return localApi(path, options);
  }
  return remoteApi(path, options);
}

export const patch = (table, id, data) => api(`/${table}/${id}`, {method: 'PATCH', body: JSON.stringify({data})});
export const remove = (table, id) => api(`/${table}/${id}`, {method: 'DELETE'});
export const create = (path, data) => api(path, {method: 'POST', body: JSON.stringify({data})});
