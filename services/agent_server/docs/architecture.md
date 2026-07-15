# agent-server 架构说明

## 1. 系统概览

agent-server 是 doudou-agent 的 AI 后端服务，采用**插件式架构**。中枢负责 AI 对话循环，插件通过外部目录扫描注册工具（Tool）和技能（Skill），扩展具体业务能力。

```
┌─────────────────────────────────────────────────────────────┐
│                    agent-server (中枢)                        │
│                                                              │
│  POST /chat (SSE) ──► AgentLoop                              │
│                           │                                  │
│      ┌────────────────────┼────────────────────┐             │
│      ▼                    ▼                    ▼             │
│  ToolRegistry        EventBus           SessionManager       │
│  (工具合并/调度)    (钩子串行)          (会话历史)            │
│      │                    │                    │             │
│      └────────────────────┼────────────────────┘             │
│                           │                                  │
│  ┌────────────────────────┴────────────────────────┐         │
│  │              PluginManager                       │         │
│  │   目录扫描 → on_load → register_tools            │         │
│  └────────────────────────┬────────────────────────┘         │
│                           │                                  │
│     ┌─────────┬──────────┼──────────┬──────────┐             │
│     ▼         ▼          ▼          ▼          ▼             │
│  ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────┐           │
│  │Todo  │ │Search│ │ MCP    │ │File  │ │ 未来   │           │
│  │插件  │ │插件  │ │内置插件│ │插件  │ │ 插件   │           │
│  └──────┘ └──────┘ └────────┘ └──────┘ └────────┘           │
│                                                              │
│  LLM Provider ──┬── OpenAI (兼容 DeepSeek/Ollama/OpenRouter)  │
│                 └── Anthropic (扩展预留)                      │
└──────────────────────────────────────────────────────────────┘
```

## 2. 核心组件

### 2.1 main.py — FastAPI 应用入口

- `GET /health` — 健康检查
- `POST /chat` — 对话端点，接收 `{"session_id": "...", "content": "..."}`，返回 SSE 流
- 启动时通过 `lifespan` 上下文管理器加载插件，关闭时调用 `on_shutdown`
- 认证通过 `TokenAuth` middleware 实现，从数据库查询 token 进行 SHA-256 哈希比对

### 2.2 AgentLoop — AI 对话循环

`services/agent_server/agent/loop.py`

AgentLoop 是系统的核心运行时，每次 `POST /chat` 请求启动一次循环：

```
客户端消息
    │
    ▼
on_message 钩子 (插件可按需修改消息)
    │
    ▼
pre_llm_call 钩子 (插件可注入 system prompt)
    │
    ▼
调用 LLM (带 ToolRegistry 合并后的工具列表)
    │
    ├─ LLM 返回 tool_calls → 执行工具 → 回传结果 → 再次调 LLM
    │   (最多 max_tool_rounds 轮，默认 10)
    │
    └─ LLM 返回文本 → post_llm_call 钩子 → 流式推送 → 完成
    │
    ▼
SSE 流 (token → tool_call → tool_result → done)
```

**超时与限制：**

| 配置项                         | 默认值 | 说明                     |
| ------------------------------ | ------ | ------------------------ |
| `session.max_tool_rounds`      | 10     | 单条消息最大工具调用轮数 |
| `session.tool_timeout_sec`     | 30     | 单个工具执行超时（秒）   |
| `session.history_max_messages` | 50     | 会话保留的最大消息数     |

### 2.3 PluginManager — 插件管理器

`services/agent_server/plugin/manager.py`

扫描 `AGENT_SERVER_PLUGIN_EXTERNAL_DIRS` 指定目录的一级子目录，查找其中的 `__init__.py` 和 `Plugin` 子类并加载。

**加载流程：**

```
读取 settings.py 中的 plugin.external_dirs
    │
    ▼
扫描外部插件目录
    │
    ▼
过滤隐藏目录、非目录和缺少 `__init__.py` 的目录
    │
    ▼
对每个发现的插件：
  1. 实例化插件类
  2. 调用 on_load(config)
  3. 调用 register_tools() → 注册到 ToolRegistry
  4. 调用 register_skills() → 注册到 SkillRegistry
    │
    ▼
服务关闭 → 调用 on_shutdown（倒序）
```

### 2.4 ToolRegistry — 工具注册表

