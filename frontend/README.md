# Inches — frontend

Vite + React + TypeScript + Tailwind。多智能体审议主题的聊天壳：登录 / 注册 / 聊天页，数据走 `src/services/api.ts`。

## 本地运行

```bash
npm install
npm run dev
```

构建：`npm run build`；预览：`npm run preview`。

## `VITE_API_URL` 与 mock（必读）

| 配置 | 行为 |
|------|------|
| **未设置** `VITE_API_URL` | 全部 API 在浏览器内 **mock**（延迟与数据为前端伪造）。无需 Python、无需任何后端即可开发/演示 UI。 |
| **已设置** `VITE_API_URL`（如 `http://127.0.0.1:8000`） | 对该基址发真实 `fetch`：`/api/register`、`/api/login`、`/api/chat`。请求与响应形状以 `src/services/api.ts` 中的 `RegisterResult`、`LoginResult`、`ChatResult` 为准。 |

本仓库在根目录提供 **`server.py`**（Flask）：`python server.py` 可在 `http://127.0.0.1:8000` 提供 `/api/*`。只设置 `VITE_API_URL` 而 **没有**启动该服务时，会出现 `Failed to fetch`。

可在 `frontend` 目录创建 `.env.local`：

```bash
# 有真实 API 时再取消注释并改成你的服务地址
# VITE_API_URL=http://127.0.0.1:8000
```

## 与仓库根目录 Python CLI 的关系

- 根目录的 `python main.py` 是 **终端里的审议引擎**，与当前前端 **无自动集成**。
- 若要让 UI 使用真实审议结果，需要自己实现 HTTP 层（或代理）并满足 `api.ts` 的契约，而不是仅运行 CLI。

仓库总览见根目录 [`README.md`](../README.md)。

---

## Vite 模板说明

本项目由 Vite React-TS 模板初始化。扩展 ESLint（含 type-aware 规则）可参考 [Vite 插件文档](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) 与 [typescript-eslint](https://typescript-eslint.io/getting-started/)。
