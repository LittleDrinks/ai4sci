import { useEffect, useRef, useState } from "react";
import { useWorld } from "./WorldContext";

async function resolveEntity(id, projectId, fetchEntity, selectProject, request, setStatus) {
  try {
    const value = await fetchEntity(id);
    if (request.current !== id) return;
    if (value.project_id !== projectId) await selectProject(value.project_id);
    if (request.current === id) setStatus("done");
  } catch { if (request.current === id) setStatus("failed"); }
}

export function useProjectEntity(id, collection, fetchEntity) {
  const world = useWorld();
  const entity = world.data[collection].find((item) => item.id === id);
  const request = useRef("");
  const [status, setStatus] = useState("idle");
  useEffect(() => {
    if (world.loading || entity || request.current === id) return;
    request.current = id; setStatus("loading");
    resolveEntity(id, world.projectId, fetchEntity, world.selectProject, request, setStatus);
  }, [id, entity?.id, world.loading, world.projectId, world.selectProject, fetchEntity]);
  const resolving = world.loading || (!entity && (request.current !== id || status === "loading"));
  return { ...world, entity, resolving };
}
