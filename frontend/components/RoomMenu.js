'use client';
import {useEffect,useState} from 'react';
import Modal from './Modal';
import GoogleFountainPicker from './GoogleFountainPicker';
import {api,setStorageMode} from '@/lib/api';
import {flushDrafts} from '@/lib/draft-saver.mjs';

export default function RoomMenu({open,onClose,workspace,drive,auth,presence=[],storageMode,branchId,setBranchId,onNew,onBackup,onOpened,reload,onProjectListChanged}){
  const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);
  const [collab,setCollab]=useState(null),[inviteEmail,setInviteEmail]=useState(''),[inviteRole,setInviteRole]=useState('editor');
  const [renameTitle,setRenameTitle]=useState(workspace?.project?.title||''),[trash,setTrash]=useState([]);
  async function action(fn){setBusy(true);setMessage('');try{await flushDrafts();await fn()}catch(e){setMessage(e.message)}finally{setBusy(false)}}
  const [pickerOpen,setPickerOpen]=useState(false);
  const source=workspace?.project_source;

  async function refreshMembers(){
    if(!auth?.authenticated||!workspace?.project?.id||storageMode==='local'){setCollab(null);return}
    try{setCollab(await api(`/projects/${workspace.project.id}/members`))}catch(e){setMessage(e.message)}
  }
  async function refreshTrash(){
    if(!(storageMode==='local'||auth?.authenticated)){setTrash([]);return}
    try{setTrash(await api('/projects/trash'))}catch(e){setMessage(e.message)}
  }
  useEffect(()=>{setRenameTitle(workspace?.project?.title||'')},[workspace?.project?.id,workspace?.project?.title]);
  useEffect(()=>{if(open){void refreshMembers();void refreshTrash()}},[open,workspace?.project?.id,auth?.authenticated,storageMode]);

  async function sendInvite(){
    if(!inviteEmail.trim()||!workspace?.project?.id)return;
    await action(async()=>{
      await api(`/projects/${workspace.project.id}/invites`,{method:'POST',body:JSON.stringify({email:inviteEmail.trim(),role:inviteRole})});
      setInviteEmail('');setMessage(`Magic-link invitation sent.`);await refreshMembers();
    });
  }

  const role=storageMode==='local'?'owner':(workspace?.access?.role||collab?.role||'viewer');
  const canEditProject=role==='owner'||role==='editor';
  const canTrashProject=role==='owner';

  async function renameProject(){
    const title=renameTitle.trim();
    if(!workspace?.project?.id||!title||title===workspace.project.title)return;
    await action(async()=>{
      await api(`/projects/${workspace.project.id}/rename`,{method:'POST',body:JSON.stringify({name:title})});
      setMessage('Project renamed.');
      await reload();
      await onProjectListChanged?.(workspace.project.id);
    });
  }

  async function trashProject(){
    if(!workspace?.project?.id)return;
    if(!window.confirm(`Move “${workspace.project.title}” to Trash? Collaborators will lose access until you restore it. The Drive mirror will be left alone.`))return;
    await action(async()=>{
      await api(`/projects/${workspace.project.id}/trash`,{method:'POST'});
      onClose();
      await onProjectListChanged?.();
    });
  }

  async function restoreProject(item){
    await action(async()=>{
      await api(`/projects/${item.id}/restore`,{method:'POST'});
      await refreshTrash();
      await onProjectListChanged?.(item.id);
      setMessage(`Restored ${item.title}.`);
    });
  }

  async function deleteForever(item){
    const typed=window.prompt(`Permanent deletion cannot be undone. Type the project title exactly to delete it:

${item.title}`,'');
    if(typed===null)return;
    if(typed!==item.title){setMessage('Project title did not match. Nothing was deleted.');return}
    const deleteDrive=Boolean(drive?.connected&&window.confirm('Also permanently delete Pressure Room’s .pressureroom mirror from Google Drive? The original linked Fountain file, if any, will not be deleted.'));
    await action(async()=>{
      await api(`/projects/${item.id}/permanent`,{method:'DELETE',body:JSON.stringify({confirm_title:typed,delete_drive_mirror:deleteDrive})});
      await refreshTrash();
      await onProjectListChanged?.();
      setMessage(`Permanently deleted ${item.title}.`);
    });
  }

  const storageTitle=storageMode==='local'?'This browser':auth?.authenticated?'Pressure Room Cloud':'Google Drive';
  const storageCopy=storageMode==='local'?'Stories stay on this device. Download a backup regularly.':auth?.authenticated?auth.email:drive?.email;
  return <Modal open={open} suspended={pickerOpen} onClose={onClose} title="Your room">
    <div className="room-menu">
      <div className="storage-summary"><span className="eyebrow">Story storage</span><h3>{storageTitle}</h3><p>{storageCopy}</p>{auth?.authenticated&&drive?.connected&&<small>Google Drive mirror: {drive.email}</small>}</div>
      {workspace&&<label>Story path<select value={branchId} onChange={e=>setBranchId(e.target.value)}>{workspace.branches.map(b=><option value={b.id} key={b.id}>{b.name}</option>)}</select></label>}
      {source&&<label>Path saved to linked Fountain file<select disabled={busy} value={source.branch_id||workspace.branches.find(b=>b.is_main)?.id||''} onChange={e=>{const branch_id=e.target.value;action(async()=>{await api(`/projects/${workspace.project.id}/fountain-branch`,{method:'POST',body:JSON.stringify({data:{branch_id}})});await reload()})}}>{workspace.branches.map(b=><option value={b.id} key={b.id}>{b.name}</option>)}</select><small>Only this path is written to {source.drive_file_name}.</small></label>}

      {auth?.authenticated&&workspace&&<details className="advanced-details collaboration-details" open={false}><summary><span>Collaborators</span><small>{presence.length>1?`${presence.length} active`:'Sharing & permissions'}</small></summary><div className="form-stack">
        {collab?.members?.map(member=><div className="collaborator-row" key={member.user_id}><div><strong>{member.email||member.user_id}</strong><small>{member.role}{presence.some(p=>p.user_id===member.user_id)?' · in room':''}</small></div>{collab.role==='owner'&&member.role!=='owner'&&<button className="button compact secondary" disabled={busy} onClick={()=>action(async()=>{await api(`/projects/${workspace.project.id}/members/${member.user_id}`,{method:'DELETE'});await refreshMembers()})}>Remove</button>}</div>)}
        {collab?.role==='owner'&&<><div className="section-divider">Invite</div><label>Email<input type="email" value={inviteEmail} placeholder="writer@example.com" onChange={e=>setInviteEmail(e.target.value)}/></label><label>Role<select value={inviteRole} onChange={e=>setInviteRole(e.target.value)}><option value="editor">Editor</option><option value="viewer">Viewer</option></select></label><button className="button secondary" disabled={busy||!inviteEmail.trim()} onClick={sendInvite}>Send magic-link invite</button>{collab?.invites?.length>0&&<div className="pending-invites"><small>Pending</small>{collab.invites.map(inv=><span key={inv.id}>{inv.email} · {inv.role}</span>)}</div>}</>}
        {collab&&<p className="microcopy">Your role: {collab.role}. Editors can change story content. Viewers can read it. Only the owner manages access and the optional Drive mirror.</p>}
      </div></details>}

      {workspace&&<details className="advanced-details" open={false}><summary><span>Project management</span><small>Rename & Trash</small></summary><div className="form-stack">
        {canEditProject&&<label>Project name<div className="inline-field"><input value={renameTitle} maxLength={200} onChange={e=>setRenameTitle(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')void renameProject()}}/><button className="button compact secondary" disabled={busy||!renameTitle.trim()||renameTitle.trim()===workspace.project.title} onClick={renameProject}>Rename</button></div></label>}
        {canTrashProject?<><button className="button secondary danger-action" disabled={busy} onClick={trashProject}>Move project to Trash</button><p className="microcopy">Trash preserves the story, branches, collaborators, and Drive mirror. Only the owner can restore or permanently delete it.</p></>:<p className="microcopy">Only the project owner can move a shared project to Trash.</p>}
      </div></details>}

      {(storageMode==='local'||auth?.authenticated)&&<details className="advanced-details" open={!workspace&&trash.length>0}><summary><span>Trash</span><small>{trash.length?`${trash.length} project${trash.length===1?'':'s'}`:'Empty'}</small></summary><div className="form-stack">
        {!trash.length&&<p className="microcopy">Trash is empty.</p>}
        {trash.map(item=><div className="collaborator-row" key={item.id}><div><strong>{item.title}</strong><small>{item.trashed_at?`Moved ${new Date(item.trashed_at).toLocaleDateString()}`:'In Trash'}</small></div><div className="trash-actions"><button className="button compact secondary" disabled={busy} onClick={()=>restoreProject(item)}>Restore</button><button className="quiet-action danger-ghost" disabled={busy} onClick={()=>deleteForever(item)}>Delete forever</button></div></div>)}
      </div></details>}

      {workspace&&<button className="button" onClick={()=>{onClose();onBackup()}}>Export & backup</button>}
      <button className="button secondary" onClick={()=>{onClose();onNew()}}>New story</button>
      {drive?.connected&&drive?.picker_configured&&<GoogleFountainPicker onBeforeShow={()=>setPickerOpen(true)} onFinished={()=>setPickerOpen(false)} onOpened={async result=>{onClose();await onOpened(result.project_id)}}/>}
      <details className="advanced-details"><summary><span>Storage & account</span></summary><div className="form-stack">
        {storageMode==='local'&&auth?.authenticated&&<button className="button secondary" disabled={busy} onClick={()=>action(async()=>{setStorageMode('cloud');window.location.reload()})}>Open cloud workspace</button>}
        {storageMode==='local'&&!auth?.enabled&&drive?.configured&&<button className="button secondary" disabled={busy} onClick={()=>action(async()=>{setStorageMode('drive');window.location.href=drive?.connected?'/':'/api/google/connect'})}>Use Google Drive</button>}
        {storageMode!=='local'&&<button className="button secondary" disabled={busy} onClick={()=>action(async()=>{setStorageMode('local');window.location.reload()})}>Open browser-local stories</button>}
        {auth?.authenticated&&!drive?.connected&&drive?.configured&&<button className="button secondary" disabled={busy} onClick={()=>{window.location.href='/api/google/connect'}}>Connect Google Drive mirror</button>}
        {drive?.connected&&<button className="button secondary" disabled={busy} onClick={()=>action(async()=>{
          await api('/google/disconnect',{method:'POST'});
          const prefix=`pressure-room-draft-v2:${storageMode}:${auth?.email||drive?.email||''}:`;
          const keys=Object.keys(localStorage).filter(k=>k.startsWith(prefix));
          if(keys.length&&window.confirm('Download any unsynced drafts before clearing them. Clear this account’s recovery drafts from this browser?'))keys.forEach(k=>localStorage.removeItem(k));
          window.location.reload();
        })}>Disconnect Google Drive</button>}
        {auth?.authenticated&&<button className="button secondary" disabled={busy} onClick={()=>action(async()=>{await api('/auth/logout',{method:'POST'});setStorageMode('');window.location.reload()})}>Sign out of Pressure Room</button>}
        <p className="microcopy">Cloud stories live in Supabase. Google Drive is an optional owner-controlled mirror/export. Browser-local stories remain a separate collection on this device.</p>
      </div></details>
      {message&&<p role="alert" className="form-message">{message}</p>}
    </div>
  </Modal>
}
