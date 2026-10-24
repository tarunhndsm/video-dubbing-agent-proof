import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

for (const args of [['--unknown'], ['create', '--sorce', 'a'], ['create', '--source', 'a'],
  ['verify', '--output', 'x', '--output', 'y'], ['models', '--source', 'a']]) {
  test('usage validation before environment access: ' + args.join(' '), () => {
    const child = spawnSync(process.execPath, ['agent.mjs', ...args, '--json'], {
      encoding: 'utf8', cwd: import.meta.dirname,
      env: { ...process.env, DUBBING_PYTHON: '/no/dubbing/python' }
    });
    assert.equal(child.status, 2);
    assert.equal(JSON.parse(child.stdout).code, 'USAGE');
    assert.equal(child.stderr, '');
  });
}
test('help does not require a Python environment', () => {
  const child = spawnSync(process.execPath, ['agent.mjs', 'create', '--help', '--json'], {
    encoding: 'utf8', cwd: import.meta.dirname,
    env: { ...process.env, DUBBING_PYTHON: '/no/dubbing/python' }
  });
  assert.equal(child.status, 0);
  assert.deepEqual(JSON.parse(child.stdout).required, ['source', 'brief', 'output']);
});
