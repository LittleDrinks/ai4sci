import { ArrowLeft, FileCode2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { artifactUrl, getArtifactMetadata } from "../api";
import { ArtifactReview } from "../components/ArtifactReview";
import { EmptyState } from "../components/EmptyState";
import { Status } from "../components/Status";
import { useProjectEntity } from "../context/useProjectEntity";
import { formatTime, shortId } from "../utils";

function ReportMeta({ report, agents }) {
  const agent = agents.find((item) => item.id === report.agent_id);
  return <dl className="report-meta"><div><dt>作者</dt><dd>{agent?.name || shortId(report.agent_id)}</dd></div><div><dt>创建时间</dt><dd>{formatTime(report.created_at)}</dd></div><div><dt>媒体类型</dt><dd>{report.content_type || "text/html"}</dd></div><div><dt>SHA-256</dt><dd><code>{report.sha256 || "-"}</code></dd></div></dl>;
}

export function ReportDetailPage() {
  const { id } = useParams();
  const { data, entity: report, resolving } = useProjectEntity(id, "artifacts", getArtifactMetadata);
  if (resolving) return <div className="page-loading">正在加载报告...</div>;
  if (!report) return <EmptyState icon={FileCode2} title="未找到报告" detail="此产物不属于当前项目。" action={<Link className="button secondary" to="/reports"><ArrowLeft size={16} />报告</Link>} />;
  return <section className="report-detail"><header className="detail-header"><Link className="back-link" to="/reports"><ArrowLeft size={17} />报告</Link><div><span className="eyebrow">HTML 产物</span><h1>{report.title}</h1><p>智能体生成的研究报告</p></div><Status value={report.status} /><ArtifactReview artifact={report} /></header><ReportMeta report={report} agents={data.agents} /><div className="report-frame"><iframe title={report.title} src={artifactUrl(report.id)} sandbox="" referrerPolicy="no-referrer" /></div></section>;
}
