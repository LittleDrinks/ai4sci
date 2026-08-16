---
sources:
  - title: ChatGPT conversation 6a7c7f09-4e98-83e8-a851-971faa56c655
    url: https://chatgpt.com/c/6a7c7f09-4e98-83e8-a851-971faa56c655
  - title: AI 科研闭环：最终方案汇总（初审版）
    path: /mnt/e/xwechat_files/wxid_x6e64hefjyox12_ba3b/temp/RWTemp/2026-08/76b92c0e95b900f06fc4fae1e5bf0e83/闭环方案汇总.md
  - title: Can LLM design high-quality experiments? A Comprehensive and Systematic Benchmark on Autonomous Experimental Design
    url: https://arxiv.org/abs/2608.03501
  - title: Large Language Models Cannot Self-Correct Reasoning Yet
    url: https://arxiv.org/abs/2310.01798
  - title: Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate
    url: https://arxiv.org/abs/2509.05396
  - title: AI scientists produce results without reasoning scientifically
    url: https://arxiv.org/abs/2604.18805
  - title: AutoResearchBench: Benchmarking AI Agents on Complex Scientific Literature Discovery
    url: https://arxiv.org/abs/2604.25256
  - title: Language agents achieve superhuman synthesis of scientific knowledge
    url: https://arxiv.org/abs/2409.13740
  - title: LEC: Linear Expectation Constraints for Selection-Conditioned Risk Control in Selective Prediction and Routing Systems
    url: https://arxiv.org/abs/2512.01556
  - title: AIDE: AI-Driven Exploration in the Space of Code
    url: https://arxiv.org/abs/2502.13138
  - title: Autonomous inorganic materials synthesis in a robotic lab
    url: https://www.nature.com/articles/s41586-023-06734-w
  - title: Accelerating scientific breakthroughs with an AI co-scientist
    url: https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/
