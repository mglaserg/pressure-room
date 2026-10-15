'use client';
import {useEffect, useMemo, useRef, useState} from 'react';
import {create, localApi, patch, remoteApi, remove} from '@/lib/api';
import {createDraftSaver, flushDrafts} from '@/lib/draft-saver.mjs';
import {downloadBlob} from '@/lib/portable.mjs';
import {parseFountain} from '@/lib/fountain.mjs';

const blank = {slugline:'', screenplay_text:'', opening_behavior:'', scene_want:'', obstacle:'', tactic:'', pressure:'', choice:'', start_state:'', end_state:'', cut_on:'', notes:'', audience_knows:'', audience_waits_for:'', withheld_information:'', game_premise:'', game_rule:'', game_restriction:'', game_escalation:'', game_consequence:'', moral_delta:0, pov_character_id:null};

export default function WriteView({workspace, episode, sceneId, setSceneId, reload, storageScope, onSceneSaved}) {
  const scenes = useMemo(() => (workspace?.scenes || []).filter(s=>s.episode_id===episode?.id).sort((a,b)=>a.scene_no-b.scene_no), [workspace, episode]);
  const selected = scenes.find(s=>s.id===sceneId) || scenes[0];
  const writingMode = workspace?.project?.writing_mode || 'screenplay';
  const unitName=writingMode==='novel'?'Chapter':writingMode==='sketch'?'Beat':'Scene';
  const episodeNoun=writingMode==='novel'?'part':writingMode==='sketch'?'set':'episode';
  const [draft, setDraft] = useState(selected || blank);
  const [focus,setFocus]=useState(false);
  const [structureOpen, setStructureOpen] = useState(false);
  const [saveState, setSaveState] = useState('saved');
  const [viewMode, setViewMode] = useState('write');
  const [actionMessage,setActionMessage]=useState('');
  const [sceneBusy,setSceneBusy]=useState(false);
  const sceneCreating = useRef(false);
  const saver = useRef(null);
  const editorRef = useRef(null);

  useEffect(()=>{
    let active = true;
    if (!selected) { setDraft(blank); return; }
    let revision=workspace.revision;
    let recordVersion=selected.version||1;
    const instance = createDraftSaver({
      key: `pressure-room-draft-v2:${storageScope}:${selected.id}`,
      storage: {
        getItem: key => localStorage.getItem(key),
        setItem: (key, value) => localStorage.setItem(key, value),
        removeItem: key => localStorage.removeItem(key),
      },
      send: async payload => {
        const saveApi = storageScope.startsWith('local:') ? localApi : remoteApi;
        const data={...payload};delete data._base;
        const result=await saveApi(`/scenes/${selected.id}`, {method:'PATCH',revision,headers:{'X-Record-Version':String(recordVersion)},body:JSON.stringify({data})});
        revision=result.revision||revision;recordVersion=result.record_version||recordVersion+1;
        onSceneSaved(selected.id,{...data,version:recordVersion},result);
        return result;
      },
      onState: state => { if (active) setSaveState(state); },
    });
    saver.current = instance;
    const recovered = instance.recover();
    setDraft(recovered ? {...selected, ...recovered} : selected);
    setSaveState(recovered ? 'offline' : 'saved');
    setSceneId(selected.id);
    if(recovered){
      const base=recovered._base;
      const matches=Object.keys(blank).every(k=>(base?.[k]??blank[k])===(selected[k]??blank[k]));
      if(base&&matches)instance.update(recovered);
      else {instance.pause();instance.update(recovered);}
    }
    const flush = () => { void instance.flush(); };
    const onVisibility = () => { if (document.visibilityState === 'hidden') flush(); };
    document.addEventListener('visibilitychange', onVisibility);
    const beforeUnload = event => {
      if (instance.isPending()) { event.preventDefault(); event.returnValue = ''; }
      flush();
    };
    window.addEventListener('pagehide', flush);
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      active = false;
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pagehide', flush);
      window.removeEventListener('beforeunload', beforeUnload);
      void instance.release();
    };
  }, [selected?.id, storageScope]);

  function chooseView(nextMode) {
    setViewMode(nextMode);
    try { localStorage.setItem('pressure-room-write-view', nextMode); } catch {}
  }

  useEffect(()=>{
    const editor=editorRef.current;
    if(!editor||viewMode!=='write')return;
    if(window.CSS?.supports?.('field-sizing','content')){
      editor.style.height='';
      return;
    }
    const frame=requestAnimationFrame(()=>{
      editor.style.height='auto';
      editor.style.height=`${Math.max(editor.scrollHeight,420)}px`;
    });
    return()=>cancelAnimationFrame(frame);
  },[draft.screenplay_text,viewMode,selected?.id,writingMode]);

  async function changeWritingMode(nextMode) {
    if(nextMode===writingMode)return;
    setActionMessage('');
    try{
      await flushDrafts();
      await patch('projects',workspace.project.id,{writing_mode:nextMode});
      await reload(selected?.id);
      chooseView('write');
    }catch(err){setActionMessage(err.message||'Could not change writing mode.');}
  }

  function insertScreenplayElement(kind) {
    const editor=editorRef.current;
    if(!editor)return;
    const value=draft.screenplay_text||'';
    const start=editor.selectionStart??value.length;
    const end=editor.selectionEnd??start;
    const before=value.slice(0,start);
    const after=value.slice(end);
    const needsBreak=before && !before.endsWith('\n\n');
    const templates={scene:'INT. LOCATION — DAY',action:'Action',character:'CHARACTER',parenthetical:'(quietly)',dialogue:'Dialogue',transition:'CUT TO:'};
    const text=`${needsBreak?'\n\n':''}${templates[kind]||''}`;
    change('screenplay_text',before+text+after);
    requestAnimationFrame(()=>{const pos=start+text.length;editor.focus();editor.setSelectionRange(pos,pos)});
  }

  function change(key, value) {
    const next = {...draft, [key]: value};
    setDraft(next);
    if (!selected?.id) return;
    const payload = Object.fromEntries(Object.keys(blank).map(k=>[k,next[k] ?? '']));
    payload.pov_character_id = next.pov_character_id || null;
    payload.moral_delta = Number(next.moral_delta || 0);
    payload._base=Object.fromEntries(Object.keys(blank).map(k=>[k,selected[k]??blank[k]]));
    saver.current?.update(payload);
  }

  async function saveNow() {
    setActionMessage('');
    try { await flushDrafts(); }
    catch (err) { setActionMessage(err.message || 'This scene could not be saved. Your draft remains on this device.'); }
  }

  useEffect(()=>{
    const onKeyDown=event=>{
      if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){
        event.preventDefault();
        void saveNow();
      }
      if(event.key==='Escape'&&focus)setFocus(false);
    };
    window.addEventListener('keydown',onKeyDown);
    return()=>window.removeEventListener('keydown',onKeyDown);
  },[focus]);

  async function switchScene(id) {
    if (!id || id === selected?.id || sceneCreating.current) return;
    sceneCreating.current = true;
    setSceneBusy(true);
    setActionMessage('');
    try {
      await flushDrafts();
      setSceneId(id);
    } catch (err) { setActionMessage(err.message || 'Save the current scene before switching.'); }
    finally { sceneCreating.current = false; setSceneBusy(false); }
  }

  async function addScene() {
    if (!episode || sceneCreating.current) return;
    sceneCreating.current = true;
    setSceneBusy(true);
    setActionMessage('');
    try {
      await flushDrafts();
      const scene_no = Math.max(0, ...scenes.map(scene => Number(scene.scene_no) || 0)) + 1;
      const initialTitle=writingMode==='novel'?'Untitled chapter':writingMode==='sketch'?'Opening beat':'INT. LOCATION — DAY';
      const r = await create(`/episodes/${episode.id}/scenes`, {scene_no, slugline:initialTitle, screenplay_text:''});
      await reload(r.id);
      chooseView('write');
    } catch (err) {
      setActionMessage(err.message || 'Could not create a scene. Try again.');
    } finally {
      sceneCreating.current = false;
      setSceneBusy(false);
    }
  }

  async function deleteScene() {
    if (!selected) return;
    const label = selected.slugline || `${unitName} ${selected.scene_no}`;
    if (sceneBusy || !window.confirm(`Delete ${unitName} ${selected.scene_no} · ${label}? This cannot be undone.`)) return;
    const index=scenes.findIndex(scene=>scene.id===selected.id);
    const nextScene=scenes[index+1]||scenes[index-1]||null;
    setActionMessage('');
    try {
      await flushDrafts();
      await remove('scenes', selected.id);
      saver.current?.discard();
      setSceneId(nextScene?.id||'');
      await reload(nextScene?.id);
    } catch (err) {
      setActionMessage(err.message||'Could not delete the scene.');
    }
  }

  if (!episode) return <Empty title={`Create a ${episodeNoun} to start writing.`} body="Give the story somewhere to happen, then put a character under pressure."/>;

  const titleLabel=writingMode==='novel'?'Chapter or section title':writingMode==='sketch'?'Sketch beat':'Scene heading';
  const titlePlaceholder=writingMode==='novel'?'Chapter One':writingMode==='sketch'?'The unusual thing arrives':'INT. LOCATION — DAY';
  const bodyPlaceholder=writingMode==='novel'?'Write the chapter…':writingMode==='sketch'?'Write the sketch. The labs can wait…':'Write the scene…';

  return (
    <div className={`write-layout ${focus?'writing-focus':''}`}>
      <aside className="scene-rail">
        <div className="rail-head">
          <div><span>{unitName}s</span><small>{scenes.length} in this {episodeNoun}</small></div>
          <button className="mini-button" onClick={addScene} disabled={sceneBusy} type="button" aria-label={`New ${unitName.toLowerCase()}`} title={`New ${unitName.toLowerCase()}`}>＋</button>
        </div>
        <div className="scene-scroll">
          {scenes.map(s=>{
            const isActive=s.id===selected?.id;
            return <button key={s.id} className={`scene-item ${isActive?'active':''}`} aria-current={isActive?'true':undefined} disabled={sceneBusy} onClick={()=>void switchScene(s.id)}>
              <span className="scene-index">{String(s.scene_no).padStart(2,'0')}</span>
              <span className="scene-item-copy"><b>{s.slugline || 'Untitled scene'}</b><small>{s.choice || s.scene_want || 'No structural note yet'}</small></span>
            </button>
          })}
        </div>
        <button className="rail-add" type="button" disabled={sceneBusy} onClick={addScene}>＋ <span>{sceneBusy?'Creating…':`New ${unitName.toLowerCase()}`}</span></button>
      </aside>

      <main className="writer-canvas">
        {actionMessage&&<p className="form-message writer-action-message" role="alert">{actionMessage}</p>}
        {selected ? <div className="writer-shell">
          <div className="mode-bar" aria-label="Writing mode">
            <span>Writing as</span>
            {['screenplay','sketch','novel'].map(mode=><button type="button" key={mode} className={writingMode===mode?'active':''} aria-pressed={writingMode===mode} onClick={()=>void changeWritingMode(mode)}>{mode[0].toUpperCase()+mode.slice(1)}</button>)}
          </div>
          <div className="writer-toolbar">
            <div className="writer-location"><span className="eyebrow">Episode {episode.number}</span><b>{unitName} {String(selected.scene_no).padStart(2,'0')}</b></div>
            <div className="writer-toolbar-actions">
              <button type="button" className="quiet-action mobile-new-scene" disabled={sceneBusy} onClick={addScene}>＋ {unitName}</button>
              <button className="quiet-action focus-button" aria-pressed={focus} onClick={()=>setFocus(v=>!v)}>{focus?'Exit focus':'Focus'}</button>
              {!focus&&<button className="quiet-action danger-ghost" type="button" onClick={deleteScene}>Delete {unitName.toLowerCase()}</button>}
              {focus&&<select className="focus-scene-select" aria-label={`${unitName} in focus mode`} value={selected.id} onChange={e=>void switchScene(e.target.value)}>{scenes.map(s=><option value={s.id} key={s.id}>{unitName} {s.scene_no}</option>)}</select>}
              {writingMode==='screenplay'&&<div className="writer-view-switch" role="group" aria-label="Writing view">
                <button type="button" className={viewMode==='write'?'active':''} aria-pressed={viewMode==='write'} onClick={()=>chooseView('write')}>Write</button>
                <button type="button" className={viewMode==='preview'?'active':''} aria-pressed={viewMode==='preview'} onClick={()=>chooseView('preview')}>Preview</button>
              </div>
              }
              <button type="button" className="quiet-action mobile-save-scene" onClick={saveNow} disabled={sceneBusy || saveState==='saving'}>Save</button>
              <div className={`save-state ${saveState}`} role="status" aria-live="polite"><i/>{saveState==='saving'?'Saving…':saveState==='conflict'?'Conflict · draft kept here':saveState==='pending'?'Save pending':saveState==='offline'?'Draft on device · save failed':saveState==='uncached'?'Backup unavailable · keep this tab open':storageScope.startsWith('local:')?'Saved in this browser':'Saved to Supabase'}{(saveState==='offline'||saveState==='uncached')&&<button className="quiet-action" onClick={()=>saver.current?.flush()}>Retry</button>}</div>
            </div>
          </div>

          {['conflict','offline','uncached'].includes(saveState)&&<div className="draft-recovery" role="alert"><p>Your draft is still on this page. Keep a copy before loading another version.</p><div className="form-actions"><button className="button secondary" onClick={()=>downloadBlob(JSON.stringify(draft,null,2),`scene-${selected.scene_no}-recovery.json`,'application/json')}>Download draft</button><button className="button secondary" onClick={()=>{downloadBlob(JSON.stringify(draft,null,2),`scene-${selected.scene_no}-recovery.json`,'application/json');saver.current?.discard();window.location.reload()}}>Download draft & load saved story</button></div></div>}
          {viewMode==='write'||writingMode!=='screenplay'
            ? <section className={`writer-paper writing-mode-${writingMode}`}>
                <label className="document-title-label"><span>{titleLabel}</span><input className="slugline-input" value={draft.slugline || ''} onChange={e=>change('slugline', e.target.value)} onBlur={()=>void saver.current?.flush()} aria-label={titleLabel} placeholder={titlePlaceholder}/></label>
                <div className="paper-rule"/>
                {writingMode==='screenplay'&&<div className="screenplay-elements" role="toolbar" aria-label="Insert screenplay element">{[['scene','Scene'],['action','Action'],['character','Character'],['parenthetical','Parenthetical'],['dialogue','Dialogue'],['transition','Transition']].map(([kind,label])=><button type="button" key={kind} onClick={()=>insertScreenplayElement(kind)}>{label}</button>)}</div>}
                <textarea ref={editorRef} className="screenplay-editor document-editor" aria-label={writingMode==='screenplay'?'Scene screenplay':`${unitName} text`} value={draft.screenplay_text || ''} onChange={e=>change('screenplay_text', e.target.value)} onBlur={()=>void saver.current?.flush()} placeholder={bodyPlaceholder} spellCheck="true"/>
              </section>
            : <><button className="quiet-action mobile-edit-scene" type="button" onClick={()=>chooseView('write')}>Edit this scene</button><ScreenplayPage slugline={draft.slugline || ''} text={draft.screenplay_text || ''}/></>}

          {writingMode==='sketch'&&!focus&&<CreativeLabs draft={draft} change={change}/>}

          <button hidden={focus} aria-expanded={structureOpen} className={`structure-toggle ${structureOpen?'active':''}`} onClick={()=>setStructureOpen(v=>!v)}>
            <span className="structure-toggle-main"><i/><span><b>Scene structure</b><small>{draft.scene_want || draft.pressure || draft.choice ? 'The machinery under the page' : 'Add only what helps you write the next beat'}</small></span></span>
            <span className="structure-toggle-meta">{structureOpen?'Close':'Want · Pressure · Choice'} <b>{structureOpen?'↑':'↓'}</b></span>
          </button>
          {structureOpen && !focus && <StructurePanel draft={draft} change={change} characters={workspace.characters || []}/>}
        </div> : <Empty title={`No ${unitName.toLowerCase()}s yet.`} body="A blank page is useful for about thirty seconds." action={sceneBusy?"Creating…":`Create the first ${unitName.toLowerCase()}`} onAction={addScene}/>}
      </main>
    </div>
  );
}

