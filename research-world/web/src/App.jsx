import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";

const ActivityPage = lazy(() => import("./pages/ActivityPage").then((value) => ({ default: value.ActivityPage })));
const AgentsPage = lazy(() => import("./pages/AgentsPage").then((value) => ({ default: value.AgentsPage })));
const MapPage = lazy(() => import("./pages/MapPage").then((value) => ({ default: value.MapPage })));
const NodeDetailPage = lazy(() => import("./pages/NodeDetailPage").then((value) => ({ default: value.NodeDetailPage })));
const QueuePage = lazy(() => import("./pages/QueuePage").then((value) => ({ default: value.QueuePage })));
const ReviewPage = lazy(() => import("./pages/ReviewPage").then((value) => ({ default: value.ReviewPage })));
const ReportDetailPage = lazy(() => import("./pages/ReportDetailPage").then((value) => ({ default: value.ReportDetailPage })));
const ReportsPage = lazy(() => import("./pages/ReportsPage").then((value) => ({ default: value.ReportsPage })));

function View({ component: Component }) {
  return <Suspense fallback={<div className="page-loading">正在载入页面...</div>}><Component /></Suspense>;
}

export function App() {
  return <Routes><Route element={<AppShell />}>
    <Route index element={<Navigate to="/activity" replace />} />
    <Route path="map" element={<View component={MapPage} />} />
    <Route path="review" element={<View component={ReviewPage} />} />
    <Route path="activity" element={<View component={ActivityPage} />} />
    <Route path="queue" element={<View component={QueuePage} />} />
    <Route path="agents" element={<View component={AgentsPage} />} />
    <Route path="reports" element={<View component={ReportsPage} />} />
    <Route path="reports/:id" element={<View component={ReportDetailPage} />} />
    <Route path="nodes/:id" element={<View component={NodeDetailPage} />} />
    <Route path="*" element={<Navigate to="/map" replace />} />
  </Route></Routes>;
}
