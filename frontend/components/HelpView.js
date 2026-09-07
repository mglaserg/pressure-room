'use client';

export default function HelpView(){
  return <div className="help-page">
    <section className="hero-card help-hero">
      <div className="hero-watermark">PR</div>
      <div className="eyebrow">The method in sixty seconds</div>
      <h1>Put the character in the room. Close the easy exits.</h1>
      <p>Pressure Room is a writing workspace for seeing why the next scene has to happen. It keeps the writer focused on <b>pressure, choice, consequence, and moral movement</b> without forcing the story into a generic beat sheet.</p>
      <div className="engine-strip"><Engine n="01" label="Want"/><b>→</b><Engine n="02" label="Pressure"/><b>→</b><Engine n="03" label="Choice"/><b>→</b><Engine n="04" label="Bill"/><b>→</b><Engine n="05" label="Change"/></div>
    </section>

    <section className="focus-card start-guide">
      <div className="guide-heading"><div><div className="eyebrow">Start here</div><h2>Your first ten minutes</h2></div><p>Do not fill everything out. Use only what helps the next choice become clearer.</p></div>
      <ol className="steps">
        <Step n="01" title="Create the moral spine" body="What does the character want? What do they believe they will never do?"/>
        <Step n="02" title="Write before diagnosing" body="Stay in Write. Get the scene onto the page before making the structure explain it."/>
        <Step n="03" title="Name the turn" body="Open Scene Structure and capture Want → Pressure → Choice. Close it again."/>
        <Step n="04" title="Make the next scene inevitable" body="Connect the scene with THEREFORE — or let the solution create a new problem with BUT."/>
        <Step n="05" title="Record the bill" body="What changed in the world? What did making that choice do to the character?"/>
        <Step n="06" title="Diagnose later" body="Use Story MRI and Room Questions when the outline needs pressure-testing, not while the scene is alive."/>
      </ol>
    </section>

    <section className="help-grid">
      <Guide symbol="✎" title="Write" body="The screenplay is the primary surface. The app should disappear while the scene is working."/>
      <Guide symbol="⑂" title="Structure" body="Moral spines, causality, bills, branches, and snapshots—one structural task at a time."/>
      <Guide symbol="◌" title="Diagnose" body="Story MRI, pressure moves, and optional room questions. Lenses, never grades."/>
      <Guide symbol="↗" title="Share" body="Send the full project or export a story packet, Markdown notes, or Fountain screenplay."/>
    </section>

    <section className="focus-card friend-card">
      <div><div className="eyebrow">Introduce it to a friend</div><h2>The one-sentence explanation</h2><blockquote>“Pressure Room tracks what a character wants, what pressure makes them choose, and what every choice costs.”</blockquote></div>
      <a className="button secondary" href="/pressure-room-quick-start.md" download>Download quick start</a>
    </section>
  </div>
}

function Engine({n,label}){return <span><small>{n}</small>{label}</span>}
function Step({n,title,body}){return <li><span>{n}</span><div><b>{title}</b><p>{body}</p></div></li>}
function Guide({symbol,title,body}){return <article className="guide-card"><span className="guide-symbol">{symbol}</span><div><h3>{title}</h3><p>{body}</p></div></article>}
