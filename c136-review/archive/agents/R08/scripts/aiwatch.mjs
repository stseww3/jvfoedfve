#!/usr/bin/env node
// aiwatch.mjs — 盯住几个内置 AI（或任意玩家号）在一段拍数里的逐拍状态：活着没有、地、兵、历史峰值、在途船数、欠账、
// 对某个编队号的在途进攻兵。只在状态变化时记一行。用真引擎重演（resim_r08.mjs 的 onTick 钩子），不改引擎、不改账本。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/aiwatch.mjs <局> --ids 101,124 --from 9700 --to 10100 [--vs 4] [--tag x]
//
// 输出：out/<局>/aiwatch[_<tag>].txt
// 用途：核实「内置 AI 被打到只剩 1/4 峰值时坍缩；如果它当时有船在海上，引擎 collapse() 只清地不除名，船靠岸后它带着几格地重新出现」。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
if (!mid || !opt('ids', null)) { console.error('用法：node aiwatch.mjs <局> --ids a,b --from T0 --to T1 [--vs 玩家号] [--tag x]'); process.exit(2); }
const ids = opt('ids', '').split(',').map(Number);
const from = +opt('from', 0), to = +opt('to', 1e9);
const vs = opt('vs', null) === null ? -1 : +opt('vs', -1);
const tag = opt('tag', null);
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));

const lines = [];
const last = new Map();
const out = resim(mid, {
  until: to,
  quiet: true,
  onTick: (g) => {
    if (g.t < from) return;
    for (const p of ids) {
      const row = [g.alive[p], g.terr[p], g.bal[p], g.peak[p], g.boatCount[p], g.debt[p],
        vs >= 0 ? g.attackTroopsOn(p, vs) : 0, vs >= 0 ? g.attackTroopsOn(vs, p) : 0];
      const key = `${row[0]}|${row[1]}|${row[4]}|${row[6] > 0 ? 1 : 0}|${row[7] > 0 ? 1 : 0}|${row[5] > 0 ? 1 : 0}`;
      if (last.get(p) === key) continue;
      last.set(p, key);
      lines.push(`${g.t} | 玩家号 ${p} | 活着 ${row[0]} | 地 ${row[1]} | 兵 ${row[2]} | 峰值 ${row[3]}（坍缩线 ${Math.floor(row[3] / 4)}）| 在途船 ${row[4]} | 欠账 ${row[5]}` +
        (vs >= 0 ? ` | 它压在 ${vs} 号身上的兵 ${row[6]} | ${vs} 号压在它身上的兵 ${row[7]}` : ''));
    }
  },
});
const head = `[AW] ${mid} 逐拍盯 ${ids.join(',')}（t=${from}~${Math.min(to, out.endTick)}；只在 活着/地/在途船/有无在途进攻/有无欠账 变化时记一行）`;
const text = [head, ...lines].join('\n') + '\n';
fs.mkdirSync(path.join(OUT, mid), { recursive: true });
fs.writeFileSync(path.join(OUT, mid, tag ? `aiwatch_${tag}.txt` : 'aiwatch.txt'), text);
console.log(text.split('\n').slice(0, 400).join('\n'));
