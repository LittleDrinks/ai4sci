import { Activity, Braces, Clock3, MessagesSquare, Network, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getRun, getRunContext, getRunJobs, getRuns, getRunWire, runEventsUrl } from "../api";
import { EmptyState } from "../components/EmptyState";
import { displayLabel, formatTime, shortId } from "../utils";

const VIEWS = [["timeline", Clock3, "Timeline"], ["wire", Braces, "Wire"], ["context", MessagesSquare, "Context"], ["jobs", Network, "Agents / Jobs"]];

function useRunActivity() {
  const [runs, setRuns] = useState([]);
  const [runId, setRunId] = useState("");
  const [data, setData] = useState({ run: null, events: [], wire: [], context: [], jobs: [] });
  useEffect(() => { getRuns().then((items) => { setRuns(items); setRunId((current) => current || items[0]?.id || ""); }); }, []);
  useEffect(() => {
    if (!runId) return undefined;
    let source;
    Promise.all([getRun(runId), getRunWire(runId), getRunContext(runId), getRunJobs(runId)]).then(([run, wire, context, jobs]) => {
      setData({ run, events: run.events, wire, context, jobs });
      source = new EventSource(runEventsUrl(runId));
      source.onmessage = ({ data: raw }) => setData((current) => appendEvent(current, JSON.parse(raw)));
    });
    return () => source?.close();
  }, [runId]);
  return { runs, runId, setRunId, data };
}

function appendEvent(data, event) {
  if (data.events.some((item) => item.event_id === event.event_id)) return data;
  return { ...data, events: [...data.events, event], jobs: projectJob(data.jobs, event) };
}

function projectJob(jobs, event) {
  if (event.type === "attempt_started" && !jobs.some((job) => job.id === event.attempt_id)) {
    return [...jobs, { id: event.attempt_id, generation_id: event.generation_id, actor: event.actor, status: "created", created_at: event.time }];
  }
  if (event.type !== "attempt_completed") return jobs;
  return jobs.map((job) => job.id === event.attempt_id ? { ...job, status: "completed", completed_at: event.time, ...event.payload } : job);
}

function RunSelect({ runs, value, onChange }) {
  return <label className="run-select"><span>Run</span><select value={value} onChange={(event) => onChange(event.target.value)}>{runs.map((run) => <option value={run.id} key={run.id}>{shortId(run.id)} · {displayLabel(run.status)}</option>)}</select></label>;
}

function ViewTabs({ value, onChange }) {
  return <div className="segmented activity-tabs">{VIEWS.map(([id, Icon, label]) => <button aria-label={label} title={label} className={value === id ? "active" : ""} onClick={() => onChange(id)} key={id}><Icon size={16} /><span>{label}</span></button>)}</div>;
}

function Timeline({ events, jobs }) {
  const generations = [...new Set(events.map((event) => event.generation_id).filter(Boolean))];
  return <div className="timeline-tree">{generations.map((generation, index) => <details open key={generation}><summary><span>Generation {index}</span><code>{shortId(generation)}</code></summary><div>{jobs.filter((job) => job.generation_id === generation).map((job) => <Attempt events={events.filter((event) => event.attempt_id === job.id)} job={job} key={job.id} />)}</div></details>)}</div>;
}

function Attempt({ job, events }) {
  return <details open className="timeline-attempt"><summary><span>{job.actor}</span><code>{shortId(job.id)}</code><i className={`state-dot ${job.status}`} /></summary><ol>{events.map((event) => <li key={event.event_id}><time>{formatTime(event.time, false)}</time><div><b>{displayLabel(event.type)}</b><p>{eventSummary(event)}</p></div></li>)}</ol></details>;
}

function eventSummary(event) {
  return event.payload.message || event.payload.error || Object.values(event.payload).filter((value) => typeof value === "string").join(" · ") || `${event.entity.type} ${shortId(event.entity.id)}`;
}

function Wire({ events }) {
  const [query, setQuery] = useState("");
  const visible = useMemo(() => events.filter((event) => JSON.stringify(event).toLowerCase().includes(query.toLowerCase())), [events, query]);
  return <div><label className="wire-search"><Search size={16} /><input aria-label="Search wire events" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search events" /></label><div className="wire-list">{visible.map((event) => <details key={event.event_id}><summary><time>{formatTime(event.time, false)}</time><b>{event.type}</b><code>{shortId(event.attempt_id || event.entity.id)}</code></summary><pre>{JSON.stringify(event, null, 2)}</pre></details>)}</div></div>;
}

function Context({ items }) {
  return <div className="context-list">{items.map((item) => <details key={item.attempt_id}><summary><b>{item.actor}</b><code>{shortId(item.attempt_id)}</code></summary><pre>{JSON.stringify(item.content, null, 2)}</pre></details>)}</div>;
}

function AgentsJobs({ jobs }) {
  return <div className="jobs-table"><table><thead><tr><th>Agent</th><th>Attempt</th><th>Generation</th><th>Status</th><th>Started</th></tr></thead><tbody>{jobs.map((job) => <tr key={job.id}><td>{job.actor}</td><td><code>{shortId(job.id)}</code></td><td><code>{shortId(job.generation_id)}</code></td><td>{displayLabel(job.status)}</td><td>{formatTime(job.created_at)}</td></tr>)}</tbody></table></div>;
}

function ActivityView({ view, data }) {
  if (view === "wire") return <Wire events={data.events} items={data.wire} />;
  if (view === "context") return <Context items={data.context} />;
  if (view === "jobs") return <AgentsJobs jobs={data.jobs} />;
  return <Timeline events={data.events} jobs={data.jobs} />;
}

export function ActivityPage() {
  const { runs, runId, setRunId, data } = useRunActivity();
  const [view, setView] = useState("timeline");
  if (!runs.length) return <EmptyState icon={Activity} title="No runs" detail="" />;
  return <section className="content-page activity-page"><header className="activity-header"><div><span className="eyebrow">Activity</span><h1>{data.run ? shortId(data.run.id) : "Run"}</h1></div><RunSelect runs={runs} value={runId} onChange={setRunId} /></header><div className="activity-toolbar"><ViewTabs value={view} onChange={setView} /><span>{data.events.length} events</span></div><ActivityView view={view} data={data} /></section>;
}
