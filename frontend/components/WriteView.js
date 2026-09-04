'use client';
import {useEffect, useMemo, useRef, useState} from 'react';
import {create, patch} from '@/lib/api';

const blank = {slugline:'', screenplay_text:'', opening_behavior:'', scene_want:'', obstacle:'', tactic:'', pressure:'', choice:'', start_state:'', end_state:'', cut_on:'', notes:'', moral_delta:0, pov_character_id:null};

export default function WriteView({workspace, episode, sceneId, setSceneId, reload}) {
  const scenes = useMemo(() => (workspace?.scenes || []).filter(s=>s.episode_id===episode?.id).sort((a,b)=>a.scene_no-b.scene_no), [workspace, episode]);
  const selected = scenes.find(s=>s.id===sceneId) || scenes[0];
  const [draft, setDraft] = useState(selected || blank);
  const [structureOpen, setStructureOpen] = useState(false);
  const [saveState, setSaveState] = useState('saved');
  const timer = useRef(null);

  useEffect(()=>{
    if (selected) {
      const cached = typeof window !== 'undefined' ? localStorage.getItem(`pressure-room-draft:${selected.id}`) : null;
      setDraft(cached ? {...selected, screenplay_text: cached} : selected);
      setSceneId(selected.id);
    } else setDraft(blank);
  }, [selected?.id]);

  function change(key, value) {
    const next = {...draft, [key]: value}; setDraft(next);
    if (key==='screenplay_text' && selected?.id) localStorage.setItem(`pressure-room-draft:${selected.id}`, value);
    if (!selected?.id) return;
    setSaveState('saving');
    clearTimeout(timer.current);
    timer.current = setTimeout(async ()=>{
      const fields = ['slugline','screenplay_text','opening_behavior','scene_want','obstacle','tactic','pressure','choice','start_state','end_state','cut_on','notes','moral_delta','pov_character_id'];
      const payload = Object.fromEntries(fields.map(k=>[k,next[k] ?? '']));
      payload.pov_character_id = next.pov_character_id || null;
      payload.moral_delta = Number(next.moral_delta || 0);
      try { await patch('scenes', selected.id, payload); setSaveState('saved'); localStorage.removeItem(`pressure-room-draft:${selected.id}`); }
      catch { setSaveState('offline'); }
    }, 750);
  }

  async function addScene() {
    if (!episode) return;
    const scene_no = (scenes.at(-1)?.scene_no || 0) + 1;
    const r = await create(`/episodes/${episode.id}/scenes`, {scene_no, slugline:'INT. LOCATION — DAY', screenplay_text:''});
    await reload(r.id);
  }

  if (!episode) return <Empty title="Create an episode to start writing."/>;

  return (
    <div className="write-layout">
      <aside className="scene-rail">
        <div className="rail-head"><span>Scenes</span><button className="mini-button" onClick={addScene}>＋</button></div>
        <div className="scene-scroll">
          {scenes.map(s=><button key={s.id} className={`scene-item ${s.id===selected?.id?'active':''}`} onClick={()=>setSceneId(s.id)}><b>{String(s.scene_no).padStart(2,'0')}</b><span>{s.slugline || 'Untitled scene'}</span></button>)}
        </div>
        <button className="button ghost full" onClick={addScene}>＋ New scene</button>
      </aside>

      <main className="writer-canvas">
        {selected ? <>
          <div className="writer-toolbar">
            <div className="scene-number">SCENE {String(selected.scene_no).padStart(2,'0')}</div>
            <div className={`save-state ${saveState}`}>{saveState==='saving'?'Saving…':saveState==='offline'?'Saved locally':'Saved'}</div>
          </div>
          <input className="slugline-input" value={draft.slugline || ''} onChange={e=>change('slugline', e.target.value)} aria-label="Scene heading"/>
          <textarea className="screenplay-editor" value={draft.screenplay_text || ''} onChange={e=>change('screenplay_text', e.target.value)} placeholder="Write the scene…" spellCheck="true"/>
          <button className={`structure-toggle ${structureOpen?'active':''}`} onClick={()=>setStructureOpen(v=>!v)}>
            <span>Structure</span><span>{structureOpen?'Hide':'Want · Pressure · Choice'}</span>
          </button>
          {structureOpen && <StructurePanel draft={draft} change={change} characters={workspace.characters || []}/>} 
        </> : <Empty title="No scenes yet." action="Create the first scene" onAction={addScene}/>} 
      </main>
    </div>
  );
}

function StructurePanel({draft, change, characters}) {
  return <section className="structure-panel">
    <div className="three-up">
      <Field label="Want" value={draft.scene_want} onChange={v=>change('scene_want',v)} placeholder="What do they want?"/>
      <Field label="Pressure" value={draft.pressure} onChange={v=>change('pressure',v)} placeholder="What narrows their options?"/>
      <Field label="Choice" value={draft.choice} onChange={v=>change('choice',v)} placeholder="What do they decide?"/>
    </div>
    <details className="advanced-details">
      <summary>Advanced structure</summary>
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

function Field({label,value,onChange,placeholder=''}) { return <label>{label}<textarea rows="2" value={value || ''} placeholder={placeholder} onChange={e=>onChange(e.target.value)}/></label> }
function Empty({title,action,onAction}) { return <div className="empty-state"><div className="empty-mark">PR</div><h2>{title}</h2>{action&&<button className="button" onClick={onAction}>{action}</button>}</div> }
