'use client';
import {useRef, useState} from 'react';
import Modal from './Modal';
import {API, api} from '@/lib/api';

export default function ShareSheet({open, onClose, project, onImported}) {
  const input = useRef(null);
  const [mode, setMode] = useState('copy');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  if (!project) return null;

  async function importFile(file) {
    if (!file) return;
    setBusy(true); setMessage('');
    const body = new FormData(); body.append('file', file);
    try {
      const result = await api(`/import?mode=${mode}`, {method:'POST', body});
      setMessage('Project imported.');
      await onImported?.(result.project_id);
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  const exports = [
    ['Pressure Room project', 'package', '.pressureroom — full editable project'],
    ['Story packet PDF', 'pdf', 'Friendly, shareable overview'],
    ['Story packet Markdown', 'markdown', 'Portable structured notes'],
    ['Screenplay Fountain', 'fountain', 'Open in Fountain-compatible screenwriting tools'],
  ];

  return (
    <Modal open={open} onClose={onClose} title="Share & export">
      <p className="muted">Send the whole project to another writer, or export only what they need.</p>
      <div className="export-list">
        {exports.map(([label,kind,note]) => (
          <a className="export-row" key={kind} href={`${API}/projects/${project.id}/export/${kind}`}>
            <div><strong>{label}</strong><span>{note}</span></div><b>↓</b>
          </a>
        ))}
      </div>
      <div className="section-divider" />
      <div className="eyebrow">Import a project</div>
      <div className="segmented compact">
        <button className={mode==='copy'?'active':''} onClick={()=>setMode('copy')}>Import as copy</button>
        <button className={mode==='replace'?'active':''} onClick={()=>setMode('replace')}>Restore / replace</button>
      </div>
      <input ref={input} type="file" accept=".pressureroom,.zip" hidden onChange={e=>importFile(e.target.files?.[0])}/>
      <button className="button secondary full" disabled={busy} onClick={()=>input.current?.click()}>{busy?'Importing…':'Choose .pressureroom file'}</button>
      {message && <p className="form-message">{message}</p>}
      <p className="microcopy">GitHub sync will build on this portable project format; it is not required to share or back up your work.</p>
    </Modal>
  );
}
