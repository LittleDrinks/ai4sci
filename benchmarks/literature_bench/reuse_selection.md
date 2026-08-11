---
sources:
  - title: AstaBench
    url: https://github.com/allenai/asta-bench
  - title: AstaBench LitQA2 source
    url: https://github.com/Future-House/lab-bench
  - title: SciFact data and code
    url: https://github.com/allenai/scifact
  - title: SciFact evaluator
    url: https://github.com/allenai/scifact-evaluator
  - title: Fact or Fiction: Verifying Scientific Claims
    url: https://aclanthology.org/2020.emnlp-main.609/
  - title: QASPER dataset
    url: https://huggingface.co/datasets/allenai/qasper
  - title: QASPER official baseline and evaluator
    url: https://github.com/allenai/qasper-led-baseline
  - title: QASPER paper
    url: https://arxiv.org/abs/2105.03011
---
# 文献沉淀基准复用筛选
## 首选：SciFact
SciFact 最适合做第一个“整篇文档检索 vs claim+evidence 图谱记忆”对照。它有约 1.4K 条专家改写的科学 claim、约 5K 篇科学摘要；`claims_train.jsonl` 和 `claims_dev.jsonl` 给出每条 claim 的证据文档 ID、SUPPORT/CONTRADICT 标签以及证据句子编号，`corpus.jsonl` 给出文档标题和按句切分的摘要。数据包约 3.1 MB，官方 S3 可直接下载，不需要账号或受限模型。
官方任务本身已经拆成文档检索、证据句选择和标签判断三个阶段，`doc/evaluation.md` 给出公开 evaluator 的输入格式和文档级、句子级 Precision/Recall/F1。claims/evidence annotation 是 CC BY 4.0，摘要继承 S2ORC 的 ODC-By 1.0，代码是 Apache-2.0；产品原型只需要保留数据来源与许可证记录。
最小对照应固定同一 claim、同一 corpus 和同一预算：
1. `whole_document`：检索候选摘要，向模型提供候选摘要原文，再输出文档 ID、SUPPORT/CONTRADICT 和句子编号。
2. `claim_evidence_graph`：仅向模型提供由 train claims 与 corpus 预先沉淀的 claim、evidence-sentence、document 和 SUPPORT/CONTRADICT 边；dev claim 的 gold edge、target split 标签和人工答案不能进入图谱。
3. `oracle_evidence`：直接给 gold 文档，区分“检索失败”和“推理/标签失败”。这是官方 pipeline 已支持的边界对照，不是产品能力。
用官方 SciFact evaluator 重算三组输出，至少报告文档级 F1、句子级 F1、标签准确率和输入 token；另加图谱构建 token、检索 token、图谱证据覆盖率。这样能回答图谱是否减少输入并保留可追溯证据，不能把图谱自身的预抽取质量伪装成模型能力。
## AstaBench 复用判断
### LitQA2
AstaBench 0.5.4 的 LitQA2 wrapper 可直接复用 Inspect 的 Task/Solver/Scorer。公开 LAB-Bench 数据有 199 条 LitQA2 样本，每条包含生物学论文 DOI、选择题、`key-passage` 和 `is_opensource`；完整 AstaBench 版本从 `futurehouse/lab-bench` Hugging Face 数据集读取。
官方 scorer 只计算 accuracy、coverage 和 precision；`key-passage` 是答案支持段落，但不进入 scorer 的证据句级评分。因而 LitQA2 适合测试“图谱能否找到对应文献/支持段”，不适合严格比较 claim+evidence 图谱是否保留了 gold evidence。LAB-Bench 的公开样本可直接取得，但完整 AstaBench suite 的数据与标准检索工具可能需要 Hugging Face 许可与 token；本地 smoke 不应下载全套。
### PaperFinder
PaperFinder 的 metadata/specific 分支有 Semantic Scholar CorpusID 的 gold set，要求逐篇返回论文 ID 和从论文逐字摘取的 markdown evidence，官方 scorer 对已知 gold set 计算 F1/nDCG/estimated-recall。semantic 分支没有完整 gold set，依赖 LLM relevance judge 和估计的集合大小。
它能测“检索到哪些论文以及是否给出可审查原文”，但不是一个固定文献内容问答集；semantic 评分含额外 judge 方差，PaperFinder 的 retrieval tool 还依赖 Asta 服务。保留为第二阶段端到端检索对照，不作为首个本地 benchmark。
### SQA
SQA 有 110 个公开问题实例，target rubric 包含答案长度、领域要点、引用和 evidence snippets；官方 scorer 使用 grader model 评估 ingredient recall、answer precision、citation precision/recall。它更接近研究报告审查，但评分成本高、答案判定依赖 grader model，不能作为低成本结构化证据基准。
## 备选：QASPER
QASPER 覆盖 1,585 篇 NLP 全文论文和 5,049 个问题。每个问题由只读标题/摘要的 NLP 实践者提出，答案由另一批实践者标注，数据同时给出 extractive/free-form/yes-no answer、证据段落、highlighted evidence，以及跨段落、表格和图形证据。官方 `qasper-led-baseline/scripts/evaluator.py` 本地计算 Answer F1 和 Evidence F1，且 baseline 直接支持不同 context 长度。
QASPER 比 SciFact 更贴近“整篇论文压缩为可检索证据”，也是图谱记忆的长期主基准：whole-document 组输入全文，claim+evidence graph 组只输入图谱返回的段落/表格/answer evidence，比较 Answer F1、Evidence F1、输入 token 和跨段证据覆盖。它的代价是数据规模、全文解析和多模态证据更重；官方数据托管在 Hugging Face，实际 full-text 文件不是轻量 Git checkout，先用单篇 fixture 或公开 dev 子集验证接口，再决定是否下载全量。数据集标注许可为 CC BY 4.0，baseline 代码 Apache-2.0。
## 最小运行路径
1. 复用远端 `/data/zsm/ai4sci-design-bench-20260809/astabench-smoke` 中 AstaBench 0.5.4 与 Inspect AI 0.3.233，只借用 Task/Solver/Scorer、结构化日志和有界并发；不写新的 Asta runner。
2. 首轮不接模型：从 SciFact 官方 S3 下载 `data.tar.gz`，固定 dev 的 10 条小切片，写三份符合官方 evaluator 输入格式的静态预测，先验证 whole-document、graph evidence、oracle 的计分和 token 统计。
3. 首轮接模型时沿用已有 ResearchHarness 的 OpenAI-compatible client；模型只看到当前组允许的证据。图谱构建用固定抽取结果，避免把“抽图质量”和“检索策略”混为一个变量。
4. 通过后扩到完整 dev，再做图谱构建消融：仅文档、文档+句子、claim+evidence 边；target claim 的 gold evidence 永不提前写入图谱。
## 不能回答的设计问题
- SciFact 不能证明图谱能发现新机制；它测的是已标注 claim 的证据检索和核验。
- SciFact 只提供摘要，不代表湿实验、全文表格、图像或代码证据；QASPER 才覆盖全文与多模态证据。
- 官方 scorer 只能判断预测是否命中 gold evidence，不能判断图谱节点是否足够帮助人类审查，也不能测渐进式披露的阅读时间。
- 静态图谱对照不能决定“哪些事件应该入图”；这需要 AuditBench 的入图审核和人工/独立审核者数据。
- 若图谱由 gold evidence 直接生成，会产生标签泄漏；必须分别报告固定抽取、模型抽取和 oracle 三种构建方式。
## 结论
先用 SciFact 做低成本、可复现、证据级的 graph-memory preflight；QASPER 做全文和跨段证据扩展；AstaBench 只复用外层执行与日志接口，LitQA2/PaperFinder/SQA 分别作为文献选择、开放检索和长报告的后续任务，不把它们拼成一个新 schema。
## 数据预检
远端 `/data/zsm/ai4sci-design-bench-20260809/literature` 固定 SciFact `68b98a56` 与 evaluator `66feffc`。官方 10 条 evaluator fixture 与预期指标完全一致；下载数据含 809 条 train claim、300 条 dev claim 和 5183 篇摘要。
dev 使用的 182 篇证据文档全部存在于 corpus，其中 110 篇也被 train claim 引用。train/dev 有 2 条规范化 claim 与 evidence 完全相同：`Obesity decreases life quality.` 与 `There is no association between HNF4A mutations and diabetes risks.`。正式消融先按规范化 claim+evidence 去重重切，dev gold edge 不进入图谱；共享文档可以保留，因为它模拟同一文献支持不同命题。
## 官方检索基线
SciFact 原仓库的 TF-IDF abstract retriever 在隔离依赖目录中直接运行，未修改官方代码。完整 dev、top-3 的官方 `abstract_retrieval.py` 得到 `Hit one=0.8467`、`Hit all=0.8333`；产物位于 `/data/zsm/ai4sci-design-bench-20260809/literature/scifact-retrieval`。旧仓库锁定 Python 3.7、scikit-learn 0.22.2 和 Transformers 2.7，检索层可用当前 `jsonlines`、`scikit-learn` 复现，预训练判别模型栈尚未验证。graph-memory 组必须使用相同 dev 切分和 top-3 文档预算，并以官方指标与输入 Token 同时报数。
去除两条 train/dev 精确重复后，train 中已审核的 claim-evidence 边覆盖 365 篇文档。把每篇文档关联的历史 claim 聚合为检索文本，仍用官方 TF-IDF 和 top-3，完整 dev 得到 `Hit one=0.74`、`Hit all=0.7267`。排除 112 条 NEI 后，188 条有证据 claim 的 Hit one 为 0.5851，历史图谱的理论上限为 0.5957；完整摘要语料为 0.7553。历史关系一旦存在几乎可以被检索到，主要缺口是新证据文档从未入图。图谱替代旧对话，不替代外部文献检索与新证据入图。
## 证据作用域消融
从 SciFact dev 按 ID 固定抽取 10 条 SUPPORT、10 条 CONTRADICT，标签不进入提示。每条独立审核分别只看 claim、只看该 claim 的 gold evidence、看全部 20 组 evidence；后两组使用相同 gold 事实，差别只有披露范围。
`gpt-5.4-mini` 三组为 1/20、15/20、14/20，Token 为 1828、4504、54536；`gpt-5.6-luna` 为 0/20、16/20、16/20，Token 为 2154、5241、55878。全局 evidence 没有提高准确率，消耗约 10.7–12.1 倍 Token，两个模型各出现额外 UNKNOWN 或错误矛盾。人工纠正应写成带来源、按 claim/resource 检索的图谱证据；全局 Skill 只保存审核行为，不持续累积事实正文。该消融使用 oracle evidence，只回答披露作用域，不代表自动检索已经解决。
## 外部检索升级信号
在 188 条有证据 dev claim 上，历史图谱 TF-IDF 的 top-1 相似度识别“任一 gold 文档在图中”的 AUROC 为 0.9666，识别 top-3 实际命中的 AUROC 为 0.9795；top-1/top-2 margin 的覆盖 AUROC 为 0.9047。按 top-1 分数从低到高把固定比例请求升级到完整摘要检索，0%、20%、40%、100% 升级时 Hit one 分别为 0.5851、0.7606、0.8830、0.7553。历史图谱擅长已见文献，全文检索补未见文献；全量替换会丢掉前者优势。
按 train claim ID 固定拆分 638 条构图、108 条有证据 calibration，在 calibration 选择相似度阈值 0.38294：Hit one 0.8981、回退率 0.4444。该阈值原样应用到 dev 后 Hit one 0.8830、回退率 0.4309，与 dev frontier 的最优点一致。低置信度具备触发一次有预算上限外部检索的校准信号；自动触发或人工确认待产品裁决，返回内容始终是待审证据。
