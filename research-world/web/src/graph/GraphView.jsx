import { Background, Controls, MiniMap, ReactFlow, useReactFlow } from "@xyflow/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { edgeHandles, edgeSource, edgeTarget, layoutGraph, NODE_HEIGHT, NODE_WIDTH } from "./layout";
import { ResearchNode } from "./ResearchNode";
import { SignalEdge } from "./SignalEdge";

const NODE_TYPES = { research: ResearchNode };
const EDGE_TYPES = { signal: SignalEdge };
const ACTIVE = new Set(["running", "leased", "claimed"]);
const EXECUTION = ["running", "queued", "awaiting_review"];
const COMPACT_ZOOM = 0.42;
const COMPACT_WIDTH = 188;
const COMPACT_HEIGHT = 58;
const EMPTY_LAYOUT = { signature: "", nodes: [], routes: new Map() };
const ARIA_LABELS = {
  "node.a11yDescription.default": "按回车或空格选择节点，按 Esc 取消。",
  "node.a11yDescription.keyboardDisabled": "按回车或空格选择节点。",
  "edge.a11yDescription.default": "按回车或空格选择关系，按 Esc 取消。",
  "controls.ariaLabel": "图谱控制",
  "controls.zoomIn.ariaLabel": "放大",
  "controls.zoomOut.ariaLabel": "缩小",
  "controls.fitView.ariaLabel": "显示全部",
  "minimap.ariaLabel": "图谱缩略图",
  "handle.ariaLabel": "关系连接点",
};

function activeSubjects(jobs) {
  return new Set(jobs.filter((job) => ACTIVE.has(job.status)).map((job) => job.subject_id).filter(Boolean));
}

function flowEdges(edges, jobs, nodes, selectedId, overview, routes, relations) {
  const subjects = activeSubjects(jobs);
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  return edges.map((edge, index) => toFlowEdge(edge, index, { subjects, nodeMap, selectedId, overview, routes, relations }));
}

function toFlowEdge(edge, index, context) {
  const id = `edge-${index}`;
  const active = context.subjects.has(edgeSource(edge)) || context.subjects.has(edgeTarget(edge));
  const incident = Boolean(context.selectedId) && [edgeSource(edge), edgeTarget(edge)].includes(context.selectedId);
  const related = context.overview && context.relations.edges.has(id);
  const muted = context.overview && (context.selectedId ? !related : !active);
  const strokeWidth = context.overview ? related ? 6 : active ? 7.5 : 4.5 : active ? 5.6 : incident ? 4.8 : 4;
  return { id, source: edgeSource(edge), target: edgeTarget(edge), ...edgeHandles(edge, context.nodeMap),
    type: "signal", data: { ...edge, active, incident, related, muted, route: context.routes.get(id) },
    style: { strokeWidth, opacity: muted ? 0.05 : 1 } };
}

export function GraphView({ nodes, edges, jobs, selectedId, onSelect, overview = false }) {
  const signature = graphSignature(nodes, edges);
  const [compact, setCompact] = useState(overview);
  const layout = useGraphLayout(nodes, edges, signature);
  const relations = useMemo(() => graphRelations(edges, selectedId, overview), [edges, selectedId, overview]);
  const flowNodes = useMemo(() => decorateLayout(layout.nodes, nodes, jobs, relations.nodes, selectedId, overview, compact), [layout.nodes, nodes, jobs, relations.nodes, selectedId, overview, compact]);
  const flowEdgesValue = useMemo(() => layout.signature ? flowEdges(edges, jobs, flowNodes, selectedId, overview, layout.routes, relations) : [], [layout, edges, jobs, flowNodes, selectedId, overview, relations]);
  const fitViewOptions = { padding: overview ? 0.08 : 0.1, minZoom: 0.05, maxZoom: 1 };
  const updateZoom = useCallback((_, viewport) => setCompact(overview && viewport.zoom < COMPACT_ZOOM), [overview]);
  useEffect(() => setCompact(overview), [overview, signature]);
  return <ReactFlow className={compact ? "semantic-compact" : ""} nodes={flowNodes} edges={flowEdgesValue} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} onMove={updateZoom} onNodeClick={(_, node) => onSelect(node.id)} nodesDraggable={false} nodesConnectable={false} elementsSelectable deleteKeyCode={null} fitView fitViewOptions={fitViewOptions} minZoom={0.05} maxZoom={1.5} ariaLabelConfig={ARIA_LABELS} proOptions={{ hideAttribution: true }}>
    <FitOnChange signature={layout.signature} options={fitViewOptions} />
    <Background gap={24} size={1} color="#d8ddd8" />{overview && <MiniMap position="bottom-left" pannable zoomable nodeColor="#244c3e" maskColor="rgba(242,247,244,.78)" />}<Controls position="top-right" showInteractive={false} />
  </ReactFlow>;
}

