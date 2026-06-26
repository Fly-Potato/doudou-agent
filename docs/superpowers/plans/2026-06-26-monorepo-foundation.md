# Monorepo Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a platform-only monorepo base for future Python, React Native, and Tauri projects.

**Architecture:** pnpm and Turborepo manage the JavaScript/Rust-facing workspace; uv manages the root Python quality environment and later Python workspace. No product application is created. Repository checks validate the base configuration rather than application behavior.

**Tech Stack:** pnpm 11, Turborepo, Prettier, uv, Ruff, GitHub Actions.

---

### Task 1: Specify and validate the repository contract

**Files:**

- Create: `tooling/tests/scaffold.test.mjs`

- [ ] **Step 1: Write the failing structural test**

Create a Node built-in test that requires the root configuration, workspace directories, governance files, CI workflow, and documentation. It must assert that `package.json` has `check`, `format:check`, `lint`, `typecheck`, `test`, and `build` scripts; that the pnpm workspace includes `apps/*` and `packages/*`; and that the virtual Python root does not declare a uv workspace before Python members exist.

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tooling/tests/scaffold.test.mjs`

Expected: FAIL because `package.json` and the remaining base files are absent.

- [ ] **Step 3: Add the minimal repository base**

Create the pnpm/Turbo root configuration, the virtual uv/Ruff project, empty future-project group directories, formatting and Git configuration, CI workflow, and README. Do not create an application manifest, source directory, native mobile directory, Tauri `src-tauri` directory, Cargo workspace, or Python member package.

- [ ] **Step 4: Run the structural test to verify it passes**

Run: `node --test tooling/tests/scaffold.test.mjs`

Expected: PASS with all repository contract assertions green.

### Task 2: Generate and verify dependency locks

**Files:**

- Create: `pnpm-lock.yaml`
- Create: `uv.lock`

- [ ] **Step 1: Generate JavaScript lockfile**

Run: `pnpm install`

- [ ] **Step 2: Generate Python lockfile**

Run: `uv lock`

- [ ] **Step 3: Run quality checks**

Run: `pnpm run check:structure`, `pnpm run format:check`, `uv run ruff check .`, and `uv run ruff format --check .`.

Expected: each command exits with status 0.

### Task 3: Validate CI-equivalent installation

**Files:**

- Verify: `.github/workflows/quality.yml`

- [ ] **Step 1: Verify frozen dependency restoration**

Run: `pnpm install --frozen-lockfile` and `uv sync --locked`.

- [ ] **Step 2: Verify the aggregate repository check**

Run: `pnpm run check`.

Expected: structural validation, formatting validation, Ruff, and Turborepo task discovery complete without error.
