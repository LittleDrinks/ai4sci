import { Background, Controls, MiniMap, ReactFlow } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import { ResearchNode } from "./ResearchNode";
import { SignalEdge } from "./SignalEdge";


const NODE_TYPES = { research: ResearchNode };
const EDGE_TYPES = { signal: SignalEdge };


export function GraphView({ nodes, edges, selectedId, onSelect, onStart, newIds }) {
  const compact = useCompactGraph();
  const flowNodes = useMemo(() => layoutNodes(nodes, selectedId, onStart, newIds, compact), [nodes, selectedId, onStart, newIds, compact]);
  const flowEdges = useMemo(() => decorateEdges(edges, selectedId), [edges, selectedId]);
  return <ReactFlow nodes={flowNodes} edges={flowEdges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} onNodeClick={(_, node) => onSelect(node.id)} nodesDraggable={false} nodesConnectable={false} fitView fitViewOptions={{ padding: .12, maxZoom: 1 }} minZoom={.15} maxZoom={1.5} proOptions={{ hideAttribution: true }}>
    <Background gap={24} size={1} color="var(--graph-dot)" /><MiniMap pannable zoomable nodeColor={(node) => node.data.life_state === "ghost" ? "#9ca3af" : "#4b5563"} maskColor="var(--minimap-mask)" /><Controls showInteractive={false} />
  </ReactFlow>;
}


function layoutNodes(nodes, selectedId, onStart, newIds, compact) {
  const counts = new Map();
  return nodes.map((node) => {
    const row = counts.get(node.kind) || 0;
    counts.set(node.kind, row + 1);
    const position = compact ? { x: row * 310, y: lane(node.kind) * 150 } : { x: lane(node.kind) * 320, y: row * 170 };
    return { id: node.id, type: "research", position,
      width: 280, height: 128, selected: node.id === selectedId,
      data: { ...node, onStart, justCompleted: newIds.has(node.id) } };
  });
}


function useCompactGraph() {
  const [compact, setCompact] = useState(() => matchMedia("(max-width: 640px)").matches);
  useEffect(() => {
    const query = matchMedia("(max-width: 640px)");
    const update = () => setCompact(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return compact;
}


function decorateEdges(edges, selectedId) {
  return edges.map((edge, index) => ({ id: `edge-${index}`, source: edge.source, target: edge.target,
    sourceHandle: "source-right", targetHandle: "target-left", type: "signal", data: { ...edge,
      incident: [edge.source, edge.target].includes(selectedId), muted: Boolean(selectedId) && ![edge.source, edge.target].includes(selectedId) },
    style: { strokeWidth: edge.polarity === "refutes" ? 2.5 : 3.5, strokeDasharray: edge.polarity === "refutes" ? "7 5" : undefined } }));
}


function lane(kind) {
  return { question: 0, source: 1, direction: 2, experiment: 3 }[kind] ?? 0;
}
