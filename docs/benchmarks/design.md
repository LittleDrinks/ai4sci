---
sources:
  - title: ResearchClawBench
    url: https://arxiv.org/abs/2606.07591
  - title: Anti-Autoresearch
    path: /home/q2635/wsl-workspace/music/Anti-Autoresearch
  - title: NetworkX
    url: https://networkx.org/
  - title: LongMemEval-V2
    url: https://github.com/xiaowu0162/LongMemEval-V2
  - title: AMA-Bench
    url: https://github.com/AMA-Bench/AMA-Bench
  - title: STATE-Bench
    url: https://github.com/microsoft/STATE-Bench
  - title: HypoBench
    url: https://github.com/ChicagoHAI/hypothesis-generation
  - title: EvidenceBench
    url: https://github.com/EvidenceBench/EvidenceBench
  - title: AstaBench
    url: https://github.com/allenai/asta-bench
  - title: Inspect AI
    url: https://inspect.aisi.org.uk/
  - title: RE-Bench
    url: https://github.com/METR/RE-Bench
  - title: MLE-bench
    url: https://github.com/openai/mle-bench
  - title: Matbench
    url: https://github.com/materialsproject/matbench
  - title: TELBench and DRIFT
    url: https://github.com/NJU-LINK/DRIFT
  - title: AgentRx
    url: https://github.com/microsoft/AgentRx
  - title: SciFact
    url: https://github.com/allenai/scifact
