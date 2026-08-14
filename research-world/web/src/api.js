async function decode(response) {
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}

export const getBootstrap = (projectId) => fetch(`/api/v1/bootstrap${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`).then(decode);
export const attemptLogUrl = (id) => `/api/v1/attempts/${encodeURIComponent(id)}/log`;

const post = (url, body = {}) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(decode);

export async function postCommand(type, payload) {
  if (type === "create_project") {
    return post("/api/v1/projects", { name: payload.title, question: payload.question });
  }
  if (type === "plan_project") return post(`/api/v1/projects/${encodeURIComponent(payload.project_id)}/plan`);
  if (type === "run_direction") return post(`/api/v1/directions/${encodeURIComponent(payload.direction_id)}/admit-run`);
  if (type === "message") return post(`/api/v1/projects/${encodeURIComponent(payload.project_id)}/messages`, payload);
  throw new Error("Unknown command");
}
