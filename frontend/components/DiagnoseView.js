'use client';
import {useEffect, useState} from 'react';
import {api} from '@/lib/api';

const TABS=[['mri','Story MRI','Shape'],['pressure','Pressure Lab','Moves'],['questions','Room Questions','Interrogate']];

export default function DiagnoseView({episode}) {
  const [section,setSection]=useState('mri');
  const [data,setData]=useState(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    setData(null);setError('');
    if(episode) api(`/episodes/${episode.id}/diagnostics`).then(setData).catch(e=>setError(e.message));
  },[episode?.id]);
  if(!episode)return <div className="empty-state"><div className="empty-orbit"><span>P</span><i/><span>R</span></div><h2>Create an episode to diagnose.</h2></div>;
  return <div className="focus-page">
    <div className="subnav diagnose-subnav">{TABS.map(([id,label,note])=><button key={id} className={section===id?'active':''} onClick={()=>setSection(id)}><b>{label}</b><small>{note}</small></button>)}</div>
    <section className="focus-card diagnose-card">
      {error?<div className="empty-state compact-empty"><h2>Diagnostics could not load.</h2><p className="muted">{error}</p></div>:!data?<DiagnosticLoading/>:section==='mri'?<MRI rows={data.mri}/>:section==='pressure'?<Pressure moves={data.pressure_moves}/>:<Questions questions={data.questions}/>}
    </section>
  </div>
}

function DiagnosticLoading(){return <div className="diagnostic-loading"><span className="eyebrow">Reading the episode</span><h2>Looking for the pressure underneath the plot.</h2><div className="loading-lines"><i/><i/><i/></div></div>}

function MRI({rows}){
  const end=rows.at(-1)||{pressure:0,moral_compromise:0,option_space:0};
  return <>
    <div className="focus-heading"><div><div className="eyebrow">Story MRI</div><h1>See the hidden shape.</h1><p className="muted">These are provocations for judgment, not quality scores.</p></div><div className="mri-summary"><Summary label="Pressure" value={end.pressure}/><Summary label="Moral" value={end.moral_compromise}/><Summary label="Options" value={end.option_space}/></div></div>
    <div className="mri-grid">{rows.map(r=><article className="mri-row" key={r.scene}><div className="mri-scene"><span>Scene</span><b>{r.scene.replace(/^S/,'')}</b></div><Meter label="Pressure" value={r.pressure}/><Meter label="Moral compromise" value={r.moral_compromise} tone="moral"/><Meter label="Option-space" value={r.option_space} tone="options"/></article>)}</div>
  </>
}
function Summary({label,value}){return <div><span>{label}</span><b>{value}<small>/10</small></b></div>}
function Meter({label,value,tone=''}) {return <div className={`meter ${tone}`}><div className="meter-copy"><span>{label}</span><b>{value}</b></div><div className="meter-track"><i style={{width:`${Math.max(0,Math.min(10,value))*10}%`}}/></div></div>}

function Pressure({moves}){
  return <>
    <div className="focus-heading"><div><div className="eyebrow">Pressure Lab</div><h1>Make the current solution stop working.</h1><p className="lead-quote">Pressure is not louder conflict. It is shrinking the character’s safe option-space.</p></div></div>
    <div className="pressure-grid">{moves.map((m,i)=><article className="pressure-card" key={m.name}><span className="pressure-number">{String(i+1).padStart(2,'0')}</span><div><div className="eyebrow">Pressure move</div><h3>{m.name}</h3><p>{m.description}</p></div></article>)}</div>
  </>
}

function Questions({questions}){
  return <>
    <div className="focus-heading"><div><div className="eyebrow">Supplementary</div><h1>Questions for the room.</h1><p className="muted">The assistant does not write the story. It asks the question everyone in the room wishes somebody else would ask.</p></div></div>
    <div className="question-list">{questions.map((q,i)=><article key={`${q}-${i}`}><span>{String(i+1).padStart(2,'0')}</span><p>{q}</p></article>)}</div>
  </>
}
