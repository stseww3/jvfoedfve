#!/usr/bin/env node
// boat_fate.mjs — 我方号每条船的下场（逐拍精确重演，只读）。
// 引擎规则（c136-data/src/sim/sim/boats.js）：
//   decayBoats L360-366：船在海上每 5 拍掉 1/128 的兵；fightBoats：敌船相遇互相消耗。
//   arrive L230-260 → landAt L262-287：真人的船靠岸时只看「落点那一格此刻归谁」——
//     中立格 / 敌方格 → 开一条进攻（没有空闲进攻槽且没有在打这个目标时，兵直接消失）；
//     自己的格       → 兵回到自己的存兵（受 150×地 上限截断）；
//     队友的格       → 兵无手续费交给这名队友：receiverRoom（150×地 上限）截断、bookDonation（t<4284 的捐兵配额）不过就整船作废，
//                      「配额或上限不收的部分沉海」。
// 输出：逐条船（出发拍、出发兵、录像里的目标、靠岸拍、靠岸时的兵、落点归属、结果）+ 汇总。
// 用法：node boat_fate.mjs <matchId> [--all]（--all：全场真人的船只出汇总）
import { simulate, Game, NEUTRAL, P_INNER } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';
const { T_LAND } = await import('file:///agent/repos/c136-data/src/sim/sim/map.js');

const args = process.argv.slice(2);
const mid = args[0];
const P = Game.prototype;
const wrap = (name, f) => { const o = P[name]; P[name] = f(o); };
const R = { on: false, boats: new Map(), cur: null, list: [] };

wrap('launchBoat', (o) => function (p) {
  o.call(this, p);
  if (!R.on) return;
  const b = this.boatN - 1;
  const rec = { id: this.bId[b], p, t0: this.t, troops0: this.bTroops[b], type: this.bType[b], fate: null };
  R.boats.set(rec.id, rec); R.list.push(rec);
});
wrap('arrive', (o) => function (b, at, type) {
  if (!R.on) return o.call(this, b, at, type);
  const rec = R.boats.get(this.bId[b]);
  R.cur = rec && (this.bSlot[b] >> 3) === rec.p ? rec : null;
  if (R.cur) { R.cur.t1 = this.t; R.cur.troops1 = this.bTroops[b]; if (type === 6) R.cur.chase = 1; }
  const r = o.call(this, b, at, type);
  if (R.cur && r && !R.cur.fate) R.cur.fate = type === 6 ? '追船结束' : '靠岸处无可落的格';
  R.cur = null;
  return r;
});
wrap('landAt', (o) => function (p, troops, c, at) {
  const rec = R.on ? R.cur : null;
  if (!rec) return o.call(this, p, troops, c, at);
  const v = this.px[c];
  if (v === T_LAND) {
    const ok = this.hasAttack(p, NEUTRAL) || this.hasFreeSlot(p);
    rec.fate = ok ? '打中立' : '无进攻槽→兵消失'; rec.owner = NEUTRAL; rec.delivered = ok ? troops : 0;
  } else if (v >= P_INNER) {
    const q = this.own[c];
    rec.owner = q;
    if (q === p) {
      const b0 = this.bal[p];
      o.call(this, p, troops, c, at);
      rec.fate = '落在自己的地→回存兵'; rec.back = this.bal[p] - b0; rec.lost = troops - rec.back;
      return;
    }
    if (!this.isEnemy(p, q)) {
      const b0 = this.bal[q];
      const room = this.receiverRoom(q, troops);
      const free = this.donationFree(q);
      const quotaOk = free || this.donQuota[q] + this.donationCost(q, room) <= this.donCap;
      o.call(this, p, troops, c, at);
      const got = this.bal[q] - b0;
      rec.fate = got > 0 ? '落在队友的地→兵交给队友' : (room < 1 ? '落在队友的地→队友已满(150×地)，整船作废' : (!quotaOk ? '落在队友的地→捐兵配额不过，整船作废' : '落在队友的地→作废'));
      rec.handed = got; rec.lost = troops - got; rec.room = room;
      return;
    }
    const ok = this.hasAttack(p, q) || this.hasFreeSlot(p);
    rec.fate = ok ? '打敌方' : '无进攻槽→兵消失'; rec.delivered = ok ? troops : 0;
  } else { rec.fate = '落点不是陆地'; }
  return o.call(this, p, troops, c, at);
});
wrap('removeBoat', (o) => function (b) {
  if (R.on) {
    const rec = R.boats.get(this.bId[b]);
    if (rec && (this.bSlot[b] >> 3) === rec.p && !rec.fate) { rec.t1 = this.t; rec.troops1 = this.bTroops[b]; rec.fate = this.bTroops[b] === 0 ? '海上打光/耗光' : (this.alive[rec.p] ? '被移除' : '船主阵亡，船消失'); }
    if (rec) R.boats.delete(this.bId[b]);
  }
  return o.call(this, b);
});

