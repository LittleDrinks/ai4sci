import { BaseEdge, Position } from "@xyflow/react";

function isHorizontal(position) {
  return position === Position.Left || position === Position.Right;
}

function pathFromPoints(points) {
  return points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ");
}

export function orthogonalPath({ sourceX, sourceY, sourcePosition, targetX, targetY }) {
  if (isHorizontal(sourcePosition)) {
    const middleX = (sourceX + targetX) / 2;
    return pathFromPoints([{ x: sourceX, y: sourceY }, { x: middleX, y: sourceY },
      { x: middleX, y: targetY }, { x: targetX, y: targetY }]);
  }
  const middleY = (sourceY + targetY) / 2;
  return pathFromPoints([{ x: sourceX, y: sourceY }, { x: sourceX, y: middleY },
    { x: targetX, y: middleY }, { x: targetX, y: targetY }]);
}

function edgePath(props) {
  return props.data?.route?.length > 1 ? pathFromPoints(props.data.route) : orthogonalPath(props);
}

function edgeClass(data) {
  return ["signal-edge", data?.active && "active", data?.incident && "incident",
    data?.related && "related", data?.muted && "muted"].filter(Boolean).join(" ");
}

export function SignalEdge(props) {
  const path = edgePath(props);
  const duration = props.data?.active ? "1.25s" : "2s";
  return <g className={edgeClass(props.data)}>
    <BaseEdge id={props.id} path={path} style={props.style} />
    {!props.data?.muted && <path className="signal-flow-path" d={path} fill="none" strokeLinecap="round" strokeDasharray="0 60" strokeDashoffset="60" aria-hidden="true">
      <animate attributeName="stroke-dashoffset" from="60" to="0" dur={duration} calcMode="linear" repeatCount="indefinite" />
    </path>}
  </g>;
}
