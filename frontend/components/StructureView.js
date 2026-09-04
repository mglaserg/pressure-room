'use client';
import {useEffect, useMemo, useState} from 'react';
import {api, create, patch, remove} from '@/lib/api';

export default function StructureView({workspace, project, branch, episode, reload}) {
  const [section,setSection] = useState('story');
  const items = [['story','Story'],['characters','Characters'],['causality','Causality'],['bills','Bills'],['branches','Branches']];
  return <div className="focus-page">
    <div className="subnav">{items.map(([id,label])=><button key={id} className={section===id?'active':''} onClick={()=>setSection(id)}>{label}</button>)}</div>
    {section==='story'&&<Story project={project} episode={episode} reload={reload}/>} 
    {section==='characters'&&<Characters workspace={workspace} project={project} reload={reload}/>} 
    {section==='causality'&&<Causality workspace={workspace} episode={episode} reload={reload}/>} 
    {section==='bills'&&<Bills workspace={workspace} project={project} episode={episode} reload={reload}/>} 
    {section==='branches'&&<Branches workspace={workspace} project={project} branch={branch} reload={reload}/>} 
  </div>
}

function Story({project,episode,reload}) {
  const [p,setP]=useState(project);
  const [message,setMessage]=useState('');
  useEffect(()=>setP(project),[project.id,project.version]);
  async function save(){
    setMessage('');
    try {
      await patch('projects',project.id,{title:p.title,premise:p.premise,theme:p.theme});
      if(episode) await patch('episodes',episode.id,{title:episode.title,logline:episode.logline});
      await reload();
      setMessage('Saved.');
    } catch (err) { setMessage(err.message); }
  }
  return <section className="focus-card"><div className="eyebrow">Story spine</div><h1>What is this story really about?</h1><p className="muted">Keep the front door simple. Deep diagnostics live elsewhere.</p>
    <div className="form-stack"><label>Title<input value={p.title||''} onChange={e=>setP({...p,title:e.target.value})}/></label><label>Premise<textarea rows="4" value={p.premise||''} onChange={e=>setP({...p,premise:e.target.value})}/></label><label>Theme / dramatic question<input value={p.theme||''} onChange={e=>setP({...p,theme:e.target.value})}/></label><div className="form-actions"><button className="button" onClick={save}>Save story</button>{message&&<span className="form-message">{message}</span>}</div></div>
  </section>
}

const CHARACTER_FIELDS = ['name','role','want','need','core_belief','moral_boundary','fear','temptation','moral_score'];
function characterPayload(draft) {
  return Object.fromEntries(CHARACTER_FIELDS.map(k=>[k, k==='moral_score' ? Number(draft?.[k] || 0) : (draft?.[k] || '')]));
}

