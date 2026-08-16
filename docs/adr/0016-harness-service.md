---
sources:
  - id: agentic-harness
    title: "Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses"
    url: https://arxiv.org/abs/2604.25850
  - id: researchclawbench
    title: "ResearchClawBench: A Benchmark for End-to-End Autonomous Scientific Research"
    url: https://arxiv.org/abs/2606.07591
  - id: container-security
    title: "NIST SP 800-190: Application Container Security Guide"
    url: https://csrc.nist.gov/pubs/sp/800/190/final
---
# 执行内核独立为 harness 服务
Agent 执行内核从 research-world 进程内的 researchharness 库拆为独立 HTTP 服务（`harness/`）：有状态 session/turn 契约、fs+webhook 工具协议、append-only trace、SQLite 持久化与结构化 benchmark 评测。自研内核把模型凭证收敛进 harness 容器，并把执行循环变成可替换论文算法的基建。
Agent harness 需要将模型、工具、状态和观测作为独立运行边界 [agentic-harness]；端到端科研基准也要求可重复的执行环境和产物接口 [researchclawbench]。容器边界将凭证与控制平面隔离 [container-security]，故执行循环不能继续作为进程内隐式状态。
## 后果
- worker 经 `HARNESS_URL` 调 harness；agent 工具由 control 的 `/api/v1/attempts/{id}/tools/{name}` 回调分发，Bearer 任务 token 鉴权。
- 模型凭证只进 harness 容器；research-world 不再持有 `researchharness` 依赖。
- benchmark 并发执行会引入 trace seq 追加竞态，需要时先换文件锁再开并行。
