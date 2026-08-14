import { ListTodo, Plus, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { JobDialog } from "../components/JobDialog";
import { Status } from "../components/Status";
import { useWorld } from "../context/WorldContext";
import { displayLabel, formatTime, shortId } from "../utils";

function jobAgent(job, agents) {
  return agents.find((agent) => agent.id === job.agent_id)?.name || shortId(job.agent_id);
}

function jobSubject(job, nodes) {
  return nodes.find((node) => node.id === job.subject_id)?.title || shortId(job.subject_id);
}

function JobAction({ job, retry }) {
  if (job.status !== "failed") return null;
  return <button className="icon-button" onClick={() => retry(job.id)} title="重试任务"><RefreshCw size={17} /></button>;
}

function QueueTable({ jobs, agents, nodes, retry, selected }) {
  return <div className="table-wrap"><table><thead><tr><th>任务</th><th>类型</th><th>研究对象</th><th>智能体</th><th>状态</th><th>创建时间</th><th><span className="sr-only">操作</span></th></tr></thead><tbody>{jobs.map((job) => <tr className={job.id === selected ? "selected-row" : ""} key={job.id}><td><code>{shortId(job.id)}</code><small>{job.error || job.prompt}</small></td><td>{displayLabel(job.kind)}</td><td>{jobSubject(job, nodes)}</td><td>{jobAgent(job, agents)}</td><td><Status value={job.status} /></td><td>{formatTime(job.created_at)}</td><td><JobAction job={job} retry={retry} /></td></tr>)}</tbody></table></div>;
}

export function QueuePage() {
  const { data, command } = useWorld();
  const [params] = useSearchParams();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("");
  const jobs = useMemo(() => data.jobs.filter((job) => !status || job.status === status).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)), [data.jobs, status]);
  const statuses = [...new Set(data.jobs.map((job) => job.status))];
  const retry = (jobId) => command("retry_job", { job_id: jobId }).catch(() => {});
  return <section className="content-page"><header className="page-header"><div><span className="eyebrow">本地调度</span><h1>任务队列</h1><p>每项任务都由已注册的本地智能体领取并执行。</p></div><button className="button primary" onClick={() => setOpen(true)}><Plus size={17} />新建任务</button></header><div className="filter-bar compact"><select aria-label="按状态筛选" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">全部状态</option>{statuses.map((value) => <option key={value} value={value}>{displayLabel(value)}</option>)}</select><span>{jobs.length} 个任务</span></div>{jobs.length ? <QueueTable jobs={jobs} agents={data.agents} nodes={data.review_nodes} retry={retry} selected={params.get("job") || ""} /> : <EmptyState icon={ListTodo} title="任务队列为空" detail="为已注册的智能体创建研究、规划或 HTML 报告任务。" action={<button className="button primary" onClick={() => setOpen(true)}><Plus size={17} />创建任务</button>} />}<JobDialog open={open} onClose={() => setOpen(false)} /></section>;
}
