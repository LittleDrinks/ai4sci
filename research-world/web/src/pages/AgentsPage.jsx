import { Bot, Cpu, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyState } from "../components/EmptyState";
import { Field, FormActions } from "../components/Field";
import { Modal } from "../components/Modal";
import { Status } from "../components/Status";
import { useWorld } from "../context/WorldContext";
import { displayLabel, formatTime, shortId } from "../utils";

const CAPABILITIES = ["plan", "research", "html_report", "audit"];
const EMPTY = { name: "", runtime_id: "", model: "", instructions: "", capabilities: CAPABILITIES };

function CapabilityList({ values = [] }) {
  return <div className="capability-list">{values.filter(Boolean).map((item) => <span key={item}>{displayLabel(item)}</span>)}</div>;
}

function RuntimeCard({ runtime }) {
  return <article className="runtime-card"><div className="runtime-icon"><Cpu size={20} /></div><div><div className="card-title"><h3>{runtime.name || runtime.id}</h3><Status value={runtime.status || "offline"} /></div><p>{runtime.sdk || "本地 SDK 运行时"} {runtime.version && `· ${runtime.version}`}</p><CapabilityList values={runtime.capabilities} /><small>最后心跳 {formatTime(runtime.last_seen)}</small></div></article>;
}

function AgentCard({ agent, runtimes }) {
  const runtime = runtimes.find((item) => item.id === agent.runtime_id);
  const status = runtime?.status === "online" ? agent.status : runtime?.status || "offline";
  return <article className="agent-card"><div className="card-title"><div className="agent-name"><Bot size={19} /><h3>{agent.name}</h3></div><Status value={status || "offline"} /></div><p>{agent.instructions || "未设置运行说明。"}</p><dl><div><dt>模型</dt><dd>{agent.model || "运行时默认值"}</dd></div><div><dt>运行时</dt><dd>{runtime?.name || shortId(agent.runtime_id)}</dd></div></dl><CapabilityList values={agent.capabilities} /></article>;
}

function AgentDialog({ open, onClose }) {
  const { data, command } = useWorld();
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => { if (open) setForm({ ...EMPTY, runtime_id: data.runtimes[0]?.id || "" }); }, [open, data.runtimes]);
  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });
  const updateCapabilities = (event) => setForm({ ...form, capabilities: [...event.target.selectedOptions].map((option) => option.value) });
  const submit = async (event) => {
    event.preventDefault(); setSubmitting(true);
    try { await command("create_agent", form); onClose(); }
    catch {}
    finally { setSubmitting(false); }
  };
  return <Modal title="注册逻辑智能体" open={open} onClose={onClose} wide><form className="form-stack" onSubmit={submit}><div className="form-grid"><Field label="名称"><input required value={form.name} onChange={update("name")} autoFocus /></Field><Field label="运行时"><select required value={form.runtime_id} onChange={update("runtime_id")}><option value="" disabled>请选择运行时</option>{data.runtimes.map((runtime) => <option key={runtime.id} value={runtime.id}>{runtime.name || runtime.id}</option>)}</select></Field></div><Field label="模型"><input required value={form.model} onChange={update("model")} placeholder="claude-sonnet-4 / gpt-5 / 运行时默认值" /></Field><Field label="运行说明"><textarea required rows="5" value={form.instructions} onChange={update("instructions")} placeholder="定义智能体的研究职责和证据标准。" /></Field><Field label="能力" hint="按住 Ctrl/Cmd 可多选"><select multiple size="4" value={form.capabilities} onChange={updateCapabilities}>{CAPABILITIES.map((value) => <option key={value} value={value}>{displayLabel(value)}</option>)}</select></Field><FormActions onCancel={onClose} submitting={submitting} submitLabel="注册智能体" /></form></Modal>;
}

export function AgentsPage() {
  const { data } = useWorld();
  const [open, setOpen] = useState(false);
  return <section className="content-page"><header className="page-header"><div><span className="eyebrow">本地 SDK</span><h1>智能体</h1><p>运行时提供执行能力；逻辑智能体定义模型、职责和能力。</p></div><button className="button primary" onClick={() => setOpen(true)} disabled={!data.runtimes.length}><Plus size={17} />注册智能体</button></header><section className="page-section"><div className="section-heading"><h2>检测到的运行时</h2><span>{data.runtimes.length} 个本地运行时</span></div>{data.runtimes.length ? <div className="runtime-grid">{data.runtimes.map((runtime) => <RuntimeCard runtime={runtime} key={runtime.id} />)}</div> : <EmptyState icon={Cpu} title="未连接运行时" detail="启动本地 Worker SDK 以注册此设备。" />}</section><section className="page-section"><div className="section-heading"><h2>逻辑智能体</h2><span>{data.agents.length} 个已注册</span></div>{data.agents.length ? <div className="agent-grid">{data.agents.map((agent) => <AgentCard agent={agent} runtimes={data.runtimes} key={agent.id} />)}</div> : <EmptyState icon={Bot} title="暂无逻辑智能体" detail="连接运行时，然后注册可执行规划、研究和报告任务的智能体。" />}</section><AgentDialog open={open} onClose={() => setOpen(false)} /></section>;
}
