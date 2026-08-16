---
source:
  - https://chatgpt.com/c/6a7ca6b6-535c-83ee-b577-9756a22728f2
  - https://chatgpt.com/c/6a7cad90-8a70-83ee-a448-e7b28d5140dc
retrieved: 2026-08-13
model: ChatGPT Pro
attachment_sha256: 33803b88a7f3f5d24ef2004becb0d16ed70e7a68e1eb7711f166e2f6dcbec6cb
---
# 系统缺口与截止日前主线
## 结论
唯一主线是一个真实 Science 125 深度题的机器可核验计算子命题，Qwen-only，从行动提交做到失败、退修、独立审核、冷重放和真人审查实验。真实案例提供实验材料，委托校准只做离线派生证据；不铺 125 题、不扩 benchmark、不补展示性 UI。
三个致命缺口依次为：没有真人证明审查带宽扩大；没有真实问题到可用科学产物的强闭环；没有模型、工具链、任务族和风险级别上的委托边界。当前最危险的自欺是把文档中的 action lifecycle、审核页面和查询 benchmark 当成已实现且已证明的审查闭环。
## 已确认的实现断点
- `server/db.py:SCHEMA` 没有 action、lease、invalidation 或 scorer 状态；`World._package_node_values` 只产生 source、claim、artifact、result。当前真实闭环是先执行、再提交并审核整个 package，不是 action 准入后执行。
- `Orchestrator.execute` 和 `_continue` 在非机械双 `revise` 后仍把当前 generation 设为 parent；`_producer_context` 无条件读取 parent 的 pending nodes。待审内容不可继续生长这一核心 invariant 没有测试保护。
- `World.claim_run` 只有 `created -> claimed`，没有 owner、lease、heartbeat 或死亡回收；不能宣称 Worker 租约已经实现。
- `bootstrap_data` 把 `review_nodes` 设为 `World.admitted_nodes()`，`ReviewPage` 却只显示 pending/revision/rejected/invalidated；节点审核队列天然为空。
- `web/src/api.js:postCommand` 除 `create_project` 外拒绝全部命令；审核、退修和失效按钮没有后端写路径。后端也没有可核验的失效传播或独立 scorer 路径。
本地运行 `test_graph.py test_orchestrator.py test_api_cli.py` 为 27 passed；这些断点不在现有测试覆盖内。普通双 `revise` 继续生长由 Pro 做过最小复现，本地仅完成静态路径核验。
## 最小实验
### 真人审查带宽
12 名有计算科研经验的评审，8 个同一 Qwen 真实运行产生的配对事件，拉丁方交叉比较原始轨迹与图谱审查包，共 96 次裁决。通过线：正确裁决且正确定位影响范围/人时提高至少 2 倍，关键错误召回率至少 90%，相对原始轨迹下降不超过 5 个百分点。失败任一安全阈值即否定核心主张。
### 真实纵向闭环
固定一个真实计算子命题、Qwen 端点、工具链、数据切分、scorer 和预算。两名非开发者各冷重放一次；通过线：2/2 规范化输出哈希一致，最终指标差不超过 1e-6，最终主张 100% 具有证据、执行和审核链，上游失效后仍能生长的后代为 0。
### 委托边界
一个 Qwen 端点、两种链路、三类任务、每格 10 例，共 60 例；前 30 校准、后 30 盲测。通过线：自动覆盖率至少 40%，关键误接收为 0，人工分钟下降至少 30%。样本不足时只报告风险—覆盖率，不自动扩大权限。
## 三周范围
第一周只修阻断 invariant：非 admitted parent 不得进入下一代；接通真实审核与失效事件；冻结 Qwen、数据、工具链、scorer、预算和实验阈值。第二周生成 8 个真实审核事件并完成配对材料，保留所有失败和退修。第三周完成 12 人实验、两次冷重放并冻结 commit、event cutoff、环境 digest、种子和产物哈希。
## 五个演示事件
1. Qwen 对真实计算子命题提交带依赖、预算、泄漏边界和失败条件的候选行动。
2. 独立准入审核发现 held-out label 泄漏并退修，失败事件不能产生后代。
3. 新会话只接收最小阻断理由，提交无泄漏版本；受限执行保存代码、输入、环境、种子、预测和哈希。
4. 独立 scorer 与结果审核发现一个上游预处理错误，系统失效受影响结果并阻断继续生长。
5. 修正后的正或负结论连同基线、置信区间、证据定位、审核记录、失效清单和冷重放结果导出为审计包。
## 不做
- 不人工打磨 125 个结果，不把节点数、报告数或查询正确率当核心证据。
- 不扩模型矩阵、benchmark、persona、多 Agent 辩论或反思流程。
- 不新增全局 schema、taxonomy、校准持久表或第二真源。
- 不补 kanban、Trace、reference、Methodology 和视觉工程。
- 不宣称跨模型、跨任务族、湿实验或 Science 125 整体的自动接受能力。
