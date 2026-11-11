// atk_fate.mjs — 「每一场进攻的下场」：我方号对每个目标的每一场进攻（从开出进攻槽到这个槽结束）
//   打出多少兵（含中途追加）、拿了多少格、退回多少兵（槽结束时剩下的兵原样回存兵）、兵在槽里放了多少拍。
//   引擎口径（src/sim/sim/game.js）：
//     expandAttack：每步按「本步候选格数 cnt」算 cost = 2·cnt + 2·def + 对方正打我的兵；cost < 槽里的兵 → 扣 cost、拿下这一圈；
//       付不起（且不是新开的槽，或对方有兵正打我）→ 槽里的兵全部按伤害打掉，进攻结束（不退兵）；
//       没有候选格（前沿不再挨着目标）→ endAttack：槽里剩下的兵全部退回存兵。
//     目标阵亡 → redirectAttackToNeutral：槽改打中立（每格 2 兵），打完同样 endAttack 退兵。
//   槽里的兵不算存兵：不吃利息，也不算进被打时的密度（def 用的是 存兵/地）。
// 用法：node atk_fate.mjs <matchId> [--bots a,b] [--min 200000] [--humans-only] [--t0 0 --t1 99999]
//   --min：只列打出 ≥ 这个数的场次（汇总仍按全部场次）。
//   --json FILE：把每一场（含每次追加的 [拍, 兵数]）写成 JSON（delay_account.py 用它把「一条指令」对到「它所在的那一场」）；带 --json 时不打印逐号文本。
import { simulate, Game, NEUTRAL } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const a = process.argv.slice(2);
const mid = a[0];
const val = (k, d) => (a.includes(k) ? a[a.indexOf(k) + 1] : d);
const MIN = +val('--min', 200000), T0 = +val('--t0', 0), T1 = +val('--t1', 99999);
const onlyBots = val('--bots', '');
const humansOnly = a.includes('--humans-only');
const jsonOut = val('--json', '');
let sq = new Map(); // p -> 号名（onStart 里按录像名单填）
const isSq = new Uint8Array(1024);
const P = Game.prototype;
const wrap = (name, f) => { const o = P[name]; P[name] = f(o); };
const open = new Map(); // key p*1024+target -> episode
const done = [];
let redirect = 0;
const key = (p, t) => p * 1024 + Math.min(t, 1023);
const get = (g, p, target, create) => {
  const k = key(p, target);
  let e = open.get(k);
  if (!e && create) { e = { p, target, t0: g.t, sent: 0, cmds: 0, tiles: 0, neutTiles: 0, ret: 0, burnt: 0, redirected: false, B0: g.bal[p], L0: g.terr[p], tL0: target < 512 ? g.terr[target] : 0, tB0: target < 512 ? g.bal[target] : 0 }; open.set(k, e); }
  return e;
};
wrap('addAttack', (o) => function (p, troops, target) {
  if (isSq[p] && !redirect) { const e = get(this, p, target, true); e.sent += troops; e.cmds++; (e.adds || (e.adds = [])).push([this.t, troops]); }
  return o.call(this, p, troops, target);
});
wrap('redirectAttackToNeutral', (o) => function (p, target) {
  if (!isSq[p]) return o.call(this, p, target);
  const e = open.get(key(p, target));
  let inSlot = 0;
  const sb = this.slotBase(p);
  for (let i = 0; i < this.atkCount[p]; i++) if (this.atkTarget[sb + i] === target) inSlot = this.atkTroops[sb + i];
  redirect = 1; o.call(this, p, target); redirect = 0;
  if (e) {
    open.delete(key(p, target));
    e.redirected = true; e.redirectT = this.t;
    const n = open.get(key(p, NEUTRAL));
    if (n) {
      // 已经有一个打中立的槽：这一场到此为止，槽里剩下的兵并进那个中立槽（记成那一场的「并入」）
      e.t1 = this.t; e.moved = inSlot; done.push(e);
      n.sent += inSlot; n.carried = (n.carried || 0) + inSlot;
    } else open.set(key(p, NEUTRAL), e);
  }
});
wrap('expandAttack', (o) => function (p, a2) {
  if (!isSq[p]) return o.call(this, p, a2);
  const k = this.slotBase(p) + a2;
  const tgt = this.atkTarget[k], tr0 = this.atkTroops[k], L0 = this.terr[p], n0 = this.atkCount[p];
  o.call(this, p, a2);
  const e = open.get(key(p, tgt));
  if (!e) return;
  const got = this.terr[p] - L0;
  if (got > 0) { if (e.redirected) e.neutTiles += got; else e.tiles += got; }
  else if (this.atkCount[p] < n0 && e.closing === undefined) { /* 槽在这一步结束：endAttack 钩子里已记账 */ }
});
wrap('endAttack', (o) => function (p, a2, troops) {
  if (!isSq[p]) return o.call(this, p, a2, troops);
  const k = this.slotBase(p) + a2;
  const tgt = this.atkTarget[k], inSlot = this.atkTroops[k];
  const b = this.bal[p];
  o.call(this, p, a2, troops);
  const e = open.get(key(p, tgt));
  if (e) {
    e.ret += this.bal[p] - b; e.t1 = this.t; e.burnt = Math.max(0, inSlot - troops) > 0 && troops < 8 ? inSlot : 0;
    open.delete(key(p, tgt)); done.push(e);
  }
});
if (P.cancelAttack) wrap('cancelAttack', (o) => function (p, target) {
  if (!isSq[p]) return o.call(this, p, target);
  const b = this.bal[p];
  const r = o.call(this, p, target);
  const e = open.get(key(p, target));
  if (e) { e.ret += this.bal[p] - b; e.t1 = this.t; e.cancelled = true; open.delete(key(p, target)); done.push(e); }
  return r;
});

