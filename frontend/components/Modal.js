'use client';
import {useEffect, useId, useRef} from 'react';

<<<<<<< HEAD
export default function Modal({open, title, onClose, children, wide=false, suspended=false}) {
=======
export default function Modal({open, title, onClose, children, wide=false}) {
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
  const dialog = useRef(null);
  const titleId = useId();
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const node = dialog.current;
<<<<<<< HEAD
    if (!open || suspended || !node) return;
=======
    if (!open || !node) return;
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
    const previous = document.activeElement;
    node.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      node.close();
      document.body.style.overflow = overflow;
      previous?.focus();
    };
<<<<<<< HEAD
  }, [open,suspended]);
=======
  }, [open]);
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
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
