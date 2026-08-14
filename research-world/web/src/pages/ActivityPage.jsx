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

function Timeline({ events, jobs, wire, context }) {
  const generations = [...new Set(events.map((event) => event.generation_id).filter(Boolean))];
  return <div className="timeline-tree">{generations.map((generation, index) => <details open key={generation}><summary><span>Generation {index}</span><code>{shortId(generation)}</code></summary><div>{jobs.filter((job) => job.generation_id === generation).map((job) => <Attempt events={events.filter((event) => event.attempt_id === job.id)} job={job} wire={wire.find((item) => item.attempt_id === job.id)} context={context.find((item) => item.attempt_id === job.id)} key={job.id} />)}</div></details>)}</div>;
}

function Attempt({ job, events, wire, context }) {
  const turns = traceTurns(wire);
  return <details open className="timeline-attempt"><summary><span>{job.actor}</span><small>{elapsed(job.created_at, job.completed_at)}</small><code>{shortId(job.id)}</code><i className={`state-dot ${job.status}`} /></summary>{turns.map((turn, index) => <TraceTurn turn={turn} index={index} key={turn.key} />)}<ControlSteps events={events} /></details>;
}

function TraceTurn({ turn, index }) {
  const metrics = turnMetrics(turn);
  return <details open className="timeline-turn"><summary><b>Turn {index + 1}</b><small>{metrics.tokens} tokens · context {signed(metrics.context)} · {metrics.errors} errors · {metrics.truncations} truncations · wait {metrics.wait}</small></summary><ol>{turn.records.map((record, step) => <TraceStep record={record} step={step} key={`${turn.key}:${record.event_index}`} />)}</ol></details>;
}

function TraceStep({ record, step }) {
  const tools = (record.tool_names || []).map((name, index) => ({ name, arguments: record.tool_arguments?.[index] }));
  return <li><time>Step {step + 1}</time><div><b>{displayLabel(record.role || record.capture_type || "trace")}</b><p>{record.text || record.error || record.termination || "Recorded event"}</p>{tools.map((tool) => <code className="trace-tool" key={tool.name}>{tool.name} {readable(tool.arguments)}</code>)}</div></li>;
}

function ControlSteps({ events }) {
  const steps = pairedEvents(events);
  if (!steps.length) return null;
  return <details className="timeline-turn"><summary><b>Control steps</b><small>{steps.length} recorded</small></summary><ol>{steps.map((event, index) => <li key={event.event_id}><time>Step {index + 1}</time><div><b>{event.pair ? `${displayLabel(event.type)} / ${displayLabel(event.pair.type)}` : displayLabel(event.type)}</b><p>{eventSummary(event)}</p></div></li>)}</ol></details>;
}

function traceTurns(wire) {
  const traces = wire?.content?.trace || [];
  let previousPrompt = 0;
  let previousEnd = null;
  return traces.flatMap((trace) => groupTurns(trace)).map((turn) => {
    const prompt = responseUsage(turn.records).prompt_tokens || previousPrompt;
    const value = { ...turn, context: prompt - previousPrompt, wait: gap(previousEnd, turn.start) };
    previousPrompt = prompt;
    previousEnd = turn.end;
    return value;
  });
}

function groupTurns(trace) {
  const records = trace.jsonl.split("\n").filter(Boolean).map(parseRecord).filter(Boolean);
  const indexes = [...new Set(records.map((record) => record.turn_index))];
  return indexes.map((index) => makeTurn(trace.name, index, records.filter((record) => record.turn_index === index)));
}

function makeTurn(name, index, records) {
  return { key: `${name}:${index}`, records, start: records[0]?.timestamp, end: records.at(-1)?.timestamp };
}

function turnMetrics(turn) {
  const usage = responseUsage(turn.records);
  const errors = turn.records.filter((record) => record.error).length;
  const truncations = turn.records.filter((record) => record.payload?.response?.finish_reason === "length").length;
  return { tokens: usage.total_tokens || 0, context: turn.context, errors, truncations, wait: turn.wait };
}

function responseUsage(records) {
  return records.reduce((usage, record) => record.payload?.response?.usage || usage, {});
}

function parseRecord(line) {
  try { return JSON.parse(line); } catch { return null; }
}

function elapsed(start, end) {
  if (!start || !end) return "running";
  return `${Math.max(0, new Date(end) - new Date(start))} ms`;
}

function gap(start, end) {
  return start && end ? `${Math.max(0, new Date(end) - new Date(start))} ms` : "0 ms";
}

function signed(value) {
  return `${value >= 0 ? "+" : ""}${value}`;
}

function eventSummary(event) {
  const result = event.pair?.payload.error || event.pair?.payload.result;
  return event.payload.message || event.payload.error || readable(result) || Object.values(event.payload).filter((value) => typeof value === "string").join(" · ") || `${event.entity.type} ${shortId(event.entity.id)}`;
}

function readable(value) {
  return typeof value === "string" ? value : value ? JSON.stringify(value) : "";
}

function pairedEvents(events) {
  const results = new Map(events.filter((event) => event.type === "tool_result").map((event) => [event.entity.id, event]));
  return events.filter((event) => event.type !== "tool_result").map((event) => event.type === "tool_call" ? { ...event, pair: results.get(event.entity.id) } : event);
}

function Wire({ events }) {
  const [query, setQuery] = useState("");
  const visible = useMemo(() => pairedEvents(events).filter((event) => JSON.stringify(event).toLowerCase().includes(query.toLowerCase())), [events, query]);
  return <div><label className="wire-search"><Search size={16} /><input aria-label="Search wire events" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search events" /></label><div className="wire-list">{visible.map((event) => <details key={event.event_id}><summary><time>{formatTime(event.time, false)}</time><b>{event.pair ? "tool_call / tool_result" : event.type}</b><code>{shortId(event.attempt_id || event.entity.id)}</code></summary><pre>{JSON.stringify(event, null, 2)}</pre></details>)}</div></div>;
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
  return <Timeline events={data.events} jobs={data.jobs} wire={data.wire} context={data.context} />;
}

export function ActivityPage() {
  const { runs, runId, setRunId, data } = useRunActivity();
  const [view, setView] = useState("timeline");
  if (!runs.length) return <EmptyState icon={Activity} title="No runs" detail="" />;
  return <section className="content-page activity-page"><header className="activity-header"><div><span className="eyebrow">Activity</span><h1>{data.run ? shortId(data.run.id) : "Run"}</h1></div><RunSelect runs={runs} value={runId} onChange={setRunId} /></header><div className="activity-toolbar"><ViewTabs value={view} onChange={setView} /><span>{data.events.length} events</span></div><ActivityView view={view} data={data} /></section>;
}
