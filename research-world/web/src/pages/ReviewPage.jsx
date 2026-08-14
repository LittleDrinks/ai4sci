import { ArrowUpRight, CheckCheck, FileCode2, GitFork } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { Status } from "../components/Status";
import { useWorld } from "../context/WorldContext";
import { displayLabel, formatTime, shortId } from "../utils";

const NODE_STATES = new Set(["pending_review", "revision_requested", "rejected", "invalidated"]);
const ARTIFACT_STATES = new Set(["pending", "pending_review", "rejected", "retracted"]);
const PENDING_STATES = new Set(["pending", "pending_review"]);

function DetailLink({ item, type }) {
  const path = type === "node" ? `/nodes/${item.id}` : `/reports/${item.id}`;
  return <Link className="icon-link" to={path} title={`查看${displayLabel(type)}`}><ArrowUpRight size={18} /></Link>;
}

function reviewOrder(left, right) {
  const pending = Number(PENDING_STATES.has(right.status)) - Number(PENDING_STATES.has(left.status));
  return pending || new Date(right.created_at) - new Date(left.created_at);
}

function itemSummary(item, type) {
  return type === "node" ? item.summary || shortId(item.id) : shortId(item.id);
}

function sourceId(item, type) {
  return type === "node" ? item.source_job_id || item.created_by?.id : item.job_id;
}

function ReviewTable({ items, type }) {
  return <div className="table-wrap"><table><thead><tr><th>{displayLabel(type)}</th><th>类型</th><th>状态</th><th>来源</th><th>创建时间</th><th><span className="sr-only">打开</span></th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><b>{item.title || displayLabel(item.kind)}</b><small>{itemSummary(item, type)}</small></td><td>{displayLabel(item.kind)}</td><td><Status value={item.status} /></td><td><code>{shortId(sourceId(item, type))}</code></td><td>{formatTime(item.created_at)}</td><td><DetailLink item={item} type={type} /></td></tr>)}</tbody></table></div>;
}

function ReviewSection({ title, icon: Icon, items, type }) {
  const emptyLabel = type === "node" ? "节点" : "产物";
  return <section className="review-section"><div className="section-heading"><h2><Icon size={18} />{title}</h2><span>{items.length}</span></div>{items.length ? <ReviewTable items={items} type={type} /> : <p className="muted">没有匹配的{emptyLabel}。</p>}</section>;
}

export function ReviewPage() {
  const { data, loading } = useWorld();
  const nodes = data.review_nodes.filter((item) => NODE_STATES.has(item.status)).sort(reviewOrder);
  const artifacts = data.artifacts.filter((item) => ARTIFACT_STATES.has(item.status)).sort(reviewOrder);
  if (loading) return <div className="page-loading">正在加载审核状态...</div>;
  if (!nodes.length && !artifacts.length) return <EmptyState icon={CheckCheck} title="暂无审核事项" detail="当前项目没有待处理或历史审核记录。" />;
  return <section className="content-page review-page"><header className="page-header"><div><span className="eyebrow">准入与修正</span><h1>审核</h1><p>{nodes.length} 个研究节点和 {artifacts.length} 个产物需要处理或保留了审核结果。</p></div></header><ReviewSection title="研究节点" icon={GitFork} items={nodes} type="node" /><ReviewSection title="产物" icon={FileCode2} items={artifacts} type="artifact" /></section>;
}
