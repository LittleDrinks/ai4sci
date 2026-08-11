# Research World
围绕单个科学问题积累可审核、可复现、可追溯的研究状态。
## Language
**研究包**：一代 Producer 提交的策略、候选 source/claim 子图、artifact、代码集合与不用代码的理由；整包保持 pending，双审通过后原子准入。
_Avoid_: 单节点提交、直接入图
**来源快照**：外部来源在获取时固定的 URL、artifact hash 与行/段/页定位；刷新创建新快照，运行中的 generation 不换 hash。
_Avoid_: 动态引用、裸 URL
**执行凭据**：工具或实验执行的命令、参数、输入 hash、环境/image digest、seed、退出码、输出 hash、资源用量与脱敏结果。
_Avoid_: 日志片段、口头复现
**Generation**：一个父代固定、策略变化显式的研究包迭代；Generation 0 盲研究，后代只读取 admitted 父代与审核反馈。
_Avoid_: retry、会话轮次
**Attempt**：一个 Agent 角色绑定 project snapshot 的隔离执行，拥有独立 workspace、Agent home 与短期 task capability。
_Avoid_: Generation、机械退修
**机械退修**：schema、引用、artifact 或 replay 门失败后在同一 Generation、同一 Attempt 原会话修正。
_Avoid_: 新一代、实质方法修订
**准入**：两个独立 Reviewer 都 approve 后，研究包的 source、claim、artifact、result 与 edges 在一个事务中变为 admitted。
_Avoid_: 保存、发布
**Activity event**：按 `event_id/run_id/generation_id/attempt_id/actor/type/time/entity/payload` 追加的运行事实；Timeline、Wire、Context 与 Agents/Jobs 都是其投影。
_Avoid_: UI 日志、数据库轮询快照
**Project snapshot**：`rw project sync` 固定的项目文件、`.agents/skills/` 与 `.mcp.json` 内容清单；目录后续变化不影响已绑定 Attempt。
_Avoid_: 文件监听、工作目录
