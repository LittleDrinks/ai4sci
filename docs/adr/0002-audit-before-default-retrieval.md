---
sources:
  - id: hep
    title: "Toward Auditable AI Scientists: A Hypothesis Evolution Protocol for LLM Agents"
    url: https://arxiv.org/abs/2607.09195
  - id: self-correction
    title: "Large Language Models Cannot Self-Correct Reasoning Yet"
    url: https://arxiv.org/abs/2310.01798
  - id: provenance-skill
    title: "F(AI)2R: Who Did What, and Who Checked? Verifiable AI Provenance as an Executable Skill"
    url: https://arxiv.org/abs/2607.25637
---
# 入图前审核，驳回内容隔离
行动与结果通过各自依赖和用途所要求的独立审核后，才能成为默认可检索的图谱内容。待审或不可判定内容可以显示，但依赖路径不得继续生长；无关分支照常运行。被驳回的内容保留为隔离记录，只在后续入图审核时用于相似性匹配；执行 Agent 只收到最小阻断理由，完整内容仅向审核 Agent 和人工披露。反复命中作为人工补充可测试 Skill 的信号，不自动进入全局规则。
HEP 不让未经 verdict 或证据的假设派生后代 [hep]，无外部反馈的模型自纠也不能提供独立验证 [self-correction]。可验证溯源要求把主张、证据和审核者连在同一条记录上 [provenance-skill]，所以默认检索只暴露已审核内容；隔离记录仍供审核端发现重复错误，却不把失败细节扩散为执行上下文。
