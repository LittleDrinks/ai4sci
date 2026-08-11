import { Circle } from "lucide-react";
import { displayLabel } from "../utils";

export function Status({ value = "unknown" }) {
  return <span className={`status status-${value}`}><Circle size={8} fill="currentColor" />{displayLabel(value)}</span>;
}

export function ActorBadge({ kind = "system", name }) {
  return <span className="actor-badge"><span>{kind === "agent" ? "智" : kind === "human" ? "人" : "系"}</span>{name || displayLabel(kind)}</span>;
}
