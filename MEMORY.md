算力资源与存储资源：`ssh smYuHangLab2; cd /data/zsm/ai4s/`，如果连接不上，暂停并提醒连接校园网
# 项目状态
## 产品
- 面向单个科学问题运行一个集群；图谱是唯一持久真源，对话上下文沉淀后删除。
- Agent 通过队列工作：规划产生行动，行动审核通过后触发执行，结果由独立线程审核；通过后入图并轮换会话。
- 人先看图谱派生的审查视图，再按节点、证据和依赖逐层展开；原始轨迹默认不进入研究图谱。
- 计算实验保留代码、输入、配置、环境、随机种子和不可变产物；湿实验按不可重跑程度保留完整证据。
## 已定
- 盲创只看问题、硬约束、评价接口和工具，一次只提交一个行动；失败后销毁，反思另开会话并接收相关图谱切片。
- 入图审核按对象依赖和用途提出问题，不共用固定缺陷 taxonomy；待审内容可显示但不能继续生长依赖路径。
- 驳回内容进入隔离记录，只在审核时做相似性匹配；执行 Agent 只看最小阻断理由。
- 机制重合只保留单个 benchmark 内的局部成对判断；冲突与传递性冲突交人工，解决前不生成方法族。
- 审查视图是图谱的确定性读模型，不是持久节点；计数、ID 存在性和影响范围由查询计算。
- 节点身份由系统根据规范化内容生成；Agent 自报 ID 不进入主键，语义重合由审核关系表达。
- 人类与 Agent 共用节点提交接口；UI、CLI 与 SDK 只做适配，提交创建待审节点，入图仍经过相同审核门。
- 行动的执行承诺审核、产物结果审核与独立评分分离；执行进程不读取隐藏目标，复现比较规范化内部内容。
- 演示 UI 全量中文；节点内容保持产生时的语言。
- 模型服务为端点实体（ADR 0015）：同模型多端点按优先级容灾，Agent 绑定端点；本地 SDK（codex 等）注册为新 runtime 按 capability 派工；演示与提交链路只用 Qwen 端点，OpenAI 兼容端点只作开发对照。
- 图谱视图升级为可拖拽 kanban（同一读模型，替换力导向布局）；Trace 视图只记 token 与耗时，按端点/模型/Agent 聚合，不维护成本单价。
- 文献分两层：系统组件理论依据落到前端 Methodology 页组件；运行时文献为 reference 节点，来源最小化（标题/URL/DOI/摘要/本地路径/校验值），主张按需展开。
- setup 为节点类型（环境配置、依赖安装、数据集下载、前期调研），经同一审核门入图，可被多个后续执行复用依赖。
## 评测证据
- SearchBench 仪表链路：ResearchClawBench + ResearchHarness 完成 36 runs/54 sessions/255472 tokens；原任务规定目标方法，不能比较方法空间创新。
- AuditBench：Anti-Autoresearch 原生缺陷 7/7，原生测试 67/67 与 21/21；外部证据缺失场景保持 unsupported。
- GraphBench：NetworkX 事件回放 11/11，测试 4/4。
- ReviewScaling：36-run 下完整图、平铺报告和原始日志均 0/4；派生审查视图 3/4，仍需类型化查询避免模型心算与猜测不存在节点。
- Sedimentation smoke：LongMemEval-V2 官方 no-retrieval memory/reader/scorer 端到端通过，选定题返回 UNKNOWN、得分 0，形成负对照。
- SearchBench v2 首题：Matbench `matbench_expt_gap` 4604 样本、5 folds，官方 record/validate/score/to_file 已跑通；训练均值 smoke MAE 1.1435269609161665。
- AstaBench/Inspect 可复用 Task、Solver、Scorer、结构化日志和有界并发；ResearchHarness 保持被测运行时。
- 方法族控制：Matbench 官方六候选的 15 对控制合议正确 14/15；一个 CrabNet 版本对发生审核分歧。
- SearchBench v2：Matbench 9 个 case 产生 20 次 planner 调用，15 个行动通过、4 个待人工、1 个格式拒绝；30 对局部判断含 22 同、4 异、4 分歧与 3 个传递性冲突，不能自动闭包成方法族。blind 与 reflect 均坍缩到 composition token/attention/graph message passing 附近。
- SearchBench v3：候选逐一对照 RF-Magpie、CrabNet 两条已入图路线；3 case、6 次规划、200657 Token 得到 5 个通过、1 个待人工，仍无自然拒绝，不能比较失败后的 blind/reflect 策略。
- SearchBench 拒绝恢复控制：Mini 的盲重抽/新反思/原会话反馈分别逃离 0/3、0/3、1/3，Luna 均为 3/3；Luna 9 个机制通过候选只有 2 个执行一致通过。模型效应大于上下文策略，机制广度与执行有效性分开报告。
- Luna 对照：3 个 case 的 6 次规划中，3 个通过、3 个待人工；跨模型 9 对有 8 对明确不同、1 对分歧，模型先验是搜索空间的重要变量。
- ReviewScaling-v3：Inspect typed `aggregate/get/impact/subgraph` 在 12/36-run 共 8 问全部正确，未知 ID 明确返回 `found:false`。
- TELBench/DRIFT：公开 1000 条 deep-research 轨迹可复用错误段金标；分层 12 条上两模型 DRIFT 宏 F1 均 0.2528、首错均 0，Token 为 bare 的约 2.39–2.53 倍。虽只选 33.83%–42.86% 的段，仍披露约 91% 字符；渐进披露按字符、Token、展开次数计量。数据卡 Apache-2.0，代码仓库无显式许可，只作远端对照。
- AgentRx：MIT 仓库公开 73 条 critical failure ground truth；54 条关键根因是首错、47 条是末错、8 条两者都不是。τ-bench 完整集另有 73 条 reward=1 运行，可测“错误宣告存在致败根因”的误报率，不能标成全程无异常。最早异常、关键根因和下游影响分开计分，不复用其十类 taxonomy。
- SciFact graph-memory：官方完整摘要 top-3 Hit one 0.8467；去重 train 图覆盖 365 篇文档，完整 dev 为 0.74；排除 NEI 后图谱 0.5851、历史覆盖上限 0.5957、完整摘要 0.7553。图谱替代旧对话，不替代新文献检索。
- SciFact 证据作用域：Mini scoped/global 为 15/20、14/20，Luna 均 16/20；全局 evidence 多用约 10.7–12.1 倍 Token且有额外错误。具体事实进带来源的作用域图谱证据，审核程序进 Skill。
- SciFact 检索升级：train calibration 阈值 0.38294 原样迁移 dev，Hit one 0.8830、回退率 0.4309；图谱 0.5851、全文 0.7553，检索结果仍需审核。
- LongMemEval-V2：问题 `01307e07` 的 100 条轨迹、3358 个截图引用完整；官方 AgentRunbook 完成 workspace 构建，但 Responses WebSocket 与当前端点不兼容，三次失败后空 context、得分 0。数据、memory 接口和 scorer 可复用，SDK 必须按运行能力调度。
- AMA-Bench：MIT 代码固定在远端 commit `ddfd319e`；官方 memory 构建/检索接口、真实轨迹专家 QA 与可扩长合成轨迹用于 LongMemEval 后的沉淀评测，不复用 AMA-Agent 图 schema。50.45 MB 数据对象首次远端下载保持 0 byte，尚无结果。
- STATE-Bench：MIT commit `5644b183` 已通过官方 tarball 固定远端；独立 CPython 3.12.13 上游测试 148/148。直接复用 300 条训练轨迹、150 条留出任务、只读 `retrieve_learnings(top_k=3)`、确定性状态断言和五次重复；百炼 Qwen 只实现官方 custom client/agent adapter，官方分数仍需锁定 GPT-5.4 simulator/judge，企业任务不裁决科学创新。
- HypoBench：MIT 代码 commit `bd37a312` 与数据 commit `7e4bbc34` 已固定远端，含 16 个真实配置和 181 个合成配置，代码编译通过。197 个配置预检发现 `election/level0..5` 共 18 条上游旧文件名引用失效，其余引用文件存在且字段等长；只运行预检通过的配置。复用固定切分、OOD、accuracy/F1 与可控深度/噪声/干扰项，只测候选规则的预测效用和迁移，不据此裁决因果、实验真实性或创新。
- EvidenceBench：MIT 代码 commit `bf1d9633` 与原始 426 个实例固定远端；测试集 CC-BY，train/dev 为 CC-BY-NC-SA。1688 组非空 gold 证据集合索引合法；8 篇没有 results-only gold，对应 16 个字段为 null。官方 evaluator 在 293 条 test gold-optimal 输入上 coverage=1.0；复用 hypothesis、候选句、aspect 覆盖与 scorer 测文献证据沉淀，不用它裁决 hypothesis 真伪。
- LongMemEval oracle state：Mini/Luna 读取 25928 字符完整状态均漏一项、得分 0；按问题词切成 1581 字符后均得分 1，Token 从约 7456 降到 617/666。渐进披露属于查询语义。
- ExecutionLoop：一个 Luna 核相似度行动首次因 `hidden_label_access` 驳回，原会话退修后独立评分 MAE 0.7151736522892789；无模型重跑 prediction 哈希一致。
## 约束
- 比赛运行时基座必须使用 Qwen；方向 A 要提交 125 个问题的轻量结果，5 个深度题只用于演示。
- 300 元学生券自领取起一年有效；学生用券中心指定模型的百炼 API 按量账单可自动抵扣，无需预购 Token，优惠券不计入现金余额。Qwen chat 与 `text-embedding-v4` 各先小额调用验证接口，首次实际收费再核对券抵扣。
- MLE-bench Nomad 官方准备链已就绪，但 Kaggle 账号未接受竞赛规则，prepare 返回 403。
- 截止 2026-09-05；提交一份不超过 20 页的 PPT/PDF、源码与可调用 API 或页面。
## 下一步
- 调研高质量科研思路/演进图样式，据此 mock 一份演示数据看 kanban 效果；现有两项目（Computer processing limits 实测残留、music 166 节点占位导入）届时丢弃，不导入 125 题为 project。
- 并行落地六条：端点+Agent 广场（同步修复 agents 仍注册 gpt-5.4-mini、与百炼 .env 不匹配的故障）、Trace 轨迹视图、reference 文献节点与 Methodology 页、CLI 补全、Map 页升级 kanban、setup 节点类型。
- 确认先前选定的 5 个深度演示题标题；当前仓库没有清单，确认前不重新选题。
- 扩展 Matbench 代表行动执行，覆盖失败执行与环境漂移；只以已裁决同机制关系去重。
- 在不同模型内继续积累真实拒绝后的转移样本；现有跨模型对照已证实模型先验改变搜索空间。
- 百炼 Key 已确认第二对生效（dotenv 同名键后者覆盖前者）；Qwen chat 与 `text-embedding-v4` 各先小额调用验证接口，首次实际收费再核对券抵扣；缩减矩阵型号待 GET /models 后定。
- 大 bench 框架已本地收集：InnovatorBench（commit 934ead3，HF 数据集现免申请但 69.7 GB 待下载决策，task 18/19 零 GPU，task_20.yaml 有上游 task_name 缺陷）；AstaBench（0.5.4 本地预检通过，DiscoveryWorld 不在套件内，"假设→实验→反馈"对应 E2E-Bench/CORE-Bench，baseline 出处 allenai/asta-bench-results）；MLE-bench（commit 507f92e 含 LFS，Lite 22 竞赛 158 GB，prepare 仍卡 Kaggle 规则接受）。
- 报告实验设计咨询提示词在 docs/benchmarks/experiment-design-prompt.md，覆盖 9 条设计主张，待外部咨询结果后定稿实验组合。
- 实验规划已定稿（外部咨询综合）：docs/benchmarks/experiment-plan.md（6 主实验 9 证据单元，叙事=认识论信息流控制四流）+ 每实验一文件（e1/e3/e4/e5/e6/e7/e8/e9）+ resource-catalog.md + related-work.md。主张一收窄为"失败信息作用取决于表示粒度×接收角色"；E9 主战场 ResearchClawBench base 40 + 12-task 消融。
- 测试环境：4×A5000（24GB×4）+ 800GB 磁盘，HF token 用户提供；InnovatorBench 仅 task 18/19/20 与缩减任务可行，8×80GB 任务不可全规模。
- 低置信度图谱查询是否自动升级一次有预算上限的外部检索待裁决；检索结果仍须入图审核。
- `research-world` 已跑通真实前后端：计划产生行动、行动准入触发执行、独立 Agent 审核、人工失效传播、退修/重开、Worker 租约和 workspace 清理；UI、CLI、导入器与 Worker 共用命令接口。
- `music/directions.yaml` 已经由通用 manifest 导入为 166 个节点、246 条关系；产品只保存来源数据的 kind 与 payload，不建立全局研究 taxonomy。
