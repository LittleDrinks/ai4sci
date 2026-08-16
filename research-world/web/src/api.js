async function decode(response) {
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new Error(body?.detail || `请求失败（${response.status}）`);
  return body;
}


const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });


export const getBootstrap = (projectId) => fetch(`/api/v1/bootstrap${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`).then(decode);
export const startWorkflow = (projectId, body) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/workflows`, json("POST", body)).then(decode);
export const confirmWorkflow = (id) => fetch(`/api/v1/workflows/${encodeURIComponent(id)}/confirm`, { method: "POST" }).then(decode);
export const resolveWorkflow = (id, body) => fetch(`/api/v1/workflows/${encodeURIComponent(id)}/resolve`, json("POST", body)).then(decode);
export const getMessages = (projectId, nodeId) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/messages?node_id=${encodeURIComponent(nodeId)}`).then(decode);
export const sendMessage = (projectId, body) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/messages`, json("POST", body)).then(decode);
export const clearConversation = (projectId, nodeId) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/messages?node_id=${encodeURIComponent(nodeId)}`, { method: "DELETE" }).then(decode);
export const materializeDraft = (projectId, body) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}/drafts/materialize`, json("POST", body)).then(decode);
export const setProjectAuto = (projectId, auto) => fetch(`/api/v1/projects/${encodeURIComponent(projectId)}`, json("PATCH", { auto })).then(decode);


export async function postCommand(type, payload) {
  if (type !== "create_project") throw new Error("不支持的命令");
  const root = payload.root || `/projects/${crypto.randomUUID()}`;
  return fetch("/api/v1/projects", json("POST", { name: payload.title, root, question: payload.question })).then(decode);
}
