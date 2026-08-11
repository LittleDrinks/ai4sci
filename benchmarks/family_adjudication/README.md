---
sources:
  - title: Matbench
    url: https://github.com/materialsproject/matbench
    commit: 936176db18ca4cd7b38cbd957c017a5bac770c6b
---
# 方法族审核
`adjudicate.py` 对同一任务内候选做双审核、反序呈现和传递性检查。`prepare_matbench_controls.py` 直接抽取 Matbench 官方 submission 描述；CrabNet 两版与 MODNet 两版是已知同机制对，RF-SCM/Magpie 与 Dummy 提供异机制控制。金标不进入审核提示。
先对六个控制候选运行全部 15 对；`score_controls.py` 统计双审核与合议准确率。控制未通过时不解释 SearchBench 的方法族发现率。
