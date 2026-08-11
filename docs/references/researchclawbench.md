---
sources:
  - title: ResearchClawBench
    url: https://arxiv.org/abs/2606.07591
  - title: ResearchClawBench Code
    url: https://github.com/InternScience/ResearchClawBench
  - title: ResearchClawBench Dataset
    url: https://huggingface.co/datasets/InternScience/ResearchClawBench
---
# ResearchClawBench
## 任务
40 个任务覆盖 10 个领域。每个任务由真实论文构造，向 Agent 提供问题、相关文献、原始数据和可执行环境，隐藏目标论文，要求产出实验代码、中间结果与研究报告。
## 评价
领域专家从目标论文构造带权重的文本与图像 rubric，以 50 分表示重新发现目标论文的水平。补充评价完整性、深度、指令遵循和专业性。
## 可复用边界
适合作为端到端结果基准和现有 Agent SDK 的统一运行入口，不直接评价图谱质量、审核时机、上下文披露或搜索策略。现有任务以干实验为主，评分集中在最终报告，真实新发现的评价仍未解决。
