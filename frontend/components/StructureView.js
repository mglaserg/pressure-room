'use client';
import {useEffect, useMemo, useState} from 'react';
import {api, create, patch, remove} from '@/lib/api';

const SECTIONS = [
  ['story','Story','Premise & theme'],
  ['characters','Characters','Moral spines'],
  ['causality','Causality','Therefore / But'],
  ['bills','Bills','Cause & cost'],
  ['branches','Branches','Alternate paths'],
];

export default function StructureView({workspace, project, branch, episode, reload}) {
  const [section,setSection] = useState('story');
  return <div className="focus-page">
    <div className="subnav structure-subnav">{SECTIONS.map(([id,label,note])=><button key={id} className={section===id?'active':''} onClick={()=>setSection(id)}><b>{label}</b><small>{note}</small></button>)}</div>
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
      setMessage('Story spine saved.');
    } catch (err) { setMessage(err.message); }
  }
  return <section className="focus-card story-focus">
    <div className="focus-heading"><div><div className="eyebrow">Story spine</div><h1>What is the story really about?</h1><p className="muted">Keep the front door simple. The deeper machinery can stay out of sight until it earns its way in.</p></div><div className="story-monogram">{(p.title||'PR').slice(0,2).toUpperCase()}</div></div>
    <div className="form-stack editorial-form">
      <label>Title<input className="title-field" value={p.title||''} onChange={e=>setP({...p,title:e.target.value})}/></label>
      <label>Premise<textarea rows="5" value={p.premise||''} placeholder="A character wants something. Getting it will cost them." onChange={e=>setP({...p,premise:e.target.value})}/></label>
      <label>Theme / dramatic question<input value={p.theme||''} placeholder="What truth is the story arguing with?" onChange={e=>setP({...p,theme:e.target.value})}/></label>
      <div className="form-actions"><button className="button" onClick={save}>Save story</button>{message&&<span className="form-message">{message}</span>}</div>
    </div>
  </section>
}

const CHARACTER_FIELDS = ['name','role','want','need','core_belief','moral_boundary','fear','temptation','moral_score'];
function characterPayload(draft) {
  return Object.fromEntries(CHARACTER_FIELDS.map(k=>[k, k==='moral_score' ? Number(draft?.[k] || 0) : (draft?.[k] || '')]));
}
function initials(name=''){return name.split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join('').toUpperCase()||'—'}

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

  return <section className="split-focus character-workspace">
    <aside className="compact-list character-list">
      <div className="rail-head"><div><span>Characters</span><small>{chars.length} in the room</small></div><button className="mini-button" onClick={()=>{setCreating(true);setMessage('')}}>＋</button></div>
      {chars.map(c=><button key={c.id} className={!creating&&c.id===selected?.id?'active':''} onClick={()=>choose(c.id)}><span className="character-avatar small">{initials(c.name)}</span><span className="character-list-copy"><b>{c.name}</b><small>{c.role||'Character'}</small></span><i className="compromise-dot" style={{'--score':Number(c.moral_score||0)}}/></button>)}
      <button className={creating?'active add-character-rail':'add-character-rail'} onClick={()=>{setCreating(true);setMessage('')}}><span className="character-avatar small">＋</span><span className="character-list-copy"><b>New character</b><small>Start a moral spine</small></span></button>
    </aside>

    <div className="focus-card character-focus">
      {creating?<>
        <CharacterHero draft={newDraft} creating/>
        <p className="muted character-intro">Start with the want and the line they believe they will never cross. The rest can emerge later.</p>
        <CharacterForm draft={newDraft} setDraft={setNewDraft}/>
        <div className="form-actions"><button className="button" onClick={add}>Create character</button><button className="quiet-action" onClick={()=>setCreating(false)}>Cancel</button>{message&&<span className="form-message">{message}</span>}</div>
      </>:selected?<>
        <CharacterHero draft={draft}/>
        <CharacterForm draft={draft} setDraft={setDraft}/>
        <div className="form-actions"><button className="button" onClick={save}>Save character</button><button className="quiet-action danger-ghost" onClick={destroy}>Delete character</button>{message&&<span className="form-message">{message}</span>}</div>
      </>:<div className="empty-state"><div className="empty-orbit"><span>P</span><i/><span>R</span></div><h2>Who is entering the room?</h2><p className="muted">Give the story someone whose choices can narrow.</p><button className="button" onClick={()=>setCreating(true)}>Create a character</button></div>}
    </div>
  </section>
}

function CharacterHero({draft,creating=false}){
  const score=Number(draft.moral_score||0);
  return <header className="character-hero">
    <div className="character-avatar">{creating?'＋':initials(draft.name)}</div>
    <div className="character-hero-copy"><div className="eyebrow">{creating?'New character':'Moral spine'}</div><h1>{draft.name||'Unnamed character'}</h1><p>{draft.role||'Character'}</p>{draft.core_belief&&<blockquote>“{draft.core_belief}”</blockquote>}</div>
    <div className="moral-gauge"><span>Compromise</span><b>{score}<small>/10</small></b><div><i style={{width:`${score*10}%`}}/></div></div>
  </header>
}

