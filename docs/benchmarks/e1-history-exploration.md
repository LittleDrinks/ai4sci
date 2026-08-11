---
status: planned
sources:
  - title: "MOOSE-Chem: Large Language Models for Rediscovering Unseen Chemistry Scientific Hypotheses"
    url: https://proceedings.iclr.cc/paper_files/paper/2025/hash/51fd9a7d1706023cb9f8210cc6ac357c-Abstract-Conference.html
    role: primary published trajectory bank and evaluator; no direct history-access ablation
  - title: "ScienceAgentBench: Toward Rigorous Assessment of Language Agents for Data-Driven Scientific Discovery"
    url: https://proceedings.iclr.cc/paper_files/paper/2025/file/f12b4df26344f3be803c06b555252efe-Paper-Conference.pdf
    role: execution-failure replication; no matched history-access ablation
  - title: "Dictionaries, Not Darwin: Set-Level Selection Beats LLM Evolution in Scientific Equation Discovery"
    url: https://arxiv.org/abs/2607.04108
    role: adjacent evidence for fresh sampling versus parent-conditioned search
  - title: "Mutation Without Variation: Convergence Dynamics in LLM-Driven Program Evolution"
    url: https://arxiv.org/abs/2606.05408
    role: adjacent evidence for lineage convergence
  - title: "AutoScientists: Self-Organizing Agent Teams for Long-Running Scientific Experimentation"
    url: https://arxiv.org/abs/2605.28655
    role: counterevidence that shared failure summaries can reduce duplicate work
  - title: "InnovatorBench: Evaluating Agents' Ability to Conduct Innovative LLM Research"
    url: https://arxiv.org/abs/2510.27598
    role: deferred functional validation after strategy selection
artifacts:
  - path: datasets/Checkpoints_MSC.zip
    role: MOOSE-Chem frozen rejected-route bank and official evaluation inputs
  - path: datasets/scienceagentbench_*_UPLOAD.zip
    role: ScienceAgentBench published agent traces and verifier results
  - path: datasets/hal-decrypt.sh
    role: ScienceAgentBench trace decryption
