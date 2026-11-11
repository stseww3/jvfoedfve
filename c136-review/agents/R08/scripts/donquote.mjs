#!/usr/bin/env node
// donquote.mjs — 给 donrej.py 用：对 out/<mid>/don_unexec.json 里每一笔「日志有、录像没有」的捐款，
// 在真引擎重演里从它的本地拍 t 起 400 拍，逐拍判断「如果这一拍执行，会不会成交；不成交卡在哪一环」。
// 环节顺序与引擎 donate() 一致（src/sim/sim/game.js L404-416）：捐出方能动 → 受捐方活着 → 是队友 → 硬上限余量 → 受捐额度。
//   bash c136-review/tools/run-heavy.sh node donquote.mjs <matchId> [--replay-from X] [--peer X]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k) => (args.includes(k) ? args[args.indexOf(k) + 1] : undefined);
const odir = path.join(HERE, '..', 'out', mid);
const list = JSON.parse(fs.readFileSync(path.join(odir, 'don_unexec.json'), 'utf8'));
const SPAN = 400;
const iV = (a, b) => Math.floor(a / b);
for (const d of list) { d.seq = []; d.qAt = {}; d.last = null; }
const tMax = list.reduce((m, d) => Math.max(m, d.t + SPAN), 0);

function code(g, d) {
  const p = d.donor, q = d.to;
  if (!g.canAct(p)) return 5;
  if (q >= 512 || g.alive[q] === 0) return 1;
  if (!g.isTeammate(p, q)) return 2;
  const B = g.bal[p];
  const fee = iV(64 * B, 1024);
  let v = Math.min(iV(B * (d.pct + 1), 1024), B - fee);
  v = g.receiverRoom(q, v);
  if (v < 1) return g.terr[q] * 150 - g.bal[q] < 1 ? 3 : 6;
  if (!g.canReceive(q, v)) return 4;
  return 0;
}

resim(mid, {
  quiet: true, noWrite: true, until: tMax + 1, replayFrom: opt('--replay-from'), peer: opt('--peer'), peerTag: opt('--peer-tag'),
  onTick(g) {
    for (const d of list) {
      if (g.t < d.t || g.t > d.t + SPAN) continue;
      const c = code(g, d);
      if (c !== d.last) { d.seq.push([g.t, c]); d.last = c; }
      if (c === 4 && (g.t - d.t) % 1 === 0) {
        const B = g.bal[d.donor];
        const v = g.receiverRoom(d.to, Math.min(iV(B * (d.pct + 1), 1024), B - iV(64 * B, 1024)));
        d.qAt[g.t] = `${g.donQuota[d.to]}+${g.donationCost(d.to, v)}>${g.donCap}`;
      }
      d.tEnd = g.t + 1;
    }
  },
});
for (const d of list) delete d.last;
fs.writeFileSync(path.join(odir, 'don_unexec_eval.json'), JSON.stringify(list));
console.log(`${mid}: ${list.length} 笔未执行捐款已问价`);
