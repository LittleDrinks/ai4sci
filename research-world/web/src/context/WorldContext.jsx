import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { getBootstrap, postCommand, streamUrl } from "../api";

const EMPTY = { projects: [], nodes: [], review_nodes: [], edges: [], events: [], jobs: [], agents: [], runtimes: [], artifacts: [] };
const WorldContext = createContext(null);

function useWorldState() {
  const [data, setData] = useState(EMPTY);
  const [projectId, setProjectId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  return { data, setData, projectId, setProjectId, loading, setLoading, error, setError };
}

function useRefresh(state, desiredProject) {
  return useCallback(async (nextId = state.projectId) => {
    if (desiredProject.current && nextId && nextId !== desiredProject.current) return;
    try {
      const result = await getBootstrap(nextId);
      if (desiredProject.current && result.active_project_id !== desiredProject.current) return;
      desiredProject.current = result.active_project_id;
      state.setData(result);
      state.setProjectId(result.active_project_id);
      state.setError("");
    } catch (error) { state.setError(error.message); }
    finally { state.setLoading(false); }
  }, [state.projectId]);
}

function useEventStream(projectId, refresh) {
  const timer = useRef(null);
  const [streamState, setStreamState] = useState("idle");
  useEffect(() => {
    if (!projectId) return undefined;
    const source = new EventSource(streamUrl(projectId));
    source.onopen = () => setStreamState("live");
    source.onerror = () => setStreamState("reconnecting");
    source.onmessage = () => { clearTimeout(timer.current); timer.current = setTimeout(() => refresh(projectId), 120); };
    return () => { clearTimeout(timer.current); source.close(); };
  }, [projectId, refresh]);
  return streamState;
}

export function WorldProvider({ children }) {
  const state = useWorldState();
  const desiredProject = useRef("");
  const refresh = useRefresh(state, desiredProject);
  useEffect(() => { refresh(""); }, []);
  useEffect(() => {
    const timer = setInterval(() => refresh(state.projectId), 5000);
    return () => clearInterval(timer);
  }, [state.projectId, refresh]);
  const streamState = useEventStream(state.projectId, refresh);
  const selectProject = useCallback((id) => { desiredProject.current = id; state.setLoading(true); state.setProjectId(id); return refresh(id); }, [refresh]);
  const command = async (type, payload) => {
    try { const result = await postCommand(type, payload); await refresh(result?.project_id || state.projectId); return result; }
    catch (error) { state.setError(error.message); throw error; }
  };
  const value = useMemo(() => ({ ...state, refresh, command, selectProject, streamState }), [state.data, state.projectId, state.loading, state.error, streamState, refresh, selectProject]);
  return <WorldContext.Provider value={value}>{children}</WorldContext.Provider>;
}

export function useWorld() {
  const value = useContext(WorldContext);
  if (!value) throw new Error("useWorld requires WorldProvider");
  return value;
}