---
# E01 失败历史与探索策略（C1、C2）
## 裁决目标
| 实验 | 问题 | 能支持的结论 |
|---|---|---|
| E01a | 生成前看到本任务的具体被拒路线，是否比同长度无关历史更容易复现旧路线并减少新路线？ | 具体失败历史是否造成锚定或探索锁死 |
| E01b | 哪种历史访问策略能减少旧路线复现，同时不降低候选质量？ | 盲创、图谱匹配、最小阻断与反思如何组合 |
MOOSE-Chem 的 Matched Score（MS）衡量候选与隐藏论文假设的匹配，不等于实验可行性或科学真伪。ScienceAgentBench 衡量程序执行与任务完成，不等于科学原创性。结论限于“路线复现、路线覆盖和既有 verifier 质量”。
## 操作定义
- 新根生成：只读取任务、约束和统一文献包，不读取候选祖先或失败历史；每次使用新会话。
- 谱系生成：读取上一候选或其祖先后继续修改；是否要求“brainstorm”不改变其谱系属性。
- 路线：解决问题所依赖的材料、机制和方法组合；措辞变化不构成新路线。
- 图谱匹配：候选生成后，再判断其是否与任一被拒路线同机制；生成器不可见匹配过程，除非策略明确把结果送入反思会话。
- 抽象阻断：只保留失败违反的约束、适用范围和修复目标，删除材料名、方法名、候选文本和路线顺序。
## Frozen failure bank
统一使用 MOOSE-Chem `gpt4/corpus_300/survey_1/gdthInsp_0/roundInsp_1/intraEA_1/interEA_1/beamsize_15` 的 51 组生成与评分文件。候选满足以下条件才可成为被拒路线：automatic MS≤2、四维平均分≥3、生成—批评—修订—裁决链完整。三失败条件的三条路线使用不同 ancestry signature；单失败条件使用其中第一条，形成嵌套剂量。
归档预检中，47/51 个任务至少有一条 MS≤2 候选，40/51 至少有三条；完整轨迹和 ancestry 去重后再冻结最终 eligible set。冻结文件记录 task、route ID、原始轨迹、MS、四维分、裁决理由、ancestry、token 数与内容哈希。任何新生成开始后不得更换路线或阈值。
所有生成器可见版本都删除 ground truth、ground-truth inspiration、MS 和 MS 评分理由，只保留 `rejected` 标签；这些字段仅供离线选样、评分和审计。Abstract blocker 只从原生成轨迹中的 critic feedback 抽取；第二个盲化模型检查其中是否残留具体实体或方法，残留则该路线退出 bank，不重抽。Concrete digest 只含最终候选、具体路线摘要和 `rejected` 标签。Full route 含该路线的全部候选、推理、原始批评、修订和 `rejected` 标签。
路线匹配器在新实验前冻结。校准集以同 ancestry 的相邻修订为正例，以不同 ancestry 的同任务候选为 hard negative，并加入跨任务负例。两个不同模型家族独立输出 `same/different`；主分数取两个二元判断的均值，严格合议结果作敏感性分析。校准集 balanced accuracy<0.80 或 Cohen's κ<0.60 时不运行主实验。
## E01a：具体失败历史是否锁死探索
### 条件
| 条件 | 生成前输入 | 作用 |
|---|---|---|
| Blind | 无失败历史 | 生态基线 |
| Length control | 其他主题的完整被拒历史 | 与 Full route 精确匹配 token 数、消息角色和位置，隔离输入长度与“读历史”本身 |
| Abstract blocker | 本任务的路线无关阻断 | 测试能否保留教训而不暴露具体方向 |
| Concrete digest | 本任务的具体路线与裁决摘要 | 测试具体方向而非长对话的影响 |
| Full route | 本任务的完整被拒轨迹 | 被检验的全量失败经验策略 |
除 Blind 外均跑 1 条和 3 条失败两种剂量。每个 task×condition×seed 独立生成 6 个候选；六次调用互不读取彼此输出。任务包、模型、采样参数、输出 schema、最大输出 token 与调用数相同。只有 Full route 与 Length control 宣称输入 token 匹配；其他条件原样报告披露 token，不填充伪造等长上下文。
Length control 从不同主题任务中按 token 长度配对，保持相同消息角色序列，末条消息在 tokenizer token 边界截断到 Full route 的精确 token 数；不得包含本任务实体。任务包不含 ground truth、MS、官方评分理由或评测器输出。
### 运行
单失败与三失败共同使用最终三路线 eligible set，避免剂量间任务构成变化。主实验使用 `gpt-5.4-mini`、2 seeds、全部 eligible tasks 和 9 个条件：Blind 1 组，其余 4 种表示各含 2 个剂量。相同 task×seed 在各条件间配对，合计 `eligible tasks×9×2×6` 次生成调用。核心三组 Blind、Length control、Full route 随后在 `gpt-5.6-luna` 上复跑；两模型方向不一致时，C1 只能写成模型条件效应。
### 指标
- Primary：被拒路线复现率。所有条件都对同一 task 的冻结目标路线计分，即使 Blind 与 Length control 没看到它们；主分数为全部 `candidate×target route` 配对的同机制判断均值，避免三路线条件因匹配机会更多而机械升高。命中任一路线的候选比例另报。
- Co-primary：新路线覆盖，即 6 个候选中不匹配该 task 三条冻结目标路线且彼此不同的路线数。
- Quality guardrail：官方 Top MS、四维平均分与 validity 分；官方 evaluator 对实验条件盲化。
- Cost：输入/输出 token、首次新路线调用数、每条新路线调用数。
### 预注册比较
主比较为 `Full route - Length control`，分别报告 1 条和 3 条剂量。`Full route - Blind` 只表示完整系统效果，不能排除长度干扰。Abstract blocker 与 Concrete digest 用于定位“抽象教训、具体路线、完整对话”哪一层造成差异，不替代主比较。
以 task 为聚类单位做 10,000 次 paired bootstrap；候选不是独立样本。报告均值差、95% CI 与每任务散点，不按候选数量放大样本量。
### 裁决
- 锚定成立：Full route 相对 Length control 的复现率差 95% CI 下界>0。
- 探索锁死成立：锚定成立，且新路线覆盖差 95% CI 上界<0。
- 三失败效应大于单失败只比较归一化后的每路线复现率，作为剂量证据，不作为锁死成立的必要条件。
- Full route 与 Length control 无差异时，C1 不成立；Full route 更少复现旧路线时，失败历史对该模型是有益信息。
- 只有 Full route 与 Blind 有差异时，结论是长上下文负担，不能归因于具体失败路线。
## E01b：失败后采用哪种策略
E01a 未发现锚定时停止“缓解锁死”验证；E01b 只能另立为探索效率比较。E01a 发现锚定后比较以下策略。
### 固定预算
每个 task×arm×seed 恰好 6 次生成调用和至多 1 次选择调用。所有生成候选都进入复现率、覆盖与 Top MS 统计；策略最终提交的候选另报 Selected MS。选择器不可见 ground truth、官方 MS 与实验条件，只能读取候选、任务、图谱匹配和统一四维审核。
### 对照组
| 策略 | 六次生成如何使用历史 | 选择方式 |
|---|---|---|
| Blind | 6 个相互独立的新根 | 图谱盲化选择器 |
| Full-reflect | 从冻结失败路线开始；每轮读取完整失败库和上一候选后修订 | 图谱盲化选择器 |
| Full+novelty | 与 Full-reflect 相同，另明确要求更换机制家族 | 图谱盲化选择器 |
Full+novelty 检验一句显式提示能否解决问题；若能，不需要用结构隔离解释收益。
### 候选策略
| 策略 | 生成与匹配流程 | 被检验的设计 |
|---|---|---|
| Blind+discard | 生成新根；匹配被拒路线则丢弃；下一调用仍为新根，不披露失败内容 | 只用图谱做提交门控 |
| Blind+blocker | 生成新根；匹配后在新会话中只给当前候选和一条抽象阻断，修订一次；修订后回到新根 | 最小信息触发反思 |
| Abstract-memory | 每个新根在生成前读取全部抽象阻断，不读取具体路线 | 提炼经验后再盲创 |
| Blind-batch+selector | 先生成 6 个独立新根；图谱感知选择器排除旧路线并按有效性和批内多样性选候选 | 生成与历史彻底隔离 |
Blind+discard 与 Blind-batch+selector 的区别是前者只做逐候选拒绝，后者在完整盲创批次上联合去重和选择。Blind+blocker 的修订调用计入 6 次预算，且同一候选最多修订一次，防止重新形成无限反思链。
随机历史删除只作机制诊断：Full-reflect 从三条冻结路线中分别保留 0、1、2、3 条，1 条和 2 条各使用 3 个预先冻结的随机 mask。它不参与策略选择；若复现率不随具体路线暴露量变化，不把相关性解释为历史剂量效应。
### 两阶段运行
Development：eligible set 按冻结前的 baseline Top MS 分层，再以固定哈希选 10 个任务；`gpt-5.4-mini`、1 seed、全部 7 组。四个候选策略先按 `Top MS相对Blind≥-0.25` 过滤，再依次按更低复现率、更高新路线覆盖、更少 token 排序，最多选 2 个。少于 2 个合格时不补入失败策略。
Confirmation：其余 eligible tasks、2 seeds；固定运行 Blind、Full-reflect、Full+novelty 和 development 选出的至多 2 个策略。提示、匹配器、选择器、阈值和排序规则全部冻结。随后在 `gpt-5.6-luna` 上只复跑 Blind、Full-reflect 和胜出策略；不重新选策略。模型间方向不一致时，结论限定到模型家族，不写成系统通则。
### 成功标准
候选策略相对 Full-reflect 同时满足：复现率下降的 95% CI 上界<0，新路线覆盖上升的 95% CI 下界>0；相对 Blind 的 Top MS 非劣，差值 95% CI 下界>-0.25。Selected MS、validity 和 token 成本决定满足条件策略间的最终选择。
Full+novelty 与胜出结构策略在复现率、覆盖、Top MS 上等效时，不支持“必须隔离失败历史”的架构主张。Full-reflect 不比 Blind 差时，不支持默认采用 blind-first。所有策略均损害 Top MS 时，保留 Full-reflect 并否决当前四种替代方案。
## 外部验证
ScienceAgentBench 单列 execution-failure stratum：从公开 trace 抽取每轮中间程序，以官方 verifier 离线重放，只纳入至少 3 次连续 `success=0` 且程序与执行反馈完整的任务；复跑 E01a 的 Blind、Length control、Abstract blocker 与 Full route。主质量指标改为官方 success、valid program 和 CodeBERT score；结果不与 MOOSE-Chem 合并。
InnovatorBench 只在 E01b 得到胜出策略后验证最终功能收益，不参与开发、阈值选择或首轮结论。其 2–36 小时任务成本不用于证明 E01a 的历史锚定。