---
# 评测设计
## 固定原则
图谱是唯一持久真源；原始对话默认丢弃；信息入图前独立审核；通过后轮换上下文；规划与实验分离；盲创会话只提交一次。
## SearchBench
比较全量反思、独立盲创、盲创失败后新建反思、盲创在原会话接收反馈四种策略。所有组使用相同任务、模型、工具、Token 与实验预算。共享 blind 只计一个唯一候选；只有真实拒绝后产生的新会话进入失败后策略比较。
指标包括每百万 Token 通过审核的唯一候选、与已入图行动明确同机制的比例、局部关系冲突率、不可执行率、事实错误率、首个明确不同机制候选成本与最终实验结果。执行样本覆盖通过候选，以已裁决同机制关系去重，不依赖自动方法族闭包。
上下文装配单独消融完整图谱、显式依赖加按需展开、语义检索，不与规划策略做完整笛卡尔积。发现曲线趋平后分别测试重置会话、补充文献、更换模型或 Skill、人工介入能否恢复新增方法族。
## AuditBench
从有效图谱快照注入释义重复、证据错配、缺失来源、观察冲突、复现漂移、严重事实错误与方法伪创新。评价检出率、误杀率、Token、延迟，以及通过、退修、重开、人工介入和隔离处置是否正确。
## GraphBench
以确定性事件回放和性质测试覆盖并发提交、重复消费、审核竞态、执行中上游失效、重试幂等、哈希不一致、取消和重新排队。核心不变量是未审核依赖不能执行、同一行动不能重复执行、隔离记录不进入默认检索、失效传播覆盖全部后代、同一事件序列重建相同图谱。
## ReviewEval
固定一组真实运行图谱，让审查者回答本周期新增机制、失败原因、待执行行动和上游错误影响范围。比较图谱渐进披露、平铺报告与原始日志，记录时间、正确率、置信度、展开次数以及 AI 预审是否改善判断。
公开轨迹实验改用 TELBench harmful spans 与 AgentRx critical failure gold。每位审查者在互斥、配平轨迹上比较原始轨迹、确定性审查视图、审查视图加 AI 预审；同一轨迹不重复曝光。原型夹具只验证数据没有丢失，不计入可读性结果。
## SedimentationBench
复用 LongMemEval-V2 的 Agent 轨迹、问题、证据与评分器，把图谱沉淀实现为其 memory module。比较无检索、原始状态切片、状态切片加轨迹笔记和图谱证据，评价状态回忆、动态变化、工作流、环境陷阱、错误前提、回答延迟与披露 Token。图谱版本不能读取原始轨迹；完整性由下游问题而非摘要长度判断。
第二阶段复用 AMA-Bench 的真实 Agent 轨迹、专家 QA、可扩长合成轨迹与两阶段 memory 接口，测目标、因果和状态信息随轨迹长度的保留。产品图谱仅实现官方 `memory_construction` 与 `memory_retrieve` 边界；AMA-Agent 作为对照，不提供产品 schema。除正确率外报告构建与检索 Token、披露字符、延迟及长度退化曲线。
## ExperienceDisclosureBench
复用 STATE-Bench Agent Learning Track 的训练轨迹、留出任务、只读 `retrieve_learnings` hook、状态断言和五次重复。四组都注册同一工具并固定 Qwen Agent、`top_k=3`、模拟器、Judge 与任务：空历史返回空列表；未过滤历史返回直接提炼结果；图谱组只返回已审核、与任务相关的经验；隔离组另由审核检索匹配驳回记录，执行 Agent 只收到最小阻断理由。离线构建模型与预算固定，构建成本单列，不通过给弱组补 Token 伪造成本相等。
按同一留出任务配对报告 pass@1、pass^5、无效状态变更、轮数、检索次数、披露 Token 和总成本；另列未过滤历史相对空历史使成功变失败的任务，以及图谱组是否恢复。不预先给这些任务建立失败 taxonomy。该实验裁决历史披露是否帮助执行，不把企业流程标签或成功率解释为科学创新。
官方 300 条训练文件只有对话，没有成功标签；共 2319 条消息、2842 次工具调用和约 749K 字符，最长 31 条消息。审核、入图与隔离由被测系统完成，不能读取留出任务作为 oracle；较长尺度退化交给 AMA-Bench 与真实研究图。
## HypothesisUtilityBench
复用 HypoBench 的固定 train/test/OOD 数据、生成与推理接口、accuracy 和 F1。比较无候选、未审核候选、只披露已审核相关候选、加入文献候选四组；模型、样本、随机种子和候选预算固定。按真实任务、规则深度、噪声与干扰项分层报告测试集收益、OOD 收益、每个有效候选 Token 和退化曲线。
该实验只裁决候选假设是否形成可迁移的预测规则。不能据此宣称因果机制成立、实验已复现或产生科学创新；HypoBench 的 hypothesis bank 只作为被测接口，不进入产品 schema。
## LiteratureEvidenceBench
复用 EvidenceBench 原始 426 个生物医学 hypothesis-paper 对、句级 aspect gold、最优预算与固定预算 scorer。比较整篇论文直接披露、入图时抽取 evidence、查询时按需抽取、入图加按需补取四组；固定模型、论文、查询和证据句预算，报告 aspect recall、句级 precision、披露 Token、延迟与入图成本。
系统只实现候选 evidence 的存取与来源关联，不预设 benchmark 的 aspect 类型为产品 schema。results-only gold 缺失的 8 篇论文从对应子指标分母排除；该实验裁决证据披露和沉淀策略，不裁决 hypothesis 真伪。
## 方法族标注
两个独立审核者对同一任务内的候选行动成对判断核心机制是否相同，不预设跨任务分类。分歧与不满足传递性的结果交给人工裁决。激进但不可执行或不能产生证据的候选不计为有效新增。
## 最小规模
仪表链路先用一个任务、四种搜索策略、三个随机种子、每次三个候选。共享 blind 按内容与产生它的会话去重；每个唯一候选独立审核，机制重合采用带控制对的双审核局部关系。实验执行覆盖已通过候选，并以人工解决后的明确同机制关系去重。
## 2026-08-09 预检
SearchBench 复用 ResearchClawBench `Astronomy_000` 与 ResearchHarness，完成 36 次运行、54 个会话和 255472 Token。20 个候选通过结构与证据锚点检查。后续对覆盖全部候选的 30 对样本执行两个独立会话审核，审核者一致率与顺序对称率均为 30/30，全部判断为同一机制，10 个闭合三角形无传递冲突。该任务文本已规定贝叶斯框架、完整后验和超辐射模型，不能检验搜索策略能否发现新方法族；结果只证明 Harness、会话策略与成对审核链路可运行。当时尚无已知异机制控制对，方法结论已由 Matbench 控制实验取代。
AuditBench 复用 Anti-Autoresearch 的 ledger、检查器、裁决器、taxonomy、原生 fixtures 与测试。原生缺陷 7/7、测试 67/67 和 21/21；自定义证据包内确定性场景 2/2、模型场景 2/2。五个依赖外部语料、资源注册表或仓库产物的场景不可判定，标记为 unsupported，不计召回率。
GraphBench 复用 NetworkX 3.4.2 处理依赖拓扑、环检测与后代传播，11/11 场景、4/4 测试通过。事件日志与审核、执行、重试、隔离状态是当前领域夹具，不是产品 schema。
ReviewEval-preflight 仅验证已有原型的 7 个产物、14 个事件在三种表示中没有丢失。固定四问的小模型代理结果为渐进图谱 4/4、平铺报告 3/4、原始日志 4/4；无真人参与，不能判断可读性。
AstaBench 0.5.4 与 Inspect AI 0.3.233 已在远端完成官方 demo 冒烟：任务发现、单样本评分、四样本并发和 AstaBench 11 个 validation task 配置展开均成功。Inspect 可直接承担 Task、Solver、Scorer、结构化日志与有界并发；ResearchHarness 继续作为被测研究运行时。远端 Python 3.10 低于 AstaBench 要求的 3.11，本轮只证明接口可复用，不证明生产部署兼容。
ReviewScaling-preflight 从 SearchBench 的 36 个真实结果、198 个图事件和 54 份轨迹构造三种审查输入，固定 24000 字符预算。12-run 时渐进图谱、平铺报告、原始日志分别答对 2/4、1/4、2/4；36-run 时均为 0/4。当前“渐进图谱”仍是完整节点与边的 JSON 串行化后从尾部截断，不具备总览索引或按问题展开，不能代表目标交互。该失败要求下一轮比较“可验证总览+按需子图”与原始序列，而非宣称图谱天然提高可读性。
ReviewScaling-v2 不增加持久字段，只从同一事件流生成状态分面、异常列表和按 ID 索引的派生审查视图。修正字段名敏感的 scorer 后，该视图在 12-run 与 36-run 均为 3/4，长度分别为 3916 与 15768 字符；36-run 的完整图、平铺报告和原始日志仍均为 0/4。剩余错误是把不存在的 ID 猜成已有状态，以及把明确的隔离计数 28 答成 20。由此需要在派生视图之上提供程序化聚合与精确查找，让不存在和计数由查询结果证明，不能交给模型从整页内容心算。
SearchBench v2 第一项改用 Matbench `matbench_expt_gap`：4604 个真实实验带隙样本只暴露化学组成，固定五折与官方记录、验证、评分接口均已在远端跑通；训练均值 smoke 的 MAE 为 1.1435269609161665。该任务可形成物理描述符、核/树模型、组成嵌入与集成等方法分叉，CPU 可执行。MLE-bench Nomad 保留为含空间群、晶格和几何的扩展；官方准备链已就绪，但 Kaggle 账号未接受竞赛规则并返回 403，不能自动代替用户同意条款。RE-Bench `Fix Embedding` 保留为重型备选。
Sedimentation smoke 复用 LongMemEval-V2 `01307e07` 的 100 条文本轨迹、官方 `no_retrieval` memory、保存/恢复接口、reader 与答案 scorer。初始 smoke 只下载 29 张问题截图共 3112508 bytes；后续 AgentRunbook 验证下载并校验官方轨迹截图归档，3358 个引用缺失数为 0。官方 memory 构建与恢复成功，金答案判 true、缺短语答案判 false。接入现有 OpenAI-compatible endpoint 后，`gpt-5.4-mini` 在空上下文中返回 `UNKNOWN`，官方得分 0，使用 181 tokens，形成可重复的负对照。自定义范围只剩被测图谱 memory module，不再自建轨迹、问题、reader 或评分器。
ReviewScaling-v3 复用 Inspect AI 0.3.233 的 Task、tool、agent loop、scorer 和 `.eval` 日志，只向模型暴露 `aggregate/get/impact/subgraph` 四个只读类型化查询。12-run 与 36-run 共 8 个样本全部答对，9 次工具调用；未知 ID 返回 `found:false`。该结果只证明确定性查询消除了模型计数和存在性猜测，不代表真人可读性已经验证。
TELBench/DRIFT 在 1000 条公开 deep-research 轨迹上提供 harmful error span 金标。按 benchmark 与难度分层固定 12 条后，Mini bare/DRIFT 宏 F1 为 0.1861/0.2528，Luna 为 0.2472/0.2528；两模型 bare 首错准确率均为 0.0833，DRIFT 均为 0。DRIFT 消耗约 2.39–2.53 倍 Token，无 API 回退。Mini/Luna 虽只选择 42.86%/33.83% 的语义段，字符披露仍为 91.21%/91.49%；节点或段数量不能代理审查负担，渐进披露按实际字符、Token 和展开次数计量。TELBench 每条都含有害错误，298 条最终答对仍各有错误段；它能测定位漏检，不能单独测误报。DRIFT 只证明 claim-centric 对照增加覆盖，不能证明首错追溯或真人可读性。数据卡为 Apache-2.0，代码仓库无显式许可，不进入产品依赖。
AgentRx MIT 仓库公开的 73 条 ground truth 中，critical root cause 只有 54 条是时间上首个失败，47 条是最后失败，8 条两者都不是；Magentic-One 每条平均 6.70 个失败点。τ-bench 完整集的 73 条 reward=1 运行用于计算“错误宣告存在致败根因”的误报率，不标成全程无异常。评测必须把 earliest anomaly、critical root cause 和 downstream impact 分开计分。AgentRx 十类 taxonomy 只属于原 benchmark 的分析标签，不进入产品 schema。
LongMemEval-V2 问题 `01307e07` 的 100 条轨迹与 3358 个截图引用均完整。官方 `agentrunbook_c_v2` 完成 memory workspace 构建，但其 OpenAI Agents SDK 查询依赖 Responses WebSocket，当前兼容端点连续三次关闭连接，官方回退为空 context 并得分 0。数据、memory 接口与 scorer 可复用；具体 SDK 只有在模型能力与传输协议匹配时才可运行。官方 `rag_query_to_slice_notes` 将 embedding 模型名同时传给 API 与 Hugging Face tokenizer；百炼 `text-embedding-v4` 不能原样替换默认 `Qwen/Qwen3-Embedding-8B`。官方组需远端本地 embedding 服务，解耦 tokenizer 的实现另列 adapter 组。
同题的 oracle state 含 25928 字符 AXTree。Mini 与 Luna 读取完整 state 都漏掉三个答案之一并得分 0；只按问题词 `Incident` 取 1581 字符匹配行后均得分 1，Token 从约 7456 降到 617/666。selector 不读取金答案。完整证据会降低答案完整性，按问题派生的可验证切片是 memory 查询语义，不只是前端渐进披露。
方法族校准直接抽取 Matbench 六份官方 submission 描述。15 个控制对中合议正确 14/15：13 个异机制对全部正确，CrabNet 两版出现一次双审核分歧，MODNet 两版一致判同；无解析或接口错误。方法族判断可以用于局部审核，但分歧必须保留。
SearchBench v2 在 Matbench 上完成 9 个共享 case：20 次 planner 调用、457373 Token，15 个行动通过双维度审核、4 个待人工、1 个格式拒绝，真实拒绝只触发 2 条后续分支。15 个已入图候选抽样审核 30 对，22 对同机制、4 对异机制、4 对分歧；15 个闭合三角形有 3 个传递性冲突。候选几乎全部落在元素 token、attention 与图消息传递附近，blind 与 reflect 都发生模型先验坍缩；当前结果不能证明盲创比反思更创新，也不能把成对判断自动闭包为方法族。
SearchBench v3 把候选逐一与 RF-Magpie、CrabNet 两条已入图路线比较：任一路线一致判同即拒绝，全部一致判异才接受。3 个 case、6 次规划、200657 Token 得到 5 个通过和 1 个待人工，仍没有自然拒绝。多路线门禁可运行，但当前历史覆盖与机制粒度不足以稳定触发失败后分支；不能以人为植入的失败替代策略证据。
已知拒绝恢复控制不估计自然拒绝率，只比较明确重合后的恢复。Mini 的重新盲创、全新反思、原会话反馈分别逃离 0/3、0/3、1/3；Luna 三组均为 3/3。Mini 仍坍缩到元素图消息传递，Luna 转向核与邻域插值；但 Luna 的 9 个候选只有 2 个执行审核一致通过。模型选择本身是搜索策略变量，机制广度与执行有效性必须分别报告；每格 3 个 case 不足以排序上下文策略。
SciFact 官方 TF-IDF abstract retriever 在完整 dev 的 top-3 文档检索上得到 `Hit one=0.8467`、`Hit all=0.8333`。这只是原文检索基线；graph-memory 需要先去除 2 条 train/dev 精确 claim+evidence 重复，再以同一切分、top-3 预算和官方 evaluator 比较证据命中与输入 Token。
去重后的 train claim-evidence 图覆盖 365 篇文档；同一官方检索器在完整 dev 得到 `Hit one=0.74`。排除 NEI 后，历史图命中 0.5851，覆盖上限 0.5957，完整摘要语料为 0.7553。关系存在时检索已接近上限，差距主要来自从未入图的新文献；系统需要外部检索补图，而不是保留旧对话弥补覆盖。
SciFact 20 条 claim 的证据作用域消融中，Mini 的 scoped/global evidence 为 15/20、14/20，Token 4504/54536；Luna 均为 16/20，Token 5241/55878。全局事实没有准确率收益，却多用约一个数量级 Token并引入额外错误。人工事实纠正进入带来源、按 claim/resource 检索的图谱证据；全局 Skill 保存审核程序，不累积事实正文。结果使用 oracle evidence，只裁决披露作用域。
SciFact 历史图谱的 top-1 相似度预测 gold 文档覆盖的 AUROC 为 0.9666。train 的 638/108 build-calibration split 选出阈值 0.38294，原样应用 dev 后 Hit one 0.8830、回退率 0.4309；图谱单独为 0.5851，全文单独为 0.7553。低置信度可作为一次有预算上限外部检索的触发信号；自动触发或人工确认待裁决，返回证据仍需入图审核。
SciFact 官方 evaluator 的 10 条 fixture 与预期指标完全一致，数据为 809 train claims、300 dev claims、5183 篇摘要。dev 的 182 个证据文档全部存在于 corpus，110 个在 train 证据图出现；train/dev 另有 2 条 claim 文本与 evidence 完全相同。图谱记忆消融必须在规范化 claim+evidence 去重后重切分，target claim 的 gold edge 不得入图。
相同 Matbench 题面改用 `gpt-5.6-luna` 完成 3 个 case、6 次规划和 159240 Token，3 个候选通过、3 个待人工；候选转向核插值、显式元素对交互与鲁棒线性模型。每模型按内容哈希取 3 个通过候选进行 15 对完整审核：9 个跨模型对中 8 个明确不同、1 个分歧；Mini 内部 2 同、1 分歧，Luna 内部 2 异、1 同。模型差异已表现为搜索空间差异，后续策略消融必须跨模型分层报告，不能把单模型输出当作问题搜索空间。
Luna 的一个已通过核相似度行动由 ResearchHarness 默认本地工具执行。首份 Matbench submission 格式验证通过，但执行代码读取 held-out target 自行评分；结果审核以 `hidden_label_access` 驳回，原工作会话退修后删除目标访问，再由独立进程评分 MAE 0.7151736522892789。无模型、无会话重跑得到相同 prediction SHA-256 与分数。官方 `validate()` 只验证提交结构，不能替代来源审核；执行承诺审核与产物审核必须分开。
