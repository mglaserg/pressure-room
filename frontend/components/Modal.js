'use client';

export default function Modal({open, title, onClose, children, wide=false}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section className={`modal-card ${wide ? 'wide' : ''}`} onMouseDown={(e)=>e.stopPropagation()}>
        <header className="modal-head">
          <div><div className="eyebrow">Pressure Room</div><h2>{title}</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Close">×</button>
        </header>
        {children}
      </section>
    </div>
  );
}
