---
sources:
  - id: qwen-api
    title: "首次调用千问 API"
    url: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
  - id: qwen-model-catalog
    title: "百炼模型大全"
    url: https://help.aliyun.com/zh/model-studio/models
  - id: longmemeval
    title: "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues"
    url: https://arxiv.org/abs/2605.12493
---
# 模型服务为端点实体
模型服务抽象为端点实体：同一模型的多个端点按优先级容灾，Agent 绑定端点而非模型名；本地 SDK 注册为 runtime 按 capability 派工。演示与提交链路只用 Qwen 端点，OpenAI 兼容端点只作开发对照。
千问调用需要同时确定模型 ID、API host、鉴权和可用模型集合 [qwen-api; qwen-model-catalog]；模型名不能表达这些运行边界。LongMemEval-V2 还表明兼容接口不等于完整运行能力 [longmemeval]，因此端点而非模型名承担故障转移和可复现路由，SDK 只有通过能力探针后才能参与派工。
