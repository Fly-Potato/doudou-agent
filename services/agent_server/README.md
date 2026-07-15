# agent-server

doudou-agent 的 AI 后端服务。集中处理 AI 请求、会话编排、工具调用和流式响应。

## 架构概览

```
客户端 (POST /chat)  ──►  agent-server  ──►  LLM (OpenAI / 兼容)
                              │
                   PluginManager (插件系统)
                    ├── ToolRegistry   — 工具注册与调度
                    ├── EventBus       — 生命周期钩子
                    └── SessionManager — 会话历史（内存）
```

- 采用**插件式架构**，通过外部插件目录动态发现插件
- 与客户端通过 **SSE（Server-Sent Events）** 通信，支持流式文本、工具调用事件
- 支持 OpenAI 兼容的任何 LLM 服务（DeepSeek、Ollama、OpenRouter 等）

## 快速开始

### 前置要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器
- （可选）[mise](https://mise.jdx.dev/) — monorepo 推荐环境管理

### 安装

```bash
# 在 monorepo 根目录或本目录
uv sync
```

### 配置

通过环境变量配置运行时参数：

```powershell
$env:AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS = '10'
$env:AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC = '30'
$env:AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES = '50'
$env:AGENT_SERVER_AUTH_DB_URL = 'sqlite+aiosqlite:///tokens.db'
$env:AGENT_SERVER_TIMEZONE = 'UTC'
```

完整配置项见 `settings.py`。生产环境应通过部署平台注入环境变量，不要将数据库连接和令牌写入源码。

`auth.db_url` 支持任意 SQLAlchemy 兼容数据库：

| 前缀                                     | 用途     |
| ---------------------------------------- | -------- |
| `sqlite+aiosqlite:///tokens.db`          | 开发环境 |
| `postgresql+asyncpg://user:pass@host/db` | 生产环境 |

### 运行

```bash
# 启动服务
uv run agent-server serve --host 0.0.0.0 --port 8888

# 生成认证令牌（首次使用）
uv run agent-server generate-token

# 列出令牌
uv run agent-server list-tokens

# 删除令牌
uv run agent-server delete-token 1
```

服务监听地址和端口由 `serve --host --port` 指定。

## API

### `GET /health`

健康检查。

```json
{ "status": "ok" }
```

### `POST /chat`

发送消息并获取 SSE 流式响应。

**请求头：**

| 头              | 值                                     |
| --------------- | -------------------------------------- |
| `Authorization` | `Bearer <token>`（配置了 auth 时必填） |
| `Content-Type`  | `application/json`                     |

**请求体：**

```json
{
  "session_id": "s1",
  "content": "帮我记录一条待办",
  "provider": "deepseek"
}
```

**响应（SSE）：**

```
event: token
data: {"content": "好的，"}

event: token
data: {"content": "已为您添加待办事项"}

event: done
data: {"session_id": "s1"}
```

| 事件          | 说明                                            |
| ------------- | ----------------------------------------------- |
| `token`       | LLM 回复的文本片段                              |
| `tool_call`   | LLM 调用了某个工具                              |
| `tool_result` | 工具执行结果                                    |
| `done`        | 本轮对话完成                                    |
| `error`       | 出错（`code`: `MAX_ROUNDS` / `INTERNAL_ERROR`） |

## 插件开发

插件是扩展业务能力的标准方式。详见 [docs/plugin-spec.md](docs/plugin-spec.md)。

### 快速创建一个插件

```python
# doudou_todo/plugin.py
from doudou_agent_sdk import Plugin, Tool


class TodoPlugin(Plugin):
    @property
    def name(self) -> str:
        return "doudou-todo"

    def register_tools(self) -> list[Tool]:
        async def add_todo(session_id: str, **params) -> dict:
            return {"ok": True, "title": params["title"]}

        return [
            Tool(
                name="add_todo",
                description="添加一条待办事项",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "待办标题"}
                    },
                    "required": ["title"],
                },
                handler=add_todo,
            )
        ]
```

在 `pyproject.toml` 中注册：

```toml
[project.entry-points."doudou_agent.plugins"]
doudou-todo = "doudou_todo.plugin:TodoPlugin"
```

## 开发

### 测试

```bash
uv run pytest
```

### 代码质量

```bash
uv run ruff check .
uv run ruff format --check .
```

## 配置参考

完整配置项见 [docs/architecture.md](docs/architecture.md#6-配置参考)。

## 许可

MIT
