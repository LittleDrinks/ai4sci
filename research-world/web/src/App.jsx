import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";

const LeaderPage = lazy(() => import("./pages/LeaderPage").then((value) => ({ default: value.LeaderPage })));
const RoadmapPage = lazy(() => import("./pages/RoadmapPage").then((value) => ({ default: value.RoadmapPage })));

function View({ component: Component }) {
  return <Suspense fallback={<div className="page-loading">正在载入页面...</div>}><Component /></Suspense>;
}

export function App() {
  return <Routes><Route element={<AppShell />}>
    <Route index element={<Navigate to="/leader" replace />} />
    <Route path="leader" element={<View component={LeaderPage} />} />
    <Route path="roadmap" element={<View component={RoadmapPage} />} />
    <Route path="*" element={<Navigate to="/leader" replace />} />
  </Route></Routes>;
}
