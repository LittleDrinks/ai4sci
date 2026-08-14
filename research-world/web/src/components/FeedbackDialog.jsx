import { useState } from "react";
import { Field } from "./Field";
import { Modal } from "./Modal";

const LABELS = {
  revise: ["要求修改", "发送反馈"],
  restart: ["根据反馈重新执行", "重新执行"],
  reject: ["拒绝输出", "拒绝"],
  invalidate: ["使节点失效", "确认失效"],
};

export function FeedbackDialog({ action, noun, busy, warning, onClose, onSubmit }) {
  const [feedback, setFeedback] = useState("");
  if (!action) return null;
  const [title, submitLabel] = LABELS[action];
  const placeholder = action === "invalidate" ? "说明此节点不再有效的原因。" : `说明此${noun}需要修改的内容。`;
  const submit = (event) => {
    event.preventDefault();
    onSubmit(feedback.trim());
  };
  return <Modal title={title} open onClose={onClose}><form className="form-stack" onSubmit={submit}>{warning && <div className="impact-warning">{warning}</div>}<Field label={action === "invalidate" ? "原因" : "审核反馈"}><textarea autoFocus required value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder={placeholder} /></Field><div className="form-actions"><button type="button" className="button secondary" onClick={onClose}>取消</button><button className={`button ${action === "reject" || action === "invalidate" ? "danger" : "primary"}`} disabled={busy || !feedback.trim()}>{busy ? "处理中..." : submitLabel}</button></div></form></Modal>;
}
