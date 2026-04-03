# Inches

仓库包含两部分：**根目录的 Python 多智能体审议引擎（CLI）** 与 **`frontend/` 里的 Web UI**。二者默认**互不自动连接**。

## Python 审议引擎（CLI）

在仓库根目录：

```bash
pip install -r requirements.txt   # 按需；无 key 时仍可 mock 运行
python main.py                    # 或 python main.py --task "你的问题"
```

需要真实模型时设置环境变量之一：`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`GOOGLE_API_KEY` 或 `GEMINI_API_KEY`。详见各模块与 `models.py`。

## Web 前端

```bash
cd frontend
npm install
npm run dev
```

## 重要：`VITE_API_URL` 与后端

- **未设置 `VITE_API_URL`**：前端使用 `api.ts` 的 **内置 mock**（含演示用冲绳骨架等），**不会**调用 Python，因此会看到「mock 示例」类提示——这是预期行为。
- **要走真实多智能体审议**：先在本机启动 API，再让前端指向它。

```bash
# 终端 1 — 仓库根目录（需已配置至少一种 LLM API key，否则引擎仍为 mock）
pip install -r requirements.txt
python server.py
# 监听 http://127.0.0.1:8000

# 终端 2 — frontend
# 在 frontend/.env.local 写入：
#   VITE_API_URL=http://127.0.0.1:8000
cd frontend && npm run dev
```

实现文件为根目录 [`server.py`](server.py)：`POST /api/chat` 会调用 `orchestrator.run_deliberation`；`/api/register` 与 `/api/login` 为开发用占位。仅设置 `VITE_API_URL` 而 **未**运行 `server.py` 时会出现 `Failed to fetch`。

CLI `python main.py` 与 `server.py` 相互独立，但共用同一套 `orchestrator` 与模型配置。

更多前端侧细节见 [`frontend/README.md`](frontend/README.md)。
