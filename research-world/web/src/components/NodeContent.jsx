import { displayLabel, objectEntries, text } from "../utils";

function Value({ value }) {
  if (value === null || value === undefined) return <span>-</span>;
  if (Array.isArray(value)) return <ArrayValue values={value} />;
  if (typeof value === "object") return <ObjectValue value={value} />;
  if (typeof value === "string" && /^https?:\/\//.test(value)) return <a href={value} target="_blank" rel="noreferrer">{value}</a>;
  return <span>{String(value)}</span>;
}

function ArrayValue({ values }) {
  if (!values.length) return <span>-</span>;
  if (values.every((value) => value && typeof value === "object" && !Array.isArray(value))) return <RecordTable rows={values} />;
  return <ul className="value-list">{values.map((value, index) => <li key={index}><Value value={value} /></li>)}</ul>;
}

function ObjectValue({ value }) {
  if (value.type === "image" && value.src) return <figure className="evidence-media"><img src={value.src} alt={value.alt || "研究证据"} />{value.caption && <figcaption>{value.caption}</figcaption>}</figure>;
  if (value.type === "audio" && value.src) return <audio controls src={value.src} />;
  if (value.type === "video" && value.src) return <video controls src={value.src} />;
  if (value.type === "code" && value.text) return <pre className="code-evidence"><code>{value.text}</code></pre>;
  if (Array.isArray(value.rows)) return <RecordTable rows={value.rows} columns={value.columns} />;
  return <dl className="nested-data">{objectEntries(value).map(([key, item]) => <div key={key}><dt>{displayLabel(key)}</dt><dd><Value value={item} /></dd></div>)}</dl>;
}

function RecordTable({ rows, columns }) {
  const keys = columns || [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return <div className="inline-table"><table><thead><tr>{keys.map((key) => <th key={key}>{displayLabel(key)}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{keys.map((key) => <td key={key}><Value value={row[key]} /></td>)}</tr>)}</tbody></table></div>;
}

export function DataGrid({ data }) {
  const entries = objectEntries(data);
  if (!entries.length) return <p className="muted">未记录结构化数据。</p>;
  return <dl className="data-grid">{entries.map(([key, value]) => <div key={key}><dt>{displayLabel(key)}</dt><dd><Value value={value} /></dd></div>)}</dl>;
}

export function NodeSummary({ node }) {
  return <><p className="lead-copy">{node.summary || "未记录摘要。"}</p><DataGrid data={node.content} /></>;
}

export function DependencyList({ ids, nodes }) {
  if (!ids?.length) return <p className="muted">无依赖节点。</p>;
  return <ul className="plain-list">{ids.map((id) => <li key={id}><span>{nodes.find((node) => node.id === id)?.title || text(id)}</span><code>{text(id)}</code></li>)}</ul>;
}
