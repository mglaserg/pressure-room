'use client';
import {useEffect, useMemo, useRef, useState} from 'react';
import {create, patch} from '@/lib/api';
import {parseFountain} from '@/lib/fountain.mjs';

const blank = {slugline:'', screenplay_text:'', opening_behavior:'', scene_want:'', obstacle:'', tactic:'', pressure:'', choice:'', start_state:'', end_state:'', cut_on:'', notes:'', moral_delta:0, pov_character_id:null};

export default function WriteView({workspace, episode, sceneId, setSceneId, reload}) {
  const scenes = useMemo(() => (workspace?.scenes || []).filter(s=>s.episode_id===episode?.id).sort((a,b)=>a.scene_no-b.scene_no), [workspace, episode]);
  const selected = scenes.find(s=>s.id===sceneId) || scenes[0];
  const [draft, setDraft] = useState(selected || blank);
  const [structureOpen, setStructureOpen] = useState(false);
  const [saveState, setSaveState] = useState('saved');
  const [viewMode, setViewMode] = useState('edit');
  const timer = useRef(null);

  useEffect(()=>{
    if (selected) {
      const cached = typeof window !== 'undefined' ? localStorage.getItem(`pressure-room-draft:${selected.id}`) : null;
      setDraft(cached ? {...selected, screenplay_text: cached} : selected);
      setSceneId(selected.id);
    } else setDraft(blank);
  }, [selected?.id]);

  useEffect(()=>{
    const saved = typeof window !== 'undefined' ? localStorage.getItem('pressure-room-write-view') : null;
    if (saved === 'page') setViewMode('page');
  },[]);

  useEffect(()=>()=>clearTimeout(timer.current),[]);

  function chooseView(nextMode) {
    setViewMode(nextMode);
    if (typeof window !== 'undefined') localStorage.setItem('pressure-room-write-view', nextMode);
  }

  function change(key, value) {
    const next = {...draft, [key]: value};
    setDraft(next);
    if (key==='screenplay_text' && selected?.id) localStorage.setItem(`pressure-room-draft:${selected.id}`, value);
    if (!selected?.id) return;
    setSaveState('saving');
    clearTimeout(timer.current);
    timer.current = setTimeout(async ()=>{
      const fields = ['slugline','screenplay_text','opening_behavior','scene_want','obstacle','tactic','pressure','choice','start_state','end_state','cut_on','notes','moral_delta','pov_character_id'];
      const payload = Object.fromEntries(fields.map(k=>[k,next[k] ?? '']));
      payload.pov_character_id = next.pov_character_id || null;
      payload.moral_delta = Number(next.moral_delta || 0);
      try {
        await patch('scenes', selected.id, payload);
        setSaveState('saved');
        localStorage.removeItem(`pressure-room-draft:${selected.id}`);
      } catch {
        setSaveState('offline');
      }
    }, 700);
  }

  async function addScene() {
    if (!episode) return;
    const scene_no = (scenes.at(-1)?.scene_no || 0) + 1;
    const r = await create(`/episodes/${episode.id}/scenes`, {scene_no, slugline:'INT. LOCATION — DAY', screenplay_text:''});
    await reload(r.id);
  }

  if (!episode) return <Empty title="Create an episode to start writing." body="Give the story somewhere to happen, then put a character under pressure."/>;

  return (
    <div className="write-layout">
      <aside className="scene-rail">
        <div className="rail-head">
          <div><span>Scenes</span><small>{scenes.length} in this episode</small></div>
          <button className="mini-button" onClick={addScene} aria-label="New scene">＋</button>
        </div>
        <div className="scene-scroll">
          {scenes.map(s=>{
            const isActive=s.id===selected?.id;
            return <button key={s.id} className={`scene-item ${isActive?'active':''}`} onClick={()=>setSceneId(s.id)}>
              <span className="scene-index">{String(s.scene_no).padStart(2,'0')}</span>
              <span className="scene-item-copy"><b>{s.slugline || 'Untitled scene'}</b><small>{s.choice || s.scene_want || 'No structural note yet'}</small></span>
            </button>
          })}
        </div>
        <button className="rail-add" onClick={addScene}>＋ <span>New scene</span></button>
      </aside>

      <main className="writer-canvas">
        {selected ? <div className="writer-shell">
          <div className="writer-toolbar">
            <div className="writer-location"><span className="eyebrow">Episode {episode.number}</span><b>Scene {String(selected.scene_no).padStart(2,'0')}</b></div>
            <div className="writer-toolbar-actions">
              <div className="writer-view-switch" role="group" aria-label="Writing view">
                <button type="button" className={viewMode==='edit'?'active':''} aria-pressed={viewMode==='edit'} onClick={()=>chooseView('edit')}>Edit</button>
                <button type="button" className={viewMode==='page'?'active':''} aria-pressed={viewMode==='page'} onClick={()=>chooseView('page')}>Page</button>
              </div>
              <div className={`save-state ${saveState}`}><i/>{saveState==='saving'?'Saving':saveState==='offline'?'Saved on this device':'Saved'}</div>
            </div>
          </div>

          {viewMode==='edit'
            ? <section className="writer-paper">
                <input className="slugline-input" value={draft.slugline || ''} onChange={e=>change('slugline', e.target.value)} aria-label="Scene heading" placeholder="INT. LOCATION — DAY"/>
                <div className="paper-rule"/>
                <textarea className="screenplay-editor" value={draft.screenplay_text || ''} onChange={e=>change('screenplay_text', e.target.value)} placeholder="Write the scene…" spellCheck="true"/>
              </section>
            : <ScreenplayPage slugline={draft.slugline || ''} text={draft.screenplay_text || ''}/>}

          <button className={`structure-toggle ${structureOpen?'active':''}`} onClick={()=>setStructureOpen(v=>!v)}>
            <span className="structure-toggle-main"><i/><span><b>Scene structure</b><small>{draft.scene_want || draft.pressure || draft.choice ? 'The machinery under the page' : 'Add only what helps you write the next beat'}</small></span></span>
            <span className="structure-toggle-meta">{structureOpen?'Close':'Want · Pressure · Choice'} <b>{structureOpen?'↑':'↓'}</b></span>
          </button>
          {structureOpen && <StructurePanel draft={draft} change={change} characters={workspace.characters || []}/>}
        </div> : <Empty title="No scenes yet." body="A blank wall is useful for about thirty seconds." action="Create the first scene" onAction={addScene}/>}
      </main>
    </div>
  );
}

