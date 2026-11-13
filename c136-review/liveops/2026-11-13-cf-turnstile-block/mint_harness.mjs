// Test the engine's real donor + mint code without starting the 40 bots: cut the donor/mint block
// out of an engine file (normally the patch preview), run mints through it, print what happened.
// The block is used verbatim; only the "launch all four donors" loop is dropped and the proxy-session
// rotation is stubbed out. Mints made here are counted in the same hourly budget file as the engine.
// Token values are never printed, only their length.
// Run with cwd = c116:
//   node_apex.exe ..\c136\mint_harness.mjs <engineFile> seq <n>     n mints one after another
//   node_apex.exe ..\c136\mint_harness.mjs <engineFile> par <n>     n mints started together
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const engineFile = path.resolve(process.argv[2] || 'tsb-apex-squad.preview-patientmint.mjs');
const mode = process.argv[3] || 'seq';
const count = Math.max(1, Math.min(4, Number(process.argv[4] || 1)));
const src = fs.readFileSync(engineFile, 'utf8').replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
const a = src.indexOf("import { execSync } from 'node:child_process';");
const b = src.indexOf('// Centralized Backend Spawn Coordinator');
if (a < 0 || b < 0 || b < a) { console.log('[HARNESS] ' + JSON.stringify({ error: 'markers not found', a, b })); process.exit(1); }
let block = src.slice(a, b);
const loopRe = /for \(const ffPort of \[9228, 9229, 9230, 9231\]\) \{\n[^\n]*\n\}\n/;
if (!loopRe.test(block)) { console.log('[HARNESS] ' + JSON.stringify({ error: 'donor init loop not found' })); process.exit(1); }
block = block.replace(loopRe, '');

const header = `import fs from 'node:fs';
import path from 'node:path';
const __dirname = process.cwd();
const __t0 = Date.now();
const __log = console.log.bind(console);
console.log = (...x) => __log('+' + ((Date.now() - __t0) / 1000).toFixed(1) + 's', ...x);
console.warn = console.log;
console.error = console.log;
function rotateSocksSession() { console.log('[HARNESS] proxy rotation skipped'); return Promise.resolve(false); }
`;
const trailer = `
const __mode = ${JSON.stringify(mode)};
const __count = ${count};
const __one = async (k) => {
  const t0 = Date.now();
  try {
    const tok = await mintViaDonorChrome(9228);
    return { k, ok: true, sec: +((Date.now() - t0) / 1000).toFixed(1), tokenLen: String(tok).length };
  } catch (e) {
    return { k, ok: false, sec: +((Date.now() - t0) / 1000).toFixed(1), err: String(e?.message || e).slice(0, 120) };
  }
};
const __results = [];
if (__mode === 'par') {
  __results.push(...(await Promise.all(Array.from({ length: __count }, (_, k) => __one(k)))));
} else {
  for (let k = 0; k < __count; k++) __results.push(await __one(k));
}
await new Promise((r) => setTimeout(r, 300));
console.log('[HARNESS] ' + JSON.stringify({
  mode: __mode, results: __results, slotFreeNow: mintSlotFree(0), knobs: mintKnobs(), mintsLastHour: mintsLastHour(),
  inflight: Array.from(donorMintInflight), failStreak: Array.from(donorFailStreak),
  cooldownSec: Array.from(donorCooldownUntil).map(([p, t]) => [p, Math.round((t - Date.now()) / 1000)]),
  donorsOpen: Array.from(firefoxDonors.keys())
}));
for (const [port, d] of Array.from(firefoxDonors)) {
  try { await d.callBidi('browser.close', {}); } catch {}
  try { d.ws.close(); } catch {}
  killFirefoxOnPort(port);
}
process.exit(0);
`;
const gen = path.join(path.dirname(engineFile), '_mint_harness_gen.mjs');
fs.writeFileSync(gen, header + block + trailer, 'utf8');
try {
  await import(pathToFileURL(gen).href);
} catch (e) {
  console.log('[HARNESS] ' + JSON.stringify({ error: 'harness crashed: ' + String(e?.stack || e).slice(0, 600) }));
  process.exit(1);
}
