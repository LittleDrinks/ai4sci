async function decode(response) {
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}

export function getBootstrap(projectId) {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return fetch(`/api/bootstrap${query}`).then(decode);
}

export function getNode(nodeId) {
  return fetch(`/api/nodes/${encodeURIComponent(nodeId)}`).then(decode);
}

export function getArtifactMetadata(artifactId) {
  return fetch(`/api/artifacts/${encodeURIComponent(artifactId)}/metadata`).then(decode);
}

export function postCommand(type, payload, actor = { kind: "human", id: "local-user" }) {
  return fetch("/api/commands", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type, actor, payload }),
  }).then(decode).then((body) => body.result);
}

export function streamUrl(projectId) {
  return `/api/events/stream?project_id=${encodeURIComponent(projectId)}`;
}

export function artifactUrl(id) {
  return `/api/artifacts/${encodeURIComponent(id)}/content`;
}