const R = simulate(mid, { onStart: (g, ctx) => { sq = squadIds(mid, ctx.names, ctx.H).squad; for (const p of sq.keys()) isSq[p] = 1; } });
for (const e of open.values()) { e.t1 = R.endTick; e.open = true; done.push(e); }
const H = R.H, names = R.names;
if (jsonOut) {
  const fs = await import('node:fs');
  fs.writeFileSync(jsonOut, JSON.stringify({ mid, H, endTick: R.endTick, squad: [...sq].map(([p, bot]) => ({ p, bot })), episodes: done.map((e) => ({ ...e, adds: e.adds || [] })) }));
  console.log(`[进攻下场] ${mid}：${done.length} 场 → ${jsonOut}`);
  process.exit(0);
}
const nm = (t) => (t >= 512 ? '中立' : t < H ? `${names[t]}#${t}` : `机器人#${t}`);
const k = (v) => (Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(2) + 'M' : Math.abs(v) >= 1e4 ? Math.round(v / 1e3) + 'k' : String(Math.round(v)));
for (const [p, bot] of sq) {
  if (onlyBots && !onlyBots.split(',').includes(bot)) continue;
  const E = done.filter((e) => e.p === p && e.t0 >= T0 && e.t0 < T1 && (!humansOnly || e.target < H));
  const cls = (e) => (e.target >= 512 ? '中立' : e.target < H ? '真人' : '机器人');
  for (const c of ['中立', '机器人', '真人']) {
    const L = E.filter((e) => cls(e) === c);
    if (!L.length) continue;
    const sent = L.reduce((s, e) => s + e.sent - (e.carried || 0), 0), ret = L.reduce((s, e) => s + e.ret, 0), tiles = L.reduce((s, e) => s + e.tiles + e.neutTiles, 0);
    const park = L.reduce((s, e) => s + e.sent * (e.t1 - e.t0), 0);
    console.log(`[进攻下场] ${mid} ${bot} 打${c}：${L.length} 场，打出 ${k(sent)}，退回 ${k(ret)}（${(100 * ret / Math.max(1, sent)).toFixed(0)}%），净花 ${k(sent - ret)} 拿 ${tiles} 格（净 ${((sent - ret) / Math.max(1, tiles)).toFixed(0)} 兵/格）｜每场时长 中位 ${L.map((e) => e.t1 - e.t0).sort((x, y) => x - y)[L.length >> 1]} 拍｜兵×拍（按打出量×时长粗算）${k(park)}`);
  }
  const byT = new Map();
  for (const e of E.filter((e) => e.target < H)) {
    const r = byT.get(e.target) || { n: 0, sent: 0, ret: 0, tiles: 0, neut: 0 };
    r.n++; r.sent += e.sent; r.ret += e.ret; r.tiles += e.tiles; r.neut += e.neutTiles; byT.set(e.target, r);
  }
  for (const [t, r] of [...byT].sort((x, y) => y[1].sent - x[1].sent)) {
    console.log(`   对 ${nm(t)}：${r.n} 场 打出 ${k(r.sent)} 退回 ${k(r.ret)}（${(100 * r.ret / Math.max(1, r.sent)).toFixed(0)}%）净花 ${k(r.sent - r.ret)}｜拿它的地 ${r.tiles} 格${r.neut ? `＋它死后变中立的地 ${r.neut} 格` : ''}｜净 ${((r.sent - r.ret) / Math.max(1, r.tiles + r.neut)).toFixed(0)} 兵/格`);
  }
  for (const e of E.filter((e) => e.sent >= MIN).sort((x, y) => x.t0 - y.t0)) {
    const net = e.sent - e.ret;
    console.log(`     t=${e.t0}–${e.t1}（${e.t1 - e.t0} 拍）→ ${nm(e.target)}${e.redirected ? `（${e.redirectT} 目标阵亡，改打中立）` : ''}：${e.cmds} 条 打出 ${k(e.sent)}（开打时存兵 ${k(e.B0)}，目标 地 ${e.tL0} 兵 ${k(e.tB0)}）→ 拿 ${e.tiles}${e.neutTiles ? '+' + e.neutTiles : ''} 格，退回 ${k(e.ret)}（${(100 * e.ret / Math.max(1, e.sent)).toFixed(0)}%），净花 ${k(net)}${e.moved ? `｜槽里剩的 ${k(e.moved)} 并进已有的中立槽` : ''}${e.carried ? `｜含别的槽并入 ${k(e.carried)}` : ''}${e.open ? '｜终局时仍在槽里' : ''}${e.cancelled ? '｜被撤回' : ''}`);
  }
}
