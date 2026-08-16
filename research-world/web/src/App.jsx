import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { useWorld } from "./context/WorldContext";


const ActivityPage = lazy(() => import("./pages/ActivityPage").then((value) => ({ default: value.ActivityPage })));
const ChatPage = lazy(() => import("./pages/ChatPage").then((value) => ({ default: value.ChatPage })));
const MapPage = lazy(() => import("./pages/MapPage").then((value) => ({ default: value.MapPage })));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage").then((value) => ({ default: value.ProjectsPage })));


function View({ component: Component }) {
  return <Suspense fallback={<div className="page-loading">正在载入...</div>}><Component /></Suspense>;
}


function ProjectRequired() {
  const { loading, projectId } = useWorld();
  if (loading) return <div className="page-loading">正在载入项目...</div>;
  return projectId ? <AppShell /> : <Navigate to="/projects" replace />;
}


export function App() {
  return <Routes>
    <Route index element={<Navigate to="/projects" replace />} />
    <Route path="projects" element={<View component={ProjectsPage} />} />
    <Route element={<ProjectRequired />}>
      <Route path="map" element={<View component={MapPage} />} />
      <Route path="chat" element={<View component={ChatPage} />} />
      <Route path="activity" element={<View component={ActivityPage} />} />
    </Route>
    <Route path="*" element={<Navigate to="/projects" replace />} />
  </Routes>;
}
