import { GitBranch, MessageSquare, Play, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { getMessages, sendMessage } from "../api";
import { useWorld } from "../context/WorldContext";


const LABELS = { question: "问题", source: "来源", direction: "方向", experiment: "实验",
  pending: "待审查", admitted: "已入图", ghost: "已驳回", proposed: "待验证", supported: "已支持", refuted: "已反驳" };


export function Inspector({ node, nodes, edges, onSelect, onStart }) {
  if (!node) return <aside className="inspector inspector-empty">选择节点查看上下文。</aside>;
  return <aside className="inspector"><div className="inspector-scroll"><NodeHeader node={node} onStart={onStart} />
    <NodeRecord node={node} /><Relations node={node} nodes={nodes} edges={edges} onSelect={onSelect} />
    <Rebuttal node={node} /></div><NodeChat node={node} /></aside>;
}


function NodeHeader({ node, onStart }) {
  const title = node.payload?.title || node.payload?.text || "未命名节点";
  return <header className="inspector-header"><div className="eyebrow"><span>{LABELS[node.kind]}</span><span>{LABELS[node.life_state]}</span>{node.direction_status && <span>{LABELS[node.direction_status]}</span>}</div>
    <h1>{title}</h1>{node.rejection_reason && <p className="rejection-reason">{node.rejection_reason}</p>}
    <button className="button primary workflow-start" onClick={() => onStart(node)}><Play size={16} />发起工作流</button></header>;
}


function NodeRecord({ node }) {
  const entries = Object.entries(node.payload || {}).filter(([, value]) => value !== null && typeof value !== "object");
  return <section className="inspector-section"><h2>节点记录</h2><dl className="node-record">{entries.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl></section>;
}


function Relations({ node, nodes, edges, onSelect }) {
  const byId = new Map(nodes.map((item) => [item.id, item]));
  const related = edges.filter((edge) => edge.source === node.id || edge.target === node.id).map((edge) => ({ edge, node: byId.get(edge.source === node.id ? edge.target : edge.source) })).filter((item) => item.node);
  return <section className="inspector-section"><h2><GitBranch size={15} />证据关系</h2>{related.length ? <ul className="relation-list">{related.map(({ edge, node: item }) => <li key={`${edge.source}:${edge.target}:${edge.polarity}`}><button onClick={() => onSelect(item.id)}><span className={`polarity ${edge.polarity}`}>{edge.polarity === "supports" ? "支持" : "反驳"}</span><b>{item.payload?.title || item.payload?.text}</b></button></li>)}</ul> : <p className="muted">暂无关系</p>}</section>;
}


function Rebuttal({ node }) {
  if (!node.rebuttal) return null;
  return <section className="inspector-section"><h2>双审意见</h2><div className="rebuttal-grid">{Object.entries(node.rebuttal).map(([reviewer, value]) => <div key={reviewer}><b>{reviewer === "reviewer_a" ? "审查 A" : "审查 B"}</b><p>{value.rebuttal || value.feedback || value.decision}</p><span>{value.quality ?? "-"} / {value.diversity ?? "-"}</span></div>)}</div></section>;
}


function NodeChat({ node }) {
  const { projectId, setError } = useWorld();
  const [messages, setMessages] = useState([]);
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  useEffect(() => { getMessages(projectId, node.id).then(setMessages).catch((error) => setError(error.message)); }, [projectId, node.id]);
  const submit = async () => {
    if (!value.trim() || sending) return;
    setSending(true);
    try { const reply = await sendMessage(projectId, { node_id: node.id, message: value }); setMessages(await getMessages(projectId, node.id)); setValue(""); return reply; }
    catch (error) { setError(error.message); }
    finally { setSending(false); }
  };
  const keyDown = (event) => {
    const composing = event.isComposing || event.nativeEvent?.isComposing || event.keyCode === 229;
    if (event.key === "Enter" && !event.shiftKey && !composing) { event.preventDefault(); submit(); }
  };
  return <section className="node-chat"><header><MessageSquare size={16} /><b>节点对话</b></header><div className="node-chat-log">{messages.map((message) => <p key={message.id} className={message.role}>{message.content}</p>)}</div>
    <div className="node-composer"><textarea aria-label="节点消息" value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={keyDown} rows="2" placeholder="围绕当前节点讨论..." /><button className="icon-button" onClick={submit} disabled={sending || !value.trim()} aria-label="发送消息"><Send size={17} /></button></div></section>;
}