function Characters({workspace,project,reload}) {
  const chars=workspace.characters||[];
  const [selectedId,setSelectedId]=useState(chars[0]?.id||'');
  const [draft,setDraft]=useState(chars[0]||{});
  const [creating,setCreating]=useState(false);
  const [newDraft,setNewDraft]=useState({name:'',role:'',want:'',need:'',core_belief:'',moral_boundary:'',fear:'',temptation:'',moral_score:0});
  const [message,setMessage]=useState('');
  const selected=chars.find(c=>c.id===selectedId)||chars[0]||null;

  useEffect(()=>{
    if (!chars.length) { setSelectedId(''); setDraft({}); return; }
    if (!chars.some(c=>c.id===selectedId)) setSelectedId(chars[0].id);
  },[chars,selectedId]);
  useEffect(()=>{ if(selected) setDraft({...selected}); },[selected?.id,selected?.version]);

  const choose=id=>{setCreating(false);setMessage('');setSelectedId(id);const found=chars.find(c=>c.id===id);if(found)setDraft({...found})};
  async function add(){
    setMessage('');
    if(!newDraft.name.trim()){setMessage('Give the character a name first.');return;}
    try {
      const r=await create(`/projects/${project.id}/characters`,characterPayload(newDraft));
      setCreating(false);
      setNewDraft({name:'',role:'',want:'',need:'',core_belief:'',moral_boundary:'',fear:'',temptation:'',moral_score:0});
      await reload();
      setSelectedId(r.id);
      setMessage('Character created.');
    } catch(err){setMessage(err.message)}
  }
  async function save(){
    if(!selected)return;
    setMessage('');
    if(!draft.name?.trim()){setMessage('A character needs a name.');return;}
    try {
      await patch('characters',selected.id,characterPayload(draft));
      await reload();
      setMessage('Character saved.');
    } catch(err){setMessage(err.message)}
  }
  async function destroy(){
    if(!selected)return;
    if(!window.confirm(`Delete ${selected.name}? This cannot be undone.`)) return;
    try {
      await remove('characters',selected.id);
      setSelectedId('');
      setMessage('Character deleted.');
      await reload();
    } catch(err){setMessage(err.message)}
  }

  return <section className="split-focus"><aside className="compact-list"><div className="rail-head"><span>Characters</span><button className="mini-button" onClick={()=>{setCreating(true);setMessage('')}}>＋</button></div>{chars.map(c=><button key={c.id} className={!creating&&c.id===selected?.id?'active':''} onClick={()=>choose(c.id)}><b>{c.name}</b><span>{c.role||'Character'}</span></button>)}<button className={creating?'active add-character-rail':''} onClick={()=>{setCreating(true);setMessage('')}}><b>＋ New character</b><span>Start a moral spine</span></button></aside>
    <div className="focus-card">{creating?<><div className="eyebrow">New character</div><h1>Who is entering the pressure room?</h1><p className="muted">Start with the essentials. The deeper fields can wait.</p><CharacterForm draft={newDraft} setDraft={setNewDraft}/><div className="form-actions"><button className="button" onClick={add}>Create character</button><button className="ghost" onClick={()=>setCreating(false)}>Cancel</button>{message&&<span className="form-message">{message}</span>}</div></>:selected?<><div className="eyebrow">Moral spine</div><h1>{selected.name}</h1><CharacterForm draft={draft} setDraft={setDraft}/><div className="form-actions"><button className="button" onClick={save}>Save character</button><button className="ghost danger-ghost" onClick={destroy}>Delete</button>{message&&<span className="form-message">{message}</span>}</div></>:<div className="empty-state"><div><h2>Add a character.</h2><p className="muted">Give the story someone whose choices can narrow.</p><button className="button" onClick={()=>setCreating(true)}>＋ New character</button></div></div>}</div>
  </section>
}

function CharacterForm({draft,setDraft}) {
  return <div className="form-stack character-form">
    <div className="two-up"><label>Name<input value={draft.name||''} onChange={e=>setDraft({...draft,name:e.target.value})}/></label><label>Role<input value={draft.role||''} placeholder="Protagonist" onChange={e=>setDraft({...draft,role:e.target.value})}/></label></div>
    <label>Want<textarea rows="2" placeholder="What are they actively trying to get?" value={draft.want||''} onChange={e=>setDraft({...draft,want:e.target.value})}/></label>
    <label>Moral boundary<textarea rows="2" placeholder="What will they NOT do?" value={draft.moral_boundary||''} onChange={e=>setDraft({...draft,moral_boundary:e.target.value})}/></label>
    <label>Moral compromise <span className="range-value">{Number(draft.moral_score||0)}/10</span><input type="range" min="0" max="10" value={Number(draft.moral_score||0)} onChange={e=>setDraft({...draft,moral_score:Number(e.target.value)})}/></label>
    <details className="advanced-details"><summary>Deeper character work</summary><div className="form-stack"><Text label="Need" k="need" d={draft} set={setDraft}/><Text label="Core belief" k="core_belief" d={draft} set={setDraft}/><Text label="Fear" k="fear" d={draft} set={setDraft}/><Text label="Temptation" k="temptation" d={draft} set={setDraft}/></div></details>
  </div>
}

