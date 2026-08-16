import { BookOpen, CircleHelp, Compass, FlaskConical, LoaderCircle, X } from "lucide-react";
import { Handle, Position } from "@xyflow/react";


const ICONS = { question: CircleHelp, source: BookOpen, direction: Compass, experiment: FlaskConical };
const LABELS = { question: "问题", source: "来源", direction: "方向", experiment: "实验" };
const POSITIONS = [["top", Position.Top], ["right", Position.Right], ["bottom", Position.Bottom], ["left", Position.Left]];


function Handles({ type }) {
  return POSITIONS.map(([side, position]) => <Handle key={side} className="hidden-handle" id={`${type}-${side}`} type={type} position={position} isConnectable={false} />);
}


export function ResearchNode({ data, selected }) {
  const Icon = ICONS[data.kind] || Compass;
  const title = data.payload?.title || data.payload?.text || "未命名节点";
  const state = data.life_state === "ghost" ? "已驳回" : data.life_state === "pending" ? "待审查" : data.direction_status || "已入图";
  return <article className={`research-node kind-${data.kind} life-${data.life_state} ${data.working ? "is-working" : ""} ${data.justCompleted ? "just-completed" : ""} ${selected ? "selected" : ""}`}>
    <Handles type="target" /><header><span className="node-kind-icon" role="img" aria-label={`${LABELS[data.kind]}图标`}><Icon size={21} /></span>
      <div><span>{LABELS[data.kind]}</span><h3>{title}</h3></div></header>
    <footer><span>{state}</span>{Boolean(data.working) && <LoaderCircle className="spin" size={15} />}{data.life_state === "ghost" && <X size={14} />}</footer>
    <Handles type="source" />
  </article>;
}
