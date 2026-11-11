#!/usr/bin/env node
// tick_trace.mjs — 逐拍看一个号：每一拍的余额、领土、在途进攻（打谁:兵）、别人打它的兵（谁:兵），以及这一拍执行的它自己的指令。
// 用法：node tick_trace.mjs <matchId> <号名> <t0> <t1> [--replay other]
// 口径：一行 = 引擎拍号 g.t 时的局面（上一拍的指令和模拟都已做完）；cmds 列是“在这个局面上执行的指令”（录像拍号 = 这一行的 t），它们的效果出现在下一行。
// 输出到屏幕（拍数少，直接看）；同时写 out/<matchId>/tick_trace_<号名>_<t0>_<t1>.csv 供 q.py 复算。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch } from './resim_lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const mid = argv[0], name = argv[1], t0 = +argv[2], t1 = +argv[3];
const rp = argv.includes('--replay') ? argv[argv.indexOf('--replay') + 1] : mid;
const m = openMatch(rp);
const g = m.g;
// 号名 → 席位：先查 resim.mjs 写的 resim_meta.json（squad 表按日志里的号名），查不到再按录像里的名字或直接当席位号。
let p = -1;
try { const meta = JSON.parse(fs.readFileSync(path.resolve(HERE, '../out', mid, 'resim_meta.json'), 'utf8')); if (meta.squad && name in meta.squad) p = meta.squad[name]; } catch {}
if (p < 0) p = m.names.indexOf(name);
if (p < 0 && /^\d+$/.test(name)) p = +name;
if (p < 0) { console.error(`找不到号 ${name}`); process.exit(1); }
let pend = [];
m.onCmd = (c, r) => { if (c.player === p && (c.id === 1 || c.id === 2 || c.id === 3)) pend.push(`${c.id === 1 ? 'atk' : c.id === 2 ? 'don' : 'boat'}(pct=${c.dX},to=${c.id === 3 ? 'sea' : m.label(c.dZ)})${r ? '' : '✗'}`); };
const rows = ['t,bal,terr,dBal,dTerr,atkOut,atkIn,cmds'];
let prevB = null, prevL = null, prevCmd = '';
const snap = () => {
  const B = g.bal[p], L = g.terr[p];
  const out = m.atkOut(p).map(([t, v]) => `${m.label(t)}:${v}`).join('|');
  const inn = m.atkIn(p).map(([a, v]) => `${m.label(a)}:${v}`).join('|');
  return { t: g.t, B, L, out, inn };
};
while (g.t < t1) {
  if (g.t >= t0) {
    const s = snap();
    pend = [];
    const ok = m.tick();
    rows.push([s.t, s.B, s.L, prevB === null ? '' : s.B - prevB, prevL === null ? '' : s.L - prevL, s.out, s.inn, pend.join(' ')].join(','));
    prevB = s.B; prevL = s.L;
    if (!ok) break;
  } else if (!m.tick()) break;
}
const outDir = path.resolve(HERE, '../out', mid);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, `tick_trace_${name}_${t0}_${t1}.csv`), rows.join('\n') + '\n');
console.log(`# ${mid} ${name}（席位 ${p}）逐拍 ${t0}–${t1}：t | 余额 | 领土 | 余额变化 | 领土变化 | 在途进攻 | 被打 | 本拍执行的指令`);
for (const r of rows.slice(1)) console.log('  ' + r.split(',').join(' | '));
