import { Background, Controls, MiniMap, ReactFlow, useReactFlow } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import { edgeHandles, layoutGraph } from "./layout";
import { ResearchNode } from "./ResearchNode";
import { SignalEdge } from "./SignalEdge";


const NODE_TYPES = { research: ResearchNode };
const EDGE_TYPES = { signal: SignalEdge };
const EMPTY_LAYOUT = { signature: "", nodes: [], routes: new Map() };


export function GraphView({ nodes, edges, selectedId, onSelect, onStart, newIds }) {
  const signature = graphSignature(nodes, edges);
  const layout = useGraphLayout(nodes, edges, signature);
  const flowNodes = useMemo(() => decorateNodes(layout.nodes, nodes, selectedId, onStart, newIds), [layout.nodes, nodes, selectedId, onStart, newIds]);
  const flowEdges = useMemo(() => decorateEdges(edges, flowNodes, selectedId, layout.routes), [edges, flowNodes, selectedId, layout.routes]);
  const fit = { padding: .14, maxZoom: 1 };
  return <ReactFlow nodes={flowNodes} edges={flowEdges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} onNodeClick={(_, node) => onSelect(node.id)} nodesDraggable={false} nodesConnectable={false} fitView fitViewOptions={fit} minZoom={.15} maxZoom={1.5} proOptions={{ hideAttribution: true }}>
    <FitOnChange signature={layout.signature} options={fit} />
    <Background gap={24} size={1} color="var(--graph-dot)" /><MiniMap pannable zoomable nodeColor={(node) => node.data.life_state === "ghost" ? "#9ca3af" : "#4b5563"} maskColor="var(--minimap-mask)" /><Controls showInteractive={false} />
  </ReactFlow>;
}


function graphSignature(nodes, edges) {
  return `${nodes.map((node) => node.id).join("|")}::${edges.map((edge) => `${edge.source}>${edge.target}:${edge.polarity}`).join("|")}`;
}


function useGraphLayout(nodes, edges, signature) {
  const [layout, setLayout] = useState(EMPTY_LAYOUT);
  useEffect(() => {
    let current = true;
    layoutGraph(nodes, edges).then((value) => { if (current) setLayout({ signature, ...value }); });
    return () => { current = false; };
  }, [signature]);
  return layout.signature === signature ? layout : EMPTY_LAYOUT;
}


function decorateNodes(layout, nodes, selectedId, onStart, newIds) {
  const values = new Map(nodes.map((node) => [node.id, node]));
  return layout.map((node) => ({ ...node, selected: node.id === selectedId,
    data: { ...values.get(node.id), onStart, justCompleted: newIds.has(node.id) } }));
}


function decorateEdges(edges, nodes, selectedId, routes) {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  return edges.map((edge, index) => ({ id: `edge-${index}`, source: edge.source, target: edge.target,
    ...edgeHandles(edge, nodeMap), type: "signal", data: { ...edge, route: routes.get(`edge-${index}`),
      incident: [edge.source, edge.target].includes(selectedId), muted: Boolean(selectedId) && ![edge.source, edge.target].includes(selectedId) },
    style: { strokeWidth: edge.polarity === "lineage" ? 2 : 3.5,
      strokeDasharray: edge.polarity === "refutes" ? "7 5" : undefined } }));
}


function FitOnChange({ signature, options }) {
  const { fitView } = useReactFlow();
  useEffect(() => { if (signature) requestAnimationFrame(() => fitView(options)); }, [signature]);
  return null;
}
