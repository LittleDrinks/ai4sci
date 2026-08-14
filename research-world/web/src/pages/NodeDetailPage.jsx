import { ArrowLeft, Ban, FileCode2, GitFork, Play } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getNode } from "../api";
import { EmptyState } from "../components/EmptyState";
import { FeedbackDialog } from "../components/FeedbackDialog";
import { JobDialog } from "../components/JobDialog";
import { DataGrid, DependencyList } from "../components/NodeContent";
import { ReviewActions } from "../components/ReviewActions";
import { Status } from "../components/Status";
import { useProjectEntity } from "../context/useProjectEntity";
import { edgeSource, edgeTarget } from "../graph/layout";
import { actorName, dateValue, displayLabel, formatTime, isAdmittedNode } from "../utils";

function nodeDependencies(node, edges) {
  return edges.filter((edge) => edgeTarget(edge) === node.id).map(edgeSource);
}

function NodeArtifacts({ artifacts }) {
  if (!artifacts.length) return <p className="muted">未附加产物。</p>;
  return <ul className="plain-list">{artifacts.map((artifact) => <li key={artifact.id}><span>{artifact.title || displayLabel(artifact.kind) || "未命名产物"}</span>{artifact.content_type === "text/html" || artifact.kind === "html_report" ? <Link to={`/reports/${artifact.id}`}>打开报告</Link> : <code>{artifact.sha256 || artifact.id}</code>}</li>)}</ul>;
}

function NodeActivity({ events, agents }) {
  if (!events.length) return <p className="muted">无活动记录。</p>;
  return <ol className="detail-timeline">{events.map((event) => <li key={`${dateValue(event)}-${event.type}-${event.entity_id}`}><time>{formatTime(dateValue(event))}</time><div><b>{displayLabel(event.type)}</b><p>{event.payload?.message || event.payload?.summary || event.payload?.title || actorName(event, agents) || "状态已变更"}</p></div></li>)}</ol>;
}

function DetailActions({ open, disabled }) {
  return <div className="detail-actions"><button className="button secondary" disabled={disabled} onClick={() => open("research")}><Play size={16} />发起研究</button><button className="button secondary" disabled={disabled} onClick={() => open("html_report")}><FileCode2 size={16} />生成 HTML 报告</button></div>;
}

function descendantCount(id, edges) {
  const found = new Set([id]);
  let frontier = [id];
  while (frontier.length) {
    const next = edges.filter((edge) => frontier.includes(edgeSource(edge))).map(edgeTarget).filter((target) => !found.has(target));
    next.forEach((target) => found.add(target));
    frontier = next;
  }
  return found.size - 1;
}

function InvalidateControl({ node, edges, command }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  if (!isAdmittedNode(node) || node.kind === "question") return null;
  const warning = `此操作会使该节点及其所有下游依赖节点失效，并撤回相关产物。当前可见 ${descendantCount(node.id, edges)} 个下游节点。`;
  const submit = async (reason) => {
    setBusy(true);
    try { await command("invalidate_node", { node_id: node.id, reason }); navigate("/review"); }
    catch {}
    finally { setBusy(false); }
  };
  return <><button className="button danger" onClick={() => setOpen(true)}><Ban size={16} />使节点失效</button><FeedbackDialog action={open ? "invalidate" : ""} noun="节点" busy={busy} warning={warning} onClose={() => setOpen(false)} onSubmit={submit} /></>;
}

export function NodeDetailPage() {
  const { id } = useParams();
  const { command, data, entity: node, resolving } = useProjectEntity(id, "nodes", getNode);
  const [jobKind, setJobKind] = useState("");
  const related = useMemo(() => node ? relatedData(node, data) : null, [node, data]);
  if (resolving) return <div className="page-loading">正在加载节点...</div>;
  if (!node) return <EmptyState icon={GitFork} title="未找到节点" detail="此节点不属于当前项目。" action={<Link className="button secondary" to="/map"><ArrowLeft size={16} />研究地图</Link>} />;
  return <section className="node-detail content-page"><header className="detail-header"><Link className="back-link" to="/map"><ArrowLeft size={17} />研究地图</Link><div><span className="eyebrow">{displayLabel(node.kind)}</span><h1>{node.title}</h1><p>{node.summary || "未记录摘要。"}</p></div><aside className="detail-state-actions"><Status value={node.status} /><ReviewActions node={node} compact /><InvalidateControl node={node} edges={data.edges} command={command} /></aside></header><div className="detail-columns"><div className="detail-primary"><section className="page-section"><div className="section-heading"><h2>研究数据</h2></div><DataGrid data={node.content} /></section><section className="page-section"><div className="section-heading"><h2>依赖节点</h2><span>{related.dependencies.length}</span></div><DependencyList ids={related.dependencies} nodes={data.nodes} /></section><section className="page-section"><div className="section-heading"><h2>产物</h2><span>{related.artifacts.length}</span></div><NodeArtifacts artifacts={related.artifacts} /></section></div><aside className="detail-aside"><DetailActions disabled={!isAdmittedNode(node)} open={setJobKind} /><section><h2>溯源信息</h2><dl className="provenance"><div><dt>创建时间</dt><dd>{formatTime(node.created_at)}</dd></div><div><dt>标识符</dt><dd><code>{node.id}</code></dd></div><div><dt>任务</dt><dd>{related.jobs.length}</dd></div></dl></section><section><h2>活动记录</h2><NodeActivity events={related.events} agents={data.agents} /></section></aside></div><JobDialog open={Boolean(jobKind)} onClose={() => setJobKind("")} subjectId={node.id} kind={jobKind || "research"} /></section>;
}

function relatedData(node, data) {
  const dependencies = nodeDependencies(node, data.edges);
  const artifacts = data.artifacts.filter((item) => item.node_id === node.id);
  const jobs = data.jobs.filter((item) => item.subject_id === node.id);
  const jobIds = new Set(jobs.map((item) => item.id));
  const events = data.events.filter((item) => (item.entity_type === "node" && item.entity_id === node.id) || (item.entity_type === "job" && jobIds.has(item.entity_id)) || item.payload?.node_id === node.id).sort((a, b) => new Date(dateValue(b)) - new Date(dateValue(a)));
  return { dependencies, artifacts, jobs, events };
}