function CharacterForm({draft,setDraft}) {
  return <div className="form-stack character-form">
    <div className="two-up"><label>Name<input value={draft.name||''} onChange={e=>setDraft({...draft,name:e.target.value})}/></label><label>Role<input value={draft.role||''} placeholder="Protagonist" onChange={e=>setDraft({...draft,role:e.target.value})}/></label></div>
    <div className="character-core-grid">
      <label className="character-core want-card"><span className="field-label"><b>Want</b><small>What pulls them forward?</small></span><textarea rows="3" placeholder="What are they actively trying to get?" value={draft.want||''} onChange={e=>setDraft({...draft,want:e.target.value})}/></label>
      <label className="character-core boundary-card"><span className="field-label"><b>Moral boundary</b><small>The line they believe they won’t cross</small></span><textarea rows="3" placeholder="What will they NOT do?" value={draft.moral_boundary||''} onChange={e=>setDraft({...draft,moral_boundary:e.target.value})}/></label>
    </div>
    <label className="range-field"><span>Moral compromise <b>{Number(draft.moral_score||0)}/10</b></span><input type="range" min="0" max="10" value={Number(draft.moral_score||0)} onChange={e=>setDraft({...draft,moral_score:Number(e.target.value)})}/></label>
    <details className="advanced-details"><summary><span>Deeper character work</span><small>Need · belief · fear · temptation</small></summary><div className="form-grid"><Text label="Need" k="need" d={draft} set={setDraft}/><Text label="Core belief" k="core_belief" d={draft} set={setDraft}/><Text label="Fear" k="fear" d={draft} set={setDraft}/><Text label="Temptation" k="temptation" d={draft} set={setDraft}/></div></details>
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
    if(form.from_scene_id===form.to_scene_id){setMessage('A scene cannot cause itself.');return;}
    const duplicate=links.some(l=>l.from_scene_id===form.from_scene_id&&l.to_scene_id===form.to_scene_id&&l.relation===form.relation);
    if(duplicate){setMessage('That connection already exists.');return;}
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

  if(!episode) return <section className="focus-card"><div className="empty-state"><h2>Choose an episode.</h2><p className="muted">Causality is built episode by episode.</p></div></section>;

  return <section className="causality-layout">
    <div className="causal-map-panel">
      <div className="focus-heading compact-heading"><div><div className="eyebrow">Therefore / But</div><h1>The story should pull itself forward.</h1><p className="muted">A scene earns its place when a choice creates the next problem.</p></div><div className="causal-count"><b>{links.length}</b><span>connections</span></div></div>
      <div className="causal-map">
        {scenes.length?scenes.map((s,index)=>{
          const outgoing=links.filter(l=>l.from_scene_id===s.id);
          return <div key={s.id} className="causal-map-item">
            <article className="causal-scene-card">
              <div className="causal-scene-no">{String(s.scene_no).padStart(2,'0')}</div>
              <div className="causal-scene-copy"><span className="eyebrow">Scene</span><h3>{s.slugline||'Untitled scene'}</h3><p>{s.choice||s.scene_want||'No choice recorded yet.'}</p></div>
              {(s.moral_delta||0)!==0&&<span className="moral-delta">{s.moral_delta>0?'+':''}{s.moral_delta} moral</span>}
            </article>
            {outgoing.length>0?<div className="causal-connections">{outgoing.map(link=><div key={link.id} className={`causal-ribbon ${link.relation.toLowerCase()}`}><div className="ribbon-line"><i/><span>{link.relation}</span><i/></div><div className="ribbon-copy"><b>→ {sceneLabel(link.to_scene_id)}</b>{link.note&&<p>{link.note}</p>}</div><button className="link-remove" title="Remove connection" onClick={()=>destroy(link)}>×</button></div>)}</div>:index<scenes.length-1?<div className="causal-gap"><span>Unconnected</span></div>:null}
          </div>
        }):<div className="empty-state compact-empty"><h2>No scenes on the wall yet.</h2><p className="muted">Write the first scene, then come back to connect the chain.</p></div>}
      </div>
    </div>

    <aside className="causal-builder">
      <div className="eyebrow">Add connection</div><h2>What forces what?</h2><p className="muted">Use <b>THEREFORE</b> when the prior choice causes the next move. Use <b>BUT</b> when the solution creates a new problem.</p>
      {scenes.length>1?<div className="causal-form-card">
        <label>From<select value={form.from_scene_id} onChange={e=>changeFrom(e.target.value)}>{scenes.map(s=><option key={s.id} value={s.id}>S{s.scene_no} · {s.slugline||'Untitled'}</option>)}</select></label>
        <div className="relation-switch" role="group" aria-label="Relationship"><button className={form.relation==='THEREFORE'?'active therefore':''} onClick={()=>{setMessage('');setForm({...form,relation:'THEREFORE'})}}>THEREFORE</button><button className={form.relation==='BUT'?'active but':''} onClick={()=>{setMessage('');setForm({...form,relation:'BUT'})}}>BUT</button></div>
        <label>To<select value={form.to_scene_id} onChange={e=>{setMessage('');setForm({...form,to_scene_id:e.target.value})}}>{scenes.filter(s=>s.id!==form.from_scene_id).map(s=><option key={s.id} value={s.id}>S{s.scene_no} · {s.slugline||'Untitled'}</option>)}</select></label>
        <label className="causal-note">Why does this follow?<textarea rows="4" placeholder="Because this choice creates…" value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/></label>
        <button className="button full" disabled={busy} onClick={add}>{busy?'Connecting…':'Connect scenes'}</button>
        {message&&<span className="form-message">{message}</span>}
      </div>:<div className="empty-state compact-empty"><h3>Add one more scene.</h3><p className="muted">Two scenes are needed to create a causal link.</p></div>}
    </aside>
  </section>
}

