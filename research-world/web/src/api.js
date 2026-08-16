async function decode(response) {
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}

export const getBootstrap = (projectId) => fetch(`/api/v1/bootstrap${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`).then(decode);
export const getNode = (id) => fetch(`/api/v1/nodes/${encodeURIComponent(id)}`).then(decode);
export const getArtifactMetadata = (id) => fetch(`/api/v1/artifacts/${encodeURIComponent(id)}`).then(decode);
export const artifactUrl = (id) => `/api/v1/artifacts/${encodeURIComponent(id)}/content`;
export const getRuns = () => fetch("/api/v1/runs").then(decode);
export const createRun = (project_id) => fetch("/api/v1/runs", json("POST", { project_id })).then(decode);
export const getRun = (id) => fetch(`/api/v1/runs/${encodeURIComponent(id)}`).then(decode);
export const getRunWire = (id) => fetch(`/api/v1/runs/${encodeURIComponent(id)}/wire`).then(decode);
export const getRunContext = (id) => fetch(`/api/v1/runs/${encodeURIComponent(id)}/context`).then(decode);
export const getRunJobs = (id) => fetch(`/api/v1/runs/${encodeURIComponent(id)}/agents-jobs`).then(decode);
export const runEventsUrl = (id) => `/api/v1/runs/${encodeURIComponent(id)}/events?follow=true`;
export const sendRunMessage = (id, body) => fetch(`/api/v1/runs/${encodeURIComponent(id)}/messages`, json("POST", body)).then(decode);
const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const startWorkflow = (projectId, body) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/workflows`, json("POST", body)).then(decode);
export const confirmWorkflow = (id) => fetch(`/api/v1/workflows/${encodeURIComponent(id)}/confirm`, { method: "POST" }).then(decode);
export const resolveWorkflow = (id, body) => fetch(`/api/v1/workflows/${encodeURIComponent(id)}/resolve`, json("POST", body)).then(decode);
export const getMessages = (projectId, nodeId) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/messages?node_id=${encodeURIComponent(nodeId)}`).then(decode);
export const sendMessage = (projectId, body) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/messages`, json("POST", body)).then(decode);
export const setProjectAuto = (projectId, auto) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}`, json("PATCH", { auto })).then(decode);

export async function postCommand(type, payload) {
  if (type !== "create_project") throw new Error("Command is not available in the run control plane");
  const root = payload.root || `/projects/${payload.title.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}`;
  return fetch("/api/v1/projects", json("POST", { name: payload.title, root, question: payload.question })).then(decode);
}
