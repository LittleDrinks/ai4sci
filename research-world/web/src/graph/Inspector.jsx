import { ArrowDownToLine, ArrowUpFromLine, ClipboardList, ExternalLink, FileCode2, Focus, Play, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { JobDialog } from "../components/JobDialog";
import { ReviewActions } from "../components/ReviewActions";
import { Status } from "../components/Status";
import { SubmitNodeDialog } from "../components/SubmitNodeDialog";
import { useWorld } from "../context/WorldContext";
import { displayLabel, formatTime, isAdmittedNode, objectEntries, shortId } from "../utils";

const VISIBLE_RELATIONS = 5;

function InspectorActions({ openNode, openPlan, openJob, openReport, disabled }) {
  return <div className="inspector-actions"><button className="button secondary" disabled={disabled} onClick={openNode}><Plus size={16} />添加节点</button><button className="button secondary" disabled={disabled} onClick={openPlan}><ClipboardList size={16} />规划</button><button className="button secondary" disabled={disabled} onClick={openJob}><Play size={16} />研究</button><button className="button secondary" disabled={disabled} onClick={openReport}><FileCode2 size={16} />HTML 报告</button></div>;
}

function Provenance({ node }) {
  const actor = node.created_by;
  const source = node.content?.provenance || {};
  return <dl className="inspector-provenance"><div><dt>提交</dt><dd>{actor.id || "系统"} · {formatTime(node.created_at)}</dd></div><Source label="原始资料" path={source.source_path} hash={source.source_sha256} /><Source label="图谱快照" path={source.graph_path} hash={source.graph_sha256} /><div><dt>节点</dt><dd><code>{shortId(node.id)}</code></dd></div></dl>;
}

function Source({ label, path, hash }) {
  if (!path && !hash) return null;
  const name = path?.split(/[\\/]/).pop() || "未命名来源";
  return <div><dt>{label}</dt><dd><b title={path}>{name}</b>{hash && <code title={hash}>{shortId(hash)}</code>}</dd></div>;
}

function ArtifactLinks({ artifacts }) {
  if (!artifacts.length) return <p className="muted">暂无产物。</p>;
  return <ul className="plain-list">{artifacts.map((artifact) => <li key={artifact.id}><span>{artifact.title}</span><Link to={`/reports/${artifact.id}`}>打开</Link></li>)}</ul>;
}

function RelationList({ nodes, onSelect }) {
  return <ul>{nodes.map((item) => <li key={item.id}><button onClick={() => onSelect(item.id)}><span>{displayLabel(item.kind)}</span><b>{item.title}</b></button></li>)}</ul>;
}

function RelatedNodes({ title, icon: Icon, nodes, onSelect }) {
  if (!nodes.length) return null;
  const visible = nodes.slice(0, VISIBLE_RELATIONS);
  const hidden = nodes.slice(VISIBLE_RELATIONS);
  return <section className="relation-group"><h3><Icon size={15} />{title}<span>{nodes.length}</span></h3><RelationList nodes={visible} onSelect={onSelect} />{hidden.length > 0 && <details className="relation-more"><summary>其余 {hidden.length} 个节点</summary><RelationList nodes={hidden} onSelect={onSelect} /></details>}</section>;
}

function NodeRelations({ node, nodes, edges, onSelect }) {
  const byId = new Map(nodes.map((item) => [item.id, item]));
  const before = edges.filter((edge) => edge.target === node.id).map((edge) => byId.get(edge.source)).filter(Boolean);
  const after = edges.filter((edge) => edge.source === node.id).map((edge) => byId.get(edge.target)).filter(Boolean);
  return <section className="inspector-section"><div className="section-heading"><h2>节点关系</h2><span>{before.length + after.length}</span></div><RelatedNodes title="前置节点" icon={ArrowDownToLine} nodes={before} onSelect={onSelect} /><RelatedNodes title="后续节点" icon={ArrowUpFromLine} nodes={after} onSelect={onSelect} /></section>;
}

function FocusAction({ focused, onFocus }) {
  return <button className="button secondary inspector-focus" disabled={focused} onClick={onFocus}><Focus size={16} />{focused ? "当前聚焦节点" : "聚焦此节点"}</button>;
}

function factValue(key, value) {
  if (typeof value === "boolean") return value ? "是" : "否";
  if (key.endsWith("_percent") && typeof value === "number") return `${value}%`;
  return displayLabel(value);
}

function KeyFacts({ node }) {
  const summary = node.summary?.trim();
  const facts = objectEntries(node.content?.record).filter(([key, value]) => typeof value !== "object" && String(value).trim() !== summary && key !== "hypothesis").slice(0, 4);
  if (!facts.length) return null;
  return <section className="inspector-section inspector-facts"><div className="section-heading"><h2>关键记录</h2><span>{facts.length}</span></div><dl>{facts.map(([key, value]) => <div key={key}><dt>{displayLabel(key)}</dt><dd>{factValue(key, value)}</dd></div>)}</dl></section>;
}

function InspectorHeader({ node }) {
  return <header className="inspector-header"><div className="eyebrow"><span>{displayLabel(node.kind)}</span><Status value={node.status} /></div><h1>{node.title}</h1><p className="lead-copy">{node.summary || "未记录摘要。"}</p></header>;
}

function InspectorBody({ node, nodes, edges, artifacts, focused, onSelect, onFocus, setDialog }) {
  return <><InspectorHeader node={node} /><FocusAction focused={focused} onFocus={() => onFocus(node.id)} /><ReviewActions node={node} /><InspectorActions disabled={!isAdmittedNode(node)} openNode={() => setDialog("node")} openPlan={() => setDialog("plan")} openJob={() => setDialog("research")} openReport={() => setDialog("html_report")} /><KeyFacts node={node} /><NodeRelations node={node} nodes={nodes} edges={edges} onSelect={onSelect} /><section className="inspector-section"><div className="section-heading"><h2>产物</h2><span>{artifacts.length}</span></div><ArtifactLinks artifacts={artifacts} /></section><section className="inspector-section"><div className="section-heading"><h2>溯源</h2><Link to={`/nodes/${node.id}`}>完整详情 <ExternalLink size={14} /></Link></div><Provenance node={node} /></section></>;
}

export function Inspector({ node, nodes = [], edges = [], focused, onSelect, onFocus }) {
  const [dialog, setDialog] = useState("");
  const { data } = useWorld();
  if (!node) return <aside className="inspector inspector-empty"><p>选择节点以查看数据和可用操作。</p></aside>;
  const artifacts = data.artifacts.filter((item) => item.node_id === node.id);
  return <aside className="inspector"><div className="inspector-scroll"><InspectorBody node={node} nodes={nodes} edges={edges} artifacts={artifacts} focused={focused} onSelect={onSelect} onFocus={onFocus} setDialog={setDialog} /></div>
    <SubmitNodeDialog open={dialog === "node"} onClose={() => setDialog("")} initialDependency={node.id} />
    <JobDialog open={dialog === "plan" || dialog === "research" || dialog === "html_report"} onClose={() => setDialog("")} subjectId={node.id} kind={dialog || "research"} />
  </aside>;
}
