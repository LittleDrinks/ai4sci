---
sources:
  - id: agentrx
    title: "AgentRx: Diagnosing AI Agent Failures from Execution Trajectories"
    url: https://arxiv.org/abs/2602.02475
  - id: trrack
    title: "Trrack: A Library for Provenance-Tracking in Web-Based Visualizations"
    url: https://doi.org/10.1109/vis47514.2020.00030
  - id: prov
    title: "PROV-DM: The PROV Data Model"
    url: https://www.w3.org/TR/prov-dm/
---
# 时间与因果分离
审查分别呈现最早异常、关键根因和下游影响范围，不按时间位置自动裁决因果重要性。时间线负责定位发生顺序，依赖图负责计算失效传播，两者不共享一个排序分数。
AgentRx 的根因标注说明首个异常、关键根因和最终失败可以不同 [agentrx]；Trrack 的分支时间线只表达状态和顺序 [trrack]，PROV 另以导出和使用关系表达影响路径 [prov]。因此时间线用于定位，依赖图用于传播，两个问题不共用一个排序分数。
