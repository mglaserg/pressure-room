'use client';
import {useEffect,useState} from 'react';
import Modal from './Modal';
import GoogleFountainPicker from './GoogleFountainPicker';
import {api,setStorageMode} from '@/lib/api';
import {flushDrafts} from '@/lib/draft-saver.mjs';

export default function RoomMenu({open,onClose,workspace,drive,auth,presence=[],storageMode,branchId,setBranchId,onNew,onBackup,onOpened,reload}){
  const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);
  const [collab,setCollab]=useState(null),[inviteEmail,setInviteEmail]=useState(''),[inviteRole,setInviteRole]=useState('editor');
  async function action(fn){setBusy(true);setMessage('');try{await flushDrafts();await fn()}catch(e){setMessage(e.message)}finally{setBusy(false)}}
  const [pickerOpen,setPickerOpen]=useState(false);
  const source=workspace?.project_source;

  async function refreshMembers(){
    if(!auth?.authenticated||!workspace?.project?.id||storageMode==='local'){setCollab(null);return}
    try{setCollab(await api(`/projects/${workspace.project.id}/members`))}catch(e){setMessage(e.message)}
  }
  useEffect(()=>{if(open)void refreshMembers()},[open,workspace?.project?.id,auth?.authenticated,storageMode]);

  async function sendInvite(){
    if(!inviteEmail.trim()||!workspace?.project?.id)return;
    await action(async()=>{
      await api(`/projects/${workspace.project.id}/invites`,{method:'POST',body:JSON.stringify({email:inviteEmail.trim(),role:inviteRole})});
      setInviteEmail('');setMessage(`Magic-link invitation sent.`);await refreshMembers();
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

      <button className="button" onClick={()=>{onClose();onBackup()}}>Export & backup</button>
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
