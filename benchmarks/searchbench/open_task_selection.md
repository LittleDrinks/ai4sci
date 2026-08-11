---
sources:
  - title: MLE-bench
    url: https://github.com/openai/mle-bench
    commit: 507f92e1138bb6e40dac5c6ee7a6758e6424bf97
  - title: RE-Bench
    url: https://github.com/METR/RE-Bench
    commit: 93b98062e55f6945d4a7e213a3226dd419896170
  - title: AstaBench
    url: https://github.com/allenai/asta-bench
    commit: 8fbdbbb68a73fe4a47af4ebcf1819b90b608bd36
  - title: Matbench
    url: https://github.com/materialsproject/matbench
    commit: 936176db18ca4cd7b38cbd957c017a5bac770c6b
---
# SearchBench v2 开放任务筛选
## 结论
立即可跑的首选是 Matbench `matbench_expt_gap`；带结构信息的扩展首选是 `MLE-bench/nomad2018-predict-transparent-conductors`。Matbench 提供 4604 个真实实验带隙样本、固定五折、官方记录/验证/评分接口，题面只给化学组成与目标，不指定算法。Nomad 的方法空间更丰富，但当前 Kaggle 账号尚未接受竞赛规则，官方 prepare 返回 403，不能由系统代替用户接受条款。
RE-Bench 的 `ai_rd_triton_cumsum` 作为低层执行控制项，MLE-bench 的 `spaceship-titanic` 作为最小 CPU sanity control；两者不替代材料任务。`ai_rd_fix_embedding` 虽然方法开放，但官方资源是 1 张 H100、13 CPU、100 GB 内存，当前远端只有 RTX A6000，不进入首轮。
## 选择标准
- 结果必须由公开的可执行提交和原有 grader 产生，不用语言模型直接判断“像不像成功”。
- 题面只约束目标、输入输出和预算，不规定恢复、建模或优化机制。
- 同一题面下应存在多个可解释的机制族，而不是同一算法的参数扫描。
- 最小闭环能在远端现有资源上运行，实验输出、代码和评分可留存。
## 首选：Nomad2018
### 契约
远端来源：`/data/zsm/ai4sci-design-bench-20260809/task-scout/mle-bench/mlebench/competitions/nomad2018-predict-transparent-conductors/`。
`description.md` 要求根据材料组成、空间群、晶胞参数和几何文件预测 formation energy 与 bandgap；没有指定特征工程、模型、训练策略或集成方式。`prepare.py` 用固定 `random_state=0` 从原始训练集划分公开训练和私有测试，并把几何文件按新 ID 对齐。`grade.py` 复用 scikit-learn 的 RMSLE，对两个目标取平均，结果是确定性的数值。
### 为什么适合搜索空间
候选可以自然分成：
- 只用表格列的线性/树模型；
- 组成、空间群和晶格参数的物理特征工程；
- 从 `geometry.xyz` 提取元素统计、距离或局部结构描述符；
- 多目标回归、核方法或小型神经网络；
- 不同模型和特征视角的集成。
这些分支改变的是可解释的建模机制，不是把同一个模型的学习率从 `1e-3` 改成 `2e-3`。首轮不预设 taxonomy，候选之间仍由成对审核判断是否同一机制。
### 成本和边界
- MLE-bench README 给出的数据规模为约 0.00624 GB，题目包含约 3000 个材料；公开数据下载后预计只需 CPU 和少量磁盘。
- 远端已存在 Kaggle 凭据，但本轮没有下载数据；准备动作会调用原仓库的 Kaggle 下载和 `prepare.py`，需要先接受竞赛规则并记录数据版本。
- 当前克隆没有准备好的 competition data，不能把“已具备可运行数据”误报为事实。
- MLE-bench 原生 grader 只在最终提交时评分；中间实验应由 agent 在公开训练划分上自建验证，最终提交交给原 grader。SearchBench 记录每次候选的代码、公开验证结果、最终提交和 token/运行成本。
- 私有 `prepared/private/test.csv` 和 answers 只由 grader 读取，不进入 agent 上下文、候选摘要或图谱默认检索。
### 当前阻塞
官方 `mlebench prepare -c nomad2018-predict-transparent-conductors` 已加载 registry、任务配置与 grader，但 Kaggle 返回 403 `You must accept this competition's rules`。依赖环境位于远端 `/data/zsm/ai4sci-design-bench-20260809/mlebench-nomad`；接受规则后可原命令继续，不需要修改 benchmark。
## 立即任务：Matbench experimental gap
远端 Matbench 0.6 的 `matbench_expt_gap` 已加载 4604 条 composition-to-band-gap 数据和五个固定 folds；训练均值 smoke 经官方 `record()`、`validate()`、score 与 `to_file()` 完整通过，MAE 1.1435269609161665。数据只有化学组成，没有 Nomad 的空间群、晶格和几何文件，因此搜索空间更窄；仍可比较元素统计/物理描述符、核与树模型、组成嵌入模型、预训练表示和集成等方法族。它作为 SearchBench v2 第一项，Nomad 在规则接受后作为结构信息扩展。
### 审核器控制对
Matbench 仓库同时保存了同一五折上的已提交结果和方法说明，可用于校准成对审核器，不向盲创 Agent 披露：训练均值 MAE 1.1435269609161665；Magpie 特征加 RandomForest 0.44605499248719205；CrabNet 组成注意力网络 0.346265357025457；MODNet 描述符筛选加前馈网络 0.33267352188755905。同方法的折间结果构成已知同机制对，不同算法说明构成已知异机制对；控制只校准局部判断，不变成全局 taxonomy。
## 控制项：RE-Bench Triton
远端来源：`/data/zsm/ai4sci-design-bench-20260809/task-scout/RE-Bench/ai_rd_triton_cumsum/`。
`ai_rd_triton_cumsum.py` 只规定一个 32-bit 整数数组上的前缀和变体、正确性和 100,000,000 长度输入的运行时间；Triton 只是建议，不是必须方案。单 kernel、分块扫描、框架算子组合和不同并行归约都能形成真实分叉，评分是隐藏输入上的执行结果，适合验证“能否从已有方法跳出”。任务目录约 44 KB，输入数组约 400 MB，显存不是主要压力，编译和运行时间是主要压力。
限制：`build_steps.json` 引用的公开任务资产 `assets/score.py` 在当前克隆中不存在；没有读取或解压 official solution。完整执行闭环要先补齐公开任务资产或获得 METR runner 的合法挂载，不能直接声称当前远端已经可跑。官方 manifest 要求 1 张 H100，而远端是 3 张 RTX A6000 49 GB；若保持评分语义，应先做兼容性冒烟。
## 备选：Spaceship Titanic
远端来源：`/data/zsm/ai4sci-design-bench-20260809/task-scout/mle-bench/mlebench/competitions/spaceship-titanic/`。
它与 Nomad 使用相同的 MLE-bench 提交和 grader 契约，公开训练数据约 8700 行，目标是二分类 accuracy，CPU 即可运行。逻辑回归、树模型、缺失值处理、群组/舱位特征、文本姓名特征和集成足以产生多个方法族，适合作为没有材料背景时的最小控制题。缺点是它不测试科学数据处理，不能作为 SearchBench v2 的主任务。
## 不选项
| 任务 | 不选原因 | 可复用部分 |
| --- | --- | --- |
| RE-Bench `Fix Embedding` | 连续隐藏 loss 很适合实验，但官方 100 GB 内存/H100 规格超出当前远端；数据和受保护评分资产也不在普通克隆中 | TaskFamily 的中间评分和 best-score 聚合语义 |
| RE-Bench `Small Scaling Law` | 题面开放搜索，但评分是预设的平滑插值目标；搜索几乎退化为一维预算分配，不能代表真实实验机制 | 作为搜索策略单元测试，不作为科学任务 |
| RE-Bench `Optimize LLM Foundry` / `Restricted MLM` / `NanoGPT RL` | 分别需要 4 张 H100、2 张 H100 或外部 Replicate judge，远端资源和成本不匹配 | 任务 contract 和受限评分生命周期 |
| RE-Bench `Rust CodeContests` | 依赖旧的 GPT-3.5 API 和 500 美元 API 预算，实验结果混入模型可用性与 API 价格，不适合当前闭环 | 可复用生成程序、held-out grader 的边界设计 |
| AstaBench `DiscoveryBench` | 题面和 Python workflow 很接近科学研究，但主分数由 GPT-4o 比较 gold/generated hypothesis，不能作为确定性执行结果 | Inspect Task/Solver/Scorer、sandbox 和结构化日志 |
| AstaBench `CORE-Bench` / `DS-1000` | 代码可执行评分稳定，但题目是复现或代码补全，方法空间不是材料科学研究方法空间 | Inspect runner 和隔离执行 |
## SearchBench v2 的最小闭环
1. 加载 Matbench experimental gap 的官方五折，固定包版本、数据哈希、时间和 token 预算；每折 test 标签不进入研究 workspace。
2. 每个 agent 会话提交一个候选行动：代码、预期、公开验证方法和最小证据。只记录候选自述，不把自述当作方法族标签。
3. 审核通过后执行候选，保留代码、stdout、依赖、随机种子和资源；每折预测由 Matbench `record()` 和 `validate()` 评分。
4. 用独立审核者对候选成对判断“同一机制/不同机制”，不建立全局 taxonomy；冲突交人工。
5. 先比较盲创、reflect 和盲创失败后 reflect 三种上下文策略，再加入 Nomad 或 Triton 扩展；不要把领域任务差异与上下文策略做全量笛卡尔积。