`services/agent_server/plugin/registry.py`

- 合并所有插件的工具，按名索引
- 同名工具后加载覆盖先加载（打印警告）
- 提供 `list_definitions()` 返回 OpenAI function-calling 格式

```python
# list_definitions() 输出示例
[
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "添加一条待办事项",
            "parameters": {"type": "object", ...}
        }
    }
]
```

### 2.5 EventBus — 事件总线

`services/agent_server/event.py`

按插件加载顺序串行调用生命周期钩子。前一个插件的返回值作为下一个的输入。

### 2.6 SessionManager — 会话管理

`services/agent_server/agent/session.py`

- 按 `session_id` 隔离对话历史
- 支持消息数量裁剪（`history_max_messages`）
- 当前为内存存储，连接断开后历史丢失

### 2.7 LLMProvider — LLM 适配器

`services/agent_server/agent/llm/`

**接口：**

```python
class LLMProvider(ABC):
    async def chat_completion(
        self, messages: list[dict], tools: list[dict]
    ) -> AsyncIterator[dict]: ...
```

**现有实现：**

- `OpenAIProvider` — 通过 `base_url` 适配所有 OpenAI 兼容服务

**扩展方式：**

```python
# 新增 Azure LLM Provider
class AzureProvider(LLMProvider):
    ...

# 在 agent/llm/__init__.py 中注册
def create_provider(config):
    if config.type == "openai": return OpenAIProvider(...)
    if config.type == "azure":  return AzureProvider(...)
```

## 3. 请求处理流程

### POST /chat 完整时序

```
客户端                      agent-server                    LLM (OpenAI等)
  │                             │                              │
  │ POST /chat                  │                              │
  │ {"session_id":"s1",         │                              │
  │  "content":"帮我加一条todo"} │                              │
  │────────────────────────────►│                              │
  │                             │                              │
  │                             │── on_message 钩子            │
  │                             │── pre_llm_call 钩子          │
  │                             │── chat_completion(messages,  │
  │                             │   tools=[add_todo,...]) ────►│
  │                             │                              │
  │                             │◄── tool_call: add_todo ──────│
  │                             │                              │
  │ SSE: tool_call              │                              │
  │◄────────────────────────────│                              │
  │                             │                              │
  │                             │── 执行 tool.handler          │
  │                             │── 回传结果 → 再接 LLM        │
  │                             │                              │
  │ SSE: tool_result            │                              │
  │◄────────────────────────────│                              │
  │                             │                              │
  │                             │── chat_completion(含tool结果)│
  │                             │─────────────────────────────►│
  │                             │                              │
  │ SSE: token "已为您添加..."  │◄── streaming text ──────────│
  │◄────────────────────────────│                              │
  │ SSE: done                   │                              │
  │◄────────────────────────────│                              │
```

### SSE 事件协议

`POST /chat` 返回 `Content-Type: text/event-stream`，每条事件独立行：

```
event: token\ndata: {"content": "已为您"}\n\n
event: token\ndata: {"content": "添加待办事项"}\n\n
event: tool_call\ndata: {"calls": [{"id": "call_1", "function": {...}}]}\n\n
event: tool_result\ndata: {"tool": "add_todo", "result": "{\"id\": 1}"}\n\n
event: done\ndata: {"session_id": "s1"}\n\n
event: error\ndata: {"code": "MAX_ROUNDS", "message": "工具调用轮数超限"}\n\n
```

| 事件          | 方向          | 说明                           |
| ------------- | ------------- | ------------------------------ |
| `token`       | 服务端→客户端 | LLM 回复的文本片段（可能多次） |
| `tool_call`   | 服务端→客户端 | LLM 调用了某个工具             |
| `tool_result` | 服务端→客户端 | 工具执行结果                   |
| `done`        | 服务端→客户端 | 本轮对话完成                   |
| `error`       | 服务端→客户端 | 出错，`code` 标识错误类型      |

## 4. 认证

- `auth.db_url` 配置数据库连接（默认 `sqlite+aiosqlite:///tokens.db`），**留空则跳过认证**
- 请求头 `Authorization: Bearer <token>`，中枢通过 `TokenStore` 对 token 做 SHA-256 哈希后查询数据库
- 认证失败返回 HTTP 401
- 日志中仅输出脱敏 token（前 4 位 + `***`），不输出完整令牌

