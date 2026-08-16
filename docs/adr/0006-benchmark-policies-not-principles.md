---
sources:
  - id: researchclawbench
    title: "ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research"
    url: https://arxiv.org/abs/2606.07591
  - id: matbench
    title: "Benchmarking materials property prediction methods: the Matbench test set and Automatminer reference algorithm"
    url: https://doi.org/10.1038/s41524-020-00406-3
  - id: scientific-capability-bench
    title: "Are LLMs Ready for Scientific Discovery? A Capability-Oriented Benchmark for AI Scientists"
    url: https://arxiv.org/abs/2607.11079
---
# 评测策略，不重开原则
图谱作为唯一持久真源、原始对话默认丢弃、入图前独立审核、通过后轮换上下文、规划与实验分离、盲创单次提交作为固定原则。评测分为搜索、审核、图谱和人工审查四套，不合成总分；评测环境可隔离保留原始轨迹，结果以质量、错误、人工成本与计算成本的多维 Pareto 报告。
ResearchClawBench 测量端到端研究产物 [researchclawbench]，Matbench 测量受控材料预测 [matbench]，科学能力基准按研究阶段诊断错误 [scientific-capability-bench]；三者不是同一输出。把搜索、审核、图谱和人工审查压成总分会隐含不可审计的权重，并可能用低成本指标掩盖高影响错误；Pareto 报告保留质量、失效和成本之间的实际取舍，同时不允许 benchmark 策略改写持久化和审核原则。
