---
name: inches-deliberation
description: Runs and extends the Inches multi-agent deliberation engine (Python CLI) and aligns the Vite React frontend with api.ts contracts. Use when the user works in the inches repo, mentions deliberation agents, orchestrator, mock LLM mode, or wiring VITE_API_URL to a backend.
---

# Inches 多智能体与前端

## 快速定位

- **CLI  deliberation**：仓库根目录，`python main.py`（或 `python main.py --task "…"`）。`--save` 将状态写入 `deliberation_state.json`。
- **Live LLM**：至少设置 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`GOOGLE_API_KEY` / `GEMINI_API_KEY` 之一；否则 `models.is_mock_mode()` 为真，输出为确定性 mock。
- **前端**：`cd frontend && npm run dev`。未配置 `VITE_API_URL` 时 `api.ts` 使用内置 mock，不请求网络。

## 修改引擎时的顺序建议

1. 迭代与收敛：`orchestrator.py`（`MAX_ITERATIONS`、`CONVERGENCE_CONFLICT_THRESHOLD`）。
2. 角色与 prompt：`agents.py`。
3. 解析与 JSON 结构：`structurer.py`；与批评/冲突：`critic.py`。
4. 新 provider 或模型：只扩展 `models.py`，避免在 agent 里直接调 SDK。

## 对接真实 HTTP API（若实现）

`frontend/src/services/api.ts` 约定：

- `POST /api/register` — body `{ username, password }` → `RegisterResult`
- `POST /api/login` — body `{ username, password }` → `LoginResult`（含 `token`）
- `POST /api/chat` — body `{ message }`，Header 可带 `Authorization: Bearer <token>` → `ChatResult`（含 `structured_output.iterations` 等）

实现新后端后，在 `frontend/.env` 或环境中设置 `VITE_API_URL` 指向该服务基址（无尾部斜杠与 path 前缀冲突即可，因 `api.ts` 使用 `` `${BASE}${path}` ``）。

## 检查清单

- [ ] CLI 路径在仓库根目录执行，不在 `frontend/` 下跑 `main.py`。
- [ ] 改共享数据结构时，同时检查 `orchestrator` 产出的 state 与（若存在）前端 `ChatResult` 展示组件。
