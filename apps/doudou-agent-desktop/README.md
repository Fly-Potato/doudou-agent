# Doudou Agent Desktop

Doudou Agent 的 Tauri 桌面客户端，使用 React、TypeScript 和 Vite 构建。

## 开发命令

```bash
# 在仓库根目录执行
pnpm --filter doudou-agent-desktop dev
pnpm run desktop:dev
pnpm run desktop:build
```

`pnpm --filter doudou-agent-desktop dev` 只启动 Vite 前端；`pnpm run desktop:dev` 会同时启动
Tauri 桌面壳。Tauri 配置中的 `devUrl`、`frontendDist` 和 Vite 开发端口必须保持一致。

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