function Causality({workspace,episode,reload}) {
  const scenes=useMemo(()=>((workspace.scenes||[]).filter(s=>s.episode_id===episode?.id).sort((a,b)=>a.scene_no-b.scene_no)),[workspace,episode?.id]);
  const links=(workspace.causal_links||[]).filter(l=>l.episode_id===episode?.id);
  const [form,setForm]=useState({from_scene_id:'',relation:'THEREFORE',to_scene_id:'',note:''});
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState(false);

  useEffect(()=>{
    if(scenes.length<2){setForm(f=>({...f,from_scene_id:scenes[0]?.id||'',to_scene_id:''}));return;}
    setForm(f=>{
      const from=scenes.some(s=>s.id===f.from_scene_id)?f.from_scene_id:scenes[0].id;
      const to=scenes.some(s=>s.id===f.to_scene_id)&&f.to_scene_id!==from?f.to_scene_id:(scenes.find(s=>s.id!==from)?.id||'');
      return {...f,from_scene_id:from,to_scene_id:to};
    });
  },[episode?.id,scenes.length]);

  function changeFrom(id){
    setMessage('');
    setForm(f=>({...f,from_scene_id:id,to_scene_id:f.to_scene_id===id?(scenes.find(s=>s.id!==id)?.id||''):f.to_scene_id}));
  }
  async function add(){
    setMessage('');
    if(!episode||!form.from_scene_id||!form.to_scene_id){setMessage('Choose both scenes.');return;}
    if(form.from_scene_id===form.to_scene_id){setMessage('A scene cannot cause itself. Choose a different destination scene.');return;}
    const duplicate=links.some(l=>l.from_scene_id===form.from_scene_id&&l.to_scene_id===form.to_scene_id&&l.relation===form.relation);
    if(duplicate){setMessage('That causal connection already exists. You can remove it below before replacing it.');return;}
    setBusy(true);
    try {
      await create(`/episodes/${episode.id}/links`,{...form,note:form.note.trim()});
      setForm(f=>({...f,note:''}));
      await reload();
      setMessage('Connection added.');
    } catch(err){setMessage(err.message)} finally {setBusy(false)}
  }
  async function destroy(link){
    try { await remove('causal_links',link.id); await reload(); setMessage('Connection removed.'); }
    catch(err){setMessage(err.message)}
  }
  const sceneLabel=id=>{const s=scenes.find(x=>x.id===id);return s?`S${s.scene_no} · ${s.slugline||'Untitled scene'}`:'Scene'};

  if(!episode) return <section className="focus-card"><div className="empty-state"><div><h2>Choose an episode.</h2><p className="muted">Causality is built episode by episode.</p></div></div></section>;

  return <section className="focus-card causality-card"><div className="eyebrow">Therefore / But</div><h1>Does each scene force the next?</h1><p className="muted">Connect choices and consequences. The note explains the causal logic; it is optional, but useful.</p>
    <div className="causal-chain">{scenes.map(s=>{const outgoing=links.filter(l=>l.from_scene_id===s.id);return <div key={s.id} className="causal-node"><div className="scene-chip">S{s.scene_no}</div><div><b>{s.slugline||'Untitled scene'}</b><p>{s.choice||'No choice recorded yet.'}</p></div>{outgoing.map(link=><div key={link.id} className={`causal-arrow ${link.relation.toLowerCase()}`}><b>{link.relation} → {sceneLabel(link.to_scene_id)}</b>{link.note&&<span>{link.note}</span>}</div>)}</div>})}</div>

    {scenes.length>1?<div className="causal-form-card">
      <div className="causal-form-head"><div><div className="eyebrow">Add connection</div><h3>What forces what?</h3></div></div>
      <div className="causal-form-grid">
        <label>From scene<select value={form.from_scene_id} onChange={e=>changeFrom(e.target.value)}>{scenes.map(s=><option key={s.id} value={s.id}>S{s.scene_no} · {s.slugline||'Untitled'}</option>)}</select></label>
        <label>Relationship<select value={form.relation} onChange={e=>{setMessage('');setForm({...form,relation:e.target.value})}}><option value="THEREFORE">THEREFORE</option><option value="BUT">BUT</option></select></label>
        <label>To scene<select value={form.to_scene_id} onChange={e=>{setMessage('');setForm({...form,to_scene_id:e.target.value})}}>{scenes.filter(s=>s.id!==form.from_scene_id).map(s=><option key={s.id} value={s.id}>S{s.scene_no} · {s.slugline||'Untitled'}</option>)}</select></label>
      </div>
      <label className="causal-note">Why does this follow?<textarea rows="3" placeholder="Because this choice creates… / But this solution causes…" value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/></label>
      <div className="form-actions"><button className="button" disabled={busy} onClick={add}>{busy?'Connecting…':'Connect scenes'}</button>{message&&<span className="form-message">{message}</span>}</div>
    </div>:<div className="empty-state compact-empty"><div><h2>Add one more scene.</h2><p className="muted">You need at least two scenes to create a causal connection.</p></div></div>}

    {links.length>0&&<div className="existing-links"><div className="eyebrow">Connections</div>{links.map(link=><div className="link-row" key={link.id}><div><b>{sceneLabel(link.from_scene_id)} <span className={link.relation==='BUT'?'relation-but':'relation-therefore'}>{link.relation}</span> {sceneLabel(link.to_scene_id)}</b>{link.note&&<span>{link.note}</span>}</div><button className="mini-button danger-ghost" title="Remove connection" onClick={()=>destroy(link)}>×</button></div>)}</div>}
  </section>
}

