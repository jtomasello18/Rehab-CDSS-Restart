import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const directory = await mkdtemp(join(tmpdir(), 'aria-scribe-check-'));
try {
  const outfile = join(directory, 'check.cjs');
  await build({ entryPoints: ['tests/clinicalSoap.test.ts'], bundle: true, platform: 'node', format: 'cjs', outfile });
  await import(pathToFileURL(outfile));
} finally {
  await rm(directory, { recursive: true, force: true });
}
