'use client';
import {useEffect, useRef, useState} from 'react';
import {api, create, getStorageMode, remoteApi, setStorageMode} from '@/lib/api';
import WriteView from '@/components/WriteView';
import StructureView from '@/components/StructureView';
import DiagnoseView from '@/components/DiagnoseView';
import HelpView from '@/components/HelpView';
import ShareSheet from '@/components/ShareSheet';
import Modal from '@/components/Modal';
import RoomMenu from '@/components/RoomMenu';
import SyncNotice from '@/components/SyncNotice';
import GoogleFountainPicker from '@/components/GoogleFountainPicker';

const NAV = [
  ['write','Write','The page'],
  ['structure','Structure','The spine'],
  ['diagnose','Diagnose','The pressure'],
  ['help','How to use','The method'],
];

export default function Home(){
  const [projects,setProjects]=useState([]);
  const [projectId,setProjectId]=useState('');
  const [workspace,setWorkspace]=useState(null);
  const [mode,setMode]=useState('write');
  const [branchId,setBranchId]=useState('');
  const [episodeId,setEpisodeId]=useState('');
  const [sceneId,setSceneId]=useState('');
  const [roomMenu,setRoomMenu]=useState(false);
  const [share,setShare]=useState(false);
  const [newStory,setNewStory]=useState(false);
  const [error,setError]=useState('');
  const [drive,setDrive]=useState(null);
  const [storageMode,setStorageModeState]=useState('');
  const [projectsReady,setProjectsReady]=useState(false);
  const driveImport=useRef(null);
  const [driveImportBusy,setDriveImportBusy]=useState(false);

  async function loadProjects(prefer){
    setProjectsReady(false);
    const ps=await api('/projects');
    setProjects(ps);
    setProjectsReady(true);
    const id=prefer||projectId||ps[0]?.id||'';
    if(id){setProjectId(id);await loadWorkspace(id)} else {setProjectId('');setWorkspace(null);}
  }

  async function loadWorkspace(id,preferScene){
    const ws=await api(`/projects/${id}`);
    setWorkspace(ws);
    const branch=ws.branches.find(b=>b.id===branchId)||ws.branches.find(b=>b.is_main)||ws.branches[0];
    setBranchId(branch?.id||'');
    const eps=ws.episodes.filter(e=>e.branch_id===branch?.id);
    const ep=eps.find(e=>e.id===episodeId)||eps[0];
    setEpisodeId(ep?.id||'');
    const sc=ws.scenes.filter(s=>s.episode_id===ep?.id).sort((a,b)=>a.scene_no-b.scene_no);
    setSceneId(preferScene||sc.find(s=>s.id===sceneId)?.id||sc[0]?.id||'');
  }

  async function boot(){
    const status=await remoteApi('/google/status').catch(()=>({configured:false,required:false,connected:false,error:'Google Drive status could not be loaded.'}));
    setDrive(status);
    const preferred=getStorageMode();

    if(preferred==='local'){
      setStorageModeState('local');
      await loadProjects();
      return;
    }

    if(preferred==='drive'){
      if(status.connected){
        setStorageModeState('drive');
        await loadProjects();
        return;
      }
      setStorageMode('');
      setStorageModeState('');
      setProjectsReady(true);
      return;
    }

    if(status.connected){
      setStorageMode('drive');
      setStorageModeState('drive');
      await loadProjects();
      return;
    }

    setStorageModeState('');
    setProjectsReady(true);
  }

  useEffect(()=>{boot().catch(e=>setError(e.message))},[]);

  const project=workspace?.project;
  const branch=workspace?.branches.find(b=>b.id===branchId);
  const branchEpisodes=(workspace?.episodes||[]).filter(e=>e.branch_id===branchId);
  const episode=branchEpisodes.find(e=>e.id===episodeId)||branchEpisodes[0];

  useEffect(()=>{
    if(workspace&&branchId){
      const eps=workspace.episodes.filter(e=>e.branch_id===branchId);
      if(!eps.some(e=>e.id===episodeId)){setEpisodeId(eps[0]?.id||'');setSceneId('')}
    }
  },[branchId,workspace,episodeId]);

  async function reload(preferScene){if(projectId)await loadWorkspace(projectId,preferScene)}
  async function createEpisode(){
    if(!project||!branch)return;
    const n=Math.max(0,...branchEpisodes.map(e=>e.number))+1;
    const r=await create(`/projects/${project.id}/episodes`,{branch_id:branch.id,number:n,title:`Episode ${n}`,logline:''});
    await reload();
    setEpisodeId(r.id);
  }

  async function chooseLocalMode(){
    setStorageMode('local');
    setStorageModeState('local');
    await loadProjects();
  }

  function chooseDriveMode(){
    setStorageMode('drive');
    setStorageModeState('drive');
    if(drive?.connected){window.location.reload();return;}
    window.location.href='/api/google/connect';
  }

  async function importFirstDriveProject(file){
    if(!file)return;
    setDriveImportBusy(true);
    try{
      const body=new FormData();
      body.append('file',file);
      const result=await api('/import?mode=replace',{method:'POST',body});
      await loadProjects(result.project_id);
    }catch(e){
      setError(e.message||'Could not import that Pressure Room project.');
    }finally{
      setDriveImportBusy(false);
      if(driveImport.current)driveImport.current.value='';
    }
  }

  const showChooser = storageMode==='' && drive!==null && !workspace;
  const showDriveEmpty = storageMode==='drive' && drive?.connected && projectsReady && projects.length===0 && !workspace;
  const showLocalEmpty = storageMode==='local' && projectsReady && projects.length===0 && !workspace;

  if(error&&!workspace)return <main className="boot boot-error">
    <BrandMark large/>
    <div className="boot-copy"><span className="eyebrow">The room is closed</span><h1>Pressure Room</h1><p>{error}</p><p className="muted">The interface loaded, but it could not reach the story service.</p></div>
    <div className="boot-actions"><button className="button" onClick={()=>{setError('');boot().catch(e=>setError(e.message))}}>Try again</button><a className="button secondary" href="/api/health" target="_blank" rel="noreferrer">API health</a></div>
  </main>;

  if(showChooser)return <main className="boot">
    <BrandMark large/>
    <div className="boot-copy">
      <span className="eyebrow">Choose your room</span>
      <h1>Where should Pressure Room keep your stories?</h1>
      <p>Start locally on this device, or connect Google Drive and keep your projects in your own cloud storage.</p>
      <p className="muted">Local mode stores stories only in this browser on this device. Google Drive mode keeps each story as a portable Pressure Room project file in your Drive.</p>
    </div>
    <div className="boot-actions">
      <button className="button" onClick={chooseLocalMode}>Continue on this device</button>
      {drive?.configured
        ? <button className="button secondary" onClick={chooseDriveMode}>Connect Google Drive</button>
        : <button className="button secondary" disabled title={drive?.error||'Google Drive is not configured'}>Google Drive unavailable</button>}
    </div>
  </main>;

  if(showDriveEmpty)return <>
    <main className="boot">
      <BrandMark large/>
      <div className="boot-copy">
        <span className="eyebrow">Your Drive is connected</span>
        <h1>Your room is empty</h1>
        <p>Nothing has been written here yet. Start a new story, or bring an existing Pressure Room project into the room.</p>
        <p className="muted">Your stories will be saved automatically in the Pressure Room folder in your Google Drive{drive?.email?` as ${drive.email}`:''}.</p>
      </div>
      <div className="boot-actions">
        <button className="button" onClick={()=>setNewStory(true)}>Create a story</button>
        {drive?.picker_configured&&<GoogleFountainPicker onOpened={async result=>await loadProjects(result.project_id)}/>}
        <input ref={driveImport} type="file" accept=".pressureroom,.zip" hidden onChange={e=>importFirstDriveProject(e.target.files?.[0])}/>
        <button className="button secondary" disabled={driveImportBusy} onClick={()=>driveImport.current?.click()}>{driveImportBusy?'Importing…':'Import Pressure Room project'}</button>
      </div>
    </main>
    <RoomMenu open={roomMenu} onClose={()=>setRoomMenu(false)} workspace={workspace} drive={drive} storageMode={storageMode} branchId={branchId} setBranchId={setBranchId} onNew={()=>setNewStory(true)} onBackup={()=>setShare(true)} onOpened={loadProjects} reload={reload}/>
    <NewStory open={newStory} onClose={()=>setNewStory(false)} onCreate={async data=>{const r=await create('/projects',data);setNewStory(false);await loadProjects(r.id)}}/>
  </>;

  if(showLocalEmpty)return <>
    <main className="boot">
      <BrandMark large/>
      <div className="boot-copy">
        <span className="eyebrow">This device</span>
        <h1>Your room is empty</h1>
        <p>Start a story right away without connecting anything. You can add Google Drive later if you want cloud-backed projects.</p>
        <p className="muted">Local stories are saved in this browser on this device.</p>
      </div>
      <div className="boot-actions">
        <button className="button" onClick={()=>setNewStory(true)}>Create a story</button>
        <button className="button secondary" onClick={()=>setShare(true)}>Restore a backup</button>
        {drive?.configured&&<button className="button secondary" onClick={chooseDriveMode}>Use Google Drive instead</button>}
      </div>
    </main>
    <ShareSheet open={share} onClose={()=>setShare(false)} project={project} drive={drive} onImported={async id=>{setShare(false);await loadProjects(id)}}/>
    <RoomMenu open={roomMenu} onClose={()=>setRoomMenu(false)} workspace={workspace} drive={drive} storageMode={storageMode} branchId={branchId} setBranchId={setBranchId} onNew={()=>setNewStory(true)} onBackup={()=>setShare(true)} onOpened={loadProjects} reload={reload}/>
    <NewStory open={newStory} onClose={()=>setNewStory(false)} onCreate={async data=>{const r=await create('/projects',data);setNewStory(false);await loadProjects(r.id)}}/>
  </>;

  if(drive===null||(!workspace&&!(projectsReady&&projects.length===0)))return <main className="boot"><BrandMark large/><div className="boot-copy"><span className="eyebrow">Pressure Room</span><h1>Opening the room</h1><p className="muted">{storageMode==='drive'&&drive?.connected?'Bringing your stories down from Google Drive.':storageMode==='local'?'Opening your local room on this device.':'Preparing the room.'}</p></div><div className="boot-pulse" aria-hidden="true"><i/><i/><i/></div></main>;

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand">
        <BrandMark/>
        <div className="brand-copy"><b>Pressure Room</b><span>Stories reveal character under pressure.</span></div>
      </div>

      <div className="context-bar" aria-label="Story context">
        <label className="context-select"><span>Story</span><select value={projectId} onChange={async e=>{setProjectId(e.target.value);await loadWorkspace(e.target.value)}}>{projects.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
        <span className="context-chevron">/</span>
        {branchEpisodes.length?<label className="context-select"><span>Episode</span><select value={episode?.id||''} onChange={e=>{setEpisodeId(e.target.value);setSceneId('')}}>{branchEpisodes.map(e=><option key={e.id} value={e.id}>E{e.number} · {e.title}</option>)}</select></label>:<button className="context-add" onClick={createEpisode}>＋ Episode</button>}
      </div>

<<<<<<< HEAD
      <div className="top-actions"><button className="button compact room-menu-trigger" aria-haspopup="dialog" onClick={()=>setRoomMenu(true)}>Room <span aria-hidden="true">☰</span></button></div>
=======
      <div className="top-actions">
        {storageMode==='drive'&&drive?.connected&&<form action="/api/google/disconnect" method="post"><button className="quiet-action" title={drive.email||'Google Drive'}>Disconnect Drive</button></form>}
        {storageMode==='drive'&&workspace?.project_source?.source_kind==='fountain'&&<span className="quiet-action" title={workspace.project_source.drive_file_name||'Linked Fountain'}>Fountain ↔</span>}
        {storageMode==='drive'&&drive?.connected&&drive?.picker_configured&&<GoogleFountainPicker className="quiet-action" label="Open Fountain" onOpened={async result=>await loadProjects(result.project_id)}/>}
        {storageMode==='local'&&<span className="quiet-action" title="Saved in this browser on this device">This device</span>}
        {storageMode==='local'&&drive?.configured&&<button className="quiet-action" onClick={chooseDriveMode}>Use Drive</button>}
        <button className="quiet-action" onClick={()=>setNewStory(true)}>＋ Story</button>
        {storageMode==='drive'&&<button className="button compact" onClick={()=>setShare(true)}>Share</button>}
      </div>
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
    </header>

    <nav className="primary-nav" aria-label="Primary workspace">
      {NAV.map(([id,label,sub])=><button key={id} aria-current={mode===id?'page':undefined} className={mode===id?'active':''} onClick={()=>setMode(id)}><span className="nav-mark"/><span className="nav-label"><b>{label}</b><small>{sub}</small></span></button>)}
    </nav>

    {error&&<div className="sync-notice" role="alert"><p>{error}</p><button className="button secondary" onClick={()=>setError('')}>Dismiss</button></div>}
    <SyncNotice workspace={workspace} onResolved={id=>loadProjects(id)} onBackup={()=>setShare(true)}/>
    <div className="workspace">
<<<<<<< HEAD
      {mode==='write'&&<WriteView onSceneSaved={(id,data,result)=>setWorkspace(ws=>ws?{...ws,revision:result.revision||ws.revision,sync:result.sync||ws.sync,scenes:ws.scenes.map(scene=>scene.id===id?{...scene,...data}:scene)}:ws)} storageScope={`${storageMode}:${drive?.email||"device"}`} workspace={workspace} episode={episode} sceneId={sceneId} setSceneId={setSceneId} reload={reload}/>}
=======
      {mode==='write'&&<WriteView onSceneSaved={(id,data)=>setWorkspace(ws=>ws?{...ws,scenes:ws.scenes.map(scene=>scene.id===id?{...scene,...data}:scene)}:ws)} storageScope={`${storageMode}:${drive?.email||"device"}`} workspace={workspace} episode={episode} sceneId={sceneId} setSceneId={setSceneId} reload={reload}/>}
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
      {mode==='structure'&&<StructureView workspace={workspace} project={project} branch={branch} episode={episode} reload={reload}/>}
      {mode==='diagnose'&&<DiagnoseView episode={episode}/>}
      {mode==='help'&&<HelpView/>}
    </div>

    {<ShareSheet open={share} onClose={()=>setShare(false)} project={project} drive={drive} onImported={async id=>{setShare(false);await loadProjects(id)}}/>}
    <RoomMenu open={roomMenu} onClose={()=>setRoomMenu(false)} workspace={workspace} drive={drive} storageMode={storageMode} branchId={branchId} setBranchId={setBranchId} onNew={()=>setNewStory(true)} onBackup={()=>setShare(true)} onOpened={loadProjects} reload={reload}/>
    <NewStory open={newStory} onClose={()=>setNewStory(false)} onCreate={async data=>{const r=await create('/projects',data);setNewStory(false);await loadProjects(r.id)}}/>
  </main>
}

function BrandMark({large=false}){
  return <div className={`brand-mark ${large?'large':''}`} aria-hidden="true"><span>P</span><i/><span>R</span></div>
}

function NewStory({open,onClose,onCreate}){
  const [d,setD]=useState({title:'',premise:'',theme:''});
  return <Modal open={open} onClose={onClose} title="Open a new room"><div className="modal-intro"><p>Start with the story’s front door. You can discover the rest under pressure.</p></div><div className="form-stack"><label>Title<input autoFocus value={d.title} placeholder="Untitled story" onChange={e=>setD({...d,title:e.target.value})}/></label><label>Premise<textarea rows="4" value={d.premise} placeholder="Who wants what — and what makes it costly?" onChange={e=>setD({...d,premise:e.target.value})}/></label><label>Theme / dramatic question<input value={d.theme} placeholder="What question keeps the story alive?" onChange={e=>setD({...d,theme:e.target.value})}/></label><button className="button full" disabled={!d.title.trim()} onClick={()=>onCreate(d)}>Create story</button></div></Modal>
}
