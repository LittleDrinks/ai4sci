---
sources:
  - title: "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues"
    url: https://arxiv.org/abs/2605.12493
  - title: "MemSyco-Bench: Benchmarking Sycophancy in Agent Memory"
    url: https://arxiv.org/abs/2607.01071
  - title: "Lost in the Middle: How Language Models Use Long Contexts"
    url: https://arxiv.org/abs/2307.03172
  - title: "The Distracting Effect: Understanding Irrelevant Passages in RAG"
    url: https://arxiv.org/abs/2505.06914
  - title: "Context Length Alone Hurts LLM Performance Despite Perfect Retrieval"
    url: https://arxiv.org/abs/2510.05381
  - title: "EvidenceBench: A Benchmark for Extracting Evidence from Biomedical Papers"
    url: https://arxiv.org/abs/2504.18736
  - title: "Recalling Too Well: Sycophancy Evaluation and Mitigation in Memory-Augmented Models (MIST)"
    url: https://arxiv.org/abs/2606.10949
---
# E7 作用域图谱证据（C7）
## 假设
scoped graph 相比 global 在 accuracy 上 non-inferior 且 token 显著更少；收益不止来自"更短"——图结构与 scope/provenance 语义各有独立贡献。

## 四条件（对 E5 已构建的 graph）
| 条件 | 内容 |
|---|---|
| A Global Graph | 全部 verified nodes |
| B Scoped Graph | 按 query 裁 reachable/relevant slice，保留 provenance+scope |
| C Flat top-k RAG | 同 corpus，与 B 严格 token-match，去图结构/scope |
| D Oracle evidence slice | benchmark gold/relevant evidence（天花板） |

## 关键消融（收益分解）
- B 去掉 scope metadata：测"事实正确但当前作用域不适用"（MemSyco-Bench 专测此项）。
- B 去掉 provenance：测 conflicting evidence 下的 attribution laundering（PASB/MIST 提示持久化会丢来源）。
- 收益分解：Δ = Δ更短 + Δ检索更好 + Δ图结构 + Δ作用域语义。
- "scope 丢失"消融可从 MemSyco/SciFact/EvidenceBench/LongMemEval premise-awareness 自动构造（"A 在数据集 D、指标 M 下优于 B" → 剥成 "A 优于 B"，换数据集提问）。

## 样本
LongMemEval-V2 选 200 题，按五类 memory ability × 图规模十分位 × 领域分层预冻结；只选 Global 能在 reader 合法 context limit 内表达的 case（避免 A 被截断混淆）。200×4×3 seed = 2400 runs。

## 指标
- primary：scoped vs global accuracy non-inferiority（δ=2–3pp）；token ratio superiority。
- R = tokens(global)/tokens(scoped)：报 median、几何均值、bootstrap CI——CI 支持 >10 才写"数量级"，否则如实写 6.3×。
- 证据级指标（EvidenceBench 可训）：evidence recall/precision、provenance correctness、irrelevant-node rate、contradictory-node inclusion、tokens per supported claim。

## 回答的四个问题
B vs A：scoping 是否有用；B vs C：图结构/作用域是否有额外价值；B vs D：retriever 还有多少 headroom；消融：scope/provenance 是否必要。

## 风险
- 只做"短 context 对长 context"则全部结果可被已有文献解释（Lost in the Middle、RAG distraction、context 长度本身降性能）；same-token flat RAG 与消融是必须项。
