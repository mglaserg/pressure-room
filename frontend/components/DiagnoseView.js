'use client';
import {useEffect, useState} from 'react';
import {api} from '@/lib/api';

export default function DiagnoseView({episode}) {
  const [section,setSection]=useState('mri'); const [data,setData]=useState(null);
  useEffect(()=>{if(episode) api(`/episodes/${episode.id}/diagnostics`).then(setData).catch(()=>setData(null))},[episode?.id]);
  if(!episode)return <div className="empty-state"><h2>Create an episode to diagnose.</h2></div>;
  const items=[['mri','Story MRI'],['pressure','Pressure Lab'],['questions','Room Questions']];
  return <div className="focus-page"><div className="subnav">{items.map(([id,label])=><button key={id} className={section===id?'active':''} onClick={()=>setSection(id)}>{label}</button>)}</div>
    <section className="focus-card">{!data?<p className="muted">Reading the story…</p>:section==='mri'?<MRI rows={data.mri}/>:section==='pressure'?<Pressure moves={data.pressure_moves}/>:<Questions questions={data.questions}/>}</section>
  </div>
}
function MRI({rows}){return <><div className="eyebrow">Story MRI</div><h1>See the hidden shape.</h1><p className="muted">These are prompts for judgment, not quality scores.</p><div className="mri-grid">{rows.map(r=><div className="mri-row" key={r.scene}><b>{r.scene}</b><Meter label="Pressure" value={r.pressure}/><Meter label="Moral" value={r.moral_compromise}/><Meter label="Options" value={r.option_space} reverse/></div>)}</div></>}
function Meter({label,value,reverse}) {return <div className="meter"><span>{label}</span><div><i style={{width:`${value*10}%`}} className={reverse?'reverse':''}/></div><b>{value}</b></div>}
function Pressure({moves}){return <><div className="eyebrow">Pressure Lab</div><h1>Make the solution stop working.</h1><p className="lead-quote">Pressure is not louder conflict. It is shrinking the character’s safe option-space.</p><div className="pressure-grid">{moves.map(m=><article className="inner-card" key={m.name}><div className="eyebrow">Pressure move</div><h3>{m.name}</h3><p>{m.description}</p></article>)}</div></>}
function Questions({questions}){return <><div className="eyebrow">Supplementary</div><h1>Questions for the room.</h1><p className="muted">The assistant does not write the story. It interrogates the structure.</p><div className="question-list">{questions.map((q,i)=><article key={q}><span>{String(i+1).padStart(2,'0')}</span><p>{q}</p></article>)}</div></>}
