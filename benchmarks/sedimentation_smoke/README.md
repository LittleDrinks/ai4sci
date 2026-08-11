---
sources:
  - title: LongMemEval-V2
    url: https://github.com/xiaowu0162/LongMemEval-V2
  - title: vLLM pooling models
    url: https://docs.vllm.ai/en/latest/models/pooling_models/
---
# Sedimentation smoke
Remote root: `/data/zsm/ai4sci-design-bench-20260809/sedimentation`.
Official source: LongMemEval-V2 commit `ef67f10aacd9080c75aeb2dd527a0af25dc26f1b`; remote Python is `3.10.12`, while `pyproject.toml` declares `>=3.11`. `evaluation/run_eval.py --help` and `py_compile` pass on 3.10 without changing official code.
Selected public item: question `01307e07`, enterprise `dynamic-environment`, no question image, 100 haystack trajectories. The 29 public question screenshots and official enterprise trajectory screenshot archive are present.
Official `evaluation.harness` with `no_retrieval`, `--save-memory`, and `--skip-evaluation` completed. The saved memory reloads as `NoRetrievalMemory` and returns an empty context. `evaluation.qa_eval_metrics.eval_from_spec` scores the gold answer true and an answer missing one phrase false.
The local `.env` OpenAI-compatible endpoint returned 200 from `/models` and listed `gpt-5.4-mini`. With the endpoint key supplied through a remote mode-600 temporary file, the official reader completed for `01307e07` using `gpt-5.4-mini`: parsed response `UNKNOWN`, prompt/completion tokens `166/15`, and official scorer `score=0.0`. Temporary credential files were removed after the run.
Official configuration uses harness flags `--base-url`, `--model`, and `--api-key-file`; `run_eval.py` exposes the equivalent `READER_BASE_URL`, `READER_MODEL`, and `READER_API_KEY_ENV` settings but no key-file flag.
Dependencies were isolated under `smoke/site-packages`: `openai`, `openai-agents`, `tqdm`, and `transformers`. The official module registry imports these dependencies even for `no_retrieval`; no adapter or official-code patch was added.
Artifacts: `smoke/manifest.json`, `smoke/dependency_probe.txt`, `smoke/no_retrieval_skip/`, `smoke/no_retrieval_load_attempt/`, `smoke/no_retrieval_e2e/`, and `smoke/scorer_smoke.json`.
## 官方 AgentRunbook 边界
下载并校验官方 `enterprise_screenshots_base.tar.gz`，SHA-256 为 `5c4a67ae0856aa1ede9b040e7da7c7a2d0b76fdd6344ef87380bcdf9f4b6d7a3`。官方准备器解压并建立 984 个软链接；问题 `01307e07` 的 100 条 haystack 轨迹含 3358 个截图引用，缺失数为 0。
`agentrunbook_c_v2` 在 `/data/zsm/ai4sci-design-bench-20260809/sedimentation/agentrunbook-c-v2-one2` 完成 100 条轨迹的 memory workspace 构建，但查询阶段连续三次收到 `Responses websocket connection closed before any response events`。官方实现随后返回空 memory context，reader 输出 `UNKNOWN`，官方分数 0。失败发生在 OpenAI Agents SDK 的 Responses WebSocket 与当前 OpenAI-compatible endpoint 之间，不是数据缺失或 reader 失败；未修改官方代码。可直接复用的数据、memory 接口和 scorer 已确认，`agentrunbook_c_v2` 的传输实现不能在当前端点复用。
官方 `rag_query_to_slice_notes` 使用 HTTP controller 与 embedding endpoint，默认分别为 Qwen chat 和 `Qwen/Qwen3-Embedding-8B`。模型名虽可配置，同一名称还会传给 Hugging Face `AutoTokenizer`；百炼 `text-embedding-v4` 不能原样替换。官方基线复用 vLLM pooling runner 在远端暴露 `/v1/embeddings`；若解耦 API 模型与 tokenizer，必须标为 adapter 组而非官方原样组。
## Oracle state 披露对照
问题 `01307e07` 的金证据位于轨迹 `1d56a4d6`、state 11；其 25928 字符 AXTree 同时包含三个答案。使用官方 `build_messages`、reader client 和 scorer 时，Mini 与 Luna 读取完整 state 都只返回 `Incident Mobile, Incident Portal`，分别使用 7455、7457 Token，得分均为 0。
只用问题中已出现的字符串 `Incident` 选取同一 state 的匹配行，证据缩为 1581 字符；Mini 与 Luna 都返回完整三个标签并得分 1，分别使用 617、666 Token。selector 不读取金答案，只复用问题词。完整证据会让两个模型遗漏答案，按问题派生的可验证切片同时提高正确性并减少约 11–12 倍 Token；渐进披露属于 memory 查询语义，不只是界面呈现。
