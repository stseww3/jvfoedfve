#!/usr/bin/env node
// fidmism.mjs — 模拟器（src/sim + 重放器）和线上引擎原文第一处对不上的地方，逐拍摊开看（engdiff.mjs 找到的那几局）。
//
// 对每一局：取 engdiff 定出来的第一处不一致（拍 T、玩家 p），打出
//   · T-10 … T+12 逐拍：引擎的 地 / 兵 对 模拟器的 地 / 兵（玩家 p，以及同一拍一起对不上的其他玩家）
//   · 模拟器这一侧在这段里牵涉 p 的事件：录像指令（陆攻 / 赠兵 / 出船 / 召回 / 撤兵 / 离开）、船到岸、空壳赠兵、猎杀 / 提速事件
//   · p 的身份（真人 / 空壳 / 内置 AI、哪一队、什么时候离开），船的目的地是谁的地、和 p 是不是一队
// 只读 /agent/repos/c136-data（发现集的对局包 + src）。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/fidmism.mjs <局> [<局> …]
//   → 屏幕 + out/_cross/fidmism.txt（整份重写；把要看的局一次列全）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { resim } from './resim_r08.mjs';

const require = createRequire(import.meta.url);
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'out', '_run', 'engdiff');
const OUTF = path.join(HERE, '..', 'out', '_cross', 'fidmism.txt');
const lines = [];
const P = (s) => { console.log(s); lines.push(s); };
const KIND = { 1: '陆攻', 2: '赠兵', 3: '出船', 4: '追击/召回', 5: '撤兵', 8: '离开', 9: '离开' };

