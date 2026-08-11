---
sources:
  - title: "ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research"
    url: https://arxiv.org/abs/2606.07591
  - title: "Benchmarking AI Agents for Addressing Scientific Challenges Across Scales (SciAgentArena)"
    url: https://arxiv.org/abs/2606.12736
  - title: "AstaBench"
    url: https://github.com/allenai/asta-bench
---
# E9 端到端效果（C9）
leaderboard 证明"能打"，matched ablation 证明"为什么能打"，两者缺一不可。

## 主战场：ResearchClawBench
- base 40 task（10 领域，真实论文+原始数据+相关文献，隐藏 target paper，专家 multimodal checklist）按官方协议完整跑，报官方 mean。论文 baseline：最强 autonomous agent≈21.5，最强 ResearchHarness LLM≈20.7。
- community 16 task 单独报"ResearchClawBench-Community extension"，不混入 base 分，保持论文可比性。
- 仓库已有 ResearchClawBench + ResearchHarness 36 runs 仪表链资产。
- 可分解报：checklist reproduction score 与 beyond-target/new-discovery score——检验"盲创主要改善新发现，失败共享主要改善重发现效率"。

## 归因子集（matched ablation）
预冻结 12 task×3 seed 跨领域分层，matched-budget（模型调用额度/工具/总 token/时间相等）：
- 完整系统
- same-backbone single-agent + shared-history baseline
- 预算够则加 full−audit gate、full−scoped graph
统计：paired task difference + bootstrap CI。

## 第二 bench
- SciAgentArena：约 200 任务、stepwise verification——适合分析 gate/分离在步级的作用。
- AstaBench 子集（CORE-Bench/LitQA2）：组件 robustness check，不刷全量；HF gated 待 token。

## 成本口径
统一报 science/$ 与 science/token：UtilityPerMillionTokens、AcceptedValidClaimsPerDollar、BenchmarkScorePer1MInputTokens、NovelValidFindingsPer100AgentCalls——把 scope/token 优势与端到端表现连起来。

## 合规与基座
mix-of-agents 合规；比赛约束下演示与提交链路用 Qwen 端点（等端点广场落地），方法学证据可用 pro 模型。

## 风险
- 无第三方复现时，轨迹/快照必须完整保存自证可复现（Inspect event log + artifact hash）。
- 与 E8 的协议完整性自审联动，防"benchmark 分数没测到 intended capability"的质疑。
