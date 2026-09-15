'use client';
import {useState} from 'react';
import Modal from './Modal';
import GoogleFountainPicker from './GoogleFountainPicker';
import {api,setStorageMode} from '@/lib/api';
import {flushDrafts} from '@/lib/draft-saver.mjs';

export default function RoomMenu({open,onClose,workspace,drive,storageMode,branchId,setBranchId,onNew,onBackup,onOpened,reload}){
  const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);
  async function action(fn){setBusy(true);setMessage('');try{await flushDrafts();await fn()}catch(e){setMessage(e.message)}finally{setBusy(false)}}
  const [pickerOpen,setPickerOpen]=useState(false);
  const source=workspace?.project_source;
  return <Modal open={open} suspended={pickerOpen} onClose={onClose} title="Your room">
    <div className="room-menu">
      <div className="storage-summary"><span className="eyebrow">Story storage</span><h3>{storageMode==='local'?'This browser':'Google Drive'}</h3><p>{storageMode==='local'?'Stories stay on this device. Download a backup regularly.':drive?.email}</p></div>
      {workspace&&<label>Story path<select value={branchId} onChange={e=>setBranchId(e.target.value)}>{workspace.branches.map(b=><option value={b.id} key={b.id}>{b.name}</option>)}</select></label>}
      {source&&<label>Path saved to linked Fountain file<select disabled={busy} value={source.branch_id||workspace.branches.find(b=>b.is_main)?.id||''} onChange={e=>{const branch_id=e.target.value;action(async()=>{await api(`/projects/${workspace.project.id}/fountain-branch`,{method:'POST',body:JSON.stringify({data:{branch_id}})});await reload()})}}>{workspace.branches.map(b=><option value={b.id} key={b.id}>{b.name}</option>)}</select><small>Only this path is written to {source.drive_file_name}.</small></label>}
      <button className="button" onClick={()=>{onClose();onBackup()}}>Export & backup</button>
      <button className="button secondary" onClick={()=>{onClose();onNew()}}>New story</button>
      {storageMode==='drive'&&drive?.picker_configured&&<GoogleFountainPicker onBeforeShow={()=>setPickerOpen(true)} onFinished={()=>setPickerOpen(false)} onOpened={async result=>{onClose();await onOpened(result.project_id)}}/>}
      <details className="advanced-details"><summary><span>Storage & account</span></summary><div className="form-stack">
        {storageMode==='local'&&drive?.configured&&<button className="button secondary" disabled={busy} onClick={()=>action(async()=>{setStorageMode('drive');window.location.href=drive?.connected?'/':'/api/google/connect'})}>Use Google Drive</button>}
        {storageMode==='drive'&&<><button className="button secondary" disabled={busy} onClick={()=>action(async()=>{setStorageMode('local');window.location.reload()})}>Open browser-local stories</button>
        <button className="button secondary" disabled={busy} onClick={()=>action(async()=>{
          await api('/google/disconnect',{method:'POST'});
          const prefix=`pressure-room-draft-v2:drive:${drive?.email||''}:`;
          const keys=Object.keys(localStorage).filter(k=>k.startsWith(prefix));
          if(keys.length&&window.confirm('Download any unsynced drafts before clearing them. Clear this account’s recovery drafts from this browser?'))keys.forEach(k=>localStorage.removeItem(k));
          setStorageMode('');window.location.reload();
        })}>Disconnect this session</button></>}
        <p className="microcopy">Switching storage opens a separate collection; it does not move your stories. Use a backup to transfer one. Disconnecting does not revoke Google consent.</p>
      </div></details>
      {message&&<p role="alert" className="form-message">{message}</p>}
    </div>
  </Modal>
}
