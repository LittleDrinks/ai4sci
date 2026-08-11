# 分离执行、结果审核与评分
执行 Agent 只能读取行动、训练数据、工具和评价接口，产出代码与 prediction；隐藏目标由独立评分进程持有。提交格式验证不允许结果入图，结果审核还需检查实际输入边界、代码、环境、日志与产物哈希。一个 Matbench 行动的首份 submission 虽通过 `task.validate()`，代码仍以 `include_target=True` 读取 held-out 标签；退修移除目标访问后，独立 scorer 得到 MAE 0.7151736522892789，无模型重跑的规范化 prediction 哈希完全一致。由此放弃执行 Agent 自报测试分数，并以内部预测内容而非 gzip 容器字节判断复现。
