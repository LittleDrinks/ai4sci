---
sources:
  - title: 挑战杯 2026 阿里云榜题
    url: https://university.aliyun.com/action/tzbjbgs2026
  - title: 云工开物高校计划-阿里云百炼活动
    url: https://help.aliyun.com/zh/model-studio/introduction-to-yungongkaiwu
  - title: 使用和管理优惠券
    url: https://help.aliyun.com/zh/user-center/how-to-use-coupons
  - title: 学生权益
    url: https://university.aliyun.com/buycenter
  - title: 高校 AI 通行证
    url: https://opc.aliyun.com/summer-2026
  - title: 获取百炼 API Key
    url: https://help.aliyun.com/zh/model-studio/get-api-key
  - title: 首次调用千问 API
    url: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen
  - title: 阿里云百炼模型价格
    url: https://help.aliyun.com/zh/model-studio/model-pricing
  - title: 百炼模型大全
    url: https://help.aliyun.com/zh/model-studio/models
  - title: 百炼账单与成本管理
    url: https://help.aliyun.com/zh/model-studio/bill-query-and-cost-management
  - title: 百炼新人免费额度
    url: https://help.aliyun.com/zh/model-studio/new-free-quota
---
# 阿里云高校算力权益
## 学生
百炼专项活动为 2025-11-11 至 2026-11-10；挑战杯与学生权益页的通用券活动结束时间以页面通知为准。完成中国高校学生实名认证后可领取 300 元无门槛抵扣金，自领取日起一年有效。官方百炼活动说明其可抵扣大模型推理、训练和部署费用；API 按量调用产生后付费账单后自动抵扣。实际支持模型以券面适用商品和学生用券中心的大模型服务列表为准，不覆盖百炼全部模型。权益每日限量，先到先得。
## 教师
国内高校或科研机构教师、研究人员提交应用场景并通过审核后，可五折购买百炼平台产品服务，原价总额上限 40 万元。审核结果通常在三个工作日内短信通知，权益限科研与教学使用。
## 使用
1. 完成学生实名认证，在云工开物高校学生通用权益页领取 300 元券。
2. 在费用与成本控制台查看券的余额、有效期、订单类型与适用商品；目标 Qwen 模型必须出现在券面或学生用券中心的大模型服务列表。
3. 在学生用券中心进入“大模型服务”，确认目标模型位于指定列表并开通对应按量付费服务。API 无需预购 Token；账单出具时自动抵扣。若页面要求下单，以结算页显示的券、适用模型和实付金额为准。
4. 开通阿里云百炼，选择华北 2（北京）地域和业务空间创建 API Key。
5. 使用创建弹窗给出的 Workspace ID 与 API Host。OpenAI Python SDK 的 `base_url` 形如 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`，Key 通过 `DASHSCOPE_API_KEY` 注入。
6. 从券面适用列表复制当日 Qwen Model ID，分别对该模型和 `text-embedding-v4` 做一次最小调用。后者使用同一 API Host 的 `/embeddings` 路径。这一步验证模型权限、Key 和接口，不验证优惠券抵扣。
7. 在免费额度页查看目标模型余量。实时调用按“免费额度 → 资源包 → 节省计划 → 按量付费”扣减；不要为测试优惠券耗尽免费额度。
8. 券面已列出目标模型后即可启动低预算 benchmark；首次产生实际费用时，在账单详情核对“优惠券抵扣金额”和券的消耗明细。
9. 联调阶段开启“免费额度用完即停”；进入付费 benchmark 前设置百炼大模型推理的日账单预警，再按需关闭该开关。
API 调用是按量后付费，适用优惠券在出账时自动抵扣。券不能充值为账户余额或作为后付费账户预留金，也不能抵扣历史欠费；后付费系统仍会冻结当月消费金额，现金余额与信控额度必须覆盖冻结额。模型超出适用列表、额度用尽或权益过期后按标准价格计费。百炼按分钟出账，调用后等待账单明细生成再核验。
首次付费核验优先选券面内没有活动折扣的低价模型。学生券不可与产品折扣叠加；`qwen3.7-max` 当前限时五折，不能用它推断学生券一定生效，`qwen3.7-flash` 也仍须先检查券面模型列表。
## 接口探针
```bash
export QWEN_MODEL='券面显示的Model ID'
curl "$DASHSCOPE_API_HOST/chat/completions" -H "Authorization: Bearer $DASHSCOPE_API_KEY" -H 'Content-Type: application/json' -d "{\"model\":\"$QWEN_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"reply OK\"}],\"max_tokens\":8}"
curl "$DASHSCOPE_API_HOST/embeddings" -H "Authorization: Bearer $DASHSCOPE_API_KEY" -H 'Content-Type: application/json' -d '{"model":"text-embedding-v4","input":"graph memory smoke"}'
```
`DASHSCOPE_API_HOST` 使用创建 Key 时显示的完整 compatible-mode `/v1` 地址。Key 只进入环境变量，不写入脚本、图谱或运行产物。
预算表中的 `qwen3.7-flash` 是 2026-08-09 的低成本示例，不代表券面必然覆盖，也不作为接口默认值。
## 预算基线
SearchBench 的 36 次运行、54 个会话实耗 230683 输入 Token 与 24789 输出 Token，单次输入均低于 32K。按 2026-08-09 华北 2 公开原价估算，同一矩阵使用 `qwen3.7-flash` 约 0.066 元、`qwen3-max` 约 0.825 元、`qwen3.7-max` 约 3.661 元，未计 Batch、缓存、免费额度和活动折扣。上述三种模型与 `text-embedding-v4` 当前各有 100 万 Token 新人免费额度，有效期 90 天。300 元足以覆盖大量文本策略消融；实验执行算力、速率限制与审核质量更可能成为瓶颈。
已完成且互不重复的规划、恢复、证据作用域与记忆消融至少使用 1726754 Token。即使把所有 Token 都按输出原价计费，`qwen3.7-flash`、`qwen3-max`、`qwen3.7-max` 的费用上界也约为 1.38、17.27、62.16 元。300 元足以覆盖多轮同规模复测，先用小模型跑矩阵、只把争议样本升级到强模型。
## 首轮用途
1. 用小模型复跑 SearchBench 的缩减矩阵，验证 Qwen chat、Harness、轨迹和评分的最短闭环。
   ResearchHarness 已直接使用 OpenAI SDK Chat Completions 并接受 `api_base`、`api_key` 与 `model_name`，无需新增 provider adapter。
2. `text-embedding-v4` 探针只验证百炼向量接口。LongMemEval-V2 官方 `rag_query_to_slice_notes` 另用远端 Qwen3-Embedding-8B 服务；直接替换会因官方 tokenizer 耦合失败。远端两张 A6000 当前各有约 48.6 GB 空闲，显存满足单卡 preflight；Docker/NVIDIA runtime 不存在且驱动为 535.309，vLLM 部署兼容尚未验证。
3. 只把审核分歧、机制关系冲突和执行失败升级到强模型；不把强模型用于已由确定性查询解决的计数与追溯。
