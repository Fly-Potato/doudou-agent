# doudou-agent

> ⚠️ 项目处于早期开发阶段。API、配置格式、插件接口均可能发生不兼容变更。

doudou-agent 的 monorepo，包含 Python 服务、可复用库和桌面客户端基础。

## Toolchains

- **pnpm 11 + Turborepo** manages future JavaScript and TypeScript packages. It is the task runner
  for React Native and Tauri application commands.
- **uv** manages repository-level Python quality tools and, after Python packages exist, the Python
  workspace.
- **Ruff** formats and lints Python. **Prettier** formats repository configuration, documentation,
  and JavaScript/TypeScript.

The two dependency graphs remain separate: `pnpm-lock.yaml` is the JavaScript lockfile and `uv.lock`
is the Python lockfile.

## Layout

| Directory   | Future contents                                                                |
| ----------- | ------------------------------------------------------------------------------ |
| `apps/`     | 产品应用，当前包含 `doudou-agent-desktop`（Tauri + React）。                   |
| `packages/` | Platform-neutral TypeScript packages.                                          |
| `services/` | Deployable Python services。当前：`agent-server` AI 后端服务。                 |
| `libs/`     | Python libraries, including `doudou-agent-sdk`（插件开发 SDK）和其他可复用库。 |
| `tooling/`  | Repository checks and maintenance tooling.                                     |

React Native and Tauri applications do not share UI packages. A shared TypeScript package must not
depend on browser APIs, React Native APIs, Android/iOS code, Tauri APIs, or Rust bindings.

## agent-server

`services/agent_server/` 是 doudou-agent 的 AI 后端服务，采用插件式架构设计：

- **中枢** 负责对话循环、LLM 调用、工具调度和 SSE 流式响应
- **插件** 通过 Python 包目录扫描注册工具（Tool）和技能（Skill），支持自由开发
- **Skill** 按需加载的领域能力单元，含操作指令和关联工具，LLM 运行时决定激活
- **MCP** 内置插件支持连接 Model Context Protocol 服务器，自动发现外部工具

### 快速开始

```bash
cd services/agent_server
# 1. 设置数据库等运行时环境变量
# 2. 生成访问令牌
uv sync
uv run agent-server generate-token   # 输出原始 token，请求 API 时使用
# 3. 启动服务
uv run agent-server serve --host 0.0.0.0 --port 8888
```

### 开发插件

1. 新建 Python 包，继承 `doudou_agent_sdk.Plugin`
2. 实现 `name`、`register_tools()`，可选 `register_skills()` 和生命周期钩子
3. 将插件包放入固定的 `/plugins` 目录，目录中包含 `__init__.py`：

```text
/plugins/my_plugin/__init__.py
```

4. 重启服务，服务会自动扫描 `/plugins` 下的一级子目录。

### 技术栈

Python 3.12+, FastAPI, openai SDK, MCP SDK, SQLAlchemy 2.0, aiosqlite (开发), asyncpg (生产)

## doudou-agent-desktop

`apps/doudou-agent-desktop/` 是基于 Tauri 2、React 和 Vite 的桌面客户端。桌面端的 Web 前端与
`src-tauri/` Rust 壳保持在同一应用目录中。

```bash
# 启动 Vite 前端
pnpm --filter doudou-agent-desktop dev

# 启动 Tauri 桌面应用
pnpm run desktop:dev

# 构建桌面安装包
pnpm run desktop:build
```

## First-time setup

```sh
pnpm install
pnpm run setup:hooks
cd services/agent_server && uv sync
```

The `setup:hooks` command activates `.githooks/pre-commit`, which runs `lint-staged` on staged
files. Commit the hook as executable on POSIX systems.

## Git 提交规范

提交信息采用 Conventional Commits 格式：

```text
<type>: <中文动作式描述>
```

常用类型如下：

- `feat`：新增功能
- `fix`：修复问题
- `refactor`：重构代码，不改变功能
- `docs`：仅修改文档
- `test`：新增或修改测试
- `chore`：维护构建、依赖或工具配置

描述应使用中文、简洁明确，并以动作式短语说明变更内容。例如：

```text
feat: 新增可配置时区支持
fix: 修复流式响应断线处理
refactor: 下沉 LLM Provider 到 SDK
docs: 完善 agent-server 服务文档
```

## Commands

| Command              | Purpose                                                                        |
| -------------------- | ------------------------------------------------------------------------------ |
| `pnpm run check`     | Run repository structure, formatting, Python checks, and future package tasks. |
| `pnpm run format`    | Format repository files with Prettier.                                         |
| `pnpm run lint`      | Check repository formatting, Python linting, and future package lint tasks.    |
| `pnpm run typecheck` | Run future TypeScript package type-check tasks.                                |
| `pnpm run test`      | Run structure checks and future package tests.                                 |
| `pnpm run build`     | Build future packages in dependency order.                                     |

## Adding the first project

### React Native mobile app

Create the app under `apps/<product>-mobile`. Its `package.json` must provide `dev`, `lint`,
`typecheck`, `test`, and `build` scripts. Configure the Android and iOS projects explicitly for
the monorepo root and pnpm dependency layout.

### Tauri desktop app

Create the app under `apps/<product>-desktop`. Keep its web frontend and `src-tauri/` Rust shell in
the same application directory. Start with meaningful package scripts only; configure the Tauri
`devUrl`, frontend distribution path, and pre-build commands within that app. Add lint, typecheck,
or test scripts when the application has a real implementation and corresponding checks.

### Python service or library

Create a `pyproject.toml` inside `services/<name>` or `libs/<name>` as a standalone Python project.
If it depends on `doudou-agent-sdk`, add a source reference:

```toml
[tool.uv.sources]
doudou-agent-sdk = { path = "../../libs/doudou-agent-sdk" }
```

```sh
uv sync
```
