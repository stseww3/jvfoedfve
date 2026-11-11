// boat_trace.mjs — 本队每一条船从出海到靠岸的全程：出海拍、船上兵力、目的地、航行拍数、靠岸时还剩多少兵、落在谁的地上。
// 用法：node boat_trace.mjs <matchId> [--replay id] [--log id1,id2] [--bots a,b]
// 引擎事实（src/sim/sim/boats.js，对应线上 acW/acN）：每 5 拍（t%5==3）船上兵力减 max(1, 兵>>7)；
//   每个号同时在海上的船数由策略参数 maxBoats 限制（引擎上限 8）；靠队友岸 = 免税转给队友（受配额和 150 倍上限约束，过不了就整船作废）；
//   靠自己岸 = 兵回余额；靠无主地/敌岸 = 开一条进攻线。
// 输出 out/<matchId>/boat_trace.csv：launch,bot,troops0,balBefore,fromX,fromY,toX,toY,dist,arrive,flight,troopsArr,keptPct,landedOn,owner,mateGot,boatsAtSeaAfterLaunch,fee,aimAtLaunch,hitLoss,hitTicks,hitBy（后三列：海上被敌船打掉的兵、交战拍数、主要是谁的船）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, T_LAND, P_INNER } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const m = openMatch(mid, { replay: opt('replay', mid) });
const { g, H } = m;
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null;
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb, lb === mid ? '' : lb + ':', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[(lb === mid ? '' : lb + ':') + b] = p;
}
const label = Object.fromEntries(Object.entries(squad).map(([b, p]) => [p, b]));
const W = g.W;
const boats = new Map(); // id -> rec
const done = [];
const xy = (c) => [c % W, Math.floor(c / W)];

