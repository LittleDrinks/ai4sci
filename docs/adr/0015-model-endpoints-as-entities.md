# 模型服务为端点实体

模型服务抽象为端点实体：同一模型的多个端点按优先级容灾，Agent 绑定端点而非模型名；本地 SDK 注册为 runtime 按 capability 派工。演示与提交链路只用 Qwen 端点，OpenAI 兼容端点只作开发对照。