function Bills({workspace,project,episode,reload}) {
  const bills=workspace.bills||[]; const [show,setShow]=useState(false); const [d,setD]=useState({title:'',external_cost:'',moral_cost:'',status:'Outstanding',episode_id:episode?.id||null});
  async function add(){if(!d.title)return;await create(`/projects/${project.id}/bills`,d);setD({title:'',external_cost:'',moral_cost:'',status:'Outstanding',episode_id:episode?.id||null});setShow(false);await reload()}
  return <section className="focus-card"><div className="title-row"><div><div className="eyebrow">Cause & cost</div><h1>Bill Ledger</h1></div><button className="button" onClick={()=>setShow(v=>!v)}>＋ Record bill</button></div>{show&&<div className="bill-form"><label>Bill<input value={d.title} onChange={e=>setD({...d,title:e.target.value})}/></label><label>External bill<textarea rows="2" value={d.external_cost} onChange={e=>setD({...d,external_cost:e.target.value})}/></label><label>Moral cost<textarea rows="2" value={d.moral_cost} onChange={e=>setD({...d,moral_cost:e.target.value})}/></label><button className="button" onClick={add}>Save bill</button></div>}
    <div className="bill-list">{bills.map(b=><article key={b.id} className="bill-card"><div className="bill-status">{b.status}</div><h3>{b.title}</h3><div className="two-up"><p><span>External</span>{b.external_cost||'—'}</p><p><span>Moral</span>{b.moral_cost||'—'}</p></div><select value={b.status} onChange={async e=>{await patch('bills',b.id,{status:e.target.value});reload()}}><option>Outstanding</option><option>Escalating</option><option>Paid</option><option>Abandoned</option></select></article>)}</div>
  </section>
}

function Branches({workspace,project,branch,reload}) {
  const [name,setName]=useState('Alternate path'); const [label,setLabel]=useState('Before rewrite');
  async function clone(){if(!branch)return;await api(`/projects/${project.id}/branches/${branch.id}/clone`,{method:'POST',body:JSON.stringify({name})});await reload()}
  async function snapshot(){await api(`/projects/${project.id}/snapshots`,{method:'POST',body:JSON.stringify({label})});await reload()}
  return <section className="focus-card"><div className="eyebrow">Story laboratory</div><h1>Explore without breaking the main story.</h1><div className="two-up"><div className="inner-card"><h3>Branches</h3>{workspace.branches.map(b=><div className="list-row" key={b.id}><b>{b.name}</b><span>{b.is_main?'Main':'Alternate'}</span></div>)}<div className="inline-form"><input value={name} onChange={e=>setName(e.target.value)}/><button className="button" onClick={clone}>Branch current path</button></div></div><div className="inner-card"><h3>Snapshots</h3>{(workspace.snapshots||[]).map(s=><div className="list-row" key={s.id}><b>{s.label}</b><span>{new Date(s.created_at).toLocaleDateString()}</span></div>)}<div className="inline-form"><input value={label} onChange={e=>setLabel(e.target.value)}/><button className="button" onClick={snapshot}>Save snapshot</button></div></div></div>
  </section>
}

function Text({label,k,d,set}){return <label>{label}<textarea rows="2" value={d[k]||''} onChange={e=>set({...d,[k]:e.target.value})}/></label>}
