# 执行内核独立为 harness 服务

Agent 执行内核从 research-world 进程内的 researchharness 库拆为独立 HTTP 服务（`harness/`）：有状态 session/turn 契约、fs+webhook 工具协议、append-only trace、SQLite 持久化与结构化 benchmark 评测。researchharness 需调私有 API、改全局环境变量、状态全在内存，稳定性不可控；自研内核把模型凭证收敛进 harness 容器，并把执行循环变成可 DIY 论文算法的基建。

## Consequences

- worker 经 `HARNESS_URL` 调 harness；agent 工具由 control 的 `/api/v1/attempts/{id}/tools/{name}` 回调分发，Bearer 任务 token 鉴权。
- 模型凭证只进 harness 容器；research-world 不再持有 `researchharness` 依赖。
- benchmark 并发执行会引入 trace seq 追加竞态，需要时先换文件锁再开并行。