function Bills({workspace,project,episode,reload}) {
  const bills=workspace.bills||[];
  const [show,setShow]=useState(false);
  const [d,setD]=useState({title:'',external_cost:'',moral_cost:'',status:'Outstanding',episode_id:episode?.id||null});
  async function add(){if(!d.title)return;await create(`/projects/${project.id}/bills`,d);setD({title:'',external_cost:'',moral_cost:'',status:'Outstanding',episode_id:episode?.id||null});setShow(false);await reload()}
  return <section className="focus-card bills-focus">
    <div className="title-row"><div><div className="eyebrow">Cause & cost</div><h1>Bill Ledger</h1><p className="muted">Every shortcut writes a debt. Keep the ones that still have power over the story visible.</p></div><button className="button" onClick={()=>setShow(v=>!v)}>{show?'Close':'＋ Record bill'}</button></div>
    {show&&<div className="bill-form"><div className="eyebrow">New bill</div><label>What is owed?<input value={d.title} placeholder="The lie to the clerk" onChange={e=>setD({...d,title:e.target.value})}/></label><div className="two-up"><label>External bill<textarea rows="3" placeholder="What did this choice cause in the world?" value={d.external_cost} onChange={e=>setD({...d,external_cost:e.target.value})}/></label><label>Moral cost<textarea rows="3" placeholder="What did making this choice do to the character?" value={d.moral_cost} onChange={e=>setD({...d,moral_cost:e.target.value})}/></label></div><button className="button" onClick={add}>Save bill</button></div>}
    <div className="bill-list">{bills.length?bills.map((b,i)=><article key={b.id} className={`bill-card status-${b.status.toLowerCase()}`}><div className="bill-card-top"><div><span className="bill-number">#{String(i+1).padStart(2,'0')}</span><span className="bill-status">{b.status}</span></div><select aria-label={`Status for ${b.title}`} value={b.status} onChange={async e=>{await patch('bills',b.id,{status:e.target.value});reload()}}><option>Outstanding</option><option>Escalating</option><option>Paid</option><option>Abandoned</option></select></div><h3>{b.title}</h3><div className="bill-costs"><div><span>External bill</span><p>{b.external_cost||'—'}</p></div><div><span>Moral cost</span><p>{b.moral_cost||'—'}</p></div></div></article>):<div className="empty-state compact-empty"><h2>No bills yet.</h2><p className="muted">Either the story is very clean, or nobody has made an expensive enough choice.</p></div>}</div>
  </section>
}

function Branches({workspace,project,branch,reload}) {
  const [name,setName]=useState('Alternate path'); const [label,setLabel]=useState('Before rewrite');
  async function clone(){if(!branch)return;await api(`/projects/${project.id}/branches/${branch.id}/clone`,{method:'POST',body:JSON.stringify({name})});await reload()}
  async function snapshot(){await api(`/projects/${project.id}/snapshots`,{method:'POST',body:JSON.stringify({label})});await reload()}
  return <section className="focus-card branches-focus"><div className="eyebrow">Story laboratory</div><h1>Explore without breaking what already works.</h1><p className="muted">A story branch is a creative fork. A snapshot is a safe place to return to.</p><div className="branch-grid"><div className="inner-card branch-card"><div className="card-icon">⑂</div><h3>Story branches</h3><p>Follow a major choice down another road.</p><div className="branch-list">{workspace.branches.map(b=><div className="list-row" key={b.id}><div><b>{b.name}</b><small>{b.is_main?'Canonical story':'Alternate path'}</small></div><span>{b.is_main?'MAIN':'BRANCH'}</span></div>)}</div><div className="inline-form"><input value={name} onChange={e=>setName(e.target.value)}/><button className="button" onClick={clone}>Create branch</button></div></div><div className="inner-card branch-card"><div className="card-icon">◫</div><h3>Snapshots</h3><p>Freeze the room before a large rewrite.</p><div className="branch-list">{(workspace.snapshots||[]).map(s=><div className="list-row" key={s.id}><div><b>{s.label}</b><small>{new Date(s.created_at).toLocaleDateString()}</small></div><span>SAFE</span></div>)}</div><div className="inline-form"><input value={label} onChange={e=>setLabel(e.target.value)}/><button className="button" onClick={snapshot}>Save snapshot</button></div></div></div>
  </section>
}

function Text({label,k,d,set}){return <label>{label}<textarea rows="3" value={d[k]||''} onChange={e=>set({...d,[k]:e.target.value})}/></label>}
