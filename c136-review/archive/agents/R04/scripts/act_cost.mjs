#!/usr/bin/env node
// act_cost.mjs — 影子策略每次决策（Policy.act）在本机要算多少毫秒、时间花在哪个函数上。
// 用来对线上日志的 [HL-SLOW-TICK]（一次决策 ≥25 毫秒）：如果同一个号同一拍段影子也明显变慢，说明慢在策略自己的计算量（哪一个函数），
// 而不是线上机器被挤占。绝对毫秒数和线上机器不可比（本机 nice 19、和别的任务共用），只看「同一局里前后拍段的倍数」和「各函数的占比」。
// 用法：node scripts/act_cost.mjs <局号> --bots a,b [--from 0] [--to 1e9] [--bucket 300] [--ver va|vb|vc|c110]
//   函数耗时是「含子调用」的（buyLand 里调 offers、offers 里调 safeAt，各自都记一遍），所以各函数相加会超过 act 的总数。
// 重活：HEAVY_QUEUE=100 HEAVY_TIMEOUT=110 timeout 118 bash ../../tools/run-heavy.sh node scripts/act_cost.mjs …
import fs from 'node:fs';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { loadPolicy, versionOf, startEngine, Mirror } from './shadow.mjs';

const DATA = process.env.C136_DATA ? path.join(process.env.C136_DATA, 'bundles') : '/agent/repos/c136-data/bundles';
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const ver = opt('--ver', versionOf(mid));
const from = +opt('--from', 0), to = +opt('--to', 1e9), bucket = +opt('--bucket', 300);
const METHODS = ['updateShadowQuota', 'expandNeutral', 'buyLand', 'offers', 'tryDonateToTeammate', 'idleBoats', 'boatOut', 'boatFood', 'searchWater', 'searchFood',
  'pickTarget', 'safeAt', 'safeFinite', 'winFloor', 'floors', 'threatOf', 'isMopUp', 'defend', 'rescue', 'dpKeep'];

const logs = [];
globalThis.window = { __hlLog: (s) => logs.push(s) };
const { Policy } = await loadPolicy(ver);
const { info, api } = startEngine(mid);
const names = api.names();
const ids = [];
for (const b of (opt('--bots', '') || '').split(',').filter(Boolean)) {
  let p = /^\d+$/.test(b) ? +b : -1;
  if (p < 0) for (let q = 0; q < info.ku; q++) if (names[q] === b || names[q] === '[APEX] ' + b || (names[q] || '').endsWith(' ' + b)) { p = q; break; }
  if (p < 0) throw new Error('找不到号 ' + b);
  ids.push([b, p]);
}
let st = api.advance(1);
while (st[1] === 1 && st[2] !== 2) st = api.advance(1);
while (st[0] < from - 1 && st[2] !== 2) st = api.advance(Math.min(200, from - 1 - st[0]));
const M = new Mirror(info, api);
const g = M.g;
const slotOf = new Map();
try {
  const re = /\[HL-SPAWN[A-Z-]*\] me=(\d+) slot=(\d+)/g;
  const txt = fs.readFileSync(path.join(DATA, mid, 'in_game.log'), 'utf8');
  let mm;
  while ((mm = re.exec(txt))) slotOf.set(+mm[1], +mm[2]);
} catch (e) { /* 没有日志 */ }
const pols = ids.map(([b, p]) => {
  const pol = new Policy({}, p);
  const S = { b, p, pol, slot: slotOf.has(p) ? slotOf.get(p) : null, buckets: new Map(), cur: null };
  for (const name of METHODS) {
    if (typeof pol[name] !== 'function') continue;
    const orig = pol[name];
    pol[name] = function (...a) {
      const t0 = performance.now();
      try { return orig.apply(this, a); } finally { if (S.cur) S.cur.fn[name] = (S.cur.fn[name] || 0) + performance.now() - t0; }
    };
  }
  return S;
});
let lastPix = -1;
while (st[2] !== 2 && st[0] < to) {
  st = api.advance(1);
  const t = st[0];
  M.light();
  if (t % 5 === 0 || lastPix < 0) { M.pixels(); lastPix = t; }
  for (const S of pols) {
    if (!g.alive[S.p]) continue;
    const k = Math.floor(t / bucket) * bucket;
    let B = S.buckets.get(k);
    if (!B) S.buckets.set(k, (B = { n: 0, ms: 0, max: 0, maxT: 0, slow: 0, fn: {}, terr: 0, nb: 0 }));
    S.cur = B;
    g.me = S.p;
    if (S.slot !== null) globalThis.window.__tsbSquadSlot = S.slot; else delete globalThis.window.__tsbSquadSlot;
    const t0 = performance.now();
    try { S.pol.act(g); } catch (e) { /* 影子报错不影响计时 */ }
    const dt = performance.now() - t0;
    S.cur = null;
    if (t % 5 === 0) { B.n++; B.terr = g.terr[S.p]; }
    B.ms += dt;
    if (dt > B.max) { B.max = dt; B.maxT = t; }
    if (dt >= 25) B.slow++;
  }
  M.intents.length = 0;
}
console.log(`# ${mid} 影子策略（${ver}）每次决策的计算耗时（本机毫秒；每 ${bucket} 拍一段；函数耗时含子调用）`);
for (const S of pols) {
  console.log(`## ${S.b}#${S.p}`);
  console.log('  拍段          领土      决策拍  平均毫秒/决策拍  最大毫秒（拍）   ≥25 毫秒的拍数   耗时最多的函数（占这一段 act 总耗时）');
  let base = null;
  for (const [k, B] of [...S.buckets.entries()].sort((a, b) => a[0] - b[0])) {
    if (!B.n) continue;
    const mean = B.ms / B.n;
    if (base === null && B.ms > 0) base = mean;
    const top = Object.entries(B.fn).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([n, v]) => `${n} ${(100 * v / Math.max(1e-9, B.ms)).toFixed(0)}%`).join('，');
    console.log(`  ${String(k).padStart(5)}~${String(k + bucket - 1).padEnd(5)}  ${String(B.terr).padStart(7)}  ${String(B.n).padStart(5)}   ${mean.toFixed(2).padStart(8)}（×${(mean / Math.max(1e-9, base)).toFixed(1)}）  ${B.max.toFixed(1).padStart(7)}（${B.maxT}）  ${String(B.slow).padStart(5)}          ${top}`);
  }
}