function CreativeLabs({draft,change}) {
  const tensionPrompts=[
    draft.game_rule&&draft.game_restriction?`If “${draft.game_rule}” is the rule, what becomes costly because “${draft.game_restriction}”?`:'What simple rule makes the ordinary task difficult?',
    draft.scene_want?`What is the one action that would solve “${draft.scene_want}” — and why can’t they take it?`:'What does the central character need right now?',
    draft.game_escalation?'Can each repeat obey the same rule while raising the status, cost, or exposure?':'What repeats, and what changes each time?',
  ];
  return <section className="creative-labs" aria-label="Optional sketch development tools">
    <details className="lab-card"><summary><span><b>Game Lab</b><small>Rule · restriction · escalation</small></span><em>Optional</em></summary><p>Capture discoveries without leaving the page. These notes never become a required form.</p><div className="form-grid">
      <Field label="Premise / unusual thing" value={draft.game_premise} onChange={v=>change('game_premise',v)} placeholder="What breaks the ordinary world?"/>
      <Field label="The game or rule" value={draft.game_rule} onChange={v=>change('game_rule',v)} placeholder="What repeatable comic logic governs the scene?"/>
      <Field label="Restriction" value={draft.game_restriction} onChange={v=>change('game_restriction',v)} placeholder="What can’t or won’t the character do?"/>
      <Field label="Escalation pattern" value={draft.game_escalation} onChange={v=>change('game_escalation',v)} placeholder="How does repetition vary and get more costly?"/>
      <Field label="Consequence / ending" value={draft.game_consequence} onChange={v=>change('game_consequence',v)} placeholder="What final cost, reversal, or image completes the pattern?"/>
    </div></details>
    <details className="lab-card tension-lab"><summary><span><b>Tension Lab</b><small>Want meets an immovable rule</small></span><em>Optional</em></summary><p>Questions inspired by John Wright’s emphasis on restriction, tension, and consequence—not a score and not a formula.</p><ol>{tensionPrompts.map((prompt,index)=><li key={index}>{prompt}</li>)}</ol></details>
  </section>;
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
    <details className="advanced-details suspense-details">
      <summary><span>Suspense engine</span><small>Audience knowledge · waiting · withheld information</small></summary>
      <div className="form-grid">
        <Field label="What does the audience know?" hint="Useful when the character does not" value={draft.audience_knows} onChange={v=>change('audience_knows',v)} placeholder="The audience saw the clerk keep a copy…"/>
        <Field label="What is the audience waiting for?" hint="The live question" value={draft.audience_waits_for} onChange={v=>change('audience_waits_for',v)} placeholder="Will Mara realize she has been recorded?"/>
        <Field label="What are we withholding?" hint="Information delayed on purpose" value={draft.withheld_information} onChange={v=>change('withheld_information',v)} placeholder="Who ordered the audit…"/>
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
