# agent-server 协作约定

遵循根目录 AGENTS.md。当前仅有 `main.py` 中的 FastAPI 应用及健康检查。

- 使用 uv 与 Ruff，测试使用 pytest + FastAPI TestClient。
- PydanticAI 为精简依赖，尚未配置模型；健康检查和启动不能依赖模型密钥或外部服务。
- 不恢复旧 AgentLoop、插件 SDK、令牌管理、数据库或 SSE 协议。
- 根目录 `pnpm run check` 必须实际运行后端测试。
