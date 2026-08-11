---
sources:
  - title: "Where Do Deep-Research Agents Go Wrong? Span-Level Error Localization in Agent Trajectories (TELBench)"
    url: https://arxiv.org/abs/2606.02060
  - title: "AgentRx: Diagnosing AI Agent Failures from Execution Trajectories"
    url: https://arxiv.org/abs/2602.02475
  - title: "OpenClawBench: Benchmarking Process-side Anomalies in Real-world Agent Execution Trajectories"
    url: https://arxiv.org/abs/2605.29253
  - title: "ProcessBench: Identifying Process Errors in Mathematical Reasoning"
    url: https://arxiv.org/abs/2412.06559
  - title: "Humans or LLMs as the Judge? A Study on Judgement Biases"
    url: https://arxiv.org/abs/2402.10669
---
# E4 审核器效度：Gold-Calibrated Gate（C4）
E3 的配套：证明 gate 不是"什么都拒绝"。reviewer 不当 oracle，operating point 经金标独立校准，系统收益与误杀联合报告。

## 设计
Reviewer 作为 classifier/localizer 直接在金标上评，不跑完整 Agent：
- TELBench 全 1,000 error-localization instances（区分 harmful error 与正常 exploration/failed search/tentative hypothesis/harmless noise）
- AgentRx 全 115 人工标注失败轨迹（critical failure step + category）
- 约 500 matched clean/non-harmful spans
- 可扩充：OpenClawBench 31,264 轨迹过程异常标注；ProcessBench 3,400 数学过程标注做 cheap 预校准

## 指标
- primary：harmful-node recall；clean-node false rejection rate。
- secondary：precision、first-error localization、Brier/calibration、risk–coverage curve。
- 误杀分层：Node FPR 与 Path FPR（合法最终路径不可达率）。
- 按 claim type 分层报 FPR/FNR（如 mechanistic claim 天然更难审，可用 SDABench 六类能力分层）。

## 预注册 operating point
如 harmful recall ≥90% 的 working point 下 clean FPR ≤10%。阈值可据 pilot 冻结，不得跑完后挑最漂亮的点。

## judge 偏差控制
- 盲化 generator/reviewer 身份；跨家族评审；deterministic scorer 优先，LLM judge 只处理无法程序评价项；子集 human/gold 校准。
- 记录 Reviewer Family × Producer Family 矩阵，查 family-specific leniency（self-preference 在结构化 rubric 下仍存在）。

## 结构化审核输出（复用到图谱 schema）
审核失败不止 free-form：invariant violated、node ID、evidence、blocker type、repair action、scope——自然产生"最小阻断理由"，供 E1 的 minimal blocker 条件复用。

## 风险
- TrajErrBench（486 条标注）论文仍写"代码数据将发布"，不设为关键依赖，发布后作后验外部验证。
