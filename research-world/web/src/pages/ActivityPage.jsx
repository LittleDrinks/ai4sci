import { Activity, Filter } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { useWorld } from "../context/WorldContext";
import { dateValue, displayLabel, formatTime, shortId } from "../utils";

const eventType = (event) => event.type;
const laneId = (event) => event.actor.id;

function eventDetail(event) {
  const payload = event.payload;
  const fields = [payload.kind && displayLabel(payload.kind), payload.tool, payload.sdk, payload.decision && displayLabel(payload.decision)].filter(Boolean).join(" · ");
  return payload.message || payload.summary || payload.title || fields || shortId(event.entity_id);
}

function useFilteredEvents(events, filters) {
  return useMemo(() => events.filter((event) => (!filters.agent || laneId(event) === filters.agent) && (!filters.type || eventType(event) === filters.type) && (!filters.query || `${eventType(event)} ${eventDetail(event)} ${laneId(event)}`.toLowerCase().includes(filters.query.toLowerCase()))).sort((a, b) => new Date(dateValue(a)) - new Date(dateValue(b))), [events, filters]);
}

function ActivityFilters({ events, filters, setFilters, agents, runtimes }) {
  const types = [...new Set(events.map(eventType))].sort();
  const lanes = [...new Set(events.map(laneId))];
  return <div className="filter-bar"><Filter size={17} /><select aria-label="按参与者筛选" value={filters.agent} onChange={(event) => setFilters({ ...filters, agent: event.target.value })}><option value="">全部参与者</option>{lanes.map((id) => <option key={id} value={id}>{laneLabel(id, agents, runtimes)}</option>)}</select><select aria-label="按事件类型筛选" value={filters.type} onChange={(event) => setFilters({ ...filters, type: event.target.value })}><option value="">全部事件类型</option>{types.map((type) => <option key={type} value={type}>{displayLabel(type)}</option>)}</select><input aria-label="搜索事件" placeholder="搜索日志" value={filters.query} onChange={(event) => setFilters({ ...filters, query: event.target.value })} /></div>;
}

function laneLabel(id, agents, runtimes) {
  return agents.find((item) => item.id === id)?.name || runtimes.find((item) => item.id === id)?.name || id;
}

function LaneEvent({ event }) {
  const content = <><div><b>{displayLabel(eventType(event))}</b><code>{shortId(event.entity_id)}</code></div><p>{eventDetail(event)}</p></>;
  const href = eventHref(event);
  return href ? <Link className="lane-event" to={href}>{content}</Link> : <article className="lane-event">{content}</article>;
}

function eventHref(event) {
  if (event.entity_type === "node") return `/nodes/${event.entity_id}`;
  if (event.entity_type === "artifact") return `/reports/${event.entity_id}`;
  if (event.entity_type === "job") return `/queue?job=${encodeURIComponent(event.entity_id)}`;
  if (["agent", "runtime"].includes(event.entity_type)) return "/agents";
  return "";
}

function ActivityLanes({ events, agents, runtimes }) {
  const lanes = [...new Set(events.map(laneId))];
  const style = { gridTemplateColumns: `150px repeat(${Math.max(lanes.length, 1)}, minmax(240px, 1fr))`, minWidth: 150 + lanes.length * 240 };
  return <div className="lanes-scroll"><div className="activity-lanes" style={style}><div className="lane-corner">时间</div>{lanes.map((id) => <div className="lane-head" key={id}>{laneLabel(id, agents, runtimes)}</div>)}{events.map((event) => <ActivityRow key={`${dateValue(event)}-${eventType(event)}-${event.entity_id}`} event={event} lanes={lanes} />)}</div></div>;
}

function ActivityRow({ event, lanes }) {
  const activeLane = laneId(event);
  return <><time>{formatTime(dateValue(event))}</time>{lanes.map((id) => <div className="lane-cell" key={id}>{id === activeLane && <LaneEvent event={event} />}</div>)}</>;
}

export function ActivityPage() {
  const { data } = useWorld();
  const [filters, setFilters] = useState({ agent: "", type: "", query: "" });
  const events = useFilteredEvents(data.events, filters);
  return <section className="content-page"><header className="page-header"><div><span className="eyebrow">审计日志</span><h1>活动记录</h1><p>按时间顺序展示命令、智能体执行、工具调用、审核和产物。</p></div><span className="count-label">{events.length} 条事件</span></header><ActivityFilters events={data.events} filters={filters} setFilters={setFilters} agents={data.agents} runtimes={data.runtimes} />{events.length ? <ActivityLanes events={events} agents={data.agents} runtimes={data.runtimes} /> : <EmptyState icon={Activity} title="无匹配活动" detail="用户和智能体处理项目时，事件会显示在这里。" />}</section>;
}
