---
sources:
  - id: self-correction
    title: "Large Language Models Cannot Self-Correct Reasoning Yet"
    url: https://arxiv.org/abs/2310.01798
  - id: longmemeval
    title: "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues"
    url: https://arxiv.org/abs/2605.12493
  - id: trace-distillation
    title: "Interpretable Traces, Unexpected Outcomes: Investigating the Disconnect in Trace-Based Knowledge Distillation"
    url: https://aclanthology.org/2026.acl-long.1686/
---
# 入图后轮换执行上下文
请求进入队列后由一个临时工作会话执行，产出交给另一线程中的独立 Agent 审核。审核结果只有通过、退修、重开：通过后产出写入图谱并删除原会话；退修把最小审核意见返回原会话；重开隔离原会话，由新会话依据图谱和最小驳回理由继续。队列保存待处理工作，图谱保存持久研究状态，对话不承担跨节点记忆。
同一会话对自身产物的再解释仍是内源纠错 [self-correction]；长程 Agent 记忆也以按问题取回的紧凑证据为接口，而不是无限续接聊天 [longmemeval]。可解释轨迹的蒸馏仍可能与实际结果脱节 [trace-distillation]，故只有通过审核的图谱节点能成为跨会话契约；未通过内容只回传最小修复信息，以限制锚定和噪声继承。
