# agent-server 协作约定

遵循根目录 AGENTS.md。当前仅有 `main.py` 中的 FastAPI 应用及健康检查。

- 使用 uv 与 Ruff，测试使用 pytest + FastAPI TestClient。
- PydanticAI 为精简依赖，尚未配置模型；健康检查和启动不能依赖模型密钥或外部服务。
- 旧插件式架构已废弃，不恢复插件 SDK、目录扫描、动态加载或自建 Agent 循环；后续使用 PydanticAI 原生 Agent 与工具。
- 最小骨架阶段不添加令牌管理、数据库或流式协议。
- 根目录 `pnpm run check` 必须实际运行后端测试。
