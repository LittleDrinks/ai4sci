import { AlertTriangle, Check, CircleDot, ExternalLink, FileSearch, FlaskConical, GitBranch, ShieldCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useWorld } from "../context/WorldContext";
import { attemptLogUrl } from "../api";

const workflowIcons = { source: FileSearch, claim: GitBranch, experiment: FlaskConical, report: ShieldCheck };

function WorkItem({ item, inspect }) {
  const Icon = workflowIcons[item.kind] || CircleDot;
  return <button className={`road-work road-${item.status}`} onClick={() => inspect({ type: "work", value: item })}><Icon size={18} /><div><b>{item.kind}</b><span>{item.steps.filter((step) => step.status === "completed").length}/{item.steps.length} steps</span></div>{item.status === "completed" && <Check size={17} />}</button>;
}

function DirectionLane({ direction, cycle, work, inspect }) {
  return <article className={`road-lane road-lane-${direction.status}`}><header><button className="lane-title" onClick={() => cycle && inspect({ type: "cycle", value: cycle })}><span className="road-status">{direction.status}</span><h2>{direction.payload.title}</h2></button><span>{direction.payload.workflow}</span></header><div className="road-flow"><div className="road-origin"><CircleDot size={18} />Direction</div>{work.map((item) => <WorkItem key={item.id} item={item} inspect={inspect} />)}{!work.length && <div className="road-frontier">Frontier</div>}</div>{cycle?.brief?.open_questions?.length > 0 && <div className="open-questions"><AlertTriangle size={17} /><div><b>仍未完成</b>{cycle.brief.open_questions.map((value) => <p key={value}>{value}</p>)}</div></div>}</article>;
}

function JsonValue({ value }) {
  return <pre className="inspect-json">{JSON.stringify(value, null, 2)}</pre>;
}

function CycleDetail({ cycle }) {
  const brief = cycle.brief || {};
  return <div className="inspect-stack">{[["已获得", brief.learned], ["证据", brief.evidence], ["限制", brief.limitations], ["仍未完成", brief.open_questions], ["下一步", brief.next_moves]].map(([title, values]) => values?.length ? <section key={title}><h3>{title}</h3><ul>{values.map((value) => <li key={value}>{value}</li>)}</ul></section> : null)}</div>;
}

function WorkDetail({ item, attempts }) {
  const owned = attempts.filter((attempt) => attempt.work_item_id === item.id);
  return <div className="inspect-stack"><section><h3>Workflow steps</h3>{item.steps.map((step) => <details key={step.id}><summary><b>{step.role}</b><span>{step.status}</span></summary><JsonValue value={step.output} /></details>)}</section><section><h3>Review findings</h3>{item.findings.length ? item.findings.map((finding) => <div className={`finding finding-${finding.severity}`} key={finding.id}><b>{finding.check_id}</b><span>{finding.severity}</span><p>{finding.recommendation}</p></div>) : <p className="muted">没有 reviewer finding。</p>}</section><section><h3>Attempts</h3>{owned.map((attempt) => <a className="attempt-link" href={attemptLogUrl(attempt.id)} target="_blank" rel="noreferrer" key={attempt.id}><span><b>{attempt.actor}</b><small>{attempt.status}</small></span><ExternalLink size={16} /></a>)}</section></div>;
}

function Inspector({ selected, attempts, close }) {
  if (!selected) return null;
  const title = selected.type === "cycle" ? selected.value.brief?.title || "Cycle Brief" : `${selected.value.kind} work item`;
  return <div className="inspect-backdrop" onMouseDown={close}><aside className="result-inspector" onMouseDown={(event) => event.stopPropagation()}><header><div><span className="eyebrow">{selected.type === "cycle" ? "Research Cycle" : "Execution Record"}</span><h2>{title}</h2></div><button className="icon-button" onClick={close} title="关闭"><X size={20} /></button></header><div className="result-inspector-scroll">{selected.type === "cycle" ? <CycleDetail cycle={selected.value} /> : <WorkDetail item={selected.value} attempts={attempts} />}</div></aside></div>;
}

export function RoadmapPage() {
  const { data } = useWorld();
  const [selected, setSelected] = useState(null);
  const directions = data.nodes.filter((node) => node.kind === "direction");
  const cycles = new Map((data.cycles || []).map((cycle) => [cycle.direction_id, cycle]));
  const work = useMemo(() => Object.groupBy(data.work_items || [], (item) => item.direction_id), [data.work_items]);
  return <><div className="roadmap-page"><header className="roadmap-header"><div><span className="eyebrow">全局路线图</span><h1>研究深度与前沿</h1><p>点击 Direction 查看 Cycle Brief，点击 Work Item 查看步骤、findings 与完整日志。</p></div><Link className="button secondary" to="/leader">返回 Project Lead</Link></header><div className="roadmap-list">{directions.map((direction) => <DirectionLane key={direction.id} direction={direction} cycle={cycles.get(direction.id)} work={work[direction.id] || []} inspect={setSelected} />)}</div></div><Inspector selected={selected} attempts={data.attempts || []} close={() => setSelected(null)} /></>;
}
