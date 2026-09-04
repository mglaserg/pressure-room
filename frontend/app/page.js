'use client';
import {useEffect, useMemo, useState} from 'react';
import {api, create} from '@/lib/api';
import WriteView from '@/components/WriteView';
import StructureView from '@/components/StructureView';
import DiagnoseView from '@/components/DiagnoseView';
import HelpView from '@/components/HelpView';
import ShareSheet from '@/components/ShareSheet';
import Modal from '@/components/Modal';

export default function Home(){
  const [projects,setProjects]=useState([]); const [projectId,setProjectId]=useState(''); const [workspace,setWorkspace]=useState(null); const [mode,setMode]=useState('write');
  const [branchId,setBranchId]=useState(''); const [episodeId,setEpisodeId]=useState(''); const [sceneId,setSceneId]=useState(''); const [share,setShare]=useState(false); const [newStory,setNewStory]=useState(false); const [error,setError]=useState('');

  async function loadProjects(prefer){const ps=await api('/projects');setProjects(ps);const id=prefer||projectId||ps[0]?.id||'';if(id){setProjectId(id);await loadWorkspace(id)}else setWorkspace(null)}
  async function loadWorkspace(id,preferScene){const ws=await api(`/projects/${id}`);setWorkspace(ws);const branch=ws.branches.find(b=>b.id===branchId)||ws.branches.find(b=>b.is_main)||ws.branches[0];setBranchId(branch?.id||'');const eps=ws.episodes.filter(e=>e.branch_id===branch?.id);const ep=eps.find(e=>e.id===episodeId)||eps[0];setEpisodeId(ep?.id||'');const sc=ws.scenes.filter(s=>s.episode_id===ep?.id).sort((a,b)=>a.scene_no-b.scene_no);setSceneId(preferScene||sc.find(s=>s.id===sceneId)?.id||sc[0]?.id||'');}
  useEffect(()=>{loadProjects().catch(e=>setError(e.message))},[]);

  const project=workspace?.project; const branch=workspace?.branches.find(b=>b.id===branchId); const branchEpisodes=(workspace?.episodes||[]).filter(e=>e.branch_id===branchId); const episode=branchEpisodes.find(e=>e.id===episodeId)||branchEpisodes[0];
  useEffect(()=>{if(workspace&&branchId){const eps=workspace.episodes.filter(e=>e.branch_id===branchId);if(!eps.some(e=>e.id===episodeId)){setEpisodeId(eps[0]?.id||'');setSceneId('')}}},[branchId]);

  async function reload(preferScene){if(projectId)await loadWorkspace(projectId,preferScene)}
  async function createEpisode(){if(!project||!branch)return;const n=Math.max(0,...branchEpisodes.map(e=>e.number))+1;const r=await create(`/projects/${project.id}/episodes`,{branch_id:branch.id,number:n,title:`Episode ${n}`,logline:''});await reload();setEpisodeId(r.id)}

  if(error)return <main className="boot"><div className="brand-mark">PR</div><h1>Pressure Room</h1><p>{error}</p><p className="muted">Make sure the FastAPI server is running on port 8000.</p></main>;
  if(!workspace)return <main className="boot"><div className="brand-mark">PR</div><h1>Pressure Room</h1><p className="muted">Opening the room…</p></main>;

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark small">PR</div><div><b>Pressure Room</b><span>Writers, under pressure.</span></div></div>
      <div className="context-bar">
        <select value={projectId} onChange={async e=>{setProjectId(e.target.value);await loadWorkspace(e.target.value)}}>{projects.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}</select>
        <select value={branchId} onChange={e=>setBranchId(e.target.value)}>{workspace.branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select>
        {branchEpisodes.length?<select value={episode?.id||''} onChange={e=>{setEpisodeId(e.target.value);setSceneId('')}}>{branchEpisodes.map(e=><option key={e.id} value={e.id}>E{e.number} · {e.title}</option>)}</select>:<button className="context-add" onClick={createEpisode}>＋ Episode</button>}
      </div>
      <div className="top-actions"><button className="button ghost" onClick={()=>setNewStory(true)}>＋ Story</button><button className="button" onClick={()=>setShare(true)}>Share</button></div>
    </header>

    <nav className="primary-nav">{[['write','Write'],['structure','Structure'],['diagnose','Diagnose'],['help','How to use']].map(([id,label])=><button key={id} className={mode===id?'active':''} onClick={()=>setMode(id)}><span className="nav-dot"/>{label}</button>)}</nav>

    <div className="workspace">
      {mode==='write'&&<WriteView workspace={workspace} episode={episode} sceneId={sceneId} setSceneId={setSceneId} reload={reload}/>} 
      {mode==='structure'&&<StructureView workspace={workspace} project={project} branch={branch} episode={episode} reload={reload}/>} 
      {mode==='diagnose'&&<DiagnoseView episode={episode}/>} 
      {mode==='help'&&<HelpView/>}
    </div>

    <ShareSheet open={share} onClose={()=>setShare(false)} project={project} onImported={async id=>{setShare(false);await loadProjects(id)}}/>
    <NewStory open={newStory} onClose={()=>setNewStory(false)} onCreate={async data=>{const r=await create('/projects',data);setNewStory(false);await loadProjects(r.id)}}/>
  </main>
}

function NewStory({open,onClose,onCreate}){const [d,setD]=useState({title:'',premise:'',theme:''});return <Modal open={open} onClose={onClose} title="New story"><div className="form-stack"><label>Title<input autoFocus value={d.title} onChange={e=>setD({...d,title:e.target.value})}/></label><label>Premise<textarea rows="4" value={d.premise} onChange={e=>setD({...d,premise:e.target.value})}/></label><label>Theme / dramatic question<input value={d.theme} onChange={e=>setD({...d,theme:e.target.value})}/></label><button className="button full" disabled={!d.title.trim()} onClick={()=>onCreate(d)}>Create story</button></div></Modal>}
