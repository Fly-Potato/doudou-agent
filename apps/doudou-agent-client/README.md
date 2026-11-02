# Doudou Agent 客户端

Tauri 2 + React + TypeScript + Vite 的最小客户端，Android 与 macOS 共用前端与 Rust 入口，当前仅展示静态页面。

在仓库根目录运行：

```sh
mise exec -- pnpm run desktop:dev
mise exec -- pnpm run desktop:build
```

## Android 环境就绪后

本次初始化因缺少 NDK 未完成，尚未生成 `src-tauri/gen/android/`。安装完成并配置环境变量后运行以下命令；macOS 骨架可独立使用。

按 [Tauri 官方环境要求](https://v2.tauri.app/start/prerequisites/#android) 安装 Android Studio、SDK、NDK、JDK，并配置 `JAVA_HOME`、`ANDROID_HOME`、`NDK_HOME`。不要将本机绝对路径写入仓库。

```sh
rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android
mise exec -- pnpm --filter doudou-agent-client tauri android init
mise exec -- pnpm --filter doudou-agent-client tauri android dev
mise exec -- pnpm --filter doudou-agent-client tauri android build
```

初始化后原生工程位于 `src-tauri/gen/android/`。初始化成功不代表 APK 已编译或真机运行通过，需要另行验证。
