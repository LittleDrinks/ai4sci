---
sources:
  - id: prov
    title: "PROV-DM: The PROV Data Model"
    url: https://www.w3.org/TR/prov-dm/
  - id: provenance-skill
    title: "F(AI)2R: Who Did What, and Who Checked? Verifiable AI Provenance as an Executable Skill"
    url: https://arxiv.org/abs/2607.25637
  - id: least-privilege
    title: "NIST SP 800-53 Rev. 5: Security and Privacy Controls for Information Systems and Organizations"
    url: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
---
# 人类与 Agent 共用节点提交接口
人类与 Agent 通过同一命令接口创建待审节点，共用内容规范化、系统身份生成、结构校验、审核门和事件记录；UI、CLI 与 SDK 只是同一接口的适配器，actor 身份与权限作为来源记录。人类不能绕过接口直写图数据库，也不因人工提交而跳过入图审核，避免同一研究事实因操作者不同产生两套语义。
PROV 将 actor 与其产生的实体、活动分开归因 [prov]，可验证溯源也要求提交者和审核者在同一可执行记录中出现 [provenance-skill]。单一写入门同时落实最小权限控制 [least-privilege]，使不同入口只改变交互方式，不改变身份、验证和审核语义。
