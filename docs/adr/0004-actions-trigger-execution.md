---
sources:
  - id: plan-following
    title: "From Plan to Action: How Well Do Agents Follow the Plan?"
    url: https://arxiv.org/abs/2604.12147
  - id: liveplan
    title: "Online Monitoring and Corrective Steering of Programming Agents"
    url: https://arxiv.org/abs/2608.06701
  - id: a-lab
    title: "An autonomous laboratory for the accelerated synthesis of inorganic materials"
    url: https://www.nature.com/articles/s41586-023-06734-w
---
# 规划产生行动，行动触发执行
人类或有界自动化显式请求规划，规划 Agent 一次只提交一个候选行动；系统不因前沿为空而自行开始无界规划。行动通过独立审核后原子且幂等地创建一次执行请求。规划与执行使用不同会话，规划不直接开始实验，执行 Agent 不在实验会话中隐式决定下一步。
计划遵循可在明确的计划步骤上测量 [plan-following]，在线监控和纠偏也以离散步骤为边界 [liveplan]；自主实验系统同样在执行、观察和下一步选择之间建立可观测反馈 [a-lab]。行动因此必须是先审核的命令：它阻止空前沿触发无界扩张，并使重试不会悄然重复启动实验。
