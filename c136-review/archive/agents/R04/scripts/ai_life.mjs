#!/usr/bin/env node
// ai_life.mjs — 真引擎重放，记下每个内置 AI（引擎编号 ≥ 真人数）的「生卒」：
//   第一次有地的拍、领土峰值与峰值拍、出局拍（在场标志从 1 变 0 的那一拍；没出局记 -1）、出局前一拍的领土。
// 用来核对「我方指令落地时，它当初瞄的那个内置 AI 还在不在场」（scripts/batch_targets.py 读这张表）。
// 用法：node scripts/ai_life.mjs <局号> [--to 1700]      写到 tmp/truth/<局号>/ai_life.tsv
// 重活，请用：HEAVY_QUEUE=90 timeout 118 bash ../../tools/run-heavy.sh node scripts/ai_life.mjs <局号> --to 1700
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startEngine } from './shadow.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const to = +opt('--to', 1700);
if (!mid) { console.error('用法：node scripts/ai_life.mjs <局号> [--to 1700]'); process.exit(2); }

const { info, api } = startEngine(mid);
const N = info.players, ku = info.ku;
const terr = new Int32Array(N), bal = new Int32Array(N), peak = new Int32Array(N), alive = new Uint8Array(N), state = new Uint8Array(N), debt = new Int32Array(N);
const x0 = new Int32Array(N), y0 = new Int32Array(N), x1 = new Int32Array(N), y1 = new Int32Array(N);
let st = api.advance(1);
while (st[1] === 1 && st[2] !== 2) st = api.advance(1);
const born = new Int32Array(N).fill(-1), dead = new Int32Array(N).fill(-1), pk = new Int32Array(N), pkT = new Int32Array(N).fill(-1), lastTerr = new Int32Array(N), was = new Uint8Array(N);
while (st[2] !== 2 && st[0] <= to) {
  api.players(terr, bal, peak, alive, state, debt, x0, y0, x1, y1);
  const t = st[0];
  for (let p = ku; p < N; p++) {
    if (alive[p] && terr[p] > 0) {
      if (born[p] < 0) born[p] = t;
      if (terr[p] > pk[p]) { pk[p] = terr[p]; pkT[p] = t; }
      was[p] = 1; lastTerr[p] = terr[p];
    } else if (was[p] && dead[p] < 0) {
      dead[p] = t;
    }
  }
  st = api.advance(1);
}
const rows = ['p\tborn\tpeak\tpeakTick\tdead\tlastTerr'];
let nDead = 0, nAll = 0;
for (let p = ku; p < N; p++) {
  if (born[p] < 0) continue;
  nAll++; if (dead[p] >= 0) nDead++;
  rows.push([p, born[p], pk[p], pkT[p], dead[p], lastTerr[p]].join('\t'));
}
const out = path.join(HERE, '..', 'tmp', 'truth', mid, 'ai_life.tsv');
fs.writeFileSync(out, rows.join('\n') + '\n');
console.log(`# ${mid} 内置 AI 生卒表：有过地的 ${nAll} 个，到第 ${Math.min(to, st[0])} 拍为止出局 ${nDead} 个；写到 ${path.relative(path.join(HERE, '..'), out)}`);
