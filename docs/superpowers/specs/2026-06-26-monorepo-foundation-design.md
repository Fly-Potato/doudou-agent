# Monorepo Foundation Design

## Decision

Create a platform-only monorepo foundation. It contains no Python service or library, React Native application, Tauri application, or Rust crate.

The repository uses two dependency workspaces:

- pnpm and Turborepo for future JavaScript, TypeScript, React Native, and Tauri packages.
- uv for Python tooling now and a Python workspace once Python projects are added.

## Structure

- `apps/` will contain product applications, including separate React Native mobile and Tauri desktop applications.
- `packages/` will contain platform-neutral TypeScript packages.
- `services/` will contain deployable Python services.
- `libs/` will contain reusable Python libraries.
- `tooling/` contains repository verification only.

React Native and Tauri must not share UI packages. They may share a package only when it is independent of browser, native mobile, and Rust APIs.

## Governance

The root owns formatting, static checks, task orchestration, documentation, Git defaults, and a GitHub Actions quality workflow. Application dependencies stay in application packages. The root Python project is virtual (`package = false`) and becomes a uv workspace only after the first Python member exists; uv requires every matched member directory to contain `pyproject.toml`.
