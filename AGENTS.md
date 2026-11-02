# doudou-agent 协作约定

## 项目定位

个人 AI Agent monorepo。服务端使用 Python、FastAPI 和 PydanticAI，集中运行 Agent、模型调用与工具编排；客户端使用 Tauri 2、React、TypeScript、Vite，首期目标为 Android 与 macOS，未来可执行设备工具。

当前仅搭建最小骨架，不增加聊天、认证、数据库、设备网关、MCP、插件框架或空占位抽象，除非任务明确要求。

旧插件式架构已废弃，不恢复插件 SDK、目录扫描、动态加载或自建工具注册框架。后续 Agent 与工具使用 PydanticAI 原生能力，不沿用旧运行时抽象。

## 目录边界

- `apps/doudou-agent-client`：Android/macOS 共用 Tauri 应用，前端与 `src-tauri/` 同目录。
- `services/<name>`：可部署 Python 服务，当前为 `services/agent_server`。
- `packages/<name>`：平台无关 TypeScript 包，当前为空；不得依赖 UI、Tauri 或原生平台 API。
- `tooling/`：仓库质量工具。

不另建 React Native 应用，不新增无实际用途的包、crate、插件或任务。Android 原生工程由 Tauri CLI 生成，不手写生成文件代替初始化。

## 工具链与质量

- Node、pnpm 使用根目录 `mise.toml`，执行前确认 mise 环境；必要时 `mise exec -- <command>`。
- pnpm + Turborepo 管理前端，uv + Ruff 管理 Python；不要额外固定全局工具版本。
- 根目录 `pnpm run check` 检查结构、格式、Python 测试和前端构建。原生改动另运行 Cargo 检查，Android 改动按环境验证原生工程。
- 客户端仅维护真实需要的 dev、build、preview、tauri 脚本，不添加空 lint、test 或 typecheck。

## 协议与安全

- 未来协议优先由服务端定义，变更同步影响客户端；流式协议需明确取消、断线、重连与错误语义。
- 不设计账户、注册、登录或用户资料体系。未来认证使用高熵连接令牌、HTTPS/WSS、服务端安全哈希与客户端平台安全存储。
- 不将完整令牌写入源码、普通配置、日志、异常、分析事件或测试输出。
- 认证或连接协议实现时，覆盖令牌缺失、错误、泄露防护、连接失败及流式中断。

## 语言

新增注释使用中文，仅解释意图、约束或不明显的决策。测试名称、描述与断言失败信息使用中文。面向用户的文档使用中文，标识符和标准协议术语保持英文。

Git 提交采用 Conventional Commits：`<type>: <中文动作式描述>`。
