---
sources:
  - id: json-canonicalization
    title: "RFC 8785: JSON Canonicalization Scheme"
    url: https://www.rfc-editor.org/rfc/rfc8785.html
  - id: sha-256
    title: "FIPS PUB 180-4: Secure Hash Standard"
    url: https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf
  - id: prov
    title: "PROV-DM: The PROV Data Model"
    url: https://www.w3.org/TR/prov-dm/
---
# 系统拥有节点身份
Agent 只提交行动内容，不提交可被图谱信任的节点 ID。系统对规范化内容生成不可变 UID：同一内容重复提交映射到同一身份，相同自报 ID 的不同内容保持独立。UID 只表达内容身份，不推断语义重合；两个行动是否共享机制仍由带来源的局部审核关系表达。
JSON canonicalization 为等价结构给出稳定字节表示 [json-canonicalization]，安全哈希为该表示提供内容身份 [sha-256]；PROV 也将“同一对象”与派生、关联等关系分开表示 [prov]。因此系统 UID 只处理去重和不可变引用，语义相似仍须由可追溯的审核判断裁定。
