---
sources:
  - id: aris
    title: "ARIS: Autonomous Research via Adversarial Multi-Agent Collaboration"
    url: https://arxiv.org/abs/2605.03042
  - id: sharded-oversight
    title: "Sharding Prevents LLM Oversight Failures and Adversarial Exploitation"
    url: https://arxiv.org/abs/2608.06422
  - id: novelty-evaluation
    title: "What Is Novel? A Knowledge-Driven Framework for Bias-Aware Literature Originality Evaluation"
    url: https://arxiv.org/abs/2602.06054
---
# 分离机制审核与执行审核
候选行动入图前分别接受机制重合审核和执行有效性审核，不由一个模型同时判断新颖性、任务适配、泄漏、预算与可证伪性。机制审核保留带来源的 `same/different/uncertain` 局部判断；审核冲突或传递性冲突进入人工队列，不通过自动闭包形成方法族。
ARIS 将完整性、结果到主张映射和主张审核分为不同阶段 [aris]；多维 verdict 混在一次审核会丢失判定依据 [sharded-oversight]，而新颖性本身又要求分别比较问题、方法和主张 [novelty-evaluation]。机制重合和执行有效性的证据材料不同，所以保存局部判断、把分歧上升人工，比自动将相似关系闭包为方法族更可靠。
