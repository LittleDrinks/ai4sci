---
sources:
  - id: matbench
    title: "Benchmarking materials property prediction methods: the Matbench test set and Automatminer reference algorithm"
    url: https://doi.org/10.1038/s41524-020-00406-3
  - id: held-out-transfer
    title: "Auto Research for Materials: Auditable AI-Scientist Workflows with Held-Out Transfer"
    url: https://arxiv.org/abs/2607.17100
  - id: auditable-records
    title: "From Trajectories to Evidence: Auditable Experimental Records for Industrial Research Agents"
    url: https://arxiv.org/abs/2608.05235
---
# 分离执行、结果审核与评分
执行 Agent 只能读取行动、训练数据、工具和评价接口，产出代码与 prediction；隐藏目标由独立评分进程持有。提交格式验证不允许结果入图，结果审核还需检查实际输入边界、代码、环境、日志与产物哈希，并以规范化 prediction 内容的哈希复跑。
Matbench 将任务、划分和评分协议固定为可比较的评测边界 [matbench]，held-out transfer 则把冻结干预交给外层独立评价 [held-out-transfer]。审计记录必须同时证明输入边界和产物链 [auditable-records]，所以格式通过和执行 Agent 自报分数都不能代替独立评分，也不以压缩容器字节判断复现。
