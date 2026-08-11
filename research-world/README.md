# Research World
一个本地 Agent 集群围绕一个科学问题工作。图谱保存已准入研究状态，SQLite 保存队列、审核、租约与事件，ResearchHarness Worker 在隔离 workspace 中执行任务。
## 启动
```bash
uv sync --python 3.12
npm --prefix web install
npm --prefix web run build
uv run research-world serve
```
另开终端启动本地 Worker：
```bash
uv run research-worker --server http://127.0.0.1:8095
```
浏览器打开 `http://127.0.0.1:8095`。Worker 从仓库上级 `.env` 读取 `baseurl` 与 `apikey`，页面不接触密钥。
## 工作流
1. 新建项目并输入一个科学问题。
2. Worker 注册本地 runtime；Agents 页面在 runtime 上注册带 `plan`、`research`、`html_report` 或 `audit` capability 的逻辑 Agent。
3. 人类显式请求 Plan；规划 Agent 只提交一个行动，不执行实验。
4. 独立审核 Agent 或人工批准行动后，系统自动创建一次 Research 请求。
5. 结果进入隔离审核区；只有准入节点能成为后续任务的默认上下文和依赖。
6. `Revise` 在同一 attempt 中带审核反馈续跑原会话；`Restart` 新建 attempt；技术失败使用独立 retry 语义。
7. 上游事实被推翻时，系统失效全部后代、撤回关联报告并停止依赖任务。
8. HTML 报告在 sandbox iframe 中待审预览，批准后发布；Activity 保留人类、runtime、生产 Agent 与审核 Agent 的完整事件顺序。
任务完成后 Worker 按控制面命令删除对应 workspace。原始对话不进入默认图谱；事实、证据、限制和来源沉淀为节点内容。
## CLI
```bash
uv run research-world create-project --title "Research question" --question "What should the cluster investigate?"
uv run research-world snapshot
uv run research-world submit-node --project PROJECT_ID --title "Candidate" --dependency ROOT_NODE_ID
uv run research-world import-manifest fixtures/music-directions.json
```
UI、CLI 与导入器共用 `POST /api/commands` 领域命令；Worker 使用 `/api/runtimes`、`/api/tasks` 与 `/api/maintenance` 租约端点。节点 ID 由系统生成；调用者只提交内容、依赖和 actor 来源。
## 真实图谱
`fixtures/music-directions.json` 由现有 `music/directions.yaml` 生成，当前导入 166 个节点和 246 条关系。默认地图渐进披露问题与一跳方向，Network 模式显示全图；节点详情保留源文件路径、SHA-256、原字段和显式关系。
## 验证
```bash
uv run pytest -q
uv run python -m compileall -q server worker tests
npm --prefix web run build
```
