#!/usr/bin/env node
// snap_loss.mjs — 日志 [HL-TICK] 快照那一拍，如果这个号正好在同一拍丢了地，日志里的 terr/bal 是“这一拍结算完”的值还是“上一拍”的值？
// 用途：核对“策略在第 t 拍看到的局面 = 重演第 t 拍结算完的局面”在丢地的拍上也成立（isNoFullSend 的核对拍口径要用到）。
// 用法：node snap_loss.mjs <matchId> [--replay other] [--log id1,id2]
// 输出：每个“快照拍正好丢地”的点一行（号、拍、上一拍与本拍的领土/余额、日志值、日志等于哪一个），末尾汇总。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps } from './resim_lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const mid = argv[0];
const opt = (k, d) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const rp = opt('replay', mid);
const logs = opt('log', mid).split(',');
const m = openMatch(rp);
const g = m.g;
const snaps = new Map(); // 't|p' -> {bot, terr, bal}
const seats = new Set();
for (const id of logs) {
  const { rows } = readLogSnaps(id, logs.length > 1 ? id + ':' : '');
  for (const r of rows) { snaps.set(r.t + '|' + r.p, r); seats.add(r.p); }
}
const prev = new Map();
let nSnap = 0, nLoss = 0, eqNow = 0, eqPrev = 0, eqNone = 0;
const out = ['t,bot,p,terrPrev,terrNow,balPrev,balNow,logTerr,logBal,logEquals'];
do {
  for (const p of seats) {
    const s = snaps.get(g.t + '|' + p);
    const pv = prev.get(p);
    if (s) {
      nSnap++;
      if (pv && g.terr[p] < pv.terr) {
        nLoss++;
        const now = s.terr === g.terr[p] && s.bal === g.bal[p];
        const old = s.terr === pv.terr && s.bal === pv.bal;
        if (now) eqNow++; else if (old) eqPrev++; else eqNone++;
        out.push([g.t, s.bot, p, pv.terr, g.terr[p], pv.bal, g.bal[p], s.terr, s.bal, now ? 'now' : old ? 'prev' : 'none'].join(','));
      }
    }
    prev.set(p, { terr: g.terr[p], bal: g.bal[p] });
  }
} while (m.tick());
const outDir = path.resolve(HERE, '../out', mid);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'snap_loss.csv'), out.join('\n') + '\n');
console.log(`${mid}: 日志快照 ${nSnap} 点；其中这个号正好在快照拍丢地的 ${nLoss} 点：日志值 = 本拍结算完 ${eqNow}，= 上一拍 ${eqPrev}，两个都不是 ${eqNone}`);
for (const r of out.slice(1, 9)) console.log('  ' + r);
