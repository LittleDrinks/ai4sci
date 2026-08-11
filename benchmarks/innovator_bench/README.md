---
sources:
  - title: InnovatorBench code
    url: https://github.com/GAIR-NLP/InnovatorBench
  - title: InnovatorBench paper
    url: https://arxiv.org/abs/2510.27598
  - title: InnovatorBench dataset
    url: https://huggingface.co/datasets/GAIR/InnovatorBench
---
# InnovatorBench end-to-end LLM research
Official commit `934ead34675a0fc610618094dabeaf7bdcb44818` (2026-02-03, tip of main) is cloned at `source/`, Apache-2.0. `python -m compileall agents llm research_gym main.py` passes with three harmless SyntaxWarnings.
## Dataset access
The HF dataset `GAIR/InnovatorBench` is a single `data.tar.xz` of ~69.7 GB (HF-reported storage); it is not downloaded here. As of 2026-08-10 it is publicly downloadable: the HF API reports `gated: false` and an anonymous range request on `resolve/main/data.tar.xz` returns HTTP 206. An earlier observation that it was gated (401) no longer holds; if gating is re-enabled, request access on the dataset page with an HF account (需人工申请 only in that case). The tarball also contains the `evaluations/` tree and per-task corpora that the repo expects at `./evaluations` and `./datasets`; task workspaces, reference solutions and checkpoints follow the dataset README inside the tarball.
## ResearchGym deployment
Each run is `python main.py -t research_gym/configs/tasks/task_i.yaml -a agents/config/agent_config.yaml`. Command actions go through `computer_pool` entries in the task yaml: every computer runs the `researchgym` Docker image whose `http_terminal_server.py` exposes an unauthenticated HTTP PTY API on port 8123; GPU computers behind a NAT are reached via `cmd_proxy_url`. Web-browse actions share one cluster-wide Quart/Playwright `research_gym/backend/web_server.py` on port 8124 (`web_server_host`). `workspace_dataset_path`, `actual_workspace` and `checkpoint_base_path` must point at the extracted dataset and storage shared across the pool. Agent extension point: subclass `BaseAgent` (`agents/agents/custom_agent.py` is the worked example) implementing `get_default_system_prompt` and `step`, wire it as `agent_type` in `agents/config/agent_config.yaml`, and add the model under `model_providers` with an OpenAI-compatible `base_url` — Qwen on Bailian fits this without code changes.
## Task inventory
20 tasks in six domains; resources from `research_gym/configs/tasks/README.md`, scope from the paper appendix. Wall-clock limits are baked into the yamls and marked do-not-modify.
| task | domain | scope (reference paper) | time | hardware |
| --- | --- | --- | --- | --- |
| 1–4 | Data Construction | DatasetResearch: build/fine-tune summarization, EN–TA translation, USMLE QA datasets (Llama-3.1-8B) | 48h | CPU 100GB+ + 8×80GB GPU |
| 5 | Data Filtering | Programming Every Example: clean 100K web texts | 6h | same |
| 6 | Data Filtering | LIMO: select 800/10K math problems | 48h | CPU + 2×(8×80GB GPU) |
| 7 | Data Filtering | code instruction decontamination, top-160K | 8h | same as 1–4 |
| 8–9 | Data Augmentation | SuperGPQA / NuminaMath fine-tune Qwen2.5-7B | 48h | same |
| 10, 12 | Data Augmentation | DeepResearcher search-R data (72B synthesizer), MAC multimodal (Qwen2.5-VL-7B) | 24h | same |
| 11 | Data Augmentation | Dynamic ToM data, Qwen2-7B | 48h | same |
| 13–15 | Loss Design | DualAlign in LLaMA-Factory; GRPO anti-entropy-collapse in Verl; GammaPO vs SimPO on AlpacaEval2 | 48/48/24h | same; task 14 CPU 400GB+ |
| 16–17 | Reward Design | Search-R1 reward (Qwen-2.5-3B), GUI-R1 unified reward in Verl | 48/24h | same |
| 18 | Scaffold Construction | DeepResearcher prompt-only research agent, GPT-4.1-class API + search | 24h | CPU only, no GPU |
| 19 | Scaffold Construction | Visual Sketchpad math reasoning workflow, GPT-4o-class API | 12h | CPU only, no GPU |
| 20 | Scaffold Construction | Visual Sketchpad visual reasoning (vstar/blink) | 12h | CPU + 1×24GB GPU + SOM/GroundingDINO/DepthAnything services |
Preflight of the yamls: tasks 18/19 are the zero-GPU on-ramps and need only a CPU container, the web server, a search key and a chat-completions endpoint. Upstream defect: `task_20.yaml` still says `task_name: "task_19"`, and its only other differences from task 19 are the three vision-expert service URLs.
## External dependencies and boundaries
- Charged services: agent LLM (any OpenAI-compatible endpoint), task 18–20 rubric APIs (Azure OpenAI or native OpenAI per `env_vars`), Serper or Bing search, and the evaluation harness: vendored `alpaca_eval-0.6.2` (`pip install -e alpaca_eval-0.6.2`) plus an API key in `evaluations/base/data_classes.py`. No charged evaluation was run here.
- Can run locally now: code compilation, task/agent config inspection, `CustomAgent` development against a local endpoint, Docker image build (`research_gym/backend/docker/Dockerfile`, CUDA 12.4 base), web server startup.
- Blocked until the 69.7 GB dataset is fetched: every real task run (workspaces, reference corpora, `evaluations/` scorer tree). Tasks 1–17 additionally blocked on 8×80GB-GPU nodes; task 20 on the three VisualSketchpad vision services.
- Scores are per-domain relative metrics against hidden reference solutions (4 submissions per task, Best vs Final); the pinned README leaderboard (Claude Sonnet 4 weighted 24.01, GPT-5 12.04, GLM-4.5 11.85, Kimi-K2 5.35) is the comparison baseline. The benchmark judges research execution quality, not novelty of the produced method.
