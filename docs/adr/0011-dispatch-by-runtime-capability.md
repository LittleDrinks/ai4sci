# 按运行能力调度 Agent
集群注册 Agent 或 memory 实现时记录模型接口、工具、传输协议、上下文预算与执行资源；队列只调度满足请求能力的实现。LongMemEval-V2 的 `agentrunbook_c_v2` 能构建 100 条轨迹的 memory workspace，但其 OpenAI Agents SDK 依赖 Responses WebSocket，当前 OpenAI-compatible endpoint 连续三次关闭连接并使官方实现静默返回空 context。由此不把 SDK 名称或兼容 URL 当作能力证明，也不在协议失败后把空证据视为有效研究结果。
