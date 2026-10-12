'use client';
import {useRef,useState} from 'react';
import Modal from './Modal';
import {api,isLocalMode} from '@/lib/api';
import {downloadBlob} from '@/lib/portable.mjs';
import {flushDrafts} from '@/lib/draft-saver.mjs';

export default function ShareSheet({open,onClose,project,onImported}) {
  const input=useRef(null);
  const [mode,setMode]=useState('copy'),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const local=isLocalMode();
  async function exportFile(kind){
    if(!project)return;
    setBusy(true);setMessage('');
    try{
      await flushDrafts();
      const response=await api(`/projects/${project.id}/export/${kind}`);
      const fileName = project.title.replace(/[^\p{L}\p{N} _-]/gu,'_');
      const filenames = {
        package: `${fileName}.pressureroom`, markdown: `${fileName}-notes.md`,
        fountain: `${fileName}.fountain`, pdf: `${fileName}-story-packet.pdf`,
        'screenplay-pdf': `${fileName}-screenplay.pdf`,
        'screenplay-mobile-pdf': `${fileName}-screenplay-mobile.pdf`,
      };
      downloadBlob(await response.arrayBuffer(), filenames[kind], response.headers.get('content-type'));
      setMessage(kind === 'package' ? 'Backup downloaded. Keep it somewhere separate from this browser.' : 'Export downloaded.');
    }catch(e){
      const missingBackendExport = ['screenplay-pdf', 'screenplay-mobile-pdf'].includes(kind)
        && /Unknown export kind/i.test(e.message);
      setMessage(missingBackendExport
        ? 'The deployed story server is out of date and does not support screenplay PDFs. Deploy the updated backend (GitHub Actions → Deploy Pressure Room backend), then try again.'
        : e.message);
    }finally{setBusy(false)}
  }
  async function importFile(file){
    if(!file)return;
    if(mode==='replace'&&!window.confirm('Restore the story contained in this backup? Download a current backup first if you want an independent copy.'))return;
    setBusy(true);setMessage('');
    try{
      await flushDrafts();
      const body=new FormData();body.append('file',file);
      const result=await api(`/import?mode=${mode}`,{method:'POST',body,projectId:project?.id});
      await onImported(result.project_id);
    }catch(e){setMessage(e.message)}finally{setBusy(false);if(input.current)input.current.value=''}
  }
  const exports=local?[['Full story backup','package','Includes scenes, structure and snapshots']]:[
    ['Full story backup','package','The complete editable story and snapshots'],
    ['Screenplay PDF','screenplay-pdf','Standard screenplay pages for printing or sharing'],
    ['Mobile screenplay PDF','screenplay-mobile-pdf','Narrow pages and larger text for reading on a phone'],
    ['Screenplay (Fountain)','fountain','Editable Fountain text'],
    ['Story packet PDF','pdf','Plot, characters, structure and notes'],
    ['Structured notes','markdown','Portable story architecture']];
  return <Modal open={open} onClose={onClose} title="Export & backup">
    <p className="modal-lead">{local?'This story lives in this browser. A downloaded backup protects it if the browser or device is lost.':'Download an independent backup of your story, separate from your Supabase account.'}</p>
    {project&&<div className="export-list">{exports.map(([label,kind,note])=><button key={kind} disabled={busy} className="export-row" onClick={()=>exportFile(kind)}><span className="export-format">↓</span><div><strong>{label}</strong><span>{note}</span></div></button>)}</div>}
    <div className="section-divider"><span>Restore a backup</span></div>
    <div className="segmented"><button aria-pressed={mode==='copy'} className={mode==='copy'?'active':''} onClick={()=>setMode('copy')}>Import as a copy</button><button aria-pressed={mode==='replace'} className={mode==='replace'?'active':''} onClick={()=>setMode('replace')}>Restore original story</button></div>
    <input ref={input} type="file" accept=".pressureroom,.zip" hidden onChange={e=>importFile(e.target.files?.[0])}/>
    <button className="button secondary full" disabled={busy} onClick={()=>input.current?.click()}>{busy?'Working…':'Choose backup file'}</button>
    {message&&<p role="status" className="form-message">{message}</p>}
  </Modal>
}
