# Research World
单问题研究控制面：SQLite 图谱是真源，artifact store 按 SHA-256 寻址，Agent 通过 `rw` 与 task capability 访问固定 project snapshot。
## Start
```bash
cp .env.example .env
docker compose up --build
```
控制面：`http://127.0.0.1:8095`。启动不创建 run，不调用模型。
## Doctor
```bash
docker compose exec control rw doctor --model --embedding --mcp --runner
```
## #49
```bash
rw project create --file projects/orbits-49/project.json
rw project sync --project orbits-49
rw run start --project orbits-49 --question-id 49 --apply-selected --wait
```
## Verify
```bash
npm test
docker compose config
```
