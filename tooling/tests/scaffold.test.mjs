import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

function readRepositoryFile(relativePath) {
  return readFileSync(path.join(repositoryRoot, relativePath), 'utf8');
}

test('repository base declares all required top-level assets', () => {
  const requiredPaths = [
    '.editorconfig',
    '.gitattributes',
    '.gitignore',
    '.github/workflows/quality.yml',
    '.prettierignore',
    '.prettierrc.json',
    'README.md',
    'package.json',
    'pnpm-workspace.yaml',
    'pyproject.toml',
    'turbo.json',
    'apps/.gitkeep',
    'packages/.gitkeep',
    'services/.gitkeep',
    'libs/.gitkeep',
  ];

  for (const relativePath of requiredPaths) {
    assert.equal(
      existsSync(path.join(repositoryRoot, relativePath)),
      true,
      `${relativePath} is required`,
    );
  }
});

test('root scripts expose the repository quality contract', () => {
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
    assert.equal(typeof manifest.scripts?.[script], 'string', `${script} script is required`);
  }
});

test('workspace configuration separates platform and Python concerns', () => {
  const pnpmWorkspace = readRepositoryFile('pnpm-workspace.yaml');
  const pythonProject = readRepositoryFile('pyproject.toml');

  assert.match(pnpmWorkspace, /- 'apps\/\*'/);
  assert.match(pnpmWorkspace, /- 'packages\/\*'/);
  assert.match(pythonProject, /package = false/);
  assert.doesNotMatch(pythonProject, /\[tool\.uv\.workspace\]/);
});

test('CI only runs on master and relevant repository paths', () => {
  const workflow = readRepositoryFile('.github/workflows/quality.yml');

  assert.match(workflow, /push:\s*\r?\n\s+branches:\s*\r?\n\s+- master/);
  assert.match(workflow, /pull_request:\s*\r?\n\s+branches:\s*\r?\n\s+- master/);

  for (const pathEntry of [
    '.github/workflows/quality.yml',
    'apps/**',
    'libs/**',
    'packages/**',
    'services/**',
    'tooling/**',
    'package.json',
    'pnpm-lock.yaml',
    'pnpm-workspace.yaml',
    'pyproject.toml',
    'turbo.json',
    'uv.lock',
  ]) {
    assert.equal(workflow.includes(pathEntry), true, `missing ${pathEntry}`);
  }
});