// 海上损失拆成两类：fightBoats（L328-356，敌船在射程内每 2 拍互相打掉约一成）与 decayBoats（L360-366，每 5 拍掉 1/128）
const snap = (g) => { const m = []; for (let b = 0; b < g.boatN; b++) { const r = R.boats.get(g.bId[b]); if (r && (g.bSlot[b] >> 3) === r.p) m.push([r, b, g.bTroops[b]]); } return m; };
for (const [fn, key] of [['fightBoats', 'lostFight'], ['decayBoats', 'lostDecay']]) {
  wrap(fn, (o) => function () {
    if (!R.on) return o.call(this);
    const m = snap(this);
    const r = o.call(this);
    for (const [rec, b, v] of m) rec[key] = (rec[key] || 0) + (v - this.bTroops[b]);
    return r;
  });
}

let info = null, sq = null, names = null, H = 0, teams = null;
await simulate(mid, {
  onStart(g, inf) { info = inf; names = inf.names; H = inf.H; sq = squadIds(mid, inf.names, inf.H).squad; teams = g.teams; R.on = true; },
});
const nm = (q) => (q === NEUTRAL ? '中立' : sq.has(q) ? sq.get(q) : q < H ? `${String(names[q]).slice(0, 16)}(#${q},T${teams[q]})` : `机器人#${q}`);
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.round(x / 1000) + 'k');
const mine = R.list.filter((r) => sq.has(r.p));
const sum = (rows) => {
  const by = new Map();
  for (const r of rows) {
    const f = r.fate || '终局时仍在海上';
    const s = by.get(f) || { n: 0, sent: 0, arr: 0, deliv: 0, handed: 0, back: 0, fight: 0, decay: 0 };
    s.n++; s.sent += r.troops0; s.arr += r.troops1 ?? 0; s.deliv += r.delivered ?? 0; s.handed += r.handed ?? 0; s.back += r.back ?? 0; s.fight += r.lostFight ?? 0; s.decay += r.lostDecay ?? 0;
    by.set(f, s);
  }
  return by;
};
const show = (tag, rows) => {
  const sent = rows.reduce((a, r) => a + r.troops0, 0);
  const big = rows.filter((r) => r.troops0 >= 10000);
  console.log(`[船的下场] ${mid} ${tag}：出船 ${rows.length} 条 共 ${k(sent)}（其中 ≥10k 的 ${big.length} 条 ${k(big.reduce((a, r) => a + r.troops0, 0))}）`);
  for (const [f, s] of [...sum(rows).entries()].sort((a, b) => b[1].sent - a[1].sent)) {
    console.log(`   ${f}：${s.n} 条，出发 ${k(s.sent)}，到岸时 ${k(s.arr)}${s.deliv ? `，开成进攻 ${k(s.deliv)}` : ''}${s.handed ? `，交给队友 ${k(s.handed)}` : ''}${s.back ? `，回到存兵 ${k(s.back)}` : ''}｜海上被敌船打掉 ${k(s.fight)}、损耗 ${k(s.decay)}`);
  }
  console.log(`   海上损失合计：被敌船打掉 ${k(rows.reduce((a, r) => a + (r.lostFight ?? 0), 0))}，损耗 ${k(rows.reduce((a, r) => a + (r.lostDecay ?? 0), 0))}`);
};
if (!args.includes('--all')) {
  for (const r of mine) {
    console.log(`t=${r.t0} ${sq.get(r.p)} 出船 ${k(r.troops0)} → ${r.t1 ?? '-'} 到岸 ${r.troops1 != null ? k(r.troops1) : '-'}（海上 ${r.t1 != null ? r.t1 - r.t0 : '-'} 拍，少了 ${r.troops1 != null ? k(r.troops0 - r.troops1) : '-'}：敌船打掉 ${k(r.lostFight ?? 0)}、损耗 ${k(r.lostDecay ?? 0)}）｜落点归 ${r.owner != null ? nm(r.owner) : '-'}｜${r.fate || '终局时仍在海上'}${r.handed ? `：对方收下 ${k(r.handed)}，作废 ${k(r.lost)}` : ''}${r.back != null ? `：回 ${k(r.back)}` : ''}`);
  }
}
show('我方号', mine);
const handedTo = new Map();
for (const r of mine) if (r.handed) handedTo.set(nm(r.owner), (handedTo.get(nm(r.owner)) || 0) + r.handed);
if (handedTo.size) console.log('   交给队友明细：' + [...handedTo.entries()].sort((a, b) => b[1] - a[1]).map(([n, v]) => `${n} ${k(v)}`).join('；'));
if (args.includes('--all')) show('全场真人', R.list.filter((r) => r.p < H));
