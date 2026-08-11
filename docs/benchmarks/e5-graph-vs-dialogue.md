---
sources:
  - title: "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues"
    url: https://arxiv.org/abs/2605.12493
  - title: "AMA-Bench: Evaluating Long-Horizon Memory for Agentic Applications"
    url: https://arxiv.org/abs/2602.22769
  - title: "EvoMemBench: Benchmarking Agent Memory from a Self-Evolving Perspective"
    url: https://arxiv.org/abs/2605.18421
---
# E5 图谱状态 vs 完整对话（C5）
## 假设
沉淀后的审核通过图谱状态支撑任务继续不弱于强全历史访问，且 token/成本显著更低。注意增量定位：AMA-Agent 已用 causality graph memory，贡献是"review-gated epistemic graph 作为唯一持久状态，对话销毁后仍足够"，不是"graph 比 flat 好"。

## 载体
LongMemEval-V2 全量 451 题（5 类 memory ability，历史最大约 115M tokens，官方有 no-retrieval/RAG/AgentRunbook baseline）。第二 model 对分层 100 题做 robustness 复跑。

## 四条件
| 条件 | 内容 |
|---|---|
| A No memory | 无 |
| B Full-history agent | coding/file-search agent 可访问完整 transcript（拒绝 naive concat strawman） |
| C Strong flat baseline | 官方 RAG slice / AgentRunbook-R |
| D Accepted-only structured graph | verified claim + scope + provenance + dependencies + artifact IDs + immutable metadata |

固定同一下游 reader。

## 必须补的对照
- transcript + narrative summary（同等 consolidation compute）与 flat structured notes——证明收益来自 graph semantics 而非"多总结了一次"。
- token-match：graph slice 与 RAG baseline 匹配 token/retrieval call/retriever/reader 预算。

## 指标
- primary：answer accuracy non-inferiority（δ=2–3pp）vs 强全历史；token/latency superiority。
- 辅助：evidence recall/precision、input/retrieved tokens、latency、成本。
- 成本拆分：C_total = C_construct + Σ(C_retrieve + C_read)；画 break-even Q*（复用多少次后图谱更便宜）。
- 画 accuracy–token Pareto front。

## AMA-Bench / EvoMemBench 对照
- AMA-Agent 逐组件消融：plain causality graph / +provenance / +scope / +acceptance gate / +artifact linkage——证明区别在 epistemic governance 而非图结构本身。
- EvoMemBench：把 graph memory 接为第 16 种方法与 15 种 memory baseline 统一比较，区分 knowledge memory 与 execution experience 上的优势分布（不期待每格都赢，"只在需要 causal/provenance/scope 的任务上有明显收益"是更可信结论）。

## 风险
- AMA-Agent 是最近邻 prior art，report 必须主动对比，否则被指增量不足。
- graph 条件构建本身耗一次 LLM 推理，无 summary 对照则等于白送一次模型调用。
