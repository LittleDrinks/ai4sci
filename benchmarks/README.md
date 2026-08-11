# Benchmark 账本
Remote root: `/data/zsm/ai4sci-design-bench-20260809`.
| 设计问题 | 复用资源 | 当前证据 | 边界 |
| --- | --- | --- | --- |
| 搜索策略是否产生不同机制 | Matbench + ResearchHarness | 拒绝恢复控制中 Mini 三策略逃离 0/3、0/3、1/3，Luna 均 3/3；模型效应大于上下文策略 | 控制拒绝不估计自然拒绝率；每格 3 case，不能排序策略 |
| 机制重合判断能否稳定 | Matbench 官方提交 | 15 个控制对合议 14/15；真实候选 30 对含 4 次分歧和 3 个传递冲突 | 局部判断可用，不能自动闭包成方法族 |
| 入图审核能否挡住已知错误 | Anti-Autoresearch | 原生缺陷 7/7，原生测试 67/67 与 21/21；外部证据缺失保持 unsupported | 未测真实审核误杀率和新领域迁移 |
| 队列与图谱不变量能否保持 | NetworkX | 11/11 场景、4/4 测试通过 | 领域夹具不是产品 schema，未测分布式存储 |
| 大规模审查如何避免模型猜测 | Inspect AI + SearchBench 事件流 | 类型化查询在 12/36-run 共 8 问全对 | 只证明机器查询正确，未测真人可读性 |
| 长轨迹错误能否定位到有害承诺 | TELBench + DRIFT + AgentRx | 分层 12 条上两模型的 DRIFT 宏 F1 为 0.2528、首错均为 0；AgentRx 公开 73 条中 critical root cause 仅 54 条是首错 | TELBench 无干净负例；AgentRx 73 条 reward=1 只测关键根因误报；仍未测真人审查 |
| 丢弃对话后是否遗漏关键条件 | LongMemEval-V2 | 完整 oracle state 两模型均 0；问题词切片两模型均 1，Token 少约 11–12 倍 | 单题 oracle；官方 RAG 需本地 Qwen3-Embedding-8B 服务，百炼 `text-embedding-v4` 不能原样替换 |
| 图谱沉淀能否保留机器轨迹中的目标、因果与状态 | AMA-Bench | 官方代码已固定，数据下载尚未完成 | 复用官方 memory 接口和 QA/judge；不复用 AMA-Agent 图 schema |
| 哪些历史应向后续 Agent 披露 | STATE-Bench Agent Learning Track | 代码与 300 条训练轨迹已固定远端；上游测试 148/148 | 需 Qwen Chat Completions adapter 与锁定 Judge 凭据；只裁决披露策略，不裁决科学创新 |
| 图谱中的候选假设能否迁移到未见样本 | HypoBench | MIT 代码与 197 个数据配置已固定远端；代码编译通过，预检发现 18 条上游失效文件引用 | 用 accuracy/F1 和 OOD 退化裁决候选效用；只运行预检通过的配置，不裁决因果、实验真实性或创新性 |
| 文献进入图谱前应提取多少证据 | EvidenceBench | 426 个实例与官方 evaluator 已固定远端；1688 组非空 gold 索引合法，293 条 test oracle coverage=1.0 | 比较整篇、图谱证据和按需抽取；只裁决证据覆盖，不裁决 hypothesis 真伪 |
| 图谱证据能否替代整篇文献输入 | SciFact | 官方摘要 top-3 Hit one 0.8467；历史 claim-evidence 图为 0.74，有证据样本 0.5851/理论上限 0.5957 | 图谱替代旧对话，不替代新文献检索；摘要不代表多模态全文 |
| 事实纠正应全局共享还是按需披露 | SciFact | Mini scoped/global 为 15/20、14/20；Luna 均 16/20；全局输入多用约 10.7–12.1 倍 Token | 使用 oracle evidence，只测作用域，不测自动检索 |
| 图谱缺证据时能否自动升级检索 | SciFact | train calibration 阈值 0.38294 原样迁移 dev：Hit one 0.8830、回退 43.1% | 单数据集 TF-IDF；返回证据仍需审核 |
| 候选实验能否真实复现 | ResearchHarness + Matbench | 一个 Luna 行动经执行、泄漏驳回、原会话退修、独立评分与无会话重跑；prediction 哈希一致，MAE 0.71517 | 仅一个 CPU 行动；未测失败执行和环境漂移 |
| SDK 是否需要自建 | AstaBench + Inspect AI + ResearchHarness | AstaBench/Inspect 官方 smoke 通过；Harness 已产生结构化轨迹与 Token | 远端 Python 3.10 低于 AstaBench 3.11 要求 |
| 复用的 benchmark 自身是否可靠 | Auto Benchmark Audit | 公开 CLI 可统一收集任务、环境和 evaluator 证据 | 代码无覆盖全仓的根许可证；仅作内部质量门，尚未运行 |
| 端到端科研创新能力如何对标 | InnovatorBench + ResearchGym | commit `934ead34` 固定本地，编译通过；20 任务/6 领域清单与资源需求已盘点；HF 数据集 2026-08-10 已转公开（69.7 GB 未下载） | 任务 1–17 需 8×80GB GPU；agent/judge 均收费 API；只有任务 18/19 零 GPU 可先行；task_20.yaml task_name 为上游缺陷 |
| 假设→实验→反馈子集能否复用 | AstaBench E2E-Bench / CORE-Bench / LitQA2 / PaperFindingBench | 本地 venv 任务发现与 `--config-only` 全通过；官方 baseline 数字取自公开 `allenai/asta-bench-results` | 除 CORE-Bench 外数据在 gated `allenai/asta-bench`（需人工接受许可）；E2E/PaperFinder 还要 judge API 预算；CORE-Bench 需 Docker |
| 候选实验工程能力如何对标 | MLE-bench Lite | commit `507f92e1` 固定本地，322 个 LFS 对象完整；从官方 grading reports 复算 famou-agent 9 组 Lite any_medal 59.09–81.82% | prepare 被 Kaggle 竞赛规则 403 阻塞（22 个竞赛逐个接受，需人工操作账号）；5 个 Lite 竞赛有已知上游问题；`run_group_experiments.csv` 指针含冲突标记 |
