# Human review protocol
现有原型夹具只验证表示完整性，不计入真人可读性结论。正式任务复用 TELBench harmful spans 与 AgentRx critical failure ground truth，不自造答案。
## 输入条件
1. 原始轨迹。
2. 图谱派生的确定性审查视图。
3. 审查视图加独立 Agent 预审。
同一审查者不重复查看同一轨迹；不同条件使用按 benchmark、难度和轨迹长度配平的互斥样本，条件顺序轮换。初始屏只展示总览，所有条件允许按需展开原始证据。
## 问题
- TELBench：选择 harmful error spans 与 earliest harmful span。
- AgentRx 失败轨迹：选择 critical root cause；另记时间上最早异常。
- AgentRx τ-bench reward=1 轨迹：判断不存在导致最终失败的关键根因；不要求轨迹完全无异常。
- 两组：选择受影响的后续步骤，并指出支撑判断的原始证据。
gold、annotations、failure taxonomy 和 AI 预审正确性不向审查者披露。
## 指标
按公开 gold 计算错误段 F1、首错或关键根因准确率，并以 reward=1 控制计算关键根因误报率；记录完成时间、首次正确定位时间、展开次数、查看字符数、证据引用正确率和置信度。AI 预审组另计盲从错误率。可读性只有真人完成上述任务后才能成立，模型代理结果只作管线预检。
