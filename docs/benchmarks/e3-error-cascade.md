---
sources:
  - title: "MuSiQue: Multihop Questions via Single-hop Question Composition"
    url: https://aclanthology.org/2022.tacl-1.31/
  - title: "ProofWriter: Generating Implications, Proofs, and Abductive Statements over Natural Language"
    url: https://arxiv.org/abs/2012.13048
  - title: "SciClaimEval: Cross-modal Claim Verification in Scientific Papers"
    url: https://arxiv.org/abs/2602.07621
  - title: "Fact or Fiction: Verifying Scientific Claims (SciFact)"
    url: https://aclanthology.org/2020.emnlp-main.609/
  - title: "From Spark to Fire: Modeling and Mitigating Error Cascades in LLM-Based Multi-Agent Collaboration"
    url: https://arxiv.org/abs/2603.04474
  - title: "Agents Don't Just Agree, They Remember: Benchmarking Persistent Sycophancy in Stateful Personal Agents (PASB)"
    url: https://arxiv.org/abs/2607.10526
  - title: "From Untrusted Input to Trusted Memory: A Systematic Study of Memory Poisoning Attacks in LLM Agents (MPBench)"
    url: https://arxiv.org/abs/2606.04329
  - title: "MemSecBench: Tracking Agent Memory Poisoning from Persistence to Consequence and Repair"
    url: https://arxiv.org/abs/2607.27080
---
# E3 错误级联与审核门（C3）
## 假设
未审核知识进入默认检索会导致错误沿依赖链级联；commit 时刻的 write/retrieval eligibility 门能切断传播且不误伤 clean utility。

## 设计
2×2 factorial：注入错误节点 × Gate ON/OFF。**Gate OFF 也跑 reviewer 但忽略 verdict**——排除"gate 条件多一次强模型推理"的混淆。
Gate 是系统级语义而非提示词级：rejected 节点可展示、可写日志，但不进默认检索索引、不可被新节点声明为依赖。

## 载体分层
- ProofWriter：纯机制因果图，精确控制第 d 层 premise 替换（高内部效度）。
- MuSiQue：50×2hop + 50×3hop + 50×4hop = 150 task × 4 条件 × 3 seed = 1800 runs（语言自然度）。
- SciClaimEval：科学版主任务（1,664 专家样本；refuted 样本靠替换图表构造，天然受控污染机制，含多模态证据）。
- SciFact 30–50 claims：evidence→claim 链注入错误证据节点，科学迁移。

## 指标
- primary：downstream contamination rate（最终答案是否使用/继承注入的 false intermediate fact）。
- 辅助：污染随 hop/深度分布、bad descendants 数、propagation AUC、clean-task success、rejection rate。
- 可定义：错误繁殖数 R0=E[一个坏节点产生的坏后代]；epistemic contamination mass（按下重要性/置信度/深度加权的假后代质量和）。

## 主图
x=依赖深度，y=污染概率，gate/no-gate 两条线（可按载体分 facet）。

## 分阶段拦截率
Generated→Written→Retrieved→Depended-on→Acted-on→Final claim 各环节条件概率 P(W|G)、P(R|W)、P(D|R)、P(A|D)、P(F|A)，定位 gate 作用环节。

## 对照排
no defense / retrieval-time filter / reviewer comment only / commit gate（我方）/ commit gate + scoped provenance。From Spark to Fire 的 genealogy-graph governance 作 baseline——"error cascade 存在"不是贡献，贡献是 commit 时刻的认识论写入门。

## PASB 增补
commit policy 四档：allow-all write / write+retrieval filtering / reviewer-gated write / accepted graph+provenance+scope。报 unsafe commit rate 与三类写入失真：status promotion、attribution removal、scope broadening。

## 误杀分层
Node FPR = P(reject|valid node)；Path FPR = P(合法最终路径被切断)。后者更贴系统，必须同报。

## 风险
- MuSiQue/ProofWriter 是机制测试，不声称其本身是科学研究；科学外部效度由 SciClaimEval/SciFact 承担。
- MemSecBench/MPBench 可作安全向外部验证（加 gated_research_graph backend 进其 24 配置矩阵）。
