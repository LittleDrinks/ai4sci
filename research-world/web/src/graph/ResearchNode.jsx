import { Archive, Bot, Box, ChartNoAxesColumnIncreasing, CircleHelp, Clock3, Compass, FileCheck2, FileText, FlaskConical, History, Lightbulb, ListChecks, LoaderCircle, LockKeyhole, ShieldCheck, SlidersHorizontal, UserRound } from "lucide-react";
import { Handle, Position } from "@xyflow/react";
import { displayLabel, formatTime, shortId } from "../utils";

const ICONS = {
  question: CircleHelp, proposition: CircleHelp, direction: Compass, hypothesis: Lightbulb,
  action: FlaskConical, result: ChartNoAxesColumnIncreasing, evidence: FileCheck2, report: FileText,
  artifact: Archive, control: SlidersHorizontal, gate: ShieldCheck, history: History,
  immutable: LockKeyhole, object: Box, prerequisite: ListChecks,
};

const KIND_COLORS = {
  question: "#7768c6", proposition: "#7768c6", direction: "#7768c6", hypothesis: "#7768c6",
  action: "#55cdb3", control: "#55cdb3", prerequisite: "#55cdb3",
  result: "#788fe5", evidence: "#788fe5", report: "#788fe5", artifact: "#788fe5",
  gate: "#708078", history: "#708078", immutable: "#708078", object: "#708078",
};

const HANDLE_POSITIONS = [["top", Position.Top], ["right", Position.Right], ["bottom", Position.Bottom], ["left", Position.Left]];

function HiddenHandles({ type }) {
  return HANDLE_POSITIONS.map(([side, position]) => <Handle key={side} className="hidden-handle" id={`${type}-${side}`} type={type} position={position} isConnectable={false} />);
}

function NodeMeta({ data }) {
  const actor = data.created_by;
  const ActorIcon = actor.kind === "agent" ? Bot : UserRound;
  const owner = shortId(actor.id || "system");
  return <div className="node-meta"><span><ActorIcon size={15} />{owner}</span><time>{formatTime(data.created_at, false)}</time></div>;
}

export function ResearchNode({ data, selected }) {
  const Icon = ICONS[data.kind] || FileCheck2;
  const ExecutionIcon = data.execution_state === "running" ? LoaderCircle : data.execution_state === "queued" ? Clock3 : null;
  return <article aria-label={`${data.title}，${displayLabel(data.status)}`} className={`research-node state-${data.status} execution-${data.execution_state || "idle"} ${selected ? "selected" : ""}`}>
    <HiddenHandles type="target" />
    <header className="node-titlebar"><span className="node-kind-icon" style={{ "--kind-color": KIND_COLORS[data.kind] || "#708078" }}><Icon size={27} strokeWidth={1.8} /></span><div><span>{displayLabel(data.kind)}</span><h3>{data.title}</h3></div></header>
    <div className="node-body"><p>{data.summary || "未记录摘要。"}</p><NodeMeta data={data} /></div>{ExecutionIcon && <ExecutionIcon className="execution-mark" size={22} />}
    <HiddenHandles type="source" />
  </article>;
}
