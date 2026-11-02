import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

test('仓库基座包含必要目录与配置', () => {
  const requiredPaths = [
    '.editorconfig',
    '.gitattributes',
    '.gitignore',
    '.prettierignore',
    '.prettierrc.json',
    'README.md',
    'package.json',
    'pnpm-workspace.yaml',
    'turbo.json',
    'apps/.gitkeep',
    'packages/.gitkeep',
    'services/.gitkeep',
    'libs/.gitkeep',
    'mise.toml',
    'apps/doudou-agent-client/src-tauri/src/lib.rs',
    'services/agent_server/main.py',
  ];

  for (const relativePath of requiredPaths) {
    assert.equal(
      existsSync(path.join(repositoryRoot, relativePath)),
      true,
      `缺少必要路径 ${relativePath}`,
    );
  }
});

test('根脚本声明完整质量检查', () => {
  const manifest = JSON.parse(readRepositoryFile('package.json'));

  for (const script of [
    'build',
    'check',
    'check:structure',
    'format:check',
    'lint',
    'test',
    'typecheck',
  ]) {
    assert.equal(typeof manifest.scripts?.[script], 'string', `缺少必要脚本 ${script}`);
  }
});

function readRepositoryFile(relativePath) {
  return readFileSync(path.join(repositoryRoot, relativePath), 'utf8');
}
