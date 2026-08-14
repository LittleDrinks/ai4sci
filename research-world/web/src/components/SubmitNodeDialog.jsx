import { useEffect, useState } from "react";
import { useWorld } from "../context/WorldContext";
import { isAdmittedNode } from "../utils";
import { Field, FormActions } from "./Field";
import { Modal } from "./Modal";

const EMPTY = { kind: "direction", title: "", summary: "", content: "", dependencies: [] };

function contentValue(value) {
  if (!value.trim()) return {};
  try { return JSON.parse(value); } catch { return { notes: value.trim() }; }
}

function NodeFields({ form, update, dependencies, nodes }) {
  return <>
    <div className="form-grid"><Field label="类型"><select value={form.kind} onChange={update("kind")}><option value="direction">方向</option><option value="hypothesis">假设</option><option value="action">行动</option><option value="result">结果</option><option value="evidence">证据</option></select></Field><Field label="标题"><input required value={form.title} onChange={update("title")} autoFocus /></Field></div>
    <Field label="摘要"><textarea required rows="3" value={form.summary} onChange={update("summary")} /></Field>
    <Field label="数据" hint="输入 JSON；纯文本会自动转为备注字段"><textarea rows="5" className="code-input" value={form.content} onChange={update("content")} placeholder={'{"指标": 0.31, "样本量": 169}'} /></Field>
    <Field label="依赖节点" hint="按住 Ctrl/Cmd 可多选"><select multiple size="5" value={form.dependencies} onChange={dependencies}>{nodes.map((node) => <option key={node.id} value={node.id}>{node.title}</option>)}</select></Field>
  </>;
}

export function SubmitNodeDialog({ open, onClose, initialDependency }) {
  const { data, projectId, command } = useWorld();
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => { if (open) setForm({ ...EMPTY, dependencies: initialDependency ? [initialDependency] : [] }); }, [open, initialDependency]);
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const dependencies = (event) => setForm({ ...form, dependencies: [...event.target.selectedOptions].map((option) => option.value) });
  const submit = async (event) => {
    event.preventDefault(); setSubmitting(true);
    try { await command("submit_node", { project_id: projectId, ...form, content: contentValue(form.content) }); onClose(); }
    catch {}
    finally { setSubmitting(false); }
  };
  return <Modal title="提交研究节点" open={open} onClose={onClose} wide><form className="form-stack" onSubmit={submit}>
    <NodeFields form={form} update={update} dependencies={dependencies} nodes={data.nodes.filter(isAdmittedNode)} />
    <FormActions onCancel={onClose} submitting={submitting} submitLabel="提交审核" />
  </form></Modal>;
}
