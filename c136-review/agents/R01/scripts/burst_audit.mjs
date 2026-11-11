// burst_audit.mjs — 同一个服务器拍里同一个号落地多条指令（“叠单”）的审计，数字全部来自整局重演。
//   node burst_audit.mjs <matchId> [--replay other] [--log id1,id2] [--bots a,b] [--min 3]
// 每个叠单事件：拍、号、指令类型、条数、目标、各条 pct、执行前后余额、花掉的比例、当时自己的领土/密度、目标的领土/兵力/密度、
//   同一拍之后 300 拍内这个号的领土变化与是否阵亡。
// 输出 out/<matchId>/bursts.csv，并在标准输出给出按号汇总。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, NEUTRAL } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null; // --bots a,b：只认这些号（日志里的号分在两个实例时用）
const minN = +opt('min', 3);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const m = openMatch(mid, { replay: opt('replay', mid) });
const { g, H } = m;
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb, '', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[p] = (lb === mid ? '' : lb + ':') + b;
}
const cur = new Map(); // p|kind|target -> event (current tick)
const events = [];
let curT = -1;
const flush = () => {
  for (const e of cur.values()) if (e.n >= minN) events.push(e);
  cur.clear();
};
const balBefore = new Map();
m.onCmd = (c, r) => {
  if (g.t !== curT) { flush(); curT = g.t; }
  if (!(c.player in squad)) return;
  if (c.id !== 1 && c.id !== 2) return;
  const kind = c.id === 1 ? 'attack' : 'donate';
  const k = `${c.player}|${kind}|${c.dZ}`;
  let e = cur.get(k);
  if (!e) {
    // 余额在第一条执行后才看得到，所以用上一拍末的快照
    e = { t: g.t, p: c.player, kind, target: c.dZ, n: 0, ok: 0, pcts: [], bal0: prevBal[c.player], terr: g.terr[c.player],
      tTerr: c.dZ < NEUTRAL ? g.terr[c.dZ] : 0, tBal: c.dZ < NEUTRAL ? prevBal[c.dZ] : 0 };
    cur.set(k, e);
  }
  e.n++; if (r) e.ok++; e.pcts.push(c.dX); e.bal1 = g.bal[c.player];
};
const prevBal = new Float64Array(512);
const snapBal = () => { for (let p = 0; p < 512; p++) prevBal[p] = g.bal[p]; };
snapBal();
// 事后跟踪
const follow = [];
while (m.tick()) {
  snapBal();
  for (const e of events) if (e.f === undefined) { e.f = 1; follow.push(e); }
  for (const e of follow) {
    if (g.t === e.t + 300 || (!g.alive[e.p] && e.terr300 === undefined)) { e.terr300 = g.terr[e.p]; e.alive300 = g.alive[e.p]; e.tEnd = g.t; }
  }
}
flush();
for (const e of events) if (e.terr300 === undefined) { e.terr300 = g.terr[e.p]; e.alive300 = g.alive[e.p]; e.tEnd = g.t; }
events.sort((a, b) => a.t - b.t);
const rows = ['t,bot,p,kind,target,targetName,n,ok,pcts,bal0,bal1,spentPct,terr,dens0,dens1,tTerr,tBal,tDens,terrAfter300,aliveAfter300'];
for (const e of events) {
  rows.push([e.t, squad[e.p], e.p, e.kind, e.target, JSON.stringify(m.label(e.target)), e.n, e.ok, e.pcts.join('|'), e.bal0, e.bal1,
    e.bal0 ? (100 * (e.bal0 - e.bal1) / e.bal0).toFixed(1) : 0, e.terr, e.terr ? (e.bal0 / e.terr).toFixed(1) : 0, e.terr ? (e.bal1 / e.terr).toFixed(1) : 0,
    e.tTerr, e.tBal, e.tTerr ? (e.tBal / e.tTerr).toFixed(1) : 0, e.terr300, e.alive300].join(','));
}
fs.writeFileSync(path.join(OUT, 'bursts.csv'), rows.join('\n') + '\n');
const by = {};
for (const e of events) { const b = squad[e.p]; (by[b] ??= []).push(e); }
console.log(`${mid}: 叠单事件(同拍同目标 >=${minN} 条) ${events.length} 个`);
for (const [b, es] of Object.entries(by)) {
  const big = es.filter((e) => e.kind === 'attack' && e.target < NEUTRAL && e.bal0 > 0 && (e.bal0 - e.bal1) / e.bal0 >= 0.6);
  console.log(`  ${b}: ${es.length} 个；对玩家且单拍花掉 >=60% 余额的 ${big.length} 个: ` +
    big.map((e) => `t=${e.t} x${e.n}->${m.label(e.target)} ${e.bal0}->${e.bal1} dens ${(e.bal0 / e.terr).toFixed(0)}->${(e.bal1 / e.terr).toFixed(1)} 对方dens=${e.tTerr ? (e.tBal / e.tTerr).toFixed(0) : '-'} 300拍后terr ${e.terr}->${e.terr300}${e.alive300 ? '' : '(死)'}`).join('; '));
}
