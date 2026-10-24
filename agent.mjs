import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { encode } from '@toon-format/toon';

const root = path.dirname(fileURLToPath(import.meta.url));
const flags = { home: [], models: [], inspect: ['source'], verify: ['output'],
  create: ['source', 'brief', 'transcript', 'translations', 'output'] };
const required = { inspect: ['source'], verify: ['output'], create: ['source', 'brief', 'output'] };
const args = process.argv.slice(2), json = args.includes('--json');
const output = value => process.stdout.write(json ? JSON.stringify(value) + '\n' : encode(value));
const stop = (code, hint) => { output({ status: 'stopped', code, hint }); process.exit(2); };
const values = args.filter(x => x !== '--json');
const explicit = Boolean(values[0] && !values[0].startsWith('--'));
const command = explicit ? values[0] : 'home';
if (!Object.hasOwn(flags, command)) stop('USAGE', 'Commands: models, inspect, create, verify. Add --help.');
if (values.includes('--help')) {
  output({ bin: fileURLToPath(import.meta.url), description: 'Create a local English-to-French stock-voice dubbing proof.',
    command, flags: [...flags[command].map(x => '--' + x), '--json', '--help'],
    required: required[command] || [],
    examples: ['node agent.mjs inspect --source <video.mp4>',
      'node agent.mjs create --source <video.mp4> --brief <brief.json> --output <new-directory>'] });
  process.exit(0);
}
const supplied = new Set();
for (let i = explicit ? 1 : 0; i < values.length; i += 2) {
  const flag = values[i];
  if (!flags[command].some(x => '--' + x === flag) || supplied.has(flag) ||
      !values[i + 1] || values[i + 1].startsWith('--'))
    stop('USAGE', `Valid flags: ${flags[command].map(x => '--' + x).join(', ')}, --json, --help.`);
  supplied.add(flag);
}
if ((required[command] || []).some(x => !supplied.has('--' + x)))
  stop('USAGE', `Required flags: ${(required[command] || []).map(x => '--' + x).join(', ')}. Add --help.`);
const python = process.env.DUBBING_PYTHON || path.join(root, '.venv/bin/python');
if (!fs.existsSync(python)) {
  output({ status: 'stopped', code: 'ENVIRONMENT_REQUIRED', hint: 'Create .venv and install requirements.txt.' });
  process.exit(1);
}
const child = spawnSync(python, [path.join(root, 'backend.py'), ...(values.length ? values : ['home'])],
  { encoding: 'utf8', maxBuffer: 1048576 });
try {
  const value = JSON.parse(child.stdout);
  if (!value || typeof value !== 'object' || typeof value.status !== 'string') throw new Error();
  output(value);
} catch {
  output({ status: 'stopped', code: 'PROCESS_FAILED', hint: 'Check the local environment and input files.' });
  process.exit(1);
}
process.exit(child.status === 0 ? 0 : child.status === 2 ? 2 : 1);
