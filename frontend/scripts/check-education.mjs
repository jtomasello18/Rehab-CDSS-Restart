import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const directory = await mkdtemp(join(tmpdir(), 'aria-education-check-'));
try {
  const outfile = join(directory, 'check.cjs');
  await build({ entryPoints: ['tests/education.test.tsx'], bundle: true, platform: 'node', format: 'cjs', outfile,
    loader: { '.svg': 'dataurl', '.css': 'empty' } });
  await import(pathToFileURL(outfile));
} finally {
  await rm(directory, { recursive: true, force: true });
}