### 4.1 CLI 令牌管理

`agent-server` 提供 4 个子命令：

| 命令                | 说明                                   |
| ------------------- | -------------------------------------- |
| `serve`             | 启动 HTTP 服务                         |
| `generate-token`    | 生成新令牌，输出原始值（仅此一次可见） |
| `list-tokens`       | 列出所有令牌 ID 和创建时间             |
| `delete-token <id>` | 按 ID 删除指定令牌                     |

### 4.2 数据库模型

使用 SQLAlchemy ORM，单表存储：

```python
class Token(Base):
    __tablename__ = 'tokens'
    id: int          # 主键自增
    token_hash: str  # SHA-256 哈希，唯一索引
    created_at: datetime  # 创建时间
```

SQLAlchemy 的 `db_url` 前缀决定数据库类型：

| 前缀                                     | 用途             |
| ---------------------------------------- | ---------------- |
| `sqlite+aiosqlite:///tokens.db`          | 开发环境（默认） |
| `postgresql+asyncpg://user:pass@host/db` | 生产环境         |

## 5. 目录结构

```
services/agent_server/
├── pyproject.toml                    # 项目配置和依赖
├── settings.py                       # 环境变量配置与 AppConfig
├── README.md
├── docs/
│   ├── plugin-spec.md                # 插件开发规范
│   └── architecture.md               # 本文件
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # DummyPlugin 测试夹具
│   ├── test_plugin_manager.py        # ToolRegistry + PluginManager 测试
│   ├── test_agent_loop.py            # AgentLoop 测试
│   ├── test_auth.py                  # TokenAuth 测试
│   └── test_token_store.py           # TokenStore CRUD 测试
├── main.py                           # FastAPI 应用，SSE 端点 + CLI 子命令
├── auth.py                           # TokenAuth — 数据库令牌认证
├── models.py                         # Token ORM 模型（SQLAlchemy）
├── token_store.py                    # TokenStore — 令牌 CRUD
├── schemas.py                        # 共享类型
├── event.py                          # EventBus 钩子总线
├── plugin/
│   ├── __init__.py
│   ├── manager.py                    # PluginManager 发现/加载
│   └── registry.py                   # ToolRegistry 工具注册表
└── agent/
    ├── __init__.py
    ├── loop.py                       # AgentLoop 对话循环
    ├── session.py                    # SessionManager 会话历史
    └── llm/
        ├── __init__.py               # create_provider 工厂
        ├── base.py                   # LLMProvider ABC
        └── openai.py                 # OpenAI 兼容适配器
```

## 6. 配置参考

服务配置集中在 `settings.py`，通过环境变量覆盖默认值：

| 环境变量                                    | 默认值                          | 说明                                     |
| ------------------------------------------- | ------------------------------- | ---------------------------------------- |
| `AGENT_SERVER_HOST`                         | `0.0.0.0`                       | 监听地址                                 |
| `AGENT_SERVER_PORT`                         | `8888`                          | 监听端口                                 |
| `AGENT_SERVER_LLM_PROVIDER`                 | `deepseek`                      | Provider 名称                            |
| `AGENT_SERVER_SESSION_MAX_TOOL_ROUNDS`      | `10`                            | 单条消息最大工具调用轮数                 |
| `AGENT_SERVER_SESSION_TOOL_TIMEOUT_SEC`     | `30`                            | 单个工具执行超时（秒）                   |
| `AGENT_SERVER_SESSION_HISTORY_MAX_MESSAGES` | `50`                            | 会话保留的最大消息数                     |
| `AGENT_SERVER_AUTH_DB_URL`                  | `sqlite+aiosqlite:///tokens.db` | 数据库连接，留空则跳过认证               |
| `AGENT_SERVER_TIMEZONE`                     | `UTC`                           | ORM 默认时区                             |
| `AGENT_SERVER_PLUGIN_EXTERNAL_DIRS`         | `/plugins`                      | 外部插件目录，多个目录使用系统路径分隔符 |

例如：

```powershell
$env:AGENT_SERVER_PORT = '8888'
$env:AGENT_SERVER_AUTH_DB_URL = 'postgresql+asyncpg://user:pass@host/db'
$env:AGENT_SERVER_PLUGIN_EXTERNAL_DIRS = '/plugins;C:\plugins'
```
