# doudou-agent

> ⚠️ 项目处于早期开发阶段。API、配置格式、插件接口均可能发生不兼容变更。

Platform-only monorepo foundation for future Python services and libraries, React Native mobile
applications, and Tauri desktop applications. This repository intentionally contains no application,
service, package, Cargo crate, Android project, iOS project, or Tauri `src-tauri` directory.

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

| Directory   | Future contents                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------ |
| `apps/`     | Product applications, such as `<product>-mobile` (React Native) and `<product>-desktop` (Tauri). |
| `packages/` | Platform-neutral TypeScript packages.                                                            |
| `services/` | Deployable Python services。当前：`agent-server` AI 后端服务。                                   |
| `libs/`     | Reusable Python libraries.                                                                       |
| `tooling/`  | Repository checks and maintenance tooling.                                                       |

React Native and Tauri applications do not share UI packages. A shared TypeScript package must not
depend on browser APIs, React Native APIs, Android/iOS code, Tauri APIs, or Rust bindings.

## agent-server

`services/agent-server/` 是 doudou-agent 的 AI 后端服务，采用插件式架构设计：

- **中枢** 负责对话循环、LLM 调用、工具调度和 SSE 流式响应
- **插件** 通过 Python entry_points 注册工具（Tool）和技能（Skill），支持自由开发
- **Skill** 按需加载的领域能力单元，含操作指令和关联工具，LLM 运行时决定激活
- **MCP** 内置插件支持连接 Model Context Protocol 服务器，自动发现外部工具

### 快速开始

```bash
cd services/agent-server
# 1. 编辑 agent-server.yaml，填入 llm.api_key
# 2. 生成访问令牌
uv sync
uv run agent-server generate-token   # 输出原始 token，请求 API 时使用
# 3. 启动服务
uv run agent-server serve
```

### 开发插件

1. 新建 Python 包，继承 `agent_server.plugin.base.Plugin`
2. 实现 `name`、`register_tools()`，可选 `register_skills()` 和生命周期钩子
3. 在 `pyproject.toml` 注册 entry_point：

```toml
[project.entry-points."doudou_agent.plugins"]
my-plugin = "my_plugin.module:MyPlugin"
```

4. 在 `agent-server.yaml` 中启用：

```yaml
plugins:
  - name: my-plugin
    enabled: true
    config: {}
```

### 技术栈

Python 3.12+, FastAPI, openai SDK, PyYAML, MCP SDK, SQLAlchemy 2.0, aiosqlite (开发), asyncpg (生产)

## First-time setup

```sh
git init
pnpm install
uv lock
uv sync
pnpm run setup:hooks
```

The `setup:hooks` command activates `.githooks/pre-commit`, which runs `lint-staged` on staged
files. Commit the hook as executable on POSIX systems.

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
the same application directory. Its `package.json` must provide `dev`, `lint`, `typecheck`, `test`,
and `build` scripts; configure the Tauri `devUrl`, frontend distribution path, and pre-build commands
within that app.

### Python service or library

Create a `pyproject.toml` inside `services/<name>` or `libs/<name>`. Then add the following table to
the root `pyproject.toml` and regenerate the lockfile:

```toml
[tool.uv.workspace]
members = ["services/*", "libs/*"]
```

```sh
uv lock
uv sync
```

Do not add the workspace table before at least one matching member contains a `pyproject.toml`; uv
requires every matched workspace member directory to be a Python project.