function ScreenplayPage({slugline, text}) {
  const blocks = useMemo(()=>parseFountain(text), [text]);
  const visible = blocks.filter(block=>block.type!=='note');

  return <section className="screenplay-page-frame" aria-label="Typeset screenplay page preview">
    <div className="screenplay-page">
      <div className="fountain-line fountain-scene">{slugline || 'INT. LOCATION — DAY'}</div>
      {visible.length
        ? visible.map((block,index)=>{
            if(block.type==='blank') return <div key={index} className="fountain-blank" aria-hidden="true"/>;
            return <div key={index} className={`fountain-line fountain-${block.type}`}>{block.text}</div>;
          })
        : <div className="fountain-empty">The page is waiting for the scene.</div>}
    </div>
  </section>;
}

function StructurePanel({draft, change, characters}) {
  return <section className="structure-panel">
    <div className="structure-core">
      <Field className="structure-field want" label="Want" hint="The objective" value={draft.scene_want} onChange={v=>change('scene_want',v)} placeholder="What are they trying to get?"/>
      <Field className="structure-field pressure" label="Pressure" hint="The narrowing" value={draft.pressure} onChange={v=>change('pressure',v)} placeholder="What removes the easy option?"/>
      <Field className="structure-field choice" label="Choice" hint="The turn" value={draft.choice} onChange={v=>change('choice',v)} placeholder="What do they decide or commit to?"/>
    </div>
    <details className="advanced-details">
      <summary><span>Deeper structure</span><small>Open when the scene needs diagnosis</small></summary>
      <div className="form-grid">
        <label>POV / pressure character<select value={draft.pov_character_id || ''} onChange={e=>change('pov_character_id', e.target.value || null)}><option value="">—</option>{characters.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        <Field label="Opening behavior / image" value={draft.opening_behavior} onChange={v=>change('opening_behavior',v)}/>
        <Field label="Obstacle" value={draft.obstacle} onChange={v=>change('obstacle',v)}/>
        <Field label="Tactic" value={draft.tactic} onChange={v=>change('tactic',v)}/>
        <Field label="Starting state" value={draft.start_state} onChange={v=>change('start_state',v)}/>
        <Field label="Ending state" value={draft.end_state} onChange={v=>change('end_state',v)}/>
        <Field label="Cut on…" value={draft.cut_on} onChange={v=>change('cut_on',v)}/>
        <Field label="Notes" value={draft.notes} onChange={v=>change('notes',v)}/>
      </div>
    </details>
  </section>
}

function Field({label,value,onChange,placeholder='',hint='',className=''}) {
  return <label className={className}><span className="field-label"><b>{label}</b>{hint&&<small>{hint}</small>}</span><textarea rows="2" value={value || ''} placeholder={placeholder} onChange={e=>onChange(e.target.value)}/></label>
}

function Empty({title,body,action,onAction}) {
  return <div className="empty-state"><div className="empty-orbit"><span>P</span><i/><span>R</span></div><h2>{title}</h2>{body&&<p className="muted">{body}</p>}{action&&<button className="button" onClick={onAction}>{action}</button>}</div>
}
