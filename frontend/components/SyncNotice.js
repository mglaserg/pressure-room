'use client';
import {useState} from 'react';
import {api} from '@/lib/api';
import {flushDrafts} from '@/lib/draft-saver.mjs';

export default function SyncNotice({workspace,onResolved,onBackup}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const sync=workspace?.sync;
  if(!sync||['synced','local'].includes(sync.status))return null;
  async function resolve(action){
    setBusy(true);setError('');
    try{
      await flushDrafts();
      const result=await api(`/projects/${workspace.project.id}/sync`,{method:'POST',body:JSON.stringify({action})});
      await onResolved(result.project_id);
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  return <aside className="sync-notice" aria-label="Story sync status"><div><b>{sync.status==='conflict'?'Two versions need your attention':'Your story is waiting to sync'}</b><p>{sync.message}</p><small>Your current story remains available here. Download a backup before closing this device.</small></div><div className="form-actions">
    <button className="button secondary" disabled={busy} onClick={()=>resolve('retry')}>Retry sync</button>
    <button className="button secondary" disabled={busy} onClick={onBackup}>Download backup</button>
    {sync.status==='conflict'&&<><button className="button secondary" disabled={busy} onClick={()=>resolve('copy')}>Keep mine as a new story</button><button className="button secondary" disabled={busy} onClick={()=>resolve('load-drive')}>Load Drive + keep recovery</button></>}
  </div>{error&&<p role="alert">{error}</p>}</aside>
}
