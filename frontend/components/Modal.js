'use client';
import {useEffect, useId, useRef} from 'react';

export default function Modal({open, title, onClose, children, wide=false, suspended=false}) {
  const dialog = useRef(null);
  const titleId = useId();
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const node = dialog.current;
    if (!open || suspended || !node) return;
    const previous = document.activeElement;
    node.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      node.close();
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, [open,suspended]);
  return (
    <dialog ref={dialog} className={`modal-card modal-dialog ${wide ? 'wide' : ''}`}
      aria-labelledby={titleId} onCancel={event => {event.preventDefault(); close.current();}}
      onClick={event => {if (event.target === event.currentTarget) {
        const rect = event.currentTarget.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close.current();
      }}}>
      <header className="modal-head">
        <div><div className="eyebrow">Pressure Room</div><h2 id={titleId}>{title}</h2></div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close">×</button>
      </header>
      {open && children}
    </dialog>
  );
}
