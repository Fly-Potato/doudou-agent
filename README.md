# doudou-agent

个人 AI Agent 的 monorepo，目前仅提供可启动的最小骨架。

## 结构

- `apps/doudou-agent-client/`：Tauri 2 + React + TypeScript + Vite，Android 与 macOS 共用客户端。
- `services/agent_server/`：FastAPI 服务，仅提供 `GET /health`；已声明 PydanticAI 精简依赖，尚未配置模型。
- `packages/`：平台无关 TypeScript 包，当前为空。
- `libs/`：可复用 Python 库，当前为空。
- `tooling/`：仓库结构检查。

后续架构为服务端运行 Agent，客户端执行设备工具；当前不实现聊天、认证、会话、工具路由、MCP 或数据库。

## 准备环境

Node 与 pnpm 由根目录 `mise.toml` 管理，另需 uv、Rust 与 macOS Command Line Tools。

```sh
mise install
mise exec -- pnpm install
uv sync --directory services/agent_server
mise exec -- pnpm run setup:hooks
```

## 启动

```sh
# 后端，默认仅监听本机；无需模型密钥
mise exec -- pnpm run server:dev
# macOS 应用
mise exec -- pnpm run desktop:dev
# 仅前端预览开发
mise exec -- pnpm --filter doudou-agent-client dev
```

健康检查地址为 `http://127.0.0.1:8000/health`，返回 `{"status":"ok"}`。

## 检查与构建

```sh
mise exec -- pnpm run check
mise exec -- pnpm run test
mise exec -- pnpm run format
mise exec -- pnpm run format:py
# macOS 安装包
mise exec -- pnpm run desktop:build
```

`check` 包含仓库结构、Prettier、Ruff、后端测试及前端 TypeScript/Vite 构建；原生编译另行执行：

```sh
cargo check --manifest-path apps/doudou-agent-client/src-tauri/Cargo.toml
```

JavaScript 与 Python 分别使用 `pnpm-lock.yaml` 和服务目录中的 `uv.lock`。

## Android

Android 工程与 macOS 共用 `apps/doudou-agent-client`。环境安装完成后，参照该目录 README 初始化和构建。

## 约定

文档、注释、测试描述与提交说明使用中文。提交格式为 `<type>: <中文动作式描述>`。
