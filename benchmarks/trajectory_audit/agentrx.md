---
sources:
  - title: AgentRx
    url: https://github.com/microsoft/AgentRx
  - title: AgentRx paper
    url: https://arxiv.org/abs/2602.02475
---
# AgentRx critical failure
Remote source: `/data/zsm/ai4sci-design-bench-20260809/trajectory-audit/source/AgentRx`; commit `f228165bfec60a801fd5fedd9d8ffe0f9de0c69d`, MIT. Official tests 13/13 pass.
仓库公开 44 条 Magentic-One 与 29 条 τ-bench ground truth；论文所述 115 条中的 Flash 数据不在仓库。73 条中 critical root cause 是时间上首个失败的有 54 条，是最后失败的有 47 条，两者都不是的有 8 条。Magentic-One 每条平均 6.70 个已标注失败，critical root cause 仅 27/44 是首个失败。
τ-bench 完整文件另含 100 条运行，官方 reward 为 1 的有 73 条、为 0 的有 27 条；失败文件含 29 条。reward=1 可作为“没有导致最终任务失败的关键根因”的负例，用于计算误报率，但不能证明轨迹中没有任何中间异常。
复用 ground truth 的 critical step 与轨迹，不复用十类 failure taxonomy 作为产品分类。评测分别报告最早异常定位、critical root cause 定位和其后受影响步骤；三者不能折叠成一个时间排序或颜色。
