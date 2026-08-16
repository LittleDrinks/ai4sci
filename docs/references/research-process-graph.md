---
sources:
  - title: "Micropublications: a semantic model for claims, evidence, arguments and annotations (Clark, Ciccarese, Goble 2014)"
    url: https://pmc.ncbi.nlm.nih.gov/articles/PMC4530550/
  - title: "The SWAN biomedical discourse ontology (Ciccarese et al. 2008)"
    url: https://pmc.ncbi.nlm.nih.gov/articles/PMC4536833/
  - title: "Nanopublication Guidelines / Anatomy (Groth et al.)"
    url: https://nanopub.net/guidelines/working_draft/
  - title: "SEPIO ontology (Monarch Initiative)"
    url: https://github.com/sepio-framework/sepio-linkml
  - title: "Discourse Graphs for Augmented Knowledge Synthesis (Joel Chan)"
    url: https://joelchan.me/assets/pdf/Discourse_Graphs_for_Augmented_Knowledge_Synthesis_What_and_Why.pdf
  - title: "学术话语本体综述 (Ruiz-Iniesta, CEUR-WS 1155)"
    url: https://ceur-ws.org/Vol-1155/paper-07.pdf
  - title: "Toward Auditable AI Scientists: Hypothesis Evolution Protocol (Takahara, Mizoguchi 2026)"
    path: Zotero AA2UBMVL（科学发现与跨领域应用）
  - title: "The Last Human-Written Paper: Agent-Native Research Artifacts (Liu et al. 2026)"
    path: Zotero I2YBY654（AI4Science/AI4S）
  - title: "ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration (Yang et al. 2026)"
    path: Zotero TRYPRM7J（AI4Science）
  - title: "From Trajectories to Evidence: Auditable Experimental Records (Zhuang et al.)"
    path: Zotero（科学发现与跨领域应用）
  - title: "Workflow Cards: Structured Summaries of Workflow Executions Using Provenance Data (Marchioro et al.)"
    path: Zotero
  - title: "F(AI)²R: Who Did What, and Who Checked? (Krebs)"
    path: Zotero
  - title: "From Plan to Action: How Well Do Agents Follow the Plan? (Liu, Dehghan et al.)"
    path: Zotero
  - title: "LivePlan: Online Monitoring and Corrective Steering of Programming Agents (Liu et al.)"
    path: Zotero
  - title: "Stop Anthropomorphizing Intermediate Tokens as Reasoning Traces (Kambhampati et al.)"
    path: Zotero
  - title: "Interpretable Traces, Unexpected Outcomes (Bhambri et al.)"
    path: Zotero
  - title: "Sharding Prevents LLM Oversight Failures"
    path: Zotero
  - title: "Agentic Harness Engineering (Lin et al.)"
    path: Zotero
  - title: "TRACE: Trajectory Attribution for Automated Context Engineering (Zhao et al.)"
    path: Zotero
  - title: "Towards an AI co-scientist (Google, Nature 2026)"
    path: Zotero PMQ38NSP
  - title: "Red Queen Gödel Machine: adversarial reviewer drift on AI-generated text"
    path: Zotero
  - title: "AI Research Agents Narrow Scientific Exploration (219k-idea empirical)"
    path: Zotero 24W86TAE（arXiv:2605.27905）
  - title: "EvoScientist: memory of failed directions"
    path: Zotero 26YJUMP5（arXiv:2603.08127）
  - title: "Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity"
    path: Zotero AIELSLBM（arXiv:2510.01171）
  - title: "What Is Novel? Bias-Aware Literature Originality Evaluation"
    path: Zotero LULT2GFW
  - title: "GraphMind: Interactive Novelty Assessment System"
    path: Zotero 4B69JY2E
  - title: "DivAlign: MMR-style de-homogenization for ideation"
    url: https://arxiv.org/abs/2607.28087
  - title: "Can LLMs Generate Novel Research Ideas? (Si et al., dedup threshold 0.8)"
    url: https://arxiv.org/abs/2409.04109
  - title: "SciMON: Scientific Inspiration Machines Optimized for Novelty (rewrite threshold 0.6)"
    url: https://arxiv.org/abs/2305.14259
  - title: "Chain-of-Ideas / Idea Arena (pairwise LLM judge ~70% agreement)"
    url: https://arxiv.org/abs/2410.13185
  - title: "Doshi & Hauser: AI assistance lowers collective diversity (Science Advances 2024)"
    url: https://doi.org/10.1126/sciadv.adn5290
