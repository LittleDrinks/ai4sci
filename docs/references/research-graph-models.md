---
sources:
  - title: PROV-DM: The PROV Data Model
    url: https://www.w3.org/TR/prov-dm/
  - title: Micropublications: a semantic model for claims, evidence, arguments and annotations in biomedical communications
    url: https://pmc.ncbi.nlm.nih.gov/articles/PMC4530550/
  - title: Nanopublications
    url: https://nanopub.net/
---
# 科研图谱参考模型
## W3C PROV
复用 Entity、Activity、Agent 以及 Usage、Generation、Derivation，描述谁在何时使用什么产物完成什么活动并生成什么结果。溯源关系只回答内容如何产生，不证明科学主张成立。
## Micropublications
复用 Claim、Evidence、Support、Challenge，把科学论证表示为可包含正反证据的依赖图。实验活动与实验观察分离，观察通过论证关系影响主张。
## Nanopublications
复用 Assertion、Provenance、Publication Info 的最小组合，使可传播主张同时携带内容、产生依据与发布身份。
## 组合边界
溯源关系记录生产过程，论证关系记录相信或质疑主张的理由，两者不得相互推断。文献先作为来源存在，只有实际用于推理的原文主张才按需展开并连接到研究图谱。
