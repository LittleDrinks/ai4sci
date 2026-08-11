---
sources:
  - title: Autonomous Research Agents: A Survey of AI Scientists and the Verification Gap
    url: https://arxiv.org/abs/2608.05179
  - title: Toward Auditable AI Scientists: A Hypothesis Evolution Protocol for LLM Agents
    url: https://arxiv.org/abs/2607.09195
  - title: Auto Research for Materials: Auditable AI-Scientist Workflows with Held-Out Transfer
    url: https://arxiv.org/abs/2607.17100
  - title: NVAITC AI Scientist: A Governed End-to-End Research System - A Hypertension GWAS Case Study
    url: https://arxiv.org/abs/2607.11084
  - title: Are LLMs Ready for Scientific Discovery? A Capability-Oriented Benchmark for AI Scientists
    url: https://arxiv.org/abs/2607.11079
  - title: AutoScientists: Self-Organizing Agent Teams for Long-Running Scientific Experimentation
    url: https://arxiv.org/abs/2605.28655
  - title: AutoScientists Code
    url: https://github.com/mims-harvard/AutoScientists
  - title: AutoScientists Project
    url: https://autoscientists.openscientist.ai
  - title: Biomni Science article
    url: https://doi.org/10.1126/science.adz4351
  - title: Biomni preprint
    url: https://pmc.ncbi.nlm.nih.gov/articles/PMC12157518/
  - title: Biomni Code
    url: https://github.com/snap-stanford/biomni
  - title: Biomni Project
    url: https://biomni.stanford.edu/
  - title: FlowSearch: Advancing deep research with dynamic structured knowledge flow
    url: https://arxiv.org/abs/2510.08521
  - title: InternAgent Code
    url: https://github.com/InternScience/InternAgent
  - title: Scientific computing in the age of agentic AI
    url: https://openai.com/index/scientific-computing-agentic-ai/
  - title: Scientific computing in the age of agentic AI: an exploratory field report
    url: https://cdn.openai.com/pdf/scientific-computing-in-the-age-of-agentic-ai-an-exploratory-field-report.pdf
  - title: AI as a Scientific Collaborator
    url: https://cdn.openai.com/pdf/f4b4a5da-b2de-418d-9fcd-6b293e9dc157/oai_ai-as-a-scientific-collaborator_jan-2026.pdf
