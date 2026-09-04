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
  useEffect(()=>setP(project),[project.id,project.version]);
  async function save(){await patch('projects',project.id,{title:p.title,premise:p.premise,theme:p.theme}); if(episode) await patch('episodes',episode.id,{title:episode.title,logline:episode.logline}); await reload();}
  return <section className="focus-card"><div className="eyebrow">Story spine</div><h1>What is this story really about?</h1><p className="muted">Keep the front door simple. Deep diagnostics live elsewhere.</p>
    <div className="form-stack"><label>Title<input value={p.title||''} onChange={e=>setP({...p,title:e.target.value})}/></label><label>Premise<textarea rows="4" value={p.premise||''} onChange={e=>setP({...p,premise:e.target.value})}/></label><label>Theme / dramatic question<input value={p.theme||''} onChange={e=>setP({...p,theme:e.target.value})}/></label><button className="button" onClick={save}>Save story</button></div>
  </section>
}

function Characters({workspace,project,reload}) {
  const chars=workspace.characters||[]; const [selectedId,setSelectedId]=useState(chars[0]?.id); const selected=chars.find(c=>c.id===selectedId)||chars[0]; const [draft,setDraft]=useState(selected||{});
  useEffect(()=>{ if(selected) setDraft(selected); },[selected?.id,selected?.version]);
  const choose=id=>{setSelectedId(id);setDraft(chars.find(c=>c.id===id)||{})};
  async function add(){const r=await create(`/projects/${project.id}/characters`,{name:'New Character',role:'',want:'',moral_boundary:'',moral_score:0});await reload();setSelectedId(r.id)}
  async function save(){await patch('characters',selected.id,draft);await reload()}
  return <section className="split-focus"><aside className="compact-list"><div className="rail-head"><span>Characters</span><button className="mini-button" onClick={add}>＋</button></div>{chars.map(c=><button key={c.id} className={c.id===selected?.id?'active':''} onClick={()=>choose(c.id)}><b>{c.name}</b><span>{c.role||'Character'}</span></button>)}</aside>
    <div className="focus-card">{selected?<><div className="eyebrow">Moral spine</div><h1>{selected.name}</h1><div className="form-stack"><label>Name<input value={draft.name||''} onChange={e=>setDraft({...draft,name:e.target.value})}/></label><label>Role<input value={draft.role||''} onChange={e=>setDraft({...draft,role:e.target.value})}/></label><label>Want<textarea rows="2" value={draft.want||''} onChange={e=>setDraft({...draft,want:e.target.value})}/></label><label>Moral boundary<textarea rows="2" value={draft.moral_boundary||''} onChange={e=>setDraft({...draft,moral_boundary:e.target.value})}/></label><label>Moral compromise <span className="range-value">{draft.moral_score||0}/10</span><input type="range" min="0" max="10" value={draft.moral_score||0} onChange={e=>setDraft({...draft,moral_score:Number(e.target.value)})}/></label><details className="advanced-details"><summary>Deeper character work</summary><div className="form-stack"><Text label="Need" k="need" d={draft} set={setDraft}/><Text label="Core belief" k="core_belief" d={draft} set={setDraft}/><Text label="Fear" k="fear" d={draft} set={setDraft}/><Text label="Temptation" k="temptation" d={draft} set={setDraft}/></div></details><button className="button" onClick={save}>Save character</button></div></>:<div className="empty-state"><h2>Add a character.</h2></div>}</div>
  </section>
}

function Causality({workspace,episode,reload}) {
  const scenes=useMemo(()=>workspace.scenes.filter(s=>s.episode_id===episode?.id).sort((a,b)=>a.scene_no-b.scene_no),[workspace,episode]);
  const links=(workspace.causal_links||[]).filter(l=>l.episode_id===episode?.id); const [form,setForm]=useState({from_scene_id:scenes[0]?.id||'',relation:'THEREFORE',to_scene_id:scenes[1]?.id||'',note:''});
  async function add(){if(!episode||!form.from_scene_id||!form.to_scene_id)return;await create(`/episodes/${episode.id}/links`,form);setForm({...form,note:''});await reload()}
  return <section className="focus-card"><div className="eyebrow">Therefore / But</div><h1>Does each scene force the next?</h1><div className="causal-chain">{scenes.map((s,i)=>{const outgoing=links.find(l=>l.from_scene_id===s.id);return <div key={s.id} className="causal-node"><div className="scene-chip">S{s.scene_no}</div><div><b>{s.slugline||'Untitled scene'}</b><p>{s.choice||'No choice recorded yet.'}</p></div>{outgoing&&<div className={`causal-arrow ${outgoing.relation.toLowerCase()}`}><b>{outgoing.relation}</b><span>{outgoing.note}</span></div>}</div>})}</div>
    {scenes.length>1&&<div className="inline-form"><select value={form.from_scene_id} onChange={e=>setForm({...form,from_scene_id:e.target.value})}>{scenes.map(s=><option key={s.id} value={s.id}>S{s.scene_no}</option>)}</select><select value={form.relation} onChange={e=>setForm({...form,relation:e.target.value})}><option>THEREFORE</option><option>BUT</option></select><select value={form.to_scene_id} onChange={e=>setForm({...form,to_scene_id:e.target.value})}>{scenes.map(s=><option key={s.id} value={s.id}>S{s.scene_no}</option>)}</select><input placeholder="Why does this follow?" value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/><button className="button" onClick={add}>Connect</button></div>}
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
