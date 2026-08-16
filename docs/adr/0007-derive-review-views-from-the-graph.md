---
sources:
  - id: prov
    title: "PROV-DM: The PROV Data Model"
    url: https://www.w3.org/TR/prov-dm/
  - id: trrack
    title: "Trrack: A Library for Provenance-Tracking in Web-Based Visualizations"
    url: https://doi.org/10.1109/vis47514.2020.00030
  - id: workflow-cards
    title: "Workflow Cards: Structured Summaries of Workflow Executions Using Provenance Data"
    url: https://arxiv.org/abs/2608.11022
  - id: trace-attribution
    title: "TRACE: TRajectory Attribution for Automated Context Engineering"
    url: https://arxiv.org/abs/2608.09153
---
# 图谱存事实，审查视图按需派生
图谱保持唯一持久真源，面向人和审核 Agent 的总览不作为第二份研究状态写回图谱。审查视图从选定快照确定性生成状态分面、异常列表、精确 ID 查找、依赖子图和失效影响范围；每个值能回到产生它的节点或事件。自由文本模型只解释查询结果，不负责全局计数、判断 ID 是否存在或从截断序列推断影响范围。
PROV 把实体、活动和责任关系定义为可查询事实 [prov]；Trrack 将这类溯源聚合为交互式阅读界面 [trrack]，Workflow Cards 将执行记录压缩为可追溯摘要 [workflow-cards]，TRACE 将失败归因回具体上下文组件 [trace-attribution]。因此视图必须从快照确定性派生，既可回查每个计数、状态和影响范围，也不会把自由文本摘要写成第二真源。
