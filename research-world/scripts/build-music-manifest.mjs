import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const graphPath = resolve(root, "prototype/research-graph-substrate/public/music-graph.json");
const outputPath = resolve(import.meta.dirname, "../fixtures/music-directions.json");

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function provenance(node, sourceHash, graphHash) {
  return { source_path: node.source, source_sha256: sourceHash, source_field: node.sourceField,
    graph_path: graphPath, graph_sha256: graphHash };
}

function relations(graph, ref) {
  return graph.links.filter((link) => link.source === ref)
    .map(({ target, relation }) => ({ target_ref: target, relation }));
}

function dependencies(graph, ref) {
  const incoming = graph.links.filter((link) => link.target === ref && link.relation === "candidate")
    .map((link) => link.source);
  const required = relations(graph, ref).filter((link) => link.relation !== "candidate")
    .map((link) => link.target_ref);
  return [...new Set([...incoming, ...required])].sort();
}

function summary(node, graph) {
  if (node.detail?.hypothesis) return node.detail.hypothesis;
  const references = graph.links.filter((link) => link.target === node.id).length;
  if (!references) return `Registered in ${node.sourceField}.`;
  return `Referenced by ${references} registered research direction${references === 1 ? "" : "s"}.`;
}

function manifestNode(node, graph, sourceHash, graphHash) {
  return { ref: node.id, kind: node.kind, title: node.title, summary: summary(node, graph),
    content: { record: node.detail, provenance: provenance(node, sourceHash, graphHash),
      source_relations: relations(graph, node.id) }, dependencies: dependencies(graph, node.id) };
}

function build(graph, sourceHash, graphHash) {
  const rootNode = graph.nodes.find((node) => node.kind === "question");
  const nodes = graph.nodes.filter((node) => node.id !== rootNode.id)
    .map((node) => manifestNode(node, graph, sourceHash, graphHash));
  return { schema_version: 1, title: rootNode.title, question: rootNode.title,
    root_ref: rootNode.id, sources: [{ path: graph.source, sha256: sourceHash },
      { path: graphPath, sha256: graphHash }], nodes };
}

const graphBytes = await readFile(graphPath);
const graph = JSON.parse(graphBytes);
const sourceBytes = await readFile(graph.source);
const manifest = build(graph, sha256(sourceBytes), sha256(graphBytes));
await mkdir(resolve(import.meta.dirname, "../fixtures"), { recursive: true });
await writeFile(outputPath, `${JSON.stringify(manifest, null, 2)}\n`);
