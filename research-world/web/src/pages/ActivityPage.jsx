import { Activity, Check, Clock3, GitBranch, Pause, Play, ThumbsDown, ThumbsUp, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { confirmWorkflow, resolveWorkflow } from "../api";
import { useWorld } from "../context/WorldContext";
import "../activity.css";


const STATUS = { queued: "排队中", running: "运行中", waiting_human: "等待人工", completed: "已完成", paused: "已暂停", failed: "失败" };
const STAGE = { created: "准备", brainstorm: "头脑风暴", execute: "执行", review: "复核", reflect: "反思", complete: "完成", paused: "暂停" };


export function ActivityPage() {
  const { data, loading, refresh, setError } = useWorld();
  const [selectedId, setSelectedId] = useState("");
  useEffect(() => setSelectedId((value) => data.workflows.some((item) => item.id === value) ? value : data.workflows[0]?.id || ""), [data.workflows]);
  const workflow = data.workflows.find((item) => item.id === selectedId);
  if (loading) return <div className="page-loading">正在载入活动...</div>;
  return <section className="rw-activity"><ActivityHeader workflows={data.workflows} /><SlotStrip slots={data.slots} />
    <div className="rw-activity-workspace"><WorkflowList workflows={data.workflows} selectedId={selectedId} onSelect={setSelectedId} />
      <TracePanel workflow={workflow} refresh={refresh} setError={setError} /></div></section>;
}


function ActivityHeader({ workflows }) {
  const active = workflows.filter((item) => ["queued", "running", "waiting_human"].includes(item.status)).length;
  return <header className="rw-activity-header"><div><Activity size={19} /><h1>活动</h1></div><span>{active} 个进行中 · {workflows.length} 个工作流</span></header>;
}


function SlotStrip({ slots = [] }) {
  return <section className="slot-strip" aria-label="执行槽位"><b>执行槽位</b><ol>{slots.map((slot) => <li className={slot.workflow ? "occupied" : "idle"} key={slot.index}>
    <i /><span>槽位 {slot.index}</span><strong>{slot.workflow ? stageLabel(slot.workflow) : "空闲"}</strong></li>)}</ol></section>;
}


function WorkflowList({ workflows, selectedId, onSelect }) {
  return <nav className="workflow-list" aria-label="工作流"><header><b>工作流</b><span>{workflows.length}</span></header>
    <div>{workflows.map((workflow) => <button className={workflow.id === selectedId ? "selected" : ""} onClick={() => onSelect(workflow.id)} key={workflow.id}>
      <span><WorkflowIcon kind={workflow.kind} />{kindLabel(workflow.kind)}</span><b>{stageLabel(workflow)}</b><small>{formatDate(workflow.updated_at)}</small></button>)}</div>
    {!workflows.length && <p>暂无工作流</p>}</nav>;
}


function TracePanel({ workflow, refresh, setError }) {
  if (!workflow) return <main className="trace-empty"><Activity size={28} /><p>暂无活动记录</p></main>;
  return <main className="dsh-panel"><TraceHeader workflow={workflow} refresh={refresh} setError={setError} />
    <MetricStrip workflow={workflow} /><TraceRows events={workflow.events || []} /><TraceBottom workflow={workflow} /></main>;
}


function TraceHeader({ workflow, refresh, setError }) {
  return <header className="dsh-header"><div><span>{kindLabel(workflow.kind)}</span><h2>{stageLabel(workflow)}</h2></div>
    <div><span className={`workflow-status ${workflow.status}`}>{STATUS[workflow.status] || workflow.status}</span>
      <WorkflowActions workflow={workflow} refresh={refresh} setError={setError} /></div></header>;
}


function WorkflowActions({ workflow, refresh, setError }) {
  const [busy, setBusy] = useState(false);
  const act = async (action) => {
    setBusy(true);
    try { await action(); await refresh(workflow.project_id); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  };
  if (workflow.status !== "waiting_human") return null;
  if (!workflow.payload?.conflict_node) return <button className="button primary compact" disabled={busy} onClick={() => act(() => confirmWorkflow(workflow.id))}><Play size={15} />继续执行</button>;
  return <div className="review-controls"><button title="批准" disabled={busy} onClick={() => act(() => resolveWorkflow(workflow.id, { decision: "approve", reason: "人工批准" }))}><ThumbsUp size={15} /></button>
    <button title="驳回" disabled={busy} onClick={() => act(() => resolveWorkflow(workflow.id, { decision: "reject", reason: "人工驳回" }))}><ThumbsDown size={15} /></button></div>;
}


function MetricStrip({ workflow }) {
  return <section className="dsh-metrics" aria-label="轨迹指标">{metrics(workflow).map((metric) => <div className={metric.tone} key={metric.label}>
    <span>{metric.label}</span><b>{metric.value}</b><i style={{ width: metric.width }} /></div>)}</section>;
}


function TraceRows({ events }) {
  return <ol className="dsh-trace">{events.map((event, index) => <TraceRow event={event} index={index} key={event.id} />)}
    {!events.length && <li className="dsh-empty">等待第一条轨迹记录</li>}</ol>;
}


function TraceRow({ event, index }) {
  const role = traceRole(event);
  return <li className={`dsh-row ${role.toLowerCase()}`}><span className="trace-index">{String(index + 1).padStart(2, "0")}</span>
    <strong>{role}</strong><span className="trace-actor">{event.actor}</span><p>{eventSummary(event)}</p><time>{formatTime(event.time)}</time></li>;
}


function TraceBottom({ workflow }) {
  const blocked = workflow.events.filter((event) => ["candidate_blocked", "workflow_paused"].includes(event.type)).length;
  const completed = workflow.steps.filter((step) => step.status === "completed").length;
  return <footer className="trace-bottom"><span><Check size={14} />完成步骤 <b>{completed}/{workflow.steps.length}</b></span>
    <span><Activity size={14} />事件 <b>{workflow.events.length}</b></span><span><Pause size={14} />阻断 <b>{blocked}</b></span><span><GitBranch size={14} />谱系 <b>{shortId(workflow.lineage_id)}</b></span></footer>;
}


function metrics(workflow) {
  const duration = Math.max(0, new Date(workflow.updated_at) - new Date(workflow.created_at));
  const turns = workflow.events.filter((event) => event.type === "assistant").length;
  const calls = workflow.events.filter((event) => event.type === "tool_result").length;
  return [{ label: "Duration", value: formatDuration(duration), width: `${Math.min(100, Math.max(8, duration / 600))}%`, tone: "duration" },
    { label: "Turns", value: String(turns), width: `${Math.min(100, Math.max(8, turns * 16))}%`, tone: "turns" },
    { label: "Calls", value: String(calls), width: `${Math.min(100, Math.max(8, calls * 14))}%`, tone: "calls" }];
}


function eventSummary(event) {
  const value = event.payload || {};
  return value.text || value.reason || value.summary || value.command || compactJson(value) || event.type.replaceAll("_", " ");
}


function compactJson(value) {
  const text = JSON.stringify(value);
  return text === "{}" ? "" : text;
}


function traceRole(event) {
  if (event.type === "assistant") return "ASSISTANT";
  if (event.type === "tool_result") return "TOOL";
  return "SYSTEM";
}


function WorkflowIcon({ kind }) {
  return kind === "brainstorm" ? <GitBranch size={15} /> : <Wrench size={15} />;
}


function kindLabel(kind) {
  return kind === "brainstorm" ? "头脑风暴" : "规划 · 执行 · 复核 · 反思";
}


function stageLabel(workflow) {
  return STAGE[workflow.stage] || workflow.stage;
}


function shortId(value = "") {
  return value.split(":").at(-1).slice(0, 7);
}


function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}


function formatTime(value) {
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date(value));
}


function formatDuration(ms) {
  if (ms >= 60000) return `${Math.floor(ms / 60000)}分${Math.round(ms % 60000 / 1000)}秒`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}秒`;
  return `${ms}毫秒`;
}
