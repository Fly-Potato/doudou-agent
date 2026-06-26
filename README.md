# doudou-agent

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
| `services/` | Deployable Python services.                                                                      |
| `libs/`     | Reusable Python libraries.                                                                       |
| `tooling/`  | Repository checks and maintenance tooling.                                                       |

React Native and Tauri applications do not share UI packages. A shared TypeScript package must not
depend on browser APIs, React Native APIs, Android/iOS code, Tauri APIs, or Rust bindings.

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
