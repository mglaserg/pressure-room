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
    ['Pressure Room project', 'package', '.pressureroom', 'The complete editable room'],
    ['Story packet', 'pdf', 'PDF', 'A polished overview for another writer'],
    ['Structured notes', 'markdown', 'MD', 'Portable story architecture'],
    ['Screenplay', 'fountain', 'FOUNTAIN', 'For Fountain-compatible writing tools'],
  ];

  return (
    <Modal open={open} onClose={onClose} title="Share the room">
      <p className="modal-lead">Send the whole story to another writer, or hand them only the view they need.</p>
      <div className="export-list">
        {exports.map(([label,kind,format,note]) => (
          <a className="export-row" key={kind} href={`${API}/projects/${project.id}/export/${kind}`}>
            <span className="export-format">{format}</span><div><strong>{label}</strong><span>{note}</span></div><b>↓</b>
          </a>
        ))}
      </div>
      <div className="section-divider"><span>or bring another room in</span></div>
      <div className="eyebrow">Import a project</div>
      <div className="segmented compact">
        <button className={mode==='copy'?'active':''} onClick={()=>setMode('copy')}>Import as copy</button>
        <button className={mode==='replace'?'active':''} onClick={()=>setMode('replace')}>Restore / replace</button>
      </div>
      <input ref={input} type="file" accept=".pressureroom,.zip" hidden onChange={e=>importFile(e.target.files?.[0])}/>
      <button className="button secondary full" disabled={busy} onClick={()=>input.current?.click()}>{busy?'Importing…':'Choose .pressureroom file'}</button>
      {message && <p className="form-message">{message}</p>}
      <p className="microcopy">GitHub sync can build on this portable project format later; sharing never depends on it.</p>
    </Modal>
  );
}
