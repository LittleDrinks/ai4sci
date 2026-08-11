import { X } from "lucide-react";

export function Modal({ title, open, onClose, children, wide = false }) {
  if (!open) return null;
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
    <section className={`modal ${wide ? "modal-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}>
      <header className="modal-header"><h2>{title}</h2><button className="icon-button" onClick={onClose} title="关闭"><X size={19} /></button></header>
      <div className="modal-body">{children}</div>
    </section>
  </div>;
}
