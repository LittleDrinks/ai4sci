---
sources:
  - title: "Benchmarking Materials Property Prediction Methods: The Matbench Test Set and Automatminer Reference Algorithm"
    url: https://arxiv.org/abs/2005.00707
  - title: "CORE-Bench: Fostering the Credibility of Published Research Through a Computational Reproducibility Agent Benchmark"
    url: https://arxiv.org/abs/2409.11363
  - title: "RE-Bench: Evaluating frontier AI R&D capabilities of language model agents against human experts"
    url: https://arxiv.org/abs/2411.15114
  - title: "ReplicatorBench: Benchmarking LLM Agents for Replicability in Social and Behavioral Sciences"
    url: https://arxiv.org/abs/2602.11354
  - title: "REPRO-Bench: Can Agentic AI Systems Assess the Reproducibility of Social Science Research?"
    url: https://arxiv.org/abs/2507.18901
  - title: "AI Coding Agents Can Reproduce Social Science Findings (SocSci-Repro-Bench)"
    url: https://arxiv.org/abs/2606.11447
  - title: "RO-Crate 1.3 Specification"
    url: https://www.researchobject.org/ro-crate/specification/1.3/
---
# E6 删除对话后的复现与取证（C6）
把 memory benchmark 升级为 scientific reproducibility：对话销毁后，结构化状态+不可变产物是否足够复现、交接与追责。

## 载体
- Matbench 13 task × 2 pipeline 家族 = 26 case：invariant 层（seed/split hash/数据 checksum/环境重建/metric delta/artifact 哈希一致），定位是 reproducibility invariants 而非"真实科研全部可复现"。
- CORE-Bench（270 task）或 PaperBench（20 ICML 论文、8,316 rubric、原生 rollout/reproduction/grading 隔离）：真实外部效度。
- RE-Bench：长轨迹 handoff point（25%/50%/75%）× state representation 热图。

## 两阶段设计
- Stage A：原始 Agent 跑完，沉淀 code hash、dataset identifier+checksum、split、config、环境 digest、seed、checkpoints、命令、metrics、immutable artifact hash、graph claim+provenance（可导出 RO-Crate）。删除聊天。
- Stage B：fresh agent 新 session 新容器三条件：Full Transcript / Graph State+artifacts / Artifacts Only，26 case × 3 条件 × 3 seed = 234 replay attempts。

## 指标
- primary：replay success rate；|metric delta|（graph vs transcript 做 equivalence/non-inferiority）。
- 辅助：环境重建成功率、确定性哈希一致、人工干预次数、token、wall time。
- artifacts-only 是关键 ablation：若与 graph 持平，图谱价值被质疑；差异应体现在"为何做这个实验、审核状态、下游依赖什么"。

## 取证实验（比 replay 更能体现图谱优势）
注入已知 bug（错 split/错 seed/数据泄漏/陈旧 checkpoint/错 metric），删对话后 audit agent 凭 A transcript vs B graph+artifacts 回答：bug 在哪产生、哪些结果受影响、哪些下游 claim 要 invalidate、最小重跑集。
指标：root-cause localization、affected-descendant precision/recall（对比真实 descendants(v)）、rerun overhead = |估计集−真实集|/|真实集|。
可扩展 graph-aware incremental replay：只重跑受影响子树 vs 全量重跑，报 compute saved 与 stale-result rate。

## 不可复现判断
SocSci-Repro-Bench / ReplicatorBench 含 human-verified non-replicable：测图谱 epistemic metadata 能否让 fresh agent 判"此实验当前不可合法复现"，而非强行补东西造假成功。

## 风险
- RE-Bench 环境重算力，只作 1–2 个高真实度 replication，不作主实验；MLE-bench 同理。
- 时间不够时缩到 13 case，不取消——"对话删除后还能复现"是架构最不寻常、最被质疑的一条。
