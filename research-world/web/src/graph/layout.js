import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from "d3-force";

export const NODE_WIDTH = 320;
export const NODE_HEIGHT = 194;
const LARGE_GRAPH_SIZE = 36;
const NODE_RADIUS = Math.hypot(NODE_WIDTH / 2, NODE_HEIGHT / 2);
const OPPOSITE = { top: "bottom", right: "left", bottom: "top", left: "right" };
const ELK_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.spacing.nodeNode": "130",
  "elk.layered.spacing.nodeNodeBetweenLayers": "240",
  "elk.layered.nodePlacement.strategy": "SIMPLE",
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
};
let elkEngine;

export const edgeSource = (edge) => edge.source;
export const edgeTarget = (edge) => edge.target;

function forceSettings(count) {
  return { linkDistance: 340, linkStrength: 0.4, charge: -600, distanceMax: 1650,
    collisionIterations: 3, collisionRadius: NODE_RADIUS + 20, ticks: count > 120 ? 620 : 560 };
}

function layoutSeed(nodes) {
  return nodes.reduce((seed, node) => [...String(node.id)].reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, seed), 17);
}

function randomSource(seed) {
  let value = seed || 1;
  return () => { value = (value * 1664525 + 1013904223) >>> 0; return value / 4294967296; };
}

function validEdges(edges, ids) {
  return edges.map((edge, index) => ({ id: `edge-${index}`, source: edgeSource(edge), target: edgeTarget(edge) }))
    .filter((edge) => ids.has(edge.source) && ids.has(edge.target));
}

function graphDepths(nodes, links) {
  const depths = new Map(nodes.map((node) => [node.id, 0]));
  const incoming = new Map(nodes.map((node) => [node.id, 0]));
  const outgoing = new Map(nodes.map((node) => [node.id, []]));
  links.forEach(({ source, target }) => { incoming.set(target, incoming.get(target) + 1); outgoing.get(source).push(target); });
  const queue = nodes.filter((node) => incoming.get(node.id) === 0).map((node) => node.id);
  for (let index = 0; index < queue.length; index += 1) advanceDepth(queue[index], queue, depths, incoming, outgoing);
  return depths;
}

function advanceDepth(source, queue, depths, incoming, outgoing) {
  outgoing.get(source).forEach((target) => {
    depths.set(target, Math.max(depths.get(target), depths.get(source) + 1));
    incoming.set(target, incoming.get(target) - 1);
    if (incoming.get(target) === 0) queue.push(target);
  });
}

function addDirectionForces(simulation, nodes, depths) {
  const maxDepth = Math.max(0, ...depths.values());
  const center = maxDepth / 2;
  return simulation.force("depth", forceX((node) => (depths.get(node.id) - center) * 340).strength(0.24))
    .force("lane", forceY(0).strength(0.01));
}

function forceLayout(nodes, edges) {
  const settings = forceSettings(nodes.length);
  const points = nodes.map((node) => ({ id: node.id }));
  const links = validEdges(edges, new Set(points.map((node) => node.id)));
  const depths = graphDepths(points, links);
  const simulation = forceSimulation(points).randomSource(randomSource(layoutSeed(nodes)))
    .force("link", forceLink(links).id((node) => node.id).distance(settings.linkDistance).strength(settings.linkStrength))
    .force("charge", forceManyBody().strength(settings.charge).distanceMax(settings.distanceMax))
    .force("collide", forceCollide(settings.collisionRadius).iterations(settings.collisionIterations))
    .force("center", forceCenter(0, 0)).stop();
  addDirectionForces(simulation, points, depths);
  simulation.tick(settings.ticks);
  return { nodes: nodes.map((node, index) => forceNode(node, points[index])), routes: new Map() };
}

function forceNode(node, point) {
  return flowNode(node, point.x - NODE_WIDTH / 2, point.y - NODE_HEIGHT / 2);
}

function flowNode(node, x, y) {
  return { id: node.id, type: "research", data: { ...node }, position: { x, y },
    width: NODE_WIDTH, height: NODE_HEIGHT, draggable: false };
}

async function getElk() {
  if (elkEngine) return elkEngine;
  const { default: ELK } = await import("elkjs/lib/elk.bundled.js");
  elkEngine = new ELK();
  return elkEngine;
}

function elkGraph(nodes, edges) {
  const ids = new Set(nodes.map((node) => node.id));
  return { id: "research-graph", layoutOptions: ELK_OPTIONS,
    children: nodes.map((node) => ({ id: node.id, width: NODE_WIDTH, height: NODE_HEIGHT })),
    edges: validEdges(edges, ids).map((edge) => ({ id: edge.id, sources: [edge.source], targets: [edge.target] })) };
}

function routePoints(edge) {
  const section = edge.sections?.[0];
  return section ? [section.startPoint, ...(section.bendPoints || []), section.endPoint] : [];
}

function elkRoutes(edges) {
  return new Map(edges.map((edge) => [edge.id, routePoints(edge)]).filter(([, points]) => points.length > 1));
}

async function elkLayout(nodes, edges) {
  const elk = await getElk();
  const result = await elk.layout(elkGraph(nodes, edges));
  const positions = new Map(result.children.map((node) => [node.id, node]));
  return { nodes: nodes.map((node) => flowNode(node, positions.get(node.id).x, positions.get(node.id).y)),
    routes: elkRoutes(result.edges) };
}

export async function layoutGraph(nodes, edges) {
  return nodes.length > LARGE_GRAPH_SIZE ? forceLayout(nodes, edges) : elkLayout(nodes, edges);
}

function direction(dx, dy) {
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? "right" : "left";
  return dy >= 0 ? "bottom" : "top";
}

export function edgeSides(edge, nodeMap) {
  const source = nodeMap.get(edgeSource(edge));
  const target = nodeMap.get(edgeTarget(edge));
  if (!source || !target) return {};
  const side = direction(target.position.x - source.position.x, target.position.y - source.position.y);
  return { sourceSide: side, targetSide: OPPOSITE[side] };
}

export function edgeHandles(edge, nodeMap) {
  const { sourceSide, targetSide } = edgeSides(edge, nodeMap);
  return sourceSide ? { sourceHandle: `source-${sourceSide}`, targetHandle: `target-${targetSide}` } : {};
}
