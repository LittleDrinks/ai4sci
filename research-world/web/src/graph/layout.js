import { Position } from "@xyflow/react";


export const NODE_WIDTH = 280;
export const NODE_HEIGHT = 128;
const KIND_ORDER = ["question", "source", "direction", "experiment"];
const COLUMN_GAP = 150;
const OPPOSITE = { top: "bottom", right: "left", bottom: "top", left: "right" };
const HANDLE_POINTS = [[Position.Top, NODE_WIDTH / 2, 0], [Position.Right, NODE_WIDTH, NODE_HEIGHT / 2],
  [Position.Bottom, NODE_WIDTH / 2, NODE_HEIGHT], [Position.Left, 0, NODE_HEIGHT / 2]];
const HANDLES = ["target", "source"].flatMap((type) => HANDLE_POINTS.map(([position, x, y]) => (
  { id: `${type}-${position}`, type, position, x, y, width: 1, height: 1 })));
const OPTIONS = { "elk.algorithm": "layered", "elk.direction": "RIGHT", "elk.edgeRouting": "ORTHOGONAL",
  "elk.spacing.nodeNode": "76", "elk.layered.spacing.nodeNodeBetweenLayers": "150",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX", "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP" };
let elkEngine;


function validEdges(edges, ids) {
  return edges.map((edge, index) => ({ id: `edge-${index}`, sources: [edge.source], targets: [edge.target] }))
    .filter((edge) => ids.has(edge.sources[0]) && ids.has(edge.targets[0]));
}


function inputGraph(nodes, edges) {
  const ids = new Set(nodes.map((node) => node.id));
  return { id: "research-graph", layoutOptions: OPTIONS,
    children: nodes.map((node) => ({ id: node.id, width: NODE_WIDTH, height: NODE_HEIGHT })),
    edges: validEdges(edges, ids) };
}


async function engine() {
  if (!elkEngine) { const { default: ELK } = await import("elkjs/lib/elk.bundled.js"); elkEngine = new ELK(); }
  return elkEngine;
}


export async function layoutGraph(nodes, edges) {
  if (!nodes.length) return { nodes: [], routes: new Map() };
  const result = await (await engine()).layout(inputGraph(nodes, edges));
  const source = new Map(nodes.map((node) => [node.id, node]));
  const columns = visibleColumns(nodes);
  return { nodes: result.children.map((node) => flowNode(node, source.get(node.id), columns)), routes: new Map() };
}


function visibleColumns(nodes) {
  const kinds = new Set(nodes.map((node) => node.kind));
  return new Map(KIND_ORDER.filter((kind) => kinds.has(kind)).map((kind, index) => [kind, index]));
}


function flowNode(layout, node, columns) {
  const x = (columns.get(node.kind) || 0) * (NODE_WIDTH + COLUMN_GAP);
  return { id: node.id, type: "research", position: { x, y: layout.y }, width: NODE_WIDTH, height: NODE_HEIGHT,
    measured: { width: NODE_WIDTH, height: NODE_HEIGHT }, handles: HANDLES };
}


function direction(dx, dy) {
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? "right" : "left";
  return dy >= 0 ? "bottom" : "top";
}


export function edgeHandles(edge, nodeMap) {
  const source = nodeMap.get(edge.source);
  const target = nodeMap.get(edge.target);
  if (!source || !target) return {};
  const side = direction(target.position.x - source.position.x, target.position.y - source.position.y);
  return { sourceHandle: `source-${side}`, targetHandle: `target-${OPPOSITE[side]}` };
}
