import { ArrowRight, CheckCircle2, Circle, FlaskConical, LoaderCircle, MessageSquare, Play, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { useWorld } from "../context/WorldContext";

const statusLabel = { proposed: "待审核", frontier: "可推进", active: "执行中", completed: "已完成", blocked: "已停止" };

function Direction({ node, cycle, run }) {
  const icon = node.status === "completed" ? <CheckCircle2 /> : node.status === "active" ? <LoaderCircle className="spin" /> : <Circle />;
  const canRun = ["proposed", "frontier", "blocked"].includes(node.status);
  return <article className={`direction direction-${node.status}`}><header><span className="direction-state">{icon}{statusLabel[node.status]}</span><span className="workflow-tag">{node.payload.workflow}</span></header><h3>{node.payload.title}</h3><p>{node.payload.rationale}</p><dl><dt>本轮边界</dt><dd>{node.payload.completion_test}</dd><dt>之后仍需</dt><dd>{node.payload.remaining}</dd></dl>{cycle && <CycleStrip cycle={cycle} />}{canRun && <button className="button primary" onClick={() => run(node.id)}><Play size={16} />推进这个方向</button>}</article>;
}

function CycleStrip({ cycle }) {
  return <div className="cycle-strip"><FlaskConical size={16} /><span>Research Cycle</span><b>{statusLabel[cycle.status] || cycle.status}</b></div>;
}

function Conversation({ messages, send }) {
  const [text, setText] = useState("");
  const submit = async (event) => { event.preventDefault(); if (!text.trim()) return; await send(text.trim()); setText(""); };
  return <section className="conversation"><div className="section-title"><MessageSquare size={18} /><h2>Project Lead</h2></div><div className="messages">{messages.map((message) => <div key={message.id} className={`message ${message.role}`}><span>{message.role === "user" ? "你" : "Lead"}</span><p>{message.content}</p></div>)}</div><form onSubmit={submit}><textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="提出判断、补充材料，或要求 Lead 改变方向" /><button className="button primary" type="submit"><ArrowRight size={17} />发送</button></form></section>;
}

export function LeaderPage() {
  const { data, projectId, command } = useWorld();
  const [busy, setBusy] = useState(false);
  const directions = useMemo(() => data.nodes.filter((node) => node.kind === "direction"), [data.nodes]);
  const cycles = new Map((data.cycles || []).map((cycle) => [cycle.direction_id, cycle]));
  const act = async (operation) => { setBusy(true); try { await operation(); } finally { setBusy(false); } };
  const plan = () => act(() => command("plan_project", { project_id: projectId }));
  const run = (directionId) => act(() => command("run_direction", { direction_id: directionId }));
  const send = (content) => act(() => command("message", { project_id: projectId, content }));
  if (!projectId) return <div className="blank-state">新建一个研究项目开始。</div>;
  return <div className="leader-page"><Conversation messages={data.messages || []} send={send} /><section className="direction-board"><div className="board-heading"><div><span className="eyebrow">当前研究空间</span><h1>方向与决策点</h1></div><button className="button secondary" onClick={plan} disabled={busy || directions.length > 0}><RotateCcw size={17} />{directions.length ? "方向已生成" : "生成研究方向"}</button></div><div className="direction-grid">{directions.map((node) => <Direction key={node.id} node={node} cycle={cycles.get(node.id)} run={run} />)}</div>{!directions.length && <div className="blank-state">Lead 尚未拆解问题。生成方向后，选择一条进入完整 Research Cycle。</div>}</section></div>;
}
