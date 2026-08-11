---
status: accepted
evidence:
  - ../../benchmarks/trajectory_audit/agentrx.md
  - ../../benchmarks/trajectory_audit/README.md
---
# 时间与因果分离
审查分别呈现最早异常、关键根因和下游影响范围，不按时间位置自动裁决因果重要性。AgentRx 公开 73 条 ground truth 中只有 54 条关键根因是首错，8 条既不是首错也不是末错；TELBench 分层切片上的 DRIFT 增加错误段覆盖但未命中首错。时间线负责定位发生顺序，依赖图负责计算失效传播，两者不共享一个排序分数。