function graphSignature(nodes, edges) {
  return `${nodes.map((node) => node.id).join("|")}::${edges.map((edge) => `${edgeSource(edge)}>${edgeTarget(edge)}`).join("|")}`;
}

function useGraphLayout(nodes, edges, signature) {
  const [layout, setLayout] = useState(EMPTY_LAYOUT);
  useEffect(() => {
    let current = true;
    layoutGraph(nodes, edges).then((result) => { if (current) setLayout({ signature, ...result }); });
    return () => { current = false; };
  }, [signature]);
  return layout.signature === signature ? layout : EMPTY_LAYOUT;
}

function traceLineage(edges, selectedId, upstream) {
  const nodes = new Set([selectedId]);
  const relatedEdges = new Set();
  const queue = [selectedId];
  for (let cursor = 0; cursor < queue.length; cursor += 1) edges.forEach((edge, index) => {
    const source = upstream ? edgeTarget(edge) : edgeSource(edge);
    if (source !== queue[cursor]) return;
    const target = upstream ? edgeSource(edge) : edgeTarget(edge);
    relatedEdges.add(`edge-${index}`);
    if (!nodes.has(target)) { nodes.add(target); queue.push(target); }
  });
  return { nodes, edges: relatedEdges };
}

function mergeRelations(first, second) {
  return { nodes: new Set([...first.nodes, ...second.nodes]),
    edges: new Set([...first.edges, ...second.edges]) };
}

function lineageRelations(edges, selectedId) {
  return mergeRelations(traceLineage(edges, selectedId, true), traceLineage(edges, selectedId, false));
}

function incidentRelations(edges, selectedId) {
  const related = edges.map((edge, index) => ({ edge, id: `edge-${index}` }))
    .filter(({ edge }) => [edgeSource(edge), edgeTarget(edge)].includes(selectedId));
  return { nodes: new Set(related.flatMap(({ edge }) => [edgeSource(edge), edgeTarget(edge)])),
    edges: new Set(related.map(({ id }) => id)) };
}

function graphRelations(edges, selectedId, overview) {
  if (!selectedId) return { nodes: new Set(), edges: new Set() };
  return overview ? lineageRelations(edges, selectedId) : incidentRelations(edges, selectedId);
}

function nodeClass(id, selectedId, related, overview) {
  if (id === selectedId) return "graph-focus";
  if (related.has(id)) return "graph-related";
  return overview ? "graph-muted" : "";
}

function compactGeometry(node, compact) {
  if (!compact) return node;
  const x = node.position.x + (NODE_WIDTH - COMPACT_WIDTH) / 2;
  const y = node.position.y + (NODE_HEIGHT - COMPACT_HEIGHT) / 2;
  return { ...node, position: { x, y }, width: COMPACT_WIDTH, height: COMPACT_HEIGHT };
}

function decorateLayout(layout, nodes, jobs, related, selectedId, overview, compact) {
  const data = new Map(executionNodes(nodes, jobs).map((node) => [node.id, node]));
  return layout.filter((node) => data.has(node.id)).map((node) => ({ ...compactGeometry(node, compact),
    data: data.get(node.id), selected: node.id === selectedId,
    className: nodeClass(node.id, selectedId, related, overview), draggable: false, deletable: false }));
}

function executionNodes(nodes, jobs) {
  return nodes.map((node) => ({ ...node, execution_state: jobState(jobs, node.id) }));
}

function jobState(jobs, nodeId) {
  return EXECUTION.find((status) => jobs.some((job) => job.status === status && [job.subject_id, job.output_node_id].includes(nodeId))) || "";
}

function FitOnChange({ signature, options }) {
  const { fitView } = useReactFlow();
  useEffect(() => { if (signature) requestAnimationFrame(() => fitView(options)); }, [signature]);
  return null;
}
