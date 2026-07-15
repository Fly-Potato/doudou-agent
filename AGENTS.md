# doudou-agent 协作约定

## 项目定位

这是一个个人 AI Agent 的 monorepo。产品由多个聊天入口客户端和一个服务端构成：

- 桌面端覆盖 Windows、macOS，使用 Tauri。
- 移动端覆盖 iOS、Android，使用 React Native。
- 客户端负责聊天交互、令牌配置和消息展示，不承载实际 AI 推理、工具调用或会话编排。
- 服务端使用 Python，集中处理 AI 请求、会话编排、工具调用和流式响应。

当前仓库提供 monorepo 基座，并已包含 `apps/doudou-agent-desktop` 桌面端应用。除非任务明确要求，不新增其他应用、服务、Rust crate、Android 或 iOS 工程。

## 目录边界

- `apps/<name>-mobile`：React Native 移动端应用。
- `apps/<name>-desktop`：Tauri 桌面端应用；Web 前端与 `src-tauri/` 保持在同一应用目录。
- `services/<name>`：可部署的 Python 服务。
- `libs/<name>`：可复用的 Python 库。
- `packages/<name>`：与平台无关的 TypeScript 包，例如协议类型或客户端 SDK。

当前桌面端：

- `apps/doudou-agent-desktop`：Tauri 2 + React + Vite 桌面客户端。
- `pnpm run desktop:dev`：启动桌面壳和 Vite 开发服务。
- `pnpm run desktop:build`：构建桌面安装包。
- 桌面端暂时只维护有实际用途的 `dev`、`build`、`preview` 和 `tauri` 脚本；不要为了接入 Turbo 而添加空的 lint、typecheck 或 test 任务。

不要让共享 TypeScript 包依赖浏览器、React Native、Tauri、Rust、Android 或 iOS API。桌面端和移动端不共享 UI 组件，除非后续明确设计跨端 UI 方案。

## 客户端与服务端协议

- 对外协议优先定义在服务端契约中，客户端只是其消费者；协议修改必须同步更新所有受影响客户端。
- 聊天流式输出优先使用 HTTPS 上的流式响应或 WSS，并明确断线、取消、重连和错误消息的语义。
- 不实现账户、注册、登录、刷新令牌或用户资料体系。
- 认证采用用户输入的高熵连接令牌。令牌只通过 HTTPS/WSS 传输，服务端保存安全哈希并进行校验；不要将可逆加密字符串当作认证方案。
- 客户端不得把令牌写入源码、普通配置文件、分析事件或日志；需要持久化时使用各平台安全存储。
- 任何日志、异常和测试夹具都不得输出完整令牌；仅可输出脱敏值或不可逆标识。

## 代码、测试与提交语言

- 新增代码注释使用中文，并只解释意图、约束或不明显的设计决策；不要为显而易见的代码添加注释。
- 测试名称、测试描述、测试数据说明和断言失败信息使用中文。
- Git 提交说明使用中文，采用简洁的动作式描述，例如：`新增桌面端令牌安全存储`、`修复流式响应断线处理`。
- 面向用户的文档默认使用中文；接口字段、代码标识符和标准协议术语保持准确的英文命名。

## 质量要求

- JavaScript/TypeScript 使用 `mise` 管理的 Node 和 pnpm 运行环境，并配合 Turborepo；Python 使用 uv 和 Ruff。
- 在执行前端或脚本类命令前，优先确认 `mise` 已初始化并由其提供 `node`、`pnpm`；如果当前 shell 没有自动接管环境，就使用 `mise exec -- <command>` 运行。
- 不要在仓库内额外固定全局 Node 或 pnpm 版本，也不要绕过 `mise.toml` 直接依赖系统环境。
- 在根目录执行 `pnpm run check` 进行结构、格式和质量检查；按任务影响范围补充对应测试。
- 涉及认证或连接协议的修改，至少覆盖令牌缺失、令牌错误、令牌泄露防护、连接失败和流式中断场景。
