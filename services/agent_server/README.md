# Agent Server

FastAPI 最小服务，仅提供 `GET /health`，返回 `{"status":"ok"}`。PydanticAI 采用 `pydantic-ai-slim`，暂不配置模型或供应商，不需要 API 密钥。

```sh
uv sync
uv run uvicorn main:app --reload
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

从本目录执行。服务默认仅监听 `127.0.0.1:8000`。暂不提供聊天、认证、数据库或工具执行；不要作为完整 Agent 服务部署。
