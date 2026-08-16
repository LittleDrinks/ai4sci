---
sources:
  - id: hep
    title: "Toward Auditable AI Scientists: A Hypothesis Evolution Protocol for LLM Agents"
    url: https://arxiv.org/abs/2607.09195
  - id: held-out-transfer
    title: "Auto Research for Materials: Auditable AI-Scientist Workflows with Held-Out Transfer"
    url: https://arxiv.org/abs/2607.17100
  - id: trace-faithfulness
    title: "Position: Stop Anthropomorphizing Intermediate Tokens as Reasoning/Thinking Traces!"
    url: https://arxiv.org/abs/2504.09762
  - id: auditable-records
    title: "From Trajectories to Evidence: Auditable Experimental Records for Industrial Research Agents"
    url: https://arxiv.org/abs/2608.05235
  - id: agent-native-artifacts
    title: "The Last Human-Written Paper: Agent-Native Research Artifacts"
    url: https://arxiv.org/abs/2604.24658
---
# 以复现代替原始对话留存
Agent 的原始对话轨迹在沉淀到图谱后默认丢弃，避免噪声污染后续研究。计算实验保留代码、输入、配置、随机种子和产物哈希；质疑通过审核代码或独立 Agent 的确定性重跑处理。重跑差异与原结果并存并标出依赖路径，确认严重违反事实后使依赖结论失效。重跑成本高或结果可变的湿实验保留完整证据。
HEP 把假设和证据写成可回放事件 [hep]，而 held-out transfer 将冻结的代码、配置和产物交给独立评测 [held-out-transfer]；两者都把可复现物而非聊天文本作为核验对象。中间 token 不能当作忠实推理证据 [trace-faithfulness]，工业研究记录和 agent-native 产物也都以可检查证据链而非逐字会话支撑结论 [auditable-records; agent-native-artifacts]。因此计算结果保留可重放产物，湿实验则保留无法等成本重跑的完整原始证据。
