---
sources:
  - title: ResearchHarness
    url: https://github.com/InternScience/ResearchHarness
  - title: Matbench
    url: https://github.com/materialsproject/matbench
---
# ExecutionLoop
Luna 的已通过行动 `Stoichiometric similarity interpolation with elemental-property geometry` 进入隔离工作区。执行 Agent 直接复用 ResearchHarness 默认文件、Shell 与终端工具，读取 `action.json`，生成 `solution.py`，运行 Matbench `matbench_expt_gap` 官方五折并输出 submission；没有自建执行 SDK。
第一次 submission 通过 `task.validate()`，但代码调用 `get_test_data(..., include_target=True)` 自行计算 MAE。结果审核以 `hidden_label_access` 驳回，并把最小代码返回原工作会话。退修后代码只产生预测，五折 submission 再次通过，独立 Matbench 进程评分 MAE `0.7151736522892789`。
无模型 Key、无原会话的第二个进程重跑同一代码，规范化 prediction SHA-256 均为 `30e0d8defb1de20f47d08663e9a7e3b9a84e22ce9ff213e36516d5643f3a134a`，分数完全一致；两个 gzip 文件哈希不同。执行 Agent 首轮 24 次模型调用、313935 Token，退修 6 次调用、76970 Token；五折实际计算约 11 秒。
远端产物位于 `/data/zsm/ai4sci-design-bench-20260809/execution/stoichiometric-similarity-run1`，包含行动、两次审核、代码、submission、独立评分、复现检查和 ResearchHarness 轨迹。结论是提交格式验证、结果来源审核和独立评分必须分离；复现比较规范化预测或内部产物哈希，不比较 gzip 容器字节。