---
# 研究过程图谱：节点类型与审查界面
## 节点类型
- result 不独立成节点。无一主流系统把它当一阶知识节点：工作流传统（Kepler/AiiDA/Nanopub）把它作为 experiment 的产出负载或 provenance 数据节点。
- claim 有两派：论证建模派独立成类（SWAN 中 hypothesis/claim 为兄弟节点，靠证据强度升格；Micropub/Nanopub 以 claim 为唯一内容节点）；agent 工作流派并入 hypothesis 加信念状态（HEP 的 hypothesis–test–evidence–belief 循环、Co-Scientist、EvoScientist）。本系统是工作流系统，取后者：direction 带 proposed→supported/refuted 状态机，但必须承载完整证据链——ARIS 诊断的核心失败模式正是 claim 证据不完整被静默继承（plausible unsupported success）。
- 边类型必须带 supports/refutes 极性，否则证据图退化为引用列表（IBIS、SWAN）。
- 固定少类型优于开放 taxonomy：学术话语本体有十几个（SWAN/SALT/EXPO/CiTO…），互相重叠、采用率极低；LLM 自由生成分类产生噪声。SEPIO 模式可抄：固定骨架 + 受控扩展点。
- 被拒假设与失败实验必须留在 exploration graph（ARA 的 Storytelling Tax：线性叙事丢弃失败分支）；每条结论 grounding 到原始输出。
## 审查界面
- 原始轨迹/CoT 不能当审查界面：可验证正确的 trace 只有 28% 导向正确答案（Bhambri）；中间 token 不是可信推理窗口（Kambhampati）；可监控性是条件属性，压力下模型会主动降低它（MonitorBench）。展示层必须是结构化派生物。
- 渐进披露的已验证形态：轨迹蒸馏为分层可 drill-down 的证据语料（AHE 的 experience observability）；provenance 压成人与 LLM 都可读的结构化卡片（Workflow Cards）。
- 判建议分离：确定性规则监控器扫漂移/重复失败信号，命中才升级 LLM 或人（LivePlan，$0.08/实例）；plan compliance 本身可度量，周期性计划提醒缓解偏离（From Plan to Action，21120 条轨迹）。
- 审查必须分片：一次调用判多个维度的 verdict 会让部分判定失去证据 grounding；按维度分片显著提升与专家的一致率（Sharding，研究复现/法律/临床三域验证）。
- claim 资格化：每条结论必须有 parent（no parentless claim，F(AI)²R）；不够格的标 withheld finding 保留为带来源与适用边界的可审记录（Trajectories to Evidence）；拒绝 unsupported closure（Matrix）。
- 失败是一等公民：失败归因到 context 组件或具体 step（TRACE，96% 操作准确率）；失败分解为 regression vs residual（Regression Tax）。
## 假设评审与搜索空间
- direction 相近判定两档阈值：embedding 余弦 >0.8 判重合（Si et al. 数千 idea 人评验证的工程阈值），转 reflect/合并；0.6–0.8 灰区交 LLM 成对比较（与人一致率 ~70%，Chain-of-Ideas Idea Arena）；<0.6 视为新方向。纯 LLM 自由判定 novel/not-novel 不可靠（AI Scientist v1 有独立复现的负面证据）。精判可升级概念级对比（What Is Novel 的 idea/method/claim 结构 + 概念相似图；EvoScientist 区分 Component/Architectural novelty）。阈值源自 NLP 语料，跨学科需自校准。
- 多样性必须显式机制，prompt 要求"novel"无效：219,655 个 idea 实证更复杂框架与更大模型均不拓广探索（Narrow）；AI 辅助提升个体创造力但降低集体多样性（Doshi & Hauser）。入池用 MMR 贪心：score = 质量分 − λ·max_sim(候选, 已入池集合)，λ≈0.2（DivAlign：保留 99.9% 对齐分、最近邻相似度 0.704→0.608）；生成侧零成本叠加 Verbalized Sampling（显式概率分布采样，科研 idea 场景无实证，收益不写进设计假设）。废止 tournament/Elo：它解"相对排序"，不解"拓广搜索空间"。
- direction 评审保留两层：机械证据审计（ARIS 三阶段：证据完整性→结果-claim 映射→逐条核对，失败即驳回）+ 质量与多样性打分。双审冲突升级人，双方论点以 rebuttal 格式沉淀在节点上。同一谱系 review 反复驳回须熔断：auto 模式暂停该谱系并升级人，避免自主迭代空转。
- 评审者防漂移：LLM 评审对 AI 文本系统性降标准（RQGM，接收率 1.91×）；客观机械检查必须与主观打分剥离，并周期性用已知坏样本校准。
- 失败方向必须入记忆防重复踩坑（EvoScientist ideation memory 双记账）——幽灵车道的独立背书。
- 缺口：无 MCTS-on-ideas 成熟先例；无 rebuttal 协议对 idea 质量的实证；人介入最佳时机无定量研究；"换汤不换药"式技术深度重合无有人评背书的自动判定方法。
## 未读缺口
sensemaking 经典（Pirolli & Card、information foraging）、增量摘要/变更报告（change summarization）、learning-to-defer 审查 triage、agent 轨迹可视化的人因评估。
