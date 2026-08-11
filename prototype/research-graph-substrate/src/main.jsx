import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { ReactFlow, Background, Controls, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import cytoscape from "cytoscape";
import dagre from "dagre";
import "./styles.css";

const variants = { A: ["依赖", "从问题到验证条件"], B: ["网络", "机制邻域与共用约束"], C: ["来源", "从节点回到产生字段"] };
const icons = { question: "?", direction: "↗", object: "□", immutable: "◇", gate: "◆", prerequisite: "⌁", control: "⊣", artifact: "▤", history: "◷" };
const shapes = { question: "ellipse", direction: "round-rectangle", object: "rectangle", immutable: "diamond", gate: "hexagon", prerequisite: "tag", control: "round-tag", artifact: "vee", history: "ellipse" };

function queryVariant() {
  return new URLSearchParams(location.search).get("variant") || "A";
}

function GraphNode({ data }) {
  return <div className={`graph-node ${data.kind}`} title={data.title}><Handle type="target" position={Position.Left}/><i>{icons[data.kind]}</i><b>{data.title}</b><Handle type="source" position={Position.Right}/></div>;
}

function layoutGraph(graph) {
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 18, ranksep: 76 });
  graph.nodes.forEach((item) => g.setNode(item.id, { width: 176, height: 54 }));
  graph.links.forEach((link) => g.setEdge(link.source, link.target));
  dagre.layout(g);
  return graph.nodes.map((item) => ({ id: item.id, type: "graph", data: item, position: { x: g.node(item.id).x - 88, y: g.node(item.id).y - 27 } }));
}

function dependencySlice(graph, selected) {
  const kinds = selected.kind === "direction" ? ["question"] : ["question", "direction"];
  const base = new Set(graph.nodes.filter((node) => kinds.includes(node.kind)).map((node) => node.id));
  if (selected.kind === "direction") base.add(selected.id);
  if (selected.kind === "direction") graph.links.filter((link) => link.source === selected.id).forEach((link) => base.add(link.target));
  const nodes = graph.nodes.filter((node) => base.has(node.id));
  const links = graph.links.filter((link) => base.has(link.source) && base.has(link.target));
  return { nodes, links };
}

function DependencyView({ graph, selected, select }) {
  const visible = useMemo(() => dependencySlice(graph, selected), [graph, selected]);
  const nodes = useMemo(() => layoutGraph(visible), [visible]);
  const edges = visible.links.map((link, i) => ({ id: `e${i}`, ...link, style: { stroke: "#91a097" } }));
  return <ReactFlow key={selected.id} nodes={nodes} edges={edges} nodeTypes={{ graph: GraphNode }} onNodeClick={(_, n) => select(n.data)} fitView fitViewOptions={{ padding: .12 }} minZoom={.18}><Background gap={22} color="#d8e1dc"/><Controls/></ReactFlow>;
}

function cytoscapeElements(graph) {
  const nodes = graph.nodes.map((item) => ({ data: { ...item, label: item.title } }));
  const edges = graph.links.map((item, i) => ({ data: { id: `e${i}`, ...item } }));
  return [...nodes, ...edges];
}

function CytoscapeView({ graph, select, focus }) {
  const host = useRef(null);
  const visible = focus ? neighborhood(graph, focus) : graph;
  useEffect(() => mountCytoscape(host.current, visible, select, focus), [graph, focus]);
  return <div className="cy" ref={host}/>;
}

function neighborhood(graph, focus) {
  const ids = new Set([focus]);
  graph.links.filter((link) => link.source === focus || link.target === focus).forEach((link) => { ids.add(link.source); ids.add(link.target); });
  const nodes = graph.nodes.filter((node) => ids.has(node.id));
  const links = graph.links.filter((link) => ids.has(link.source) && ids.has(link.target));
  return { ...graph, nodes, links };
}

function mountCytoscape(host, graph, select, focus) {
  const cy = cytoscape({ container: host, elements: cytoscapeElements(graph), style: cyStyle(), layout: cyLayout(focus) });
  cy.on("tap", "node", (event) => select(graph.nodes.find((item) => item.id === event.target.id())));
  return () => cy.destroy();
}

function cyLayout(focus) {
  return focus ? { name: "concentric", fit: true, padding: 70, minNodeSpacing: 36, levelWidth: () => 2 } : { name: "cose", animate: false, fit: true, padding: 80, nodeRepulsion: () => 90000 };
}

function cyStyle() {
  return [{ selector: "node", style: { "shape": (e) => shapes[e.data("kind")], "background-color": "#f9fbfa", "border-color": "#244539", "border-width": 2, "label": "data(label)", "font-size": 13, "text-wrap": "ellipsis", "text-max-width": 128, "width": 150, "height": 52 } }, { selector: "edge", style: { "curve-style": "bezier", "width": 1.5, "line-color": "#9baba2", "target-arrow-color": "#9baba2", "target-arrow-shape": "triangle", "arrow-scale": .7 } }, { selector: ".dim", style: { "opacity": .1 } }];
}

function Inspector({ node, graph, setFocus }) {
  const links = graph.links.filter((link) => link.source === node.id || link.target === node.id);
  return <aside className="inspector"><div className="kind"><i>{icons[node.kind]}</i><span>{node.kind}</span></div><h1>{node.title}</h1><button onClick={() => setFocus(node.id)}>只看相邻节点</button><dl><dt>来源</dt><dd>{node.source}</dd><dt>字段</dt><dd>{node.sourceField}</dd><dt>关系</dt><dd>{links.length}</dd>{Object.entries(node.detail || {}).map(([k,v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{String(v)}</dd></React.Fragment>)}</dl></aside>;
}

function VariantSwitch({ active }) {
  return <nav className="switcher">{Object.entries(variants).map(([key, value]) => <a className={active === key ? "active" : ""} href={`?variant=${key}`} key={key}><b>{key} · {value[0]}</b><span>{value[1]}</span></a>)}</nav>;
}

function App() {
  const [graph, setGraph] = useState(null), [selected, setSelected] = useState(null), [focus, setFocus] = useState(null);
  const variant = queryVariant();
  useEffect(() => { fetch("/music-graph.json").then((r) => r.json()).then((data) => { setGraph(data); setSelected(data.nodes[0]); }); }, []);
  if (!graph || !selected) return <div className="loading">Loading graph...</div>;
  const view = variant === "A" ? <DependencyView graph={graph} selected={selected} select={setSelected}/> : <CytoscapeView graph={graph} select={setSelected} focus={variant === "C" ? (focus || selected.id) : null}/>;
  return <main><header><b>AMT Research Registry</b><span>{graph.nodes.length} nodes · {graph.links.length} explicit relations</span><code>music/directions.yaml</code></header><section className="workspace"><div className="canvas">{view}</div><Inspector node={selected} graph={graph} setFocus={setFocus}/></section><VariantSwitch active={variant}/></main>;
}

createRoot(document.getElementById("root")).render(<App/>);
