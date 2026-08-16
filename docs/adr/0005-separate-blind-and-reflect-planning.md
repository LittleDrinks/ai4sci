---
sources:
  - id: exploration-narrowing
    title: "AI Research Agents Narrow Scientific Exploration"
    url: https://arxiv.org/abs/2605.27905
  - id: verbalized-sampling
    title: "Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity"
    url: https://arxiv.org/abs/2510.01171
  - id: novelty-evaluation
    title: "What Is Novel? A Knowledge-Driven Framework for Bias-Aware Literature Originality Evaluation"
    url: https://arxiv.org/abs/2602.06054
---
# 分离盲创与反思
盲创会话不读取已有路线、实验历史或隔离记录，每个会话只提交一个候选行动；审核通过后形成行动节点，失败后销毁会话。需要披露重合点或沿已有工作修改时，新建反思会话并只提供相关图谱切片与最小审核意见。任何已有路线的披露都会结束盲创状态，避免一边要求独立探索，一边用历史约束其搜索。
研究 Agent 的候选会向既有语义邻域收缩 [exploration-narrowing]，单靠提示中的“新颖”不能证明搜索覆盖；采样机制只能缓解模式坍缩，不能把受历史约束的候选伪装成独立探索 [verbalized-sampling]。新颖性又需区分研究问题、方法和主张 [novelty-evaluation]，因此历史路线一旦进入上下文就结束盲创状态，转为可单独衡量增量的反思会话。