const launch0 = g.launchBoat.bind(g);
let lastBal = 0;
m.preCmd = (c) => { if (c.id === 3) lastBal = g.bal[c.player]; };
g.launchBoat = function (p) {
  const id = this.boatNextId, route = this.routeTmp;
  const r = launch0(p);
  if (label[p] !== undefined) {
    const b = this.boatN - 1;
    const a = this.subToPixel(this.subPos(route[0])), e = this.subToPixel(this.subPos(route[route.length - 1]));
    const [ax, ay] = xy(a), [ex, ey] = xy(e);
    // 出海那一拍，航线终点周围 3 格内的陆地归谁（无主 / 自己 / 队友 / 敌人 / AI），按格数最多的算
    const cls = {};
    for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) {
      const x = ex + dx, y = ey + dy;
      if (x < 0 || y < 0 || x >= W || y >= this.H) continue;
      const c = x + y * W, v = this.px[c];
      let k = null;
      if (v === T_LAND) k = 'neutral';
      else if (v >= P_INNER) { const o = this.own[c]; k = o === p ? 'self' : !this.isEnemy(p, o) ? 'mate' : o >= H ? 'ai' : 'enemy'; }
      if (k) cls[k] = (cls[k] || 0) + 1;
    }
    const aim = Object.entries(cls).sort((x, y) => y[1] - x[1])[0]?.[0] ?? '?';
    boats.set(id, { launch: this.t, p, troops0: this.bTroops[b], balBefore: lastBal, fee: lastBal - this.bal[p] - this.bTroops[b], aim, ax, ay, ex, ey, dist: Math.round(Math.hypot(ex - ax, ey - ay)), atSea: this.boatCount[p], type: this.bType[b] });
  }
  return r;
};
let cur = null;
const arrive0 = g.arrive.bind(g);
g.arrive = function (b, at, type) {
  const id = this.bId[b];
  const rec = boats.get(id);
  if (rec && type !== 6) { cur = rec; rec.arrive = this.t; rec.troopsArr = this.bTroops[b]; rec.landedOn = 'nowhere'; rec.owner = ''; }
  const r = arrive0(b, at, type);
  if (rec && type !== 6 && r) { done.push(rec); boats.delete(id); }
  cur = null;
  return r;
};
const landAt0 = g.landAt.bind(g);
g.landAt = function (p, troops, c, at) {
  if (cur) {
    const v = this.px[c];
    if (v === T_LAND) cur.landedOn = 'neutral';
    else if (v >= P_INNER) {
      const o = this.own[c];
      cur.owner = o < H ? (m.names[o] ?? '#' + o) : 'AI#' + o;
      cur.landedOn = o === p ? 'self' : !this.isEnemy(p, o) ? 'mate' : o >= H ? 'ai' : 'enemy';
      if (cur.landedOn === 'mate') { cur.mateBal0 = this.bal[o]; cur.mate = o; }
    } else cur.landedOn = 'water/edge';
  }
  const r = landAt0(p, troops, c, at);
  if (cur && cur.landedOn === 'mate') cur.mateGot = this.bal[cur.mate] - cur.mateBal0;
  return r;
};
const remove0 = g.removeBoat.bind(g);
g.removeBoat = function (b) {
  const id = this.bId[b];
  const rec = boats.get(id);
  if (rec && rec.arrive === undefined) { rec.arrive = this.t; rec.troopsArr = this.bTroops[b]; rec.landedOn = this.alive[rec.p] ? 'sunk' : 'owner-dead'; done.push(rec); boats.delete(id); }
  return remove0(b);
};
// 海上交战（boats.js fightBoats，每逢奇数拍）：本队的船被谁的船打掉多少兵。
// 做法：交战前后各记一次本队在海上每条船的兵力；掉了兵的船，把这一拍在交战距离内（FIGHT_RANGE2 = 14400，子像素坐标）的敌方船主记下来，
// 损失按这些敌方船当时的兵力比例分摊（引擎是逐条结算，这里的分摊只用来回答“主要是谁打的”）。
const FIGHT_RANGE2 = 14400;
const fight0 = g.fightBoats.bind(g);
g.fightBoats = function () {
  const mine = [];
  for (let b = 0; b < this.boatN; b++) { const rec = boats.get(this.bId[b]); if (rec) mine.push([b, rec, this.bTroops[b]]); }
  const r = fight0();
  if (!mine.length) return r;
  const S = this.sub;
  for (const [b, rec, before] of mine) {
    const loss = before - this.bTroops[b];
    if (loss <= 0) continue;
    const pb = this.bPos[b], x = pb % S, y = ~~((pb + 0.5) / S), owner = this.bSlot[b] >> 3;
    const near = [];
    let tot = 0;
    for (let o = 0; o < this.boatN; o++) {
      const oo = this.bSlot[o] >> 3;
      if (o === b || !this.isEnemyOf(owner, oo)) continue;
      const po = this.bPos[o], dx = x - (po % S), dy = y - ~~((po + 0.5) / S);
      if (dx * dx + dy * dy < FIGHT_RANGE2) { near.push([oo, this.bTroops[o]]); tot += this.bTroops[o] + 1; }
    }
    rec.hitLoss = (rec.hitLoss || 0) + loss;
    rec.hitTicks = (rec.hitTicks || 0) + 1;
    rec.hitBy ??= {};
    for (const [oo, v] of near) rec.hitBy[oo] = (rec.hitBy[oo] || 0) + loss * (v + 1) / tot;
    if (!near.length) rec.hitBy[-1] = (rec.hitBy[-1] || 0) + loss;
  }
  return r;
};
while (m.tick());
for (const rec of boats.values()) { rec.arrive = ''; rec.troopsArr = ''; rec.landedOn = 'still-at-sea'; done.push(rec); }
done.sort((a, b) => a.launch - b.launch);
const rows = ['launch,bot,troops0,balBefore,fromX,fromY,toX,toY,dist,arrive,flight,troopsArr,keptPct,landedOn,owner,mateGot,boatsAtSeaAfterLaunch,fee,aimAtLaunch,hitLoss,hitTicks,hitBy'];
const seatName = (o) => (o < 0 ? '?' : label[o] ?? (o < H ? `${m.names[o] ?? '#' + o}#${o}/T${g.teams[o]}` : 'AI#' + o));
const hitStr = (r) => (r.hitBy ? Object.entries(r.hitBy).sort((x, y) => y[1] - x[1]).slice(0, 3).map(([o, v]) => `${seatName(+o)}:${Math.round(v)}`).join(' / ') : '');
for (const r of done) {
  rows.push([r.launch, label[r.p], r.troops0, r.balBefore, r.ax, r.ay, r.ex, r.ey, r.dist, r.arrive, r.arrive === '' ? '' : r.arrive - r.launch, r.troopsArr,
    r.troopsArr === '' ? '' : (100 * r.troopsArr / Math.max(1, r.troops0)).toFixed(1), r.landedOn, JSON.stringify(r.owner || ''), r.mateGot ?? '', r.atSea, r.fee, r.aim, r.hitLoss ?? 0, r.hitTicks ?? 0, JSON.stringify(hitStr(r))].join(','));
}
fs.writeFileSync(path.join(OUT, 'boat_trace.csv'), rows.join('\n') + '\n');
console.log(`# ${mid} 本队出海 ${done.length} 条（结束拍 ${g.t}）`);
console.log(' 出海拍 号        船上兵力  出海前余额  直线距离  靠岸拍  航行拍  靠岸剩兵  留存%  落在          出海后在海上的船数');
for (const r of done) {
  console.log(`${String(r.launch).padStart(7)} ${label[r.p].padEnd(8)} ${String(r.troops0).padStart(8)} ${String(r.balBefore).padStart(10)} ${String(r.dist).padStart(8)} ${String(r.arrive).padStart(7)} ${String(r.arrive === '' ? '' : r.arrive - r.launch).padStart(6)} ${String(r.troopsArr).padStart(9)} ${(r.troopsArr === '' ? '' : (100 * r.troopsArr / Math.max(1, r.troops0)).toFixed(1)).padStart(6)}  ${(r.landedOn + (r.owner ? ':' + r.owner : '') + (r.mateGot !== undefined ? ` 到账${r.mateGot}` : '')).padEnd(34)} ${r.atSea}`);
}
const far = done.filter((r) => r.arrive !== '' && r.arrive - r.launch >= 300);
const lostAtSea = done.reduce((s, r) => s + (r.troopsArr === '' ? r.troops0 : r.troops0 - r.troopsArr), 0);
console.log(`# 航行 >=300 拍的船 ${far.length} 条；全部船在海上损耗合计 ${lostAtSea} 兵（出海合计 ${done.reduce((s, r) => s + r.troops0, 0)}）`);
// 出海手续费：引擎对每条船收余额的 32/1024（3.125%），和船上装多少兵无关（boats.js chase/boat 的 quote(p, pct, 32)）
const feeAll = done.reduce((s, r) => s + r.fee, 0);
const small = done.filter((r) => r.troops0 < r.fee);
console.log(`# 出海手续费合计 ${feeAll}；其中“船上的兵比手续费还少”的船 ${small.length} 条：装兵合计 ${small.reduce((s, r) => s + r.troops0, 0)}，手续费合计 ${small.reduce((s, r) => s + r.fee, 0)}，出海时瞄的是 ${Object.entries(small.reduce((o, r) => { o[r.aim] = (o[r.aim] || 0) + 1; return o; }, {})).map(([k, n]) => k + ' ' + n).join(' / ')}`);
for (const r of done) console.log(`#   ${r.launch} ${label[r.p]} 装兵 ${r.troops0} 手续费 ${r.fee} 出海时瞄 ${r.aim} → ${r.landedOn}${r.owner ? ':' + r.owner : ''}`);
// 每个号“船位占满”的拍数：在海上的船数 >= 策略参数 maxBoats（--max-boats，默认 2）的累计拍数
const maxBoats = +opt('max-boats', 2);
const full = {};
for (const p of Object.values(squad)) {
  const mine = done.filter((r) => r.p === p);
  if (!mine.length) continue;
  const ev = [];
  for (const r of mine) { ev.push([r.launch, 1]); ev.push([r.arrive === '' ? g.t : r.arrive, -1]); }
  ev.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let n = 0, last = 0, tot = 0; const spans = [];
  for (const [t, d] of ev) { if (n >= maxBoats) { tot += t - last; spans.push(`${last}-${t}`); } n += d; last = t; }
  full[label[p]] = `${tot} 拍（${spans.join(' ')}）`;
}
console.log(`# 在海上的船数 >= ${maxBoats}（策略 maxBoats）的时段：` + Object.entries(full).map(([b, s]) => `${b} ${s}`).join('；'));
// 海上交战汇总
const hitRows = done.filter((r) => (r.hitLoss || 0) > 0);
if (hitRows.length) {
  console.log(`# 海上被敌船打掉兵的船 ${hitRows.length} 条，合计被打掉 ${hitRows.reduce((s, r) => s + r.hitLoss, 0)} 兵（其中最后沉没的 ${hitRows.filter((r) => r.landedOn === 'sunk').length} 条，装兵合计 ${hitRows.filter((r) => r.landedOn === 'sunk').reduce((s, r) => s + r.troops0, 0)}）`);
  for (const r of hitRows.sort((x, y) => y.hitLoss - x.hitLoss).slice(0, 12)) console.log(`#   ${r.launch} ${label[r.p]} 装兵 ${r.troops0} 被打掉 ${r.hitLoss}（交战 ${r.hitTicks} 拍）→ ${r.landedOn}；主要是：${hitStr(r)}`);
}
