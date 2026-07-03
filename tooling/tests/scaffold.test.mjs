import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

test('repository base declares all required top-level assets', () => {
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

function readRepositoryFile(relativePath) {
  return readFileSync(path.join(repositoryRoot, relativePath), 'utf8');
}
