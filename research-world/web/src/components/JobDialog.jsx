import { useEffect, useState } from "react";
import { useWorld } from "../context/WorldContext";
import { isAdmittedNode } from "../utils";
import { Field, FormActions } from "./Field";
import { Modal } from "./Modal";

const EMPTY = { agent_id: "", kind: "research", subject_id: "", prompt: "" };

function agentCapabilities(agent) {
  return agent.capabilities;
}

function supports(agent, kind) {
  return agentCapabilities(agent).map((value) => String(value).trim()).includes(kind);
}

function JobFields({ form, update, updateKind, agents, subjects }) {
  return <>
    <Field label="智能体"><select required value={form.agent_id} onChange={update("agent_id")}><option value="" disabled>{agents.length ? "请选择智能体" : "没有兼容的智能体"}</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></Field>
    <Field label="任务类型"><select value={form.kind} onChange={updateKind}><option value="plan">规划</option><option value="research">研究</option><option value="html_report">HTML 报告</option></select></Field>
    <Field label="研究对象"><select required value={form.subject_id} onChange={update("subject_id")}><option value="" disabled>请选择已采纳节点</option>{subjects.map((node) => <option key={node.id} value={node.id}>{node.title}</option>)}</select></Field>
    <Field label="任务要求"><textarea required rows="6" value={form.prompt} onChange={update("prompt")} placeholder="说明研究任务、证据标准和预期输出。" /></Field>
  </>;
}

export function JobDialog({ open, onClose, subjectId = "", kind = "research" }) {
  const { data, projectId, command } = useWorld(); const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const subjects = data.nodes.filter(isAdmittedNode);
  const availableAgents = data.agents.filter((agent) => supports(agent, form.kind));
  useEffect(() => { if (open) setForm({ ...EMPTY, agent_id: data.agents.find((agent) => supports(agent, kind))?.id || "", subject_id: subjects.some((node) => node.id === subjectId) ? subjectId : subjects[0]?.id || "", kind }); }, [open, subjectId, kind]);
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const updateKind = (event) => { const nextKind = event.target.value; setForm({ ...form, kind: nextKind, agent_id: data.agents.find((agent) => supports(agent, nextKind))?.id || "" }); };
  const submit = async (event) => {
    event.preventDefault(); setSubmitting(true);
    try { await command("enqueue_job", { project_id: projectId, ...form }); onClose(); }
    catch {}
    finally { setSubmitting(false); }
  };
  return <Modal title="添加智能体任务" open={open} onClose={onClose}><form className="form-stack" onSubmit={submit}>
    <JobFields form={form} update={update} updateKind={updateKind} agents={availableAgents} subjects={subjects} />
    <FormActions onCancel={onClose} submitting={submitting} submitLabel="加入队列" />
  </form></Modal>;
}