P('# fidmism.mjs — 模拟器和线上引擎原文第一处对不上的地方（逐拍）。「引擎」= src/engine/live_game_js.js 按录像原样重放；「模拟器」= src/sim + resim_r08.mjs。');
for (const mid of process.argv.slice(2)) {
  const D = JSON.parse(fs.readFileSync(path.join(RUN, `${mid}.json`), 'utf8'));
  if (D.exactT === undefined || D.exactT === null) { P(`== ${mid}：engdiff 没有找到不一致`); continue; }
  const T = D.exactT, lo = T - 10, hi = T + 12;
  const ps = D.who.map((w) => w.p);
  // 引擎逐拍
  const { h, info, api } = startReplay(mid);
  const grab = h.run(`(function (ids) { var r = []; for (var k = 0; k < ids.length; k++) { var p = ids[k]; r.push(ah.hN[p], ah.hb[p], ah.nU[p] ? 1 : 0, ah.a6S[p], bQ.z.ky[p]); } return r; })`);
  const eng = new Map();
  let lastT = -1;
  while (true) {
    const [t, hx, st] = api.advance(1);
    if (hx) continue;
    if (t === lastT) { if (st === 2) break; continue; }
    lastT = t;
    if (t >= lo && t <= hi) eng.set(t, grab(ps));
    if (t >= hi || st === 2) break;
  }
  // 模拟器逐拍
  const sim = new Map();
  const X = resim(mid, {
    until: hi,
    onTick: (g) => { if (g.t >= lo && g.t <= hi) sim.set(g.t, ps.flatMap((p) => [g.terr[p], g.bal[p], g.alive[p] ? 1 : 0, g.state[p], g.boatCount ? g.boatCount[p] : 0])); },
  });
  const H = X.H;
  const kindOf = (p, t) => (p >= H ? '内置 AI' : X.leftT[p] >= 0 && X.leftT[p] <= t ? '空壳' : '真人');
  P('');
  P(`== ${mid}：真人 ${H}，实际 ${X.nTeams} 队；引擎对日志 ${D.engLogExact}/${D.engLogRows}，模拟器对日志 ${D.simLogExact}/${D.logRows}；全场 10 拍断面一致 ${D.nCmp - D.nBad}/${D.nCmp}`);
  P(`  第一处不一致 t=${T}：${D.who.map((w) => `${w.kind}#${w.p}（${w.name}，队 ${w.team}${w.leftT >= 0 ? `，${w.leftT} 拍离开` : ''}）`).join('；')}`);
  P(`  逐拍（每个玩家：引擎 地/兵/船数 | 模拟器 地/兵/船数；* = 不一致）`);
  for (let t = lo; t <= hi; t++) {
    const e = eng.get(t), s = sim.get(t);
    if (!e || !s) continue;
    const cells = ps.map((p, k) => {
      const bad = e[5 * k] !== s[5 * k] || e[5 * k + 1] !== s[5 * k + 1];
      return `#${p} ${e[5 * k]}/${e[5 * k + 1]}/${e[5 * k + 4]} | ${s[5 * k]}/${s[5 * k + 1]}/${s[5 * k + 4]}${bad ? ' *' : ''}`;
    });
    P(`    t=${t}  ${cells.join('   ')}`);
  }
  P(`  模拟器这一侧在 (${lo - 30}, ${hi}] 里牵涉这些玩家的事件：`);
  const set = new Set(ps);
  for (const c of X.cmdLog) {
    const [t, p, k] = c;
    if (t <= lo - 30 || t > hi) continue;
    const tgt = k === 1 || k === 2 ? Math.min(c[4], 512) : k === 3 ? c[10] : -1;
    if (!set.has(p) && !set.has(tgt)) continue;
    if (k === 1) P(`    t=${t} 陆攻 ${p}→${tgt} 千分比 ${c[3]} 成功 ${c[5]} 出兵 ${c[6]} 手续 ${c[7]} 发前余额 ${c[8]}`);
    else if (k === 2) P(`    t=${t} 赠兵 ${p}→${tgt} 千分比 ${c[3]} 成功 ${c[5]} 到账 ${c[6]} 损耗 ${c[7]} 发前余额 ${c[8]}`);
    else if (k === 3) P(`    t=${t} 出船 ${p} 千分比 ${c[3]} 成功 ${c[5]} 上船 ${c[6]} 手续 ${c[7]} 发前余额 ${c[8]} 目的地是 ${tgt >= 512 ? '无主地' : `#${tgt}（${kindOf(tgt, t)}，队 ${X.teams ? X.teams[tgt] : 0}）`}的地；出船的人是队 ${X.teams ? X.teams[p] : 0}`);
    else P(`    t=${t} ${KIND[k] || k} ${p} 参数 ${c[3]},${c[4]} 成功 ${c[5]}`);
  }
  for (const g2 of X.huskGifts) if (g2[0] > lo - 30 && g2[0] <= hi && (set.has(g2[1]) || set.has(g2[2]))) P(`    t=${g2[0]} 空壳赠兵 #${g2[1]}→#${g2[2]}：给方余额 ${g2[4]}→${g2[7]}，收方 ${g2[5]}→${g2[6]}（给方地 ${g2[8]}，收方地 ${g2[9]}）`);
  for (const l of X.landings) if (l[0] > lo - 30 && l[0] <= hi + 300 && set.has(l[1])) P(`    t=${l[0]} 船到岸 #${l[1]}→${l[2] >= 512 ? '无主地' : `#${l[2]}`} 兵 ${l[3]} 到账 ${l[4]}`);
  const ev = (X.engineEvents || []).filter((e) => e[0] <= hi);
  if (ev.length) P(`    到这一拍为止的猎杀 / 提速事件：${ev.length} 次，第一次 t=${ev[0][0]}（${ev[0][1]}），最近一次 t=${ev[ev.length - 1][0]}（${ev[ev.length - 1][1]}）`);
  else P('    到这一拍为止没有猎杀 / 提速事件');
  P(`  之后不一致的玩家数（每 90 拍；真人席位 / 内置 AI）：${D.series.slice(0, 14).map((r) => `${r[0]}:${r[1]}/${r[2]}`).join(' ')}${D.series.length > 14 ? ` … ${D.series.slice(-1).map((r) => `${r[0]}:${r[1]}/${r[2]}`)}` : ''}`);
}
fs.mkdirSync(path.dirname(OUTF), { recursive: true });
fs.writeFileSync(OUTF, lines.join('\n') + '\n');
