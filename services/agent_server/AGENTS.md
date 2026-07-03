# agent-server 协作约定

## 服务定位

doudou-agent monorepo 的 AI 后端服务。FastAPI + SSE 流式响应，插件式架构。

## 核心命令

```bash
# 启动开发服务（uvicorn 带 reload）
uv run python main.py serve

# 令牌管理
uv run python main.py generate-token   # 生成新令牌（输出一次即不可见）
uv run python main.py list-tokens      # 列出令牌（仅 ID 和时间，不含哈希）
uv run python main.py delete-token 1   # 删除令牌

# 测试
uv run pytest                                             # 全部测试
uv run pytest tests/test_auth.py -k "test_correct_token"  # 单个测试

# 代码质量
uv run ruff check . && uv run ruff format --check .
```

## 架构关键点

- **`AgentLoop`** (`agent/loop.py:20`): 核心运行时，每条 `/chat` 请求启动一次循环，SSE 推送 token / tool_call / tool_result / done / error 事件
- **插件发现**: 通过 `importlib.metadata.entry_points(group="doudou_agent.plugins")` 自动发现，非硬编码导入
- **工具 handler 签名**: `async (session_id: str, **params) -> Any`，`session_id` 由中枢自动注入，**不要在 JSON Schema 中声明**
- **`EventBus`**: 按 YAML 配置顺序串行调用插件钩子，前一个返回值作为下一个的输入
- **`SessionManager`** (`agent/session.py`): 内存存储，连接断开历史丢失；按 `history_max_messages` 裁剪
- **`ToolRegistry`**: 同名工具后加载覆盖先加载（打印警告 `被覆盖`）

## 配置

- 配置文件 `agent-server.yaml`，支持 `${ENV_VAR}` 环境变量替换
- `auth.db_url` 为空字符串时**跳过认证**；开发用 SQLite，生产用 PostgreSQL
- `llm.type` 目前仅支持 `openai`（通过 `base_url` 兼容 DeepSeek / Ollama / OpenRouter）
- 插件 `plugins[].name` 必须与 `Plugin.name` 属性一致

## 插件开发

- `Plugin` 必须实现 `name` 属性和 `register_tools()` 方法
- `on_message` / `pre_llm_call` 返回 `None` 表示不修改，返回 `dict`/`list` 则替换
- `Tool.handler` 不捕获异常时由中枢统一处理（回传错误给 LLM + 调用 `on_error` 钩子）
- 依赖 `agent-server` 时版本建议宽松（如 `>=0.1`）

## 测试

- `pytest.ini_options.asyncio_mode = "auto"`，测试函数直接标记 `async` 即可
- 认证/令牌测试使用 `sqlite+aiosqlite:///:memory:`
- `tests/conftest.py` 提供 `DummyPlugin` 夹具

## 安全

- 日志中令牌必须脱敏（`auth.py:_mask_token` — 前 4 位 + `***`），测试夹具同理
- 令牌存储使用 SHA-256 哈希，禁止可逆加密
- `TokenStore` 不接受外部传入的哈希值，只接受原始令牌

## 开发规范

- Ruff: line-length=100, target-version=py312，启用 E/F/I/B/UP 规则
- 测试名描述使用中文，断言失败信息使用中文
- 代码注释使用中文，仅解释意图和不明显的设计决策

## 参考资料

- `docs/architecture.md` — 完整架构、SSE 协议、配置参考
- `docs/plugin-spec.md` — 插件开发规范、完整示例