---
# 闭环方案与科研委托评估
## 结论
朋友的方案适合作为初审叙事和执行层需求清单，不适合作为系统内核。它保留了 provenance、确定性统计、真实数据适配、审计和复现，但把 LLM 生成、LLM 评审、角色辩论和自然语言置信度串成同一条认识链，无法证明主张、实验或代理指标成立。
ChatGPT 对话后两轮有参考价值：它把“模型是否可信”改写为“某个模型—工具链在某类任务、输入分布和错误预算下能获得多大委托范围”，再压缩为“搜索可以开放，写入必须受控”。这与当前图谱、分维审核、独立评分和会话轮换一致，不需要另造科研委托操作系统。
真正的增量只有两项：把验证成本和错误代价加入任务准入；用风险—覆盖率、合格产物/人类小时和 Agent Lift 衡量委托范围。它们应先进入 benchmark，不直接成为静态权限配置。
## 聊天记录
OpenCLI 于 2026-08-13 读取目标会话，共 6 条消息，三轮问答；三条 Assistant 回复分别为 7315、7099、7252 字符。
第一轮提出“不要预先信任 LLM”：模型输出只作候选，主张和实验必须绑定证据、失败条件、独立验证与现实反馈；内在 self-reflect 和同源多 Agent 不能充当外部验证。
第二轮补上自动化目标：“在给定错误预算下最大化可委托覆盖率”；只验收改变科学状态或消耗现实资源的边界产物；每个 Agent 模块与固定流程、单次调用比较净增益。
第三轮落到工单：Research Contract 定目标，Task Compiler 拆任务，Delegation Router 分配给程序、Agent 或人，Agent Sandbox 搜索，Acceptance Gate 决定通过、重做或升级；最终产物为已验收证据、可复现计算、待决问题和下一步候选。
## 与当前系统的对应
| 对话概念 | 当前实现 | 判断 |
|---|---|---|
| Research Contract | 问题、硬约束、评价接口和工具边界 | 已有，不新增契约类型 |
| 科研工单 | action 节点及其输入、产物和依赖 | 已有，不复制 Task schema |
| Agent Sandbox | ResearchHarness/运行时执行与隔离 scorer | 已有 |
| Acceptance Gate | 入图审核、执行承诺审核、结果审核、独立评分 | 当前实现更深，保持分维 |
| Accepted Science State | 图谱唯一持久真源；待审不可生长，驳回隔离 | 已有 |
| Capability Registry | 端点 capability 与 benchmark 结果 | 部分已有；缺风险—覆盖率和漂移证据 |
| Delegation Router | 按 capability 派工 | 仅有运行能力路由，不能宣称科学权限已校准 |
| Green/Yellow/Red | 无固定全局 taxonomy | 不持久化；按具体审核问题和风险查询派生 |
## 朋友方案
### 保留
- provenance、原始结果、代码、配置、环境、随机种子和产物哈希。
- 统计与裁定使用确定性程序，模型不生成测量数字。
- 模拟器、离线数据和在线 API 共享执行入口；真实实验保留更完整证据。
- 高成本、不可逆或缺少廉价裁决器的决策交给人。
### 删除
- 统一八阶段流水线。125 个问题共享图谱和审核机制，不共享固定科研步骤。
- 多 persona、反方 Agent 和主持人综合。它们是待 benchmark 的搜索策略，不是可信机制。
- “五维都能算出来”和 LLM confidence。依据性、创新性、可行性与收益没有统一可靠标尺。
- 四个全局 JSON 卡片。当前节点提交接口和事件图已覆盖对象演进，固定卡片会重复真源。
- “失败后永不再踩同一区域”。失败只在原条件和依赖范围内有效；环境、方法或目标变化后可以重试。
- “全局最优曲线只升不降”。单一代理指标可被投机，也会阻止探索暂时退化但最终更好的路线。
- 用带隙和形成能回答光伏“最终效率”。该代理遗漏界面、缺陷、寿命、器件与制造约束，只能定义更窄的材料筛选子问题。
## 对话论文核验
| 论文 | 支持范围 | 使用边界 |
|---|---|---|
| arXiv:2608.03501 SCOPE/OptED | 完整实验设计过大；低层数据集、基线、指标配置是瓶颈；结构化阶段和工具约束有增益 | 300 篇 AI/CS 论文的一次性设计，不覆盖湿实验、设备安全和反馈迭代 |
| arXiv:2310.01798 | 无外部反馈的内在自纠可能无效或退化 | 推理任务结论，不能推出所有反思均无效 |
| arXiv:2509.05396 | 多 Agent 辩论存在从众、迎合和错误说服 | 说明“多个角色”不等于独立证据 |
| arXiv:2604.18805 | 科学 Agent 常不吸收证据或不因反证修正 | 行为诊断不等于所有 scaffold 无价值 |
| arXiv:2604.25256 | 复杂科学文献发现仍弱，增加轨迹长度不保证覆盖 | 与任务边界明确的文献问答不可混为一谈 |
| arXiv:2409.13740 PaperQA2 | 有来源绑定和自适应检索的窄任务可形成委托通道 | 不能外推到开放式系统综述和科学裁决 |
| arXiv:2512.01556 LEC | 可在条件成立时控制选择后风险或假发现 | 是校准工具，不提供开放科研真值和永久权限 |
| arXiv:2502.13138 AIDE | 代码搜索在强 evaluator 下可形成有效 Agent loop | 必须防 hidden-label 泄漏、测试投机和环境漂移 |
| A-Lab | 目标、安全边界、测量和反馈预先固定时可批量自主实验 | 自动 XRD 判定仍有歧义，关键科学判断不能由执行成功替代 |
## 落地
1. 在 benchmark 中为每个模型—运行时—任务组合报告风险—覆盖率，不用模型自报 confidence。
2. 加入固定流程、单次调用、Agent 循环三组 matched-budget 对照，报告 Agent Lift、合格产物/人类小时和下游存活率。
3. 记录每轮是否获得新外部 observation；纯文本自评不计科研进展。
4. 授权仍由审核事实和运行 capability 派生；样本不足时只显示建议，不自动扩大权限。
5. 两篇科研创意分布论文的结论与指标并入 `ai-scientist-verification-and-systems.md`，用于约束 SearchBench，不进入产品 schema。
