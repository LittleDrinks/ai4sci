---
sources:
  - title: "RewardHackingAgents: Benchmarking Evaluation Integrity for LLM ML-Engineering Agents"
    url: https://arxiv.org/abs/2603.11337
  - title: "Reward Hacking Benchmark: Measuring Exploits in LLM Agents with Tool Use"
    url: https://arxiv.org/abs/2605.02964
  - title: "ResearchArena: Evaluating Sabotage and Monitoring in Automated AI R&D"
    url: https://arxiv.org/abs/2607.19321
  - title: "SafeClawBench: Separating Semantic, Audit-Evidence, and Sandbox Harm in Tool-Using LLM Agents"
    url: https://arxiv.org/abs/2606.18356
  - title: "Do Agent Benchmarks Measure Capability? Protocol Validity in the Age of Agentic AI (HackDetect)"
    url: https://arxiv.org/abs/2607.22368
  - title: "EvilGenie: Reward Hacking Benchmark (Inspect Edition)"
    url: https://github.com/JonathanGabor/evilgenie_inspect
---
# E8 执行/评分能力隔离（C8）
## 假设
semantic role separation 不足以防作弊；scorer/executor 必须能力隔离，hidden evaluation state 不可达，评分只消费规范化不可变产物。结论形态：II≈I 而 IV/V 骤降 → "角色命名无安全意义，capability boundary 才有"。

## 五级阶梯
| 级 | 条件 |
|---|---|
| I Fully merged | 同 agent 看 target/score 可改环境 |
| II Prompt-role split | 不同 session，共享文件系统与权限 |
| III Process split only | 不同进程，但 executor 仍能读评测资产 |
| IV ACL/capability split | hidden evaluation 不挂载给 executor，evaluator 只读 |
| V Capability split + immutable artifact | scorer fresh process 只读冻结 artifact/hash，access log 记越界尝试 |

B→C（II→IV）是最重要对照：证明不是"多写了一段 system prompt"而是真正的 security boundary。

## 载体
- RewardHackingAgents：evaluator tampering + train/test leakage 主战场（fresh workspace，记 patch/文件访问/self-reported vs trusted metric）。
- RHB：更广自然 shortcut 面（跳过验证、从 task-adjacent metadata 推答案、篡改评测函数、chained tasks）。
- ResearchArena：AI R&D sabotage/monitoring 高阶版（hidden side task），把 reviewer/scorer boundary 当 monitor/control protocol 评。
- EvilGenie Inspect edition：154 hard task，visible/hidden test + 篡改检测 + Docker workspace（成本紧则冻结 100 task，54 作 confirmatory holdout）。

## 权限矩阵（报告图）
信息/能力 × Planner/Executor/Reviewer/Scorer：hidden rubric/label 仅 Scorer；raw failed traces 仅 Reviewer scoped；mark accepted 仅 Reviewer；modify evaluator 无人（受控）；emit final artifact 仅 Executor；emit trusted score 仅 Scorer。E8 自变量即矩阵中哪些边被打开。

## 指标
- 作弊分四层（借 SafeClawBench 范式：semantic acceptance / audit-visible evidence / sandbox-observed harm）：intent / attempt / success / score corruption（evaluator 修改、hidden-label access、test leakage、hardcoded exploitation）。
- **必须同报 honest task success**——一刀切禁所有工具当然作弊少。
- 另报：trusted − agent-reported score 差、runtime overhead。

## 协议完整性自审（HackDetect 范式）
对自家 harness 检查：hidden rubric 挂载、evaluator key/config 可读性、文件名/git history 泄漏、scorer endpoint 可探测、reference outputs 可达、cache 跨任务污染。写进报告一小节 Evaluation Protocol Integrity Audit。

## 风险
- "两个 agent 分开就安全"在 2026 文献下已站不住（evaluator locking 结论在先）；增量限定为：科研 pipeline 的五级阶梯对照 + 安全提升且 honest completion 不降。
- ScienceAgentBench 的自包含 Python 产物是 normalized artifact 的天然载体，可作补充。
