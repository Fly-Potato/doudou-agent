# agent-server 插件开发规范

## 1. 概述

插件（Plugin）是 agent-server 扩展业务能力的标准方式。插件是实现了 SDK 中 `Plugin` 基类的 Python 包，放在固定的 `/plugins` 目录中，由 `PluginManager` 在启动时扫描并加载。

中枢与插件的关系：

- **中枢** 负责 AI 对话循环、LLM 调用、工具（Tool）调度、技能（Skill）激活和 SSE 流式响应
- **插件** 负责注册工具和技能，实现具体业务逻辑（数据库操作、外部 API 集成、文件处理等）
- 插件不介入核心对话循环，但可通过生命周期钩子观察和附加数据

## 2. 快速开始

### 2.1 项目结构

```
doudou-todo/
├── pyproject.toml
├── doudou_todo/
│   ├── __init__.py          # 导出 TodoPlugin
│   └── plugin.py
```

### 2.2 pyproject.toml

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "doudou-todo"
version = "0.1.0"
dependencies = ["doudou-agent-sdk"]
```

插件目录必须包含 `__init__.py`，并在其中导出 `Plugin` 子类。插件包需要能够导入 `doudou-agent-sdk`。

```python
# doudou_todo/__init__.py
from .plugin import TodoPlugin
```

### 2.3 实现插件类

```python
# doudou_todo/plugin.py
from doudou_agent_sdk import Plugin, Tool


class TodoPlugin(Plugin):
    @property
    def name(self) -> str:
        return "doudou-todo"

    def register_tools(self) -> list[Tool]:
        async def add_todo(session_id: str, **params: object) -> dict:
            title: str = params["title"]  # type: ignore
            return {"ok": True, "id": 1, "title": title}

        return [
            Tool(
                name="add_todo",
                description="添加一条待办事项",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "待办事项标题",
                        }
                    },
                    "required": ["title"],
                },
                handler=add_todo,
            )
        ]
```

### 2.4 插件目录

插件固定放置在 `/plugins` 目录，由服务启动时自动扫描。

## 3. Plugin 接口

```python
class Plugin(ABC):
    # ── 必须实现 ──────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一标识"""
        ...

    @abstractmethod
    def register_tools(self) -> list[Tool]:
        """返回插件提供的工具列表，中枢加载时调用"""
        ...

    # ── 可选覆盖 ──────────────────────────────────

    def register_skills(self) -> list[Skill]:
        """返回插件提供的技能列表"""
        return []

    async def on_load(self, config: PluginConfig | dict[str, Any] | None = None) -> None:
        """插件加载时调用"""

    async def on_shutdown(self) -> None:
        """服务关闭时调用，释放资源（数据库连接、网络连接等）"""

    async def on_message(
        self, session_id: SessionId, message: dict
    ) -> dict | None:
        """消息到达时调用。返回修改后的消息，返回 None 表示不修改。"""
        return None

    async def pre_llm_call(
        self, session_id: SessionId, messages: list[dict]
    ) -> list[dict]:
        """LLM 调用前调用。可修改消息列表（注入 system prompt 等）。"""
        return messages

    async def post_llm_call(
        self, session_id: SessionId, response: dict
    ) -> dict:
        """LLM 返回后调用。可修改响应。"""
        return response

    async def on_error(self, session_id: SessionId, error: Exception) -> None:
        """对话循环出错时调用，用于日志/告警。"""
```

### 钩子执行顺序

```
on_load(config, registry)
  ↓
(对话循环中，每条消息)
  on_message(session_id, message)
  pre_llm_call(session_id, messages)
  [LLM 调用]
  post_llm_call(session_id, response)
  └─ on_error(session_id, error)  ← 如果出错
  ↓
on_shutdown()
```

多插件按目录扫描顺序依次执行钩子，前一个的返回值作为下一个的输入。

## 4. Tool 数据结构

```python
@dataclass
class Tool:
    name: str               # 工具名（供 LLM 引用）
    description: str        # 工具说明（LLM 理解何时调用）
    parameters: dict        # OpenAI function-calling JSON Schema
    handler: Callable       # async (session_id, **params) -> Any
