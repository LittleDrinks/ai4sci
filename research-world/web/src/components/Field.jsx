export function Field({ label, children, hint }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}

export function FormActions({ onCancel, submitting, submitLabel = "保存" }) {
  return <div className="form-actions"><button type="button" className="button secondary" onClick={onCancel}>取消</button><button className="button primary" disabled={submitting}>{submitting ? "处理中..." : submitLabel}</button></div>;
}
