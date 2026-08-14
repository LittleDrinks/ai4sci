# Research World
本地科学研究控制面。Project Lead 把问题拆成多个 Direction；每个 Research Cycle 由外部 Python 状态机依次运行 Source、Claim、Experiment/Protocol、Report work item；每个 agent attempt 在独立 Docker 容器内执行；科学 reviewer 与代码 reviewer 只读冻结输出并提交 finding；完成后生成可检查的 Cycle Brief、日志、实验 receipt 和可复用代码。
## Start
仓库根目录 `.env` 使用 `baseurl`、`apikey`。密钥只注入临时 agent 容器，不写入 project、artifact 或日志。
```bash
docker compose up --build
docker compose exec control rw demo
```
Project Lead：`http://127.0.0.1:8095/leader`；完整路线图：`http://127.0.0.1:8095/roadmap`。`rw demo` 只注册八个项目，不调用模型。页面内可切换项目、生成方向、推进 Direction、给 Lead 发继续或改向指令。
## Real Run
```bash
docker compose exec control rw doctor --model --mcp --runner
docker compose exec control rw demo --run
docker compose exec control rw demo --export
```
`demo --run` 对八个问题各推进一个 Direction，会调用真实模型、真实 MCP 检索与 Docker runner。实验容器默认断网、只读根文件系统、固定 CPU/内存/PID 限额，同一输入重复执行并校验输出 hash。`demo --export` 把已完成 cycle 固化到每个 project 的 `research-dossier/`，实验源码固化到 `research-code/`。
## Delivered Demos
| Project | Evidence boundary | Executable result |
|---|---|---|
| Q001 primes | knowledge synthesis | AKS/factorization evidence gap is explicit |
| Q002 Riemann hypothesis | proof boundary | finite checks cannot close an infinite theorem |
| Q013 pandemic | forecast/backtest | replayed synthetic mass-action calibration |
| Q017 immune homeostasis | wet-lab protocol | no fabricated biological observation |
| Q049 orbital decay | simulation | replayed two-body energy-drift experiment |
| Q055 extraterrestrial life | open-world search | non-detection is bounded by search coverage |
| Q088 Mars manufacturing | engineering trade study | requirements and missing validation exposed |
| Q095 consciousness | competing theories | discriminating predictions and proxy limits |
每个 `projects/question-*/research-dossier/README.md` 是面向人的结论；`cycle.json` 保存完整结构化 work item、step、finding 与 attempt；`logs/*.log` 保存模型输入输出和 tool call；Q013、Q049 的 `research-code/` 可直接复用。
## Local Development
```bash
uv sync
uv run pytest -q
cd web && npm ci && npm run build
uv run rw serve
```
Runner 另启：
```bash
uvicorn server.runner_controller:app --host 127.0.0.1 --port 8096
```
