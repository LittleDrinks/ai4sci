---
sources:
  - id: scifact
    title: "SciFact: A Dataset for Scientific Claim Verification"
    url: https://aclanthology.org/2020.emnlp-main.609/
  - id: scifact-open
    title: "SciFact-Open: Towards open-domain scientific claim verification"
    url: https://doi.org/10.18653/v1/2022.findings-emnlp.347
  - id: prov
    title: "PROV-DM: The PROV Data Model"
    url: https://www.w3.org/TR/prov-dm/
---
# 事实进入图谱，审核程序进入 Skill
人工纠正具体事实时，新增带来源、绑定 claim 或 resource 的图谱证据；审核线程按作用域检索，规划与执行 Agent 不默认读取。只有可跨事实复用的检查步骤进入全局 Skill。
SciFact 将证据句绑定到具体科学主张 [scifact]，开放域版本显示证据覆盖与适用范围会随语料变化 [scifact-open]；PROV 也要求把产生事实的活动和来源保留为可查询关系 [prov]。事实正文因此按 claim/resource 存入图谱，Skill 只保存跨事实复用的审核步骤，避免把无边界的知识库默认灌入每次执行。
