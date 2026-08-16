import { Beaker, BookOpen, GitBranch, Lightbulb, MessageSquare, Save, SendHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getMessages, materializeDraft, sendMessage, startWorkflow } from "../api";
import { useWorld } from "../context/WorldContext";
import "../chat.css";


const KIND = { question: "问题", source: "来源", direction: "方向", experiment: "实验" };
const ICONS = { question: Lightbulb, source: BookOpen, direction: GitBranch, experiment: Beaker };


export function ChatPage() {
  const { data, loading, refresh, setError } = useWorld();
  if (loading) return <div className="page-loading">正在载入对话...</div>;
  return <ProjectChat key={data.active_project_id} data={data} refresh={refresh} setError={setError} />;
}


function ProjectChat({ data, refresh, setError }) {
  const [selectedId, setSelectedId] = useState(data.nodes.find((node) => node.kind === "question")?.id || data.nodes[0]?.id || "");
  const node = data.nodes.find((item) => item.id === selectedId) || data.nodes[0];
  const conversation = useConversation(data.active_project_id, node, refresh, setError);
  return <section className="manager-chat"><NodeRail nodes={data.nodes} selectedId={node?.id} onSelect={setSelectedId} />
    <main className="manager-thread"><ThreadHeader node={node} workflows={data.workflows} /><MessageLog messages={conversation.messages} loading={conversation.loading} />
      <Composer node={node} conversation={conversation} data={data} refresh={refresh} setError={setError} /></main>
    <ContextPane node={node} edges={data.edges} workflows={data.workflows} /></section>;
}


function useConversation(projectId, node, refresh, setError) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  useEffect(() => {
    if (!node) return undefined;
    let stale = false; setLoading(true); setDraft(""); setMessages([]);
    getMessages(projectId, node.id).then((value) => { if (!stale) setMessages(value); })
      .catch((error) => setError(error.message)).finally(() => { if (!stale) setLoading(false); });
    return () => { stale = true; };
  }, [projectId, node?.id]);
  return { messages, setMessages, loading, draft, setDraft,
    send: () => sendDraft(projectId, node, draft, setDraft, setMessages, setError),
    materialize: () => materialize(projectId, node, draft, setDraft, setMessages, refresh, setError) };
}


async function sendDraft(projectId, node, draft, setDraft, setMessages, setError) {
  const content = draft.trim();
  if (!content) return;
  setDraft("");
  setMessages((items) => [...items, { id: `draft:${Date.now()}`, role: "user", content }]);
  try { const reply = await sendMessage(projectId, { node_id: node.id, message: content }); setMessages((items) => [...items, reply]); }
  catch (error) { setDraft(content); setError(error.message); }
}


async function materialize(projectId, node, draft, setDraft, setMessages, refresh, setError) {
  const text = draft.trim();
  if (!text) return;
  try {
    await materializeDraft(projectId, { node_id: node.id, kind: "direction", payload: { text } });
    setDraft(""); setMessages([]); await refresh(projectId);
  } catch (error) { setError(error.message); }
}


function NodeRail({ nodes, selectedId, onSelect }) {
  return <aside className="node-rail"><header><MessageSquare size={16} /><b>节点上下文</b><span>{nodes.length}</span></header><div>{nodes.map((node) => {
    const Icon = ICONS[node.kind];
    return <button className={`${node.id === selectedId ? "selected" : ""} ${node.life_state}`} onClick={() => onSelect(node.id)} key={node.id}>
      <Icon size={16} /><span><b>{nodeText(node)}</b><small>{KIND[node.kind]} · {lifeLabel(node.life_state)}</small></span></button>;
  })}</div></aside>;
}


function ThreadHeader({ node, workflows }) {
  const active = workflows.filter((item) => item.node_id === node?.id && ["queued", "running", "waiting_human"].includes(item.status)).length;
  return <header className="thread-header"><div><span>{KIND[node?.kind] || "节点"}</span><h1>{nodeText(node)}</h1></div><span className={active ? "active" : ""}>{active ? `${active} 个工作流进行中` : "就绪"}</span></header>;
}


