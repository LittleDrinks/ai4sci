import { Focus, Network, Workflow } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { setProjectAuto, startWorkflow } from "../api";
import { useWorld } from "../context/WorldContext";
import { GraphView } from "../graph/GraphView";
import { Inspector } from "../graph/Inspector";
import "../map.css";


export function MapPage() {
  const { data, loading, refresh, setError } = useWorld();
  if (loading) return <div className="page-loading">正在载入研究世界...</div>;
  return <ProjectMap key={data.active_project_id} data={data} refresh={refresh} setError={setError} />;
}


function ProjectMap({ data, refresh, setError }) {
  const rootId = data.nodes.find((node) => node.kind === "question")?.id || "";
  const [selectedId, setSelectedId] = useState(rootId);
  const [overview, setOverview] = useState(true);
  const newIds = useNewNodes(data.nodes);
  const selected = data.nodes.find((node) => node.id === selectedId) || data.nodes[0];
  const relations = useMemo(() => graphEdges(data.nodes, data.edges), [data.nodes, data.edges]);
  const graph = useMemo(() => overview ? { nodes: data.nodes, edges: relations }
    : branch(data.nodes, relations, selected?.id), [data.nodes, relations, overview, selected?.id]);
  const start = async (node) => {
    try { await startWorkflow(data.active_project_id, workflowFor(node)); await refresh(data.active_project_id); }
    catch (error) { setError(error.message); }
  };
  return <section className="map-page"><MapToolbar data={data} relationCount={relations.length} overview={overview} setOverview={setOverview} refresh={refresh} setError={setError} />
    <div className="map-workspace"><div className="graph-canvas"><GraphView nodes={graph.nodes} edges={graph.edges} selectedId={selected?.id} onSelect={setSelectedId} onStart={start} newIds={newIds} /></div>
      <Inspector node={selected} nodes={data.nodes} edges={data.edges} onSelect={setSelectedId} onStart={start} /></div></section>;
}


function MapToolbar({ data, relationCount, overview, setOverview, refresh, setError }) {
  const project = data.projects.find((item) => item.id === data.active_project_id);
  const active = data.workflows.filter((item) => ["queued", "running", "waiting_human"].includes(item.status)).length;
  const toggle = async () => {
    try { await setProjectAuto(project.id, !project.auto); await refresh(project.id); }
    catch (error) { setError(error.message); }
  };
  return <header className="map-toolbar"><div><b>研究地图</b><span>{data.nodes.length} 个节点 · {relationCount} 条关系 · {active} 个流程占用槽位</span></div>
    <div className="map-tools"><label className="auto-toggle"><input type="checkbox" checked={Boolean(project?.auto)} onChange={toggle} /><span>Auto</span></label>
      <div className="segmented" aria-label="地图范围"><button className={!overview ? "active" : ""} onClick={() => setOverview(false)} title="节点上下文"><Focus size={17} /><span>上下文</span></button><button className={overview ? "active" : ""} onClick={() => setOverview(true)} title="全局结构"><Network size={17} /><span>全局</span></button></div></div></header>;
}


function workflowFor(node) {
  const kind = node.kind === "question" || node.kind === "source" || node.kind === "experiment" || node.direction_status !== "proposed"
    ? "brainstorm" : "plan-execute-review-reflect";
  return { node_id: node.id, kind, payload: kind === "brainstorm" ? { count: 8, select: 4 } : {} };
}


function branch(nodes, edges, focusId) {
  const ids = new Set([focusId]);
  edges.filter((edge) => edge.source === focusId || edge.target === focusId)
    .forEach((edge) => { ids.add(edge.source); ids.add(edge.target); });
  return { nodes: nodes.filter((node) => ids.has(node.id)),
    edges: edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)) };
}


function graphEdges(nodes, edges) {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const evidence = edges.map((edge) => orientEvidence(edge, byId));
  const evidencePairs = new Set(evidence.map((edge) => pairKey(edge.source, edge.target)));
  const lineage = nodes.filter((node) => node.parent_id && byId.has(node.parent_id))
    .filter((node) => !evidencePairs.has(pairKey(node.parent_id, node.id)))
    .map((node) => ({ source: node.parent_id, target: node.id, polarity: "lineage" }));
  return [...lineage, ...evidence];
}


function orientEvidence(edge, nodes) {
  return nodes.get(edge.source)?.parent_id === edge.target
    ? { ...edge, source: edge.target, target: edge.source } : edge;
}


function pairKey(left, right) {
  return [left, right].sort().join(":");
}


function useNewNodes(nodes) {
  const known = useRef(new Map());
  const [newIds, setNewIds] = useState(new Set());
  useEffect(() => {
    const next = new Map(nodes.map((node) => [node.id, node.life_state]));
    const admitted = nodes.filter((node) => node.life_state === "admitted" && known.current.get(node.id) === "pending").map((node) => node.id);
    known.current = next;
    if (!admitted.length) return undefined;
    setNewIds(new Set(admitted));
    const timer = setTimeout(() => setNewIds(new Set()), 1800);
    return () => clearTimeout(timer);
  }, [nodes]);
  return newIds;
}
