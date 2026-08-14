import { Focus, GitFork, Network, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { EmptyState } from "../components/EmptyState";
import { SubmitNodeDialog } from "../components/SubmitNodeDialog";
import { useWorld } from "../context/WorldContext";
import { GraphView } from "../graph/GraphView";
import { Inspector } from "../graph/Inspector";

function MapToolbar({ counts, jobs, all, canExpand, setAll, onSubmit }) {
  const active = jobs.filter((job) => ["running", "leased", "claimed"].includes(job.status)).length;
  return <div className="map-toolbar"><div><b>研究地图</b><span>{counts.nodes.visible}/{counts.nodes.total} 个节点 · {counts.edges.visible}/{counts.edges.total} 条关系 · {active} 个任务运行中</span></div><div className="map-tools">{canExpand && <MapMode all={all} setAll={setAll} />}<button className="button primary" onClick={onSubmit}><Plus size={17} />提交节点</button></div></div>;
}

function MapMode({ all, setAll }) {
  return <div className="segmented" aria-label="地图范围"><button className={!all ? "active" : ""} onClick={() => setAll(false)} title="查看聚焦节点的全部前置依赖和一层后续节点"><Focus size={17} /><span>节点上下文</span></button><button className={all ? "active" : ""} onClick={() => setAll(true)} title="查看当前问题的全部研究结构"><Network size={17} /><span>全局结构</span></button></div>;
}

function EmptyMap({ onSubmit }) {
  return <EmptyState icon={GitFork} title="研究地图为空" detail="提交第一个命题、方向、行动或证据节点。" action={<button className="button primary" onClick={onSubmit}><Plus size={17} />提交首个节点</button>} />;
}

export function MapPage() {
  const { data, loading } = useWorld();
  if (loading) return <div className="page-loading">正在载入研究世界...</div>;
  return <ProjectMap key={data.active_project_id} data={data} />;
}

function ProjectMap({ data }) {
  const rootId = data.nodes.find((node) => node.kind === "question")?.id || "";
  const [selectedId, setSelectedId] = useState(rootId);
  const [focusId, setFocusId] = useState(rootId);
  const [showAll, setShowAll] = useState(false);
  const [submitOpen, setSubmitOpen] = useState(false);
  const currentFocus = data.nodes.some((node) => node.id === focusId) ? focusId : rootId;
  const currentSelection = data.nodes.some((node) => node.id === selectedId) ? selectedId : currentFocus;
  const context = useMemo(() => visibleGraph(data.nodes, data.edges, currentFocus), [data.nodes, data.edges, currentFocus]);
  const graph = showAll ? { nodes: data.nodes, edges: data.edges } : context;
  const selected = data.nodes.find((node) => node.id === currentSelection);
  const focus = (id) => { setFocusId(id); setSelectedId(id); setShowAll(false); };
  const counts = graphCounts(graph, data);
  const canExpand = context.nodes.length < data.nodes.length || context.edges.length < data.edges.length;
  return <section className="map-page"><MapToolbar counts={counts} jobs={data.jobs} all={showAll} canExpand={canExpand} setAll={setShowAll} onSubmit={() => setSubmitOpen(true)} /><div className="map-workspace"><div className="graph-canvas">{data.nodes.length ? <GraphView nodes={graph.nodes} edges={graph.edges} jobs={data.jobs} selectedId={currentSelection} onSelect={setSelectedId} overview={showAll} layoutKey={`${showAll}:${currentFocus}`} /> : <EmptyMap onSubmit={() => setSubmitOpen(true)} />}</div><Inspector node={selected} nodes={data.nodes} edges={data.edges} focused={currentFocus === currentSelection && !showAll} onSelect={setSelectedId} onFocus={focus} /></div><SubmitNodeDialog open={submitOpen} onClose={() => setSubmitOpen(false)} /></section>;
}

function graphCounts(graph, data) {
  return { nodes: { visible: graph.nodes.length, total: data.nodes.length },
    edges: { visible: graph.edges.length, total: data.edges.length } };
}

function visibleGraph(nodes, edges, focusId) {
  const ids = branchIds(edges, focusId);
  return { nodes: nodes.filter((node) => ids.has(node.id)),
    edges: edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)) };
}

function branchIds(edges, focusId) {
  const ids = new Set([focusId]);
  let frontier = [focusId];
  while (frontier.length) frontier = addNeighbors(edges, frontier, ids, true);
  addNeighbors(edges, [focusId], ids, false);
  return ids;
}

function addNeighbors(edges, frontier, ids, ancestors) {
  const next = edges.filter((edge) => frontier.includes(ancestors ? edge.target : edge.source))
    .map((edge) => ancestors ? edge.source : edge.target).filter((id) => !ids.has(id));
  next.forEach((id) => ids.add(id));
  return next;
}
