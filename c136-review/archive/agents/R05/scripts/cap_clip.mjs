#!/usr/bin/env node
// cap_clip.mjs — 硬上限（150×地）吃掉了多少兵：逐拍精确重放，包住引擎 addBalance（game.js L752-764），
// 记下每次「想加 v、实际只加上 got」的差额，并按来源分类：
//   ret  = 进攻结束/撤回时退回的兵（endAttack L1076-1080、cancelAttack L852-856）
//   don  = 捐兵到账（transfer L388-400）
//   eco  = 利息与地租（economyTick L778-791）
//   boat = 船靠岸回到自己/交给队友（boats.js landAt L262-287）
// 用法：node scripts/cap_clip.mjs <局> [--bots a,b] [--win 300] [--list t0,t1] [--min 1000]
//   默认只看我方号；--list 给一个时间窗，逐条打印窗内 ≥ --min 的差额（拍、号、来源、想加、加上、当时地/兵/硬上限）。
import { simulate, Game } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const onlyBots = val('--bots', '') ? val('--bots', '').split(',') : null;
const WIN = +val('--win', 300);
const list = val('--list', '') ? val('--list', '').split(',').map(Number) : null;
const MIN = +val('--min', 1000);
if (!mid) { console.error('用法见文件头'); process.exit(2); }
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1000 ? Math.round(x / 1000) + 'k' : String(Math.round(x)));

const P = Game.prototype;
let ctx = 'other';
const wrapCtx = (name, label) => {
  const o = P[name];
  if (typeof o !== 'function') return;
  P[name] = function (...a) { const prev = ctx; ctx = label; try { return o.apply(this, a); } finally { ctx = prev; } };
};
wrapCtx('endAttack', 'ret'); wrapCtx('cancelAttack', 'ret'); wrapCtx('economyTick', 'eco'); wrapCtx('transfer', 'don'); wrapCtx('landAt', 'boat');
const REC = { on: false, rows: [] };
const oAdd = P.addBalance;
P.addBalance = function (p, v) {
  const b0 = this.bal[p];
  const got = oAdd.call(this, p, v);
  if (REC.on && v > got) REC.rows.push({ t: this.t, p, ctx, want: v, got, terr: this.terr[p], bal0: b0 });
  return got;
};

let squad = null, names = null;
const R = simulate(mid, {
  onStart: (g, c) => { names = c.names; squad = squadIds(mid, c.names, c.H).squad; REC.on = true; },
});
const idOf = squad; // Map: 玩家编号 → 号名
const rows = REC.rows.filter((r) => idOf.has(r.p) && (!onlyBots || onlyBots.includes(idOf.get(r.p))));
const tot = {}, byBot = {}, byWin = {};
for (const r of rows) {
  const d = r.want - r.got, b = idOf.get(r.p), w = Math.floor(r.t / WIN) * WIN;
  tot[r.ctx] = (tot[r.ctx] || 0) + d;
  (byBot[b] ||= {})[r.ctx] = ((byBot[b] || {})[r.ctx] || 0) + d;
  (byWin[w] ||= {})[r.ctx] = ((byWin[w] || {})[r.ctx] || 0) + d;
}
const fmt = (o) => Object.entries(o).sort((a, b) => b[1] - a[1]).map(([c, v]) => `${c} ${k(v)}`).join(' ') || '无';
console.log(`[硬上限吃兵] ${mid} 我方号：被 150×地 上限截掉的兵 合计 ${k(Object.values(tot).reduce((a, b) => a + b, 0))}｜按来源：${fmt(tot)}`);
for (const [b, o] of Object.entries(byBot).sort((a, b) => Object.values(b[1]).reduce((x, y) => x + y, 0) - Object.values(a[1]).reduce((x, y) => x + y, 0))) {
  console.log(`   ${b}: ${fmt(o)}`);
}
console.log(`   按 ${WIN} 拍窗：` + Object.keys(byWin).map(Number).sort((a, b) => a - b).map((w) => `${w}: ${fmt(byWin[w])}`).join('；'));
if (list) {
  console.log(`-- 逐条（t∈[${list[0]},${list[1]}]，差额 ≥ ${MIN}）`);
  for (const r of rows) {
    if (r.t < list[0] || r.t > list[1] || r.want - r.got < MIN) continue;
    console.log(`   t=${r.t} ${idOf.get(r.p)} 来源 ${r.ctx}：想加 ${k(r.want)}，加上 ${k(r.got)}，截掉 ${k(r.want - r.got)}｜当时 地 ${r.terr} 兵 ${k(r.bal0)} 硬上限 ${k(150 * r.terr)}`);
  }
}