---
# AI 科学家资料核验与系统启发
## 核验结论
五个 arXiv ID 均真实存在，均可取得 PDF 和源文件；用户给出的第五篇是省略副标题的简称。`2607.17100` 应引用 2026-07-29 修订的 v2。
`2608.05179`《Autonomous Research Agents: A Survey of AI Scientists and the Verification Gap》；Tianyu Ding、Aditya Nannapaneni、Bingfan Liu、Ling Zhang；v1 提交于 2026-06-29；arXiv HTML、PDF、源文件均可用。
`2607.09195`《Toward Auditable AI Scientists: A Hypothesis Evolution Protocol for LLM Agents》；Izumi Takahara、Teruyasu Mizoguchi；v1 提交于 2026-07-10；arXiv HTML、PDF、源文件均可用。
`2607.17100`《Auto Research for Materials: Auditable AI-Scientist Workflows with Held-Out Transfer》；Jingjie Ning、Xiaochuan Li、Shanshan Zhong、Ji Zeng、Guolin Ke；v2 修订于 2026-07-29，v1 提交于 2026-07-19；当前 HTML、PDF、源文件均为 v2。
`2607.11084`《NVAITC AI Scientist: A Governed End-to-End Research System - A Hypertension GWAS Case Study》；Eddie Huang、Ken Liao、Iven Fu、Yang-Hsien Lin、Chao-Shun Zhan、Andy Liao、Virginia Chen、Johnson Sun、Pika Wang、Richard Huang、Jiun-Cheng Jiang、Ting-Yuan Liu、Hsing-Fang Lu、Ray Y. Lee、Chi-Chou Liao、Simon See、Fuu-Jen Tsai；v1 提交于 2026-07-13；arXiv HTML、PDF、源文件均可用。
`2607.11079`《Are LLMs Ready for Scientific Discovery? A Capability-Oriented Benchmark for AI Scientists》；Chuhan Shi、Xiaoquan Ren、Sicheng Song、Haobo Li、Rui Sheng、Yushi Sun；v1 提交于 2026-07-13；arXiv PDF、源文件可用，标题中的副标题不能省略以免与其他工作混淆。
## 论文要点
### Verification Gap Survey
论文从 arXiv、Semantic Scholar、OpenReview 和 ACL Anthology 检索 2023 年至 2026 年 6 月的 12 组查询，144 条记录去重为 125 条，筛入 35 条，最终对 26 条全文编码，其中 24 个可运行系统、2 个研究或立场文；编码维度包括生命周期、自治程度、评测、发布产物、人工介入、创新验证和结果选择披露。单人阅读全文和代码，第二位编码者只对随机 10 条摘要复核；产物发布一致率 90%，自治 50%、创新验证 60%、选择策略 60%，所以后几项比例只能作方向性证据。
24 个可运行系统中 83% 发布代码，38% 发布种子或轨迹，38% 说明创新验证方法，88% 说明人工介入点，67% 披露尝试与结果选择策略。9 个 L4 闭环系统中 7 个只有机械重跑，1 个声称无外部检查，1 个使用外部物理 oracle；语料中的 LLM 时代系统没有在闭环内使用外部验证 oracle。论文建议把基线来源、评审独立性、预注册假设、每次尝试与选择规则、工具调用和模型版本写进可审计记录。
对本项目的直接启发是把“能重跑”与“能证明主张”分开：入图审核应记录人工介入、独立审核者、种子、提示、工具调用、模型和选择策略；审查视图应优先显示缺失的外部验证和下游影响，而不是把仓库链接当作复现证据。该论文自身是中期预印本，范围偏可检查的 AI/ML 系统，不能代替领域实验验证。
### Hypothesis Evolution Protocol
HEP 将假设做成追加写入的事件溯源注册表：每个假设有系统 ID、陈述、带理由的信念值、生命周期和来源；每次证据、状态转移和信念更新都追加并带作者及哈希链，当前状态由回放得到。工具分为提出、转移、附证据、查询、细化和合并；生成机制为 de-novo、inspired-by、refine、merge。未取得 verdict 或证据的假设不能产生 refine/merge 后代，生命周期为 proposed、under_test、supported、refuted、dormant。
证据区分 simulation、experiment、literature、derivation、analysis 及 supports/refutes/inconclusive；代理必须为计算或分析证据声明设置与结果可信度，未认证的附证据仍保留但不能移动信念。实验覆盖 AO2 二氧化物、双钙钛矿和 MX 化合物三个材料问题；每题约 10-20 个假设，AO2 示例 16 个假设、四种生成机制均被使用，最终合并假设信念值 .97。与同目标规划 Agent 比较时，基线使用了 83% 的测试步骤却没有信念更新，HEP 的 H→T、T→E、E→B、B→J、J→U、U→T 转移率分别为 .85、.58、.78、.40、.22、.65；结论规则在未见组合物上作了预测。
可落地的是持久化假设和证据事件，以及“未测试不得派生”的依赖门；不应直接复制 .8/.2 阈值或把代理自评当独立审核。论文是单代理、固定 MLIP 的材料实验，证据和有效性由同一代理附加，作者明确提出未来需要独立审核者和程序化检查。
### Held-Out Transfer
Auto Research 将研究拆成 Feature、Model、Representation、Data 四个可编辑轴；每个 campaign 只在一个轴上提议、编辑和评估，内层统一用五折反馈。选定代码、配置和哈希冻结后，外层 holdout 矩阵一次性评价基线和所有冻结干预，代理不能读取外层标签；主要指标是选择 regret、成对排序、覆盖广度和兼容性，而非终端流水线分数。
七个 campaign 覆盖十个 Matbench 端点，共 701 次尝试，699 次有分数；每个 campaign 最多 100 次尝试。内层选择在 10 个端点中的 9 个也是外层最佳，平均 regret 0.228 个百分点，成对排序一致率 89.3%，但二维剥离任务和 Structure Representation 显示内层收益可能在外层反转。Feature 与 Model 的确定性组合在六个结构端点均改善，外层平均提升 26.3%，但官方全五折回放属于复用搜索池的事后上下文，不能当独立验证。
对 SearchBench/AuditBench 的启发是冻结行动代码、配置、输入边界和产物哈希，独立保存隐藏标签和 scorer，报告选择可靠性、排序一致、覆盖与兼容性；评测“选中了什么”比只看最后一个分数更接近审查带宽问题。该工作只覆盖 Matbench/CPU 任务、一个 holdout 切分和有限干预轴，不能外推为一般科研发现验证。
### NVAITC Governed System
NVAITC 的执行层将 proposal readiness、持久运行状态、GPU 容器或 Kubeflow broker 分开。治理接口只允许 SQL 队列提取、模式发现、队列提交与汇总产物读取，返回行数、分组、缺失率、数值统计、QC、执行摘要和图表，不返回原始行、ID 或 PHI；状态保留容器选择、代码、broker ID、日志、指标、修复记录和稿件片段。18 次生产 proposal review 共发现 852 个缺陷，其中遗漏 414、未标新内容 216、结构 85、含糊 68、JSON 37、幻觉或捏造 27、事实矛盾 5。
高血压 GWAS 案例使用去标识化的 286422 人数据，团队人工核对表型定义；3950 人出现诊断和测量不一致，其中 2911 人有高血压测量但只有 125 人有用药记录，人工决定排除或协调。代理最后复现 FGF5、ATP2B1、CNNM2、FTO、GRB14 等已知位点，编码错误还曾静默排除全部样本，后由代理发现修复。结果是复现与治理演示，不是新发现；论文限制包括单机构、无独立复制、只从 Manhattan 图读取显著性、DILI 子实验过小、proposal 样本少和 FP16 变化。
可复用的是“受限数据通道 + 持久运行清单 + 人工表型/主张裁决”：图谱节点只接收聚合证据和 manifest，执行 Agent 不能直接接触隐藏目标或原始敏感数据；执行治理证据与科学主张证据分开，不能把 broker 成功或格式通过标作结果审核。
### SDABench
SDABench 将科学分析能力拆成 descriptive、exploratory、inferential、predictive、causal、mechanistic 六类，覆盖 Biology、Chemistry、Environment、Geography、Physics 五域；数据为 527 个真实样本和 6000 个经过筛选的合成样本，题型有选择题和开放题。合成数据由语义 DAG、因果子图、结构方程、固定种子和干扰变量生成，经回放、范围检查、专家审核、模板人工审计和选项唯一性过滤；真实数据保留为独立评测来源。
15 个模型的结果显示 descriptive 最强，inferential/causal 较弱，exploratory/predictive 和开放式 mechanistic 更难。论文把错误定位到 Scope、Variable、Function、Relationship、Conclusion 五个阶段，指出强模型主要减少范围和变量错误，函数、关系和结论错误仍存。合成 DAG 可能缺少真实混杂和测量伪影，选择题可能诱导模式匹配，首错标注会低估级联错误，且只评分答案，不验证代码、执行和科学主张。
对项目只复用“按阶段诊断”的评测视图和真实留出集，不把五类错误写成产品全局 taxonomy；图谱仍只保存行动、证据、执行和审核事实，阶段指标由评测查询派生。
## 系统资料
### AutoScientists
`AutoScientists: Self-Organizing Agent Teams for Long-Running Scientific Experimentation`（arXiv:2605.28655，2026-05-27，Shanghua Gao、Ada Fang、Marinka Zitnik，Harvard）实现无中央编排器的长期团队。共享状态包含 champion、实验日志、论坛、队列、死路登记和假设；分析 Agent 提议，实验 Agent 执行，失败也公开；第二随机种子复查改进，连续无提升触发再讨论，最终输出 champion、model card、研究结果和 dead-end registry。BioML-Bench 平均 percentile 74.4，对照 Autoresearch 66.07；蛋白任务 ACE2-Spike 从 .747 到 .840，但论文的生物医学结果仍要求专家和独立验证。
其可借鉴点是把失败路线和实验讨论公开成可查询记录，并把 recheck 作为结果审核事件；无 analyst、无跨 Agent、无自组织的消融均明显退化。它仍使用更多 token、团队规模固定且在单张 H100 上运行，不能证明自组织图谱天然可审计；blind/reflect 分离与入图审核仍需由本项目实现。
### Biomni
Science 论文题为 `Autonomous biomedical research with an artificial intelligence agent`，DOI `10.1126/science.adz4351`，2026-07-09 发表；公开预印本 `Biomni: A General-Purpose Biomedical AI Agent`（bioRxiv，2025-06-02）和 Stanford 网站、代码仓库可用。环境 Biomni-E1 从 25 个生物医学领域的近年论文抽取动作，经专家和测试用例验证，包含 150 个专用生物医学工具、105 个软件包和 59 个数据库；这不是“105 个工具 + 59 个数据库”。Biomni-A1 通过检索选资源，以代码作为动作接口，边执行边改计划。
预印本基准使用 LAB-Bench 留出测试 315 题、SeqQA 以及 HLE 52 题；DbQA 74.4%、SeqQA 81.9%、HLE 17.3%，八类真实任务相对基线平均提升 402.3%，相对直接代码 Agent 提升 43.0%，平均每任务执行 6-24 步。案例覆盖 458 个可穿戴传感器文件、单细胞和多组学分析以及 10 个真实克隆任务。限制是任务只覆盖领域子集，近期文献抽取会遗漏基础方法，临床判断、新实验推理和深层生物综合仍弱；基准与案例报告也不能替代独立实验复现。
可复用的是工具登记的测试用例、容器环境、结构化研究日志和按任务检索资源；不应把大规模工具清单直接写进全局上下文。每个工具应有版本、输入边界、测试结果、输出 provenance 和失败记录，工具调用产物先过执行审核再进入图谱。
### FlowSearch
`FlowSearch: Advancing deep research with dynamic structured knowledge flow` 的正确 arXiv ID 是 `2510.08521`，v1 提交于 2025-10-09，v2 修订于 2026-01-11；v2 作者为 Yusong Hu、Runmin Ma、Yue Fan、Jinxin Shi、Zongsheng Cao、Yuhao Zhou、Jiakang Yuan、Shuaiyu Zhang、Shiyang Feng、Xiangchao Yan、Shufei Zhang、Wenlong Zhang、Lei Bai、Bo Zhang。项目代码为 InternAgent，论文使用动态 DAG，节点类型为 search、solve、answer，planner 增长图，collector 并行执行，refiner 依据中间结果增删改节点和边；InternPlanner 用 10000 个结构化 flow 示例微调。
在 GAIA、GPQA、HLE 和 TRQA 等深度研究问答上，o4-mini 的 GAIA 平均 76.96、GPQA 87.37、HLE 30.80，带 refiner 的结果高于顺序基线。它证明的是任务规划和图式并行对问答有用，不是科学主张审核；节点和边由 LLM 修改，来源、独立性、可复现性与入图门仍未解决。对项目只借鉴 DAG 展开、依赖子图和中间结果可见性，图 UI 的状态、计数和失效传播必须从图谱查询确定性派生。
### OpenAI 科研工程案例
用户所说的“AI 科研工程师报告”对应 OpenAI 2026-07-28 的 `Scientific computing in the age of agentic AI` 及 55 页 `an exploratory field report`，不是机器之心文章本身。报告收录 8 个早期代码 Agent 案例，包含将 STAR 比对器重写为 Rust 的 rustar-aligner、MHCflurry PyTorch 重写、RustQC/FastQC-Rust、hifiasm、cyvcf2、bayesm-rs 和 HI.SIM。rustar-aligner 在 10000 条酵母 RNA-seq reads 上报告单端 99.815%、双端 99.883% 一致率；RustQC 报告 1.86 亿条 reads 从 15 小时 34 分降至 14 分 54 秒，磁盘从 2.5 TB 降到 0.1 TB。
这些数字由案例贡献者提供，报告作者做了一致性检查并尽量选取公开产物，但没有独立复现每个基准。可复用的验收模式是外部参考输出、字节或统计一致性、已知答案模拟、固定容差和真实数据边界测试；同时保留代码、环境、日志、产物哈希和维护责任，不能用 Agent 自报成功替代独立结果审核。OpenAI 另有 `AI as a Scientific Collaborator` 使用报告，讨论科学类消息和任务分布，不是上述 Rust 工程证据。
## 对项目的落地
1. 为假设增加系统 ID、状态、父子来源、证据和事件哈希；只允许通过审核的证据移动状态，未测试假设不得产生依赖后代，`dormant` 与 `refuted` 保持可查询。
2. 保持机制重合、执行有效性、结果内容、人工治理四类审核独立；对代理自评、官方格式验证、任务分数和外部复现分别建证据，不合并成单一通过分数。
3. 对每个行动冻结规范化代码、配置、输入范围、随机种子和产物哈希；执行进程不能读取 hidden labels，由独立 scorer 计算 held-out 选择 regret、排序一致和影响范围。
4. 为敏感数据和高成本工具采用 broker 接口，只返回可审计聚合、QC、日志和 manifest；表型、因果解释和高风险主张进入人工队列。
5. 图谱只存事实、证据、依赖和审核事件；FlowSearch 的 DAG、AutoScientists 的 dead-end registry 和 Biomni 的工具轨迹都作为派生审查视图或可追溯事件，不写成自由文本总览。
6. 审查带宽指标加入缺失外部验证、独立审核、尝试选择策略、人工时间、Token、计算和下游失效范围；不把节点数或最终分数当阅读成本和研究价值。
## 未核验或需修正的说法
用户列出的五篇 arXiv 论文均为 2026 年提交，但“全是 2026 年最新工作”不是稳定事实；FlowSearch 是 2025 年 v1、2026 年 v2，Biomni 的公开预印本是 2025 年而 Science 正式论文为 2026 年。
“Biomni 整合 105 个科研工具 + 59 个专业数据库”不准确；原文是 150 个专用生物医学工具、105 个软件包、59 个数据库。
“Harvard AutoScientists”可理解为作者和项目所属机构线索；可核验的是论文、Harvard 作者、公开代码和项目站点，不能把二手报道中的产品规模或长期能力当成独立证据。
“上海 AI Lab FlowSearch”的精确 ID 是 `2510.08521`；论文与 InternAgent 仓库支持项目身份，10 000 条是结构化 flow 示例，不等于已验证的科学任务数据集。
“OpenAI 的 AI 科研工程师报告”应写为 OpenAI 官方 field report；其中工程基准主要是贡献者报告，未被报告作者逐项独立复现。机器之心、量子位、智东西报道和招聘帖只作为检索线索，本清单没有把它们当一手证据；北京 AI4S 政策与个人招聘信息也未在本次资料中核验。
