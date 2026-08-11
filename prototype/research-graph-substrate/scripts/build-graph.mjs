import { readFile, writeFile, mkdir } from "node:fs/promises";
import { parse } from "yaml";

const source = "/home/q2635/wsl-workspace/music/directions.yaml";
const roleFields = ["prerequisites", "controls", "required_artifacts", "historical_direction_ids"];
const kinds = { prerequisites: "prerequisite", controls: "control", required_artifacts: "artifact", historical_direction_ids: "history" };

function label(value) {
  return String(value).replaceAll("_", " ");
}

function node(id, kind, title, sourceField, detail = {}) {
  return { id: `${kind}:${id}`, kind, title: label(title), source, sourceField, detail };
}

function uniqueRoleNodes(directions, field) {
  const values = new Set(directions.flatMap((item) => item[field] || []));
  return [...values].map((value) => node(value, kinds[field], value, `directions[*].${field}`));
}

function registryNodes(data, field, kind) {
  return data[field].map((value) => node(value, kind, value, field));
}

function directionNode(item) {
  const detail = { hypothesis: item.hypothesis, prior_percent: item.prior_percent, status: item.candidate_status };
  return node(item.id, "direction", item.title, `directions[${item.id}]`, detail);
}

function roleLinks(item, field) {
  return (item[field] || []).map((value) => ({ source: `direction:${item.id}`, target: `${kinds[field]}:${value}`, relation: field }));
}

function directionLinks(item, data) {
  const base = [{ source: "question:root", target: `direction:${item.id}`, relation: "candidate" }];
  const axes = item.changed_objects.map((value) => ({ source: `direction:${item.id}`, target: `object:${value}`, relation: "changes" }));
  const gates = data.selection_gates.map((value) => ({ source: `direction:${item.id}`, target: `gate:${value}`, relation: "requires" }));
  return base.concat(axes, gates, roleFields.flatMap((field) => roleLinks(item, field)));
}

function build(data) {
  const root = node("root", "question", "Exact instrument-aware transcription", "registry");
  const registries = registryNodes(data, "candidate_objects", "object").concat(registryNodes(data, "shared_immutable_objects", "immutable"), registryNodes(data, "selection_gates", "gate"));
  const roles = roleFields.flatMap((field) => uniqueRoleNodes(data.directions, field));
  const links = data.directions.flatMap((item) => directionLinks(item, data));
  return { nodes: [root, ...data.directions.map(directionNode), ...registries, ...roles], links, source, generatedFrom: "explicit YAML fields only" };
}

const data = parse(await readFile(source, "utf8"));
await mkdir(new URL("../public/", import.meta.url), { recursive: true });
await writeFile(new URL("../public/music-graph.json", import.meta.url), JSON.stringify(build(data), null, 2));