```

### 参数说明

| 字段          | 说明                                                                   |
| ------------- | ---------------------------------------------------------------------- |
| `name`        | 插件内唯一，建议带前缀避免冲突，如 `todo_add`                          |
| `description` | 清晰描述工具用途，影响 LLM 调用准确性                                  |
| `parameters`  | JSON Schema，与 OpenAI function-calling 格式兼容                       |
| `handler`     | 签名 `async (session_id: str, **params) -> Any`，中枢注入 `session_id` |

### handler 规范

- 必须为 `async` 函数
- 第一个参数 `session_id` 由中枢自动传入，无需在 JSON Schema 中声明
- 返回值会被 `json.dumps()` 序列化后传回 LLM
- 工具执行默认超时 30 秒（可在 `session.tool_timeout_sec` 配置）
- 不捕获异常时由中枢统一处理（回传错误信息给 LLM 并调用 on_error 钩子）

### parameters JSON Schema 示例

```python
{
    "type": "object",
    "properties": {
        "task_id": {
            "type": "integer",
            "description": "待办事项 ID"
        },
        "title": {
            "type": "string",
            "description": "新的标题"
        }
    },
    "required": ["task_id", "title"]
}
```

## 5. Skill 数据结构

技能（Skill）是更高层次的能力封装，包含操作指令和关联工具。Skill 采用懒加载模式——启动时只注入摘要，LLM 在运行时通过 `load_skill` 工具动态加载完整内容。

```python
@dataclass
class Skill:
    name: str            # 技能名，如 "todo_management"
    description: str     # 简短摘要（始终注入 system prompt）
    content: str         # 完整操作指令（LLM 调用 load_skill 时返回）
    tools: list[str]     # 关联的工具名（可选）
```

### 技能定义示例

```python
class TodoPlugin(Plugin):
    def register_skills(self) -> list[Skill]:
        return [
            Skill(
                name="todo_management",
                description="管理待办事项：添加、查询、更新、删除、总结",
                content=(
                    "当用户需要管理待办事项时，使用以下工具：\n"
                    "- add_todo: 添加新待办\n"
                    "- list_todos: 查询待办列表\n"
                    "- update_todo: 更新待办状态\n"
                    "- summarize_todos: 对待办进行总结分析\n\n"
                    "注意事项：\n"
                    "- 添加时 title 为必填\n"
                    "- 更新时至少提供一个要修改的字段"
                ),
                tools=["add_todo", "list_todos", "update_todo", "summarize_todos"],
            )
        ]
```

### 激活机制

- 启动阶段：中枢将所有已注册技能的 `description` 注入 system prompt，并注册 `load_skill` 工具
- 运行时：LLM 识别用户意图后，调用 `load_skill("todo_management")` 获取完整指令
- `load_skill` 的返回内容包含 skill 的 `content` 和可用工具列表，LLM 据此执行具体操作

## 6. 配置

外部插件固定放在 `/plugins` 目录：

- `/plugins` 下的每个一级子目录都必须包含 `__init__.py`
- 插件目录中必须定义一个 `Plugin` 子类
- 当前版本按目录加载插件，不支持单独启用或禁用插件

## 7. 发布与分发

插件作为独立 Python 包发布：

1. 包名建议使用 `doudou-<name>` 命名空间
2. 声明依赖 `doudou-agent-sdk`
3. 将插件包目录挂载或复制到固定的 `/plugins` 目录
4. 重启服务，由 `PluginManager` 扫描并加载

```text
/plugins/doudou_todo/__init__.py
/plugins/doudou_search/__init__.py
```

## 8. 完整示例

### todo 插件完整代码

```python
# doudou_todo/plugin.py
from doudou_agent_sdk import Plugin, Skill, Tool

# 模拟数据库
_TODOS: list[dict] = []
_next_id = 1


class TodoPlugin(Plugin):
    @property
    def name(self) -> str:
        return "doudou-todo"

    def register_tools(self) -> list[Tool]:
        async def add_todo(session_id: str, **params: object) -> dict:
            global _next_id
            title = str(params.get("title", ""))
            todo = {"id": _next_id, "title": title, "done": False}
            _TODOS.append(todo)
            _next_id += 1
            return todo

        async def list_todos(session_id: str, **params: object) -> list[dict]:
            return _TODOS

        async def update_todo(session_id: str, **params: object) -> dict:
            todo_id = int(params.get("id", 0))
            for t in _TODOS:
                if t["id"] == todo_id:
                    if "title" in params:
                        t["title"] = str(params["title"])
                    if "done" in params:
                        t["done"] = bool(params["done"])
                    return t
            return {"error": "not found"}

        return [
            Tool(name="add_todo", description="添加待办事项",
                 parameters={"type": "object", "properties": {
                     "title": {"type": "string"}}, "required": ["title"]},
                 handler=add_todo),
            Tool(name="list_todos", description="查询待办列表",
                 parameters={"type": "object", "properties": {}},
                 handler=list_todos),
            Tool(name="update_todo", description="更新待办状态",
                 parameters={"type": "object", "properties": {
                     "id": {"type": "integer"},
                     "title": {"type": "string"},
                     "done": {"type": "boolean"}},
                     "required": ["id"]},
                 handler=update_todo),
        ]

    def register_skills(self) -> list[Skill]:
        return [
            Skill(
                name="todo_management",
                description="管理待办事项：添加、查询、更新",
                content=(
                    "使用 add_todo 添加待办，list_todos 查询列表，"
                    "update_todo 更新状态。title 为必填字段。"
                ),
                tools=["add_todo", "list_todos", "update_todo"],
            )
        ]

    async def on_load(self, config: dict, registry=None) -> None:
        # 读取插件配置，初始化数据库连接等
        db_url = config.get("db_url", "sqlite:///todos.db")
        # 初始化连接...
```
