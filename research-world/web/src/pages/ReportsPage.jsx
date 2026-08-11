import { ExternalLink, FileCode2, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { JobDialog } from "../components/JobDialog";
import { Status } from "../components/Status";
import { useWorld } from "../context/WorldContext";
import { formatTime, shortId } from "../utils";

function isHtml(artifact) {
  return artifact.kind === "html_report";
}

function reportAgent(artifact, agents) {
  return agents.find((agent) => agent.id === artifact.agent_id)?.name || shortId(artifact.agent_id);
}

function ReportTable({ reports, agents }) {
  return <div className="table-wrap"><table><thead><tr><th>报告</th><th>作者</th><th>状态</th><th>创建时间</th><th><span className="sr-only">打开</span></th></tr></thead><tbody>{reports.map((report) => <tr key={report.id}><td><b>{report.title}</b><small>{shortId(report.id)}</small></td><td>{reportAgent(report, agents)}</td><td><Status value={report.status} /></td><td>{formatTime(report.created_at)}</td><td><Link className="icon-link" to={`/reports/${report.id}`} title="打开报告"><ExternalLink size={18} /></Link></td></tr>)}</tbody></table></div>;
}

export function ReportsPage() {
  const { data } = useWorld();
  const [open, setOpen] = useState(false);
  const reports = data.artifacts.filter(isHtml).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return <section className="content-page"><header className="page-header"><div><span className="eyebrow">智能体生成的产物</span><h1>报告</h1><p>根据已审核研究数据生成的独立 HTML 页面。</p></div><button className="button primary" onClick={() => setOpen(true)} disabled={!data.agents.length || !data.nodes.length}><Plus size={17} />请求报告</button></header>{reports.length ? <ReportTable reports={reports} agents={data.agents} /> : <EmptyState icon={FileCode2} title="暂无 HTML 报告" detail="研究数据就绪后，可将 HTML 报告任务加入队列。" action={<button className="button primary" onClick={() => setOpen(true)} disabled={!data.agents.length || !data.nodes.length}><Plus size={17} />请求报告</button>} />}<JobDialog open={open} onClose={() => setOpen(false)} kind="html_report" /></section>;
}
