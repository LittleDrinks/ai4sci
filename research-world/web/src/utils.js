export const text = (value, fallback = "-") => value === null || value === undefined || value === "" ? fallback : String(value);
export const dateValue = (item) => item?.created_at || "";
export const isAdmittedNode = (node) => node?.status === "admitted" && node?.audit === "approve";

const DISPLAY_LABELS = {
  action: "行动", admitted: "已采纳", agent: "智能体", agent_registered: "智能体已注册", approve: "通过",
  artifact: "产物", artifact_reviewed: "产物已审核", artifact_submitted: "产物已提交", audit: "审核",
  audit_completed: "审核已完成", awaiting_review: "等待审核", cancelled: "已取消", claim: "主张",
  completed: "已完成", control: "控制", direction: "方向", evidence: "证据", failed: "失败",
  gate: "门控", history: "历史", html_report: "HTML 报告", human: "用户", hypothesis: "假设",
  idle: "空闲", immutable: "不可变", invalidated: "已失效", job: "任务", job_claimed: "任务已领取",
  job_completed: "任务已完成", job_failed: "任务失败", job_output_submitted: "任务输出已提交",
  job_queued: "任务已入队", job_rejected: "任务已拒绝", job_requeued: "任务已重新入队",
  job_retried: "任务已重试", job_revision_queued: "修改任务已入队", lifecycle: "生命周期", live: "实时",
  log: "日志", message: "消息", node: "节点", node_reviewed: "节点已审核", node_submitted: "节点已提交", object: "对象",
  offline: "离线", online: "在线", pending: "待处理", pending_review: "待审核", plan: "规划",
  prerequisite: "前置条件", project: "项目", project_created: "项目已创建", proposition: "命题",
  published: "已发布", question: "问题", queued: "排队中", reconnecting: "重新连接中", reject: "拒绝", rejected: "已拒绝",
  report: "报告", research: "研究", restart: "重新执行", result: "结果", retracted: "已撤回", revise: "要求修改", revision_requested: "待修改",
  prior_percent: "先验比例", retained_pending: "保留待验证", status: "状态",
  runtime: "运行时", runtime_registered: "运行时已注册", runtime_status_changed: "运行时状态已变更",
  running: "运行中", submitted: "已提交", subgraph_invalidated: "子图已失效", syncing: "同步中",
  system: "系统", tool: "工具", tool_call: "工具调用", tool_result: "工具结果", unknown: "未知",
};

const ERROR_MESSAGES = {
  "agent capabilities must be provided by its runtime": "智能体能力必须由所选运行时提供。",
  "agent runtime cannot execute this job kind": "智能体运行时无法执行此类任务。",
  "dependencies must be admitted nodes": "依赖项必须是已采纳节点。",
  "feedback is required": "请填写反馈。", "no projects": "暂无项目。",
  "question nodes are created with projects": "问题节点会随项目一起创建。",
  "subject must be an admitted node": "研究对象必须是已采纳节点。",
  "unknown agent": "未找到智能体。", "unknown artifact": "未找到产物。", "unknown job": "未找到任务。",
  "unknown node": "未找到节点。", "unknown project": "未找到项目。", "unknown runtime": "未找到运行时。",
  "unknown subject": "未找到研究对象。", "unsupported job kind": "不支持此任务类型。",
};

export function formatTime(value, withDate = true) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return String(value);
  const options = withDate ? { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" } : { hour: "2-digit", minute: "2-digit", second: "2-digit" };
  return new Intl.DateTimeFormat("zh-CN", options).format(date);
}

export function displayLabel(value) {
  return DISPLAY_LABELS[value] || text(value).replaceAll("_", " ");
}

export function displayError(value) {
  const message = text(value, "操作失败。");
  const status = message.match(/^Request failed \((\d+)\)$/)?.[1];
  if (status) return `请求失败（HTTP ${status}）。`;
  return ERROR_MESSAGES[message] || "操作失败，请重试。";
}

export function objectEntries(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? Object.entries(value) : [];
}

export function shortId(value) {
  const id = text(value);
  return id.length > 16 ? `${id.slice(0, 8)}...${id.slice(-5)}` : id;
}

export function actorName(event, agents = []) {
  const actor = event.actor;
  const agent = agents.find((item) => item.id === actor.id);
  return agent?.name || actor.id || displayLabel(actor.kind || "system");
}
