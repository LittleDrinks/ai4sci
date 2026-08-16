---
sources:
  - id: prov
    title: "PROV-DM: The PROV Data Model"
    url: https://www.w3.org/TR/prov-dm/
  - id: micropublications
    title: "Micropublications: a semantic model for claims, evidence, arguments and annotations in biomedical communications"
    url: https://pmc.ncbi.nlm.nih.gov/articles/PMC4530550/
  - id: nanopublications
    title: "Nanopublication Guidelines"
    url: https://nanopub.net/guidelines/working_draft/
  - id: graphmind
    title: "GraphMind: Interactive Novelty Assessment System for Accelerating Scientific Discovery"
    url: https://arxiv.org/abs/2510.15706
  - id: exploration-narrowing
    title: "AI Research Agents Narrow Scientific Exploration"
    url: https://arxiv.org/abs/2605.27905
  - id: verbalized-sampling
    title: "Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity"
    url: https://arxiv.org/abs/2510.01171
  - id: divalign
    title: "DivAlign: MMR-style de-homogenization for ideation"
    url: https://arxiv.org/abs/2607.28087
  - id: evoscientist
    title: "EvoScientist: Towards Multi-Agent Evolving AI Scientists for End-to-End Scientific Discovery"
    url: https://arxiv.org/abs/2603.08127
  - id: co-scientist
    title: "Accelerating scientific discovery with Co-Scientist"
    url: https://doi.org/10.1038/s41586-026-10644-y
  - id: trrack
    title: "Trrack: A Library for Provenance-Tracking in Web-Based Visualizations"
    url: https://doi.org/10.1109/vis47514.2020.00030
---
# research-world 重设计：图谱主屏、两条 workflow、auto 闭环
research-world 从多页控制平面改为知识图谱主屏加三视图，闭环为“命题→实验→反思→新命题”。
## 数据模型
- 节点固定四类：question / source / direction / experiment。result 并入 experiment 负载；claim 不独立成类。
- direction 带状态机 `proposed→supported/refuted`，必须承载完整证据链；边带 supports/refutes 极性。
- pending 虚线节点：agent 开工前 goal 先入图；完工后 admitted 填内容，驳回变幽灵（淡化并保留理由）。被拒 direction 与失败 experiment 全部留图。
PROV 记录生产过程 [prov]，Micropublications 与 Nanopublications 记录主张、证据和发布信息 [micropublications; nanopublications]；前者不推出后者。因此以少量工作流节点保存事实和来源，以 direction 的状态和极性边保存科学论证，不另造 result 或自由 claim 层。
## 两条固定 workflow
1. brainstorm（从 question/direction 发起）：生成 N 候选（可叠 Verbalized Sampling）→ embedding 查重（余弦 >0.8 转 reflect/合并并渐进披露阻断理由；0.6–0.8 LLM 成对裁决；<0.6 入池）→ MMR 贪心入池（质量分 − 0.2·max_sim）→ pending direction 入图 → review。
2. plan-execute-review-reflect（从 direction 发起）：plan → 执行 experiment → review（机械证据审计加质量/多样性分；双审冲突升级人，rebuttal 格式沉淀）→ reflect 产新 direction 候选。
GraphMind 将新颖性审核放在交互式图谱中 [graphmind]；实证研究显示复杂 Agent 仍会收缩探索空间 [exploration-narrowing]。Verbalized Sampling 只能提供生成多样性 [verbalized-sampling]，MMR 式去同质化才把多样性放入入池目标 [divalign]，故相似度阈值只是当前运营门槛，须随语料校准，不能成为节点语义。
## auto 模式
- 开：reflect 产 direction 直接进 review；review 过即自动启动 plan-execute-review-reflect 自主迭代。
- 关：direction 启动与每步 plan 执行均需人确认。
- 熔断：同一谱系 review 连续驳回 2 次，auto 暂停该谱系并升级人。
EvoScientist 将失败方向作为后续搜索的显式记忆 [evoscientist]，Co-Scientist 将提出、执行和复核连接为受反馈约束的研究循环 [co-scientist]。幽灵车道保留失败的适用范围，熔断则避免同一谱系在无新证据时空转。
## 三视图（其余删除）
- 地图（主屏）：知识图谱式 kanban；节点闪烁表示工作中、完工动效；点击节点直接发起对应 workflow/worker；右侧栏为带节点上下文的轻量对话；非 admitted 节点淡化。
- 对话：orchestrator 定位 assistant/workflow manager；对话是草稿区，产物沉淀为图谱节点后删除。
- 活动：队列与活动合并；轨迹视图按 Duration/Turns/Calls、TOOL/ASSISTANT 行和底部统计呈现；队列降级为槽位指示。
Trrack 展示同一溯源状态可生成时间线、分支和聚合视图 [trrack]，所以地图、对话和活动是同一图谱的读模型；时间顺序、worker 状态和研究结论不互相替代。
## 变化
- 不保留向后兼容：旧节点类型、四页路由、审核/报告数据流直接删。
- embedding 走 `.env` 的 OpenAI 兼容端点；端点不支持再议本地 sentence-transformers。
- 实施顺序：数据模型 → orchestrator → workflow+auto → 图谱主屏 → 活动页 → 删页与项目切换。
