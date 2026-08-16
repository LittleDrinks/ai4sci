---
sources:
  - id: longmemeval
    title: "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues"
    url: https://arxiv.org/abs/2605.12493
  - id: agentic-harness
    title: "Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses"
    url: https://arxiv.org/abs/2604.25850
  - id: a2a
    title: "A2A Protocol Specification"
    url: https://a2a-protocol.org/latest/specification/
---
# 按运行能力调度 Agent
集群注册 Agent 或 memory 实现时记录模型接口、工具、传输协议、上下文预算与执行资源；队列只调度满足请求能力的实现。不把 SDK 名称或兼容 URL 当作能力证明，也不在协议失败后把空证据视为有效研究结果。
LongMemEval-V2 将 memory 视为运行时接口而非模型标签 [longmemeval]，agent harness 的可靠性也取决于模型外的工具、状态和观测边界 [agentic-harness]。A2A 的能力声明可用于发现候选实现 [a2a]，但只有实际探针成功才构成调度资格；协议失败时返回空上下文是失败，不是零证据结果。
