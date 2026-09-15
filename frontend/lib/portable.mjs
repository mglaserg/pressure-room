import {zipSync, unzipSync, strToU8, strFromU8} from 'fflate';

export const TABLES = ['branches','characters','episodes','scenes','causal_links','bills','story_notes'];
const MAX_JSON = 32*1024*1024;
const MAX_ZIP = 10*1024*1024;
const FIELDS = {
  project:'id title premise theme created_at updated_at version',
  branches:'id project_id name is_main created_at',
  characters:'id project_id name role want need core_belief moral_boundary fear temptation moral_score created_at updated_at version',
  episodes:'id project_id branch_id number title logline status created_at updated_at version',
  scenes:'id episode_id scene_no slugline pov_character_id opening_behavior scene_want obstacle tactic pressure choice start_state end_state cut_on notes screenplay_text moral_delta created_at updated_at version',
  causal_links:'id episode_id from_scene_id relation to_scene_id note created_at',
  bills:'id project_id episode_id scene_id character_id title external_cost moral_cost status payoff_scene_id created_at updated_at version',
  story_notes:'id project_id object_type object_id body created_at',
};

function record(value, table) {
  if (!value || typeof value!=='object' || Array.isArray(value)) throw Error('Invalid project record.');
  const out={};
  for (const key of FIELDS[table].split(' ')) {
    if (!(key in value)) continue;
    const v=value[key];
    if (v!==null && !['string','number'].includes(typeof v)) throw Error(`Invalid value for ${key}.`);
    if (typeof v==='number'&&!Number.isFinite(v)) throw Error('Invalid number.');
    out[key]=v;
  }
  if (typeof out.id!=='string'||!out.id||out.id.length>200) throw Error('Missing or invalid record ID.');
  for (const key of FIELDS[table].split(' ')) {
    if (key==='id'||key.endsWith('_id')) {
      if (out[key]!=null && (typeof out[key]!=='string'||out[key].length>200)) throw Error('Invalid relationship identifier.');
    }
  }
  return out;
}

export function validateProject(input, depth=0) {
  if (!input || input.format!=='pressure-room' || ![1,2].includes(input.format_version||1)) throw Error('Choose a Pressure Room project backup.');
  const out={format:'pressure-room',format_version:2,project:record(input.project,'project')};
  if (typeof out.project.title!=='string'||!out.project.title.trim()) throw Error('A story title is required.');
  const ids=new Set([out.project.id]);
  for (const table of TABLES) {
    const list=input[table]||[];
    if (!Array.isArray(list)||list.length>20000) throw Error('Too many project records.');
    out[table]=list.map(row=>record(row,table));
    for (const row of out[table]) {
      if(ids.has(row.id)) throw Error('Duplicate record ID.');
      ids.add(row.id);
      if('project_id' in row&&row.project_id!==out.project.id) throw Error('Record belongs to a different story.');
    }
  }
  const maps=Object.fromEntries(TABLES.map(t=>[t,new Map(out[t].map(r=>[r.id,r]))]));
  const ref=(table,id)=>{if(id!=null&&!maps[table].has(id))throw Error('Backup contains a broken relationship.');};
  for(const ep of out.episodes){if(!ep.branch_id)throw Error('Episode is missing its path.');ref('branches',ep.branch_id);}
  for(const scene of out.scenes){if(!scene.episode_id)throw Error('Scene is missing its episode.');ref('episodes',scene.episode_id);ref('characters',scene.pov_character_id);}
  for(const link of out.causal_links){
    ref('episodes',link.episode_id);ref('scenes',link.from_scene_id);ref('scenes',link.to_scene_id);
    if(!['BUT','THEREFORE'].includes(link.relation)||link.from_scene_id===link.to_scene_id||
       maps.scenes.get(link.from_scene_id)?.episode_id!==link.episode_id||maps.scenes.get(link.to_scene_id)?.episode_id!==link.episode_id)throw Error('Invalid causal connection.');
  }
  for(const bill of out.bills){ref('episodes',bill.episode_id);ref('characters',bill.character_id);ref('scenes',bill.scene_id);ref('scenes',bill.payoff_scene_id);}
  out.snapshots=[];
  if(!depth){
    if(!Array.isArray(input.snapshots||[])||(input.snapshots||[]).length>100)throw Error('Backup exceeds 100 snapshots.');
    for(const snap of input.snapshots||[]){
      const nested=snap.payload || JSON.parse(snap.payload_json||'null');
      const checked=validateProject({...nested,format:'pressure-room',format_version:2},1);
      if(checked.project.id!==out.project.id)throw Error('Snapshot belongs to a different story.');
      if(typeof snap.id!=='string'||ids.has(snap.id))throw Error('Invalid snapshot ID.');
      ids.add(snap.id);
      out.snapshots.push({id:snap.id,project_id:out.project.id,label:String(snap.label||'Snapshot'),created_at:String(snap.created_at||''),payload:checked});
    }
  }
  return out;
}

export function encodeProject(input) {
  const data=validateProject(input);
  data.snapshots=data.snapshots.map(({payload,...s})=>({...s,payload_json:JSON.stringify(payload)}));
  const json=strToU8(JSON.stringify(data));
  if(json.length>MAX_JSON)throw Error('Project exceeds the 32 MiB backup limit.');
  const zip=zipSync({'project.json':json},{level:6});
  if(zip.length>MAX_ZIP)throw Error('Project exceeds the 10 MiB backup limit.');
  return zip;
}

export function decodeProject(bytes) {
  if(bytes.length>MAX_ZIP)throw Error('Backup exceeds 10 MiB.');
  let seen=0;
  const files=unzipSync(bytes,{filter:file=>{
    if(file.name!=='project.json')return false;
    if(++seen>1||file.originalSize>MAX_JSON)throw Error('Duplicate or oversized project data.');
    return true;
  }});
  if(!files['project.json']||files['project.json'].length>MAX_JSON)throw Error('Missing or oversized project data.');
  return validateProject(JSON.parse(strFromU8(files['project.json'])));
}

export function copyProject(input, uid) {
  const data=validateProject(input);
  // Each snapshot has its own historical row set, but shares the new project ID.
  const projectId=uid();
  function remap(p){
    const mapping=new Map([[p.project.id,projectId]]);
    for(const t of TABLES)for(const r of p[t])mapping.set(r.id,uid());
    const mapped=id=>id==null?null:mapping.get(id)||id;
    const result={...p,project:{...p.project,id:projectId,title:p.project.title+' (imported)'},snapshots:[]};
    for(const t of TABLES)result[t]=p[t].map(row=>Object.fromEntries(Object.entries(row).map(([k,v])=>[k,k==='id'||k.endsWith('_id')?mapped(v):v])));
    return result;
  }
  const result=remap(data);
  result.snapshots=data.snapshots.map(s=>({...s,id:uid(),project_id:projectId,payload:remap(s.payload)}));
  return result;
}

export function downloadBlob(data, filename, type='application/zip') {
  const url=URL.createObjectURL(new Blob([data],{type}));
  const a=document.createElement('a');a.href=url;a.download=filename;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