function MessageLog({ messages, loading }) {
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages.length]);
  return <div className="manager-messages">{loading && <p className="message-placeholder">正在载入...</p>}
    {!loading && !messages.length && <p className="message-placeholder">当前节点尚无对话草稿</p>}
    {messages.map((message) => <article className={`manager-message ${message.role}`} key={message.id}><span>{message.role === "user" ? "你" : "工作流助手"}</span><p>{message.content}</p></article>)}<div ref={end} /></div>;
}


function Composer({ node, conversation, data, refresh, setError }) {
  const [sending, setSending] = useState(false);
  const submit = async () => { setSending(true); await conversation.send(); setSending(false); };
  const keyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing && !event.nativeEvent?.isComposing && event.keyCode !== 229) { event.preventDefault(); submit(); }
  };
  return <section className="manager-composer"><WorkflowCommands node={node} projectId={data.active_project_id} refresh={refresh} setError={setError} />
    <div><textarea aria-label="消息" value={conversation.draft} onChange={(event) => conversation.setDraft(event.target.value)} onKeyDown={keyDown} placeholder="围绕当前节点讨论..." />
      <button className="button secondary" disabled={!conversation.draft.trim()} onClick={conversation.materialize}><Save size={15} />沉淀方向</button>
      <button className="icon-button send-button" aria-label="发送" title="发送" disabled={sending || !conversation.draft.trim()} onClick={submit}><SendHorizontal size={18} /></button></div></section>;
}


function WorkflowCommands({ node, projectId, refresh, setError }) {
  const [busy, setBusy] = useState("");
  const run = async (action) => {
    setBusy(action.id);
    try { await startWorkflow(projectId, workflowRequest(node, action.id)); await refresh(projectId); }
    catch (error) { setError(error.message); }
    finally { setBusy(""); }
  };
  return <div className="workflow-commands">{actionsFor(node).map((action) => <button disabled={Boolean(busy)} onClick={() => run(action)} key={action.id}>
    <action.icon size={14} />{action.label}</button>)}</div>;
}


function ContextPane({ node, edges, workflows }) {
  const relations = edges.filter((edge) => edge.source === node?.id || edge.target === node?.id);
  const records = Object.entries(node?.payload || {});
  return <aside className="chat-context"><header><b>上下文</b><span>{KIND[node?.kind]}</span></header><section><h2>节点记录</h2><dl>{records.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl></section>
    <section><h2>研究状态</h2><dl><div><dt>生命态</dt><dd>{lifeLabel(node?.life_state)}</dd></div>{node?.direction_status && <div><dt>方向</dt><dd>{node.direction_status}</dd></div>}
      <div><dt>证据关系</dt><dd>{relations.length}</dd></div><div><dt>工作流</dt><dd>{workflows.filter((item) => item.node_id === node?.id).length}</dd></div></dl></section></aside>;
}


function actionsFor(node) {
  if (!node) return [];
  if (node.kind === "question" || node.kind === "source") return [{ id: "brainstorm", label: "生成方向", icon: GitBranch }];
  if (node.kind === "experiment") return [{ id: "reflect", label: "反思结果", icon: Lightbulb }];
  if (node.direction_status === "proposed") return [{ id: "research", label: "规划实验", icon: Beaker }];
  return [{ id: "reflect", label: "反思证据", icon: Lightbulb }, { id: "replan", label: "重新规划", icon: Beaker }];
}


function workflowRequest(node, action) {
  const kind = ["brainstorm", "reflect"].includes(action) ? "brainstorm" : "plan-execute-review-reflect";
  return { node_id: node.id, kind, payload: kind === "brainstorm" ? { count: 8, select: 4 } : {} };
}


function nodeText(node) {
  return node?.payload?.title || node?.payload?.text || node?.payload?.summary || "未命名节点";
}


function lifeLabel(value) {
  return { pending: "待处理", admitted: "已入图", ghost: "已驳回" }[value] || value;
}
