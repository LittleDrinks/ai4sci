# research-world 重设计：图谱主屏、两条 workflow、auto 闭环

research-world 从"多页控制平面"改为"知识图谱主屏 + 三视图"，闭环"命题→实验→反思→新命题"。依据见 docs/references/research-process-graph.md。

## 数据模型

- 节点固定四类：question / source / direction / experiment。result 并入 experiment 负载；claim 不独立成类。
- direction 带状态机 `proposed→supported/refuted`，必须承载完整证据链；边带 supports/refutes 极性。
- pending 虚线节点：agent 开工前 goal 先入图；完工两命运——admitted 填内容 / 驳回变幽灵（淡化+理由，不删除）。被拒 direction 与失败 experiment 全部留图（幽灵车道）。

## 两条固定 workflow

1. brainstorm（从 question/direction 发起）：生成 N 候选（可叠 Verbalized Sampling）→ embedding 查重（余弦 >0.8 转 reflect/合并并渐进披露阻断理由；0.6–0.8 LLM 成对裁决；<0.6 入池）→ MMR 贪心入池（质量分 − 0.2·max_sim）→ pending direction 入图 → review。
2. plan-execute-review-reflect（从 direction 发起）：plan → 执行 experiment → review（机械证据审计+质量/多样性分；双审冲突升级人，rebuttal 格式沉淀）→ reflect 产新 direction 候选。

## auto 模式

- 开：reflect 产 direction 直接进 review；review 过即自动启动 plan-execute-review-reflect 自主迭代。
- 关：direction 启动与每步 plan 执行均需人确认。
- 熔断：同一谱系 review 连续驳回 2 次 → auto 暂停该谱系，升级人。

## 三视图（其余删除）

- 地图（主屏）：知识图谱式 kanban；节点闪烁=工作中、完工动效；点击节点直接发起对应 workflow/worker（不经 orchestrator）；右侧栏为带节点上下文的轻量对话；非 admitted 节点淡化。
- 对话：orchestrator 定位 assistant/workflow manager；对话是草稿区，产物沉淀为图谱节点后删除。
- 活动：队列+活动合并；轨迹视图按 DSH 风格（Duration/Turns/Calls 彩条、TOOL/ASSISTANT 行、底部统计条）；队列降级为槽位指示。
- 删除审核/报告/智能体/队列页；项目选择独立页 + 左下角退出项目。

## Consequences

- 不保留向后兼容：旧节点类型、四页路由、审核/报告数据流直接删。
- embedding 走 .env 的 OpenAI 兼容端点；端点不支持再议本地 sentence-transformers。
- 实施顺序：数据模型 → orchestrator → workflow+auto → 图谱主屏 → 活动页 → 删页与项目切换。
