// boat_fight.mjs — 本队的船在海上被谁打掉：逐次海战（引擎 boats.js fightBoats，奇数拍结算）记录本队每条船挨的打。
// 引擎事实（src/sim/sim/boats.js L328–357，对应线上 abY）：不同队的两条船距离平方 < 14400（子格坐标）就互相扣兵；
//   挨打方兵力 v、打人方兵力 mine：v <= mine 时扣 max(1, (v + (mine − v)/10)/10)，否则扣 max(1, mine/10)；挨打的船 4 拍内减速；
//   船上兵力扣到 0 就从海上移除（boatsTick L210–216），不退兵。拦截船（type >= 64）是对方专门点名追这条船的。
// 用法：node boat_fight.mjs <matchId> [--replay id] [--log id1,id2] [--bots a,b] [--min 1000]
// 输出 out/<matchId>/boat_fight.csv：launch,bot,troops0,t0,t1,hits,lost,fate,by（对手:次数:扣兵:对手船兵力最大:是否拦截船）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });
const m = openMatch(mid, { replay: opt('replay', mid) });
const { g, H } = m;
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null;
const minTroops = +opt('min', 1000);
const squad = {};
for (const lb of opt('log', mid).split(',')) {
  const { me } = readLogSnaps(lb, lb === mid ? '' : lb + ':', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[(lb === mid ? '' : lb + ':') + b] = p;
}
const label = Object.fromEntries(Object.entries(squad).map(([b, p]) => [p, b]));
const FIGHT_RANGE2 = 14400;
const recs = new Map(); // boat id -> rec
const done = [];
const nm = (p) => (p < H ? `${m.names[p]}/T${g.teams[p]}` : `AI#${p}`);

const launch0 = g.launchBoat.bind(g);
g.launchBoat = function (p) {
  const id = this.boatNextId;
  const r = launch0(p);
  if (label[p] !== undefined) {
    const b = this.boatN - 1;
    recs.set(id, { id, launch: this.t, p, troops0: this.bTroops[b], hits: 0, lost: 0, t0: '', t1: '', by: {}, fate: 'at-sea', last: this.bTroops[b] });
  }
  return r;
};
const fight0 = g.fightBoats.bind(g);
g.fightBoats = function () {
  const before = new Map();
  for (let b = 0; b < this.boatN; b++) if (recs.has(this.bId[b]) && label[this.bSlot[b] >> 3] !== undefined) before.set(this.bId[b], this.bTroops[b]);
  // 打之前先记下每条本队船射程内的敌船（位置在 fightBoats 里不变）
  const S = this.sub, near = new Map();
  for (let b = 0; b < this.boatN; b++) {
    const id = this.bId[b];
    if (!before.has(id)) continue;
    const owner = this.bSlot[b] >> 3, pb = this.bPos[b], x = pb % S, y = ~~((pb + 0.5) / S);
    const list = [];
    for (let o = 0; o < this.boatN; o++) {
      const po = this.bSlot[o] >> 3;
      if (o === b || !this.isEnemyOf(owner, po)) continue;
      const pp = this.bPos[o], dx = x - (pp % S), dy = y - ~~((pp + 0.5) / S);
      if (dx * dx + dy * dy < FIGHT_RANGE2) list.push({ po, troops: this.bTroops[o], chaser: this.bType[o] >= 64 ? 0 : 0, type: this.bType[o], oid: this.bId[o] });
    }
    near.set(id, list);
  }
  const r = fight0();
  for (let b = 0; b < this.boatN; b++) {
    const id = this.bId[b];
    if (!before.has(id)) continue;
    const d = before.get(id) - this.bTroops[b];
    if (d <= 0) continue;
    const rec = recs.get(id);
    rec.hits++; rec.lost += d; if (rec.t0 === '') rec.t0 = this.t; rec.t1 = this.t;
    const list = near.get(id) || [];
    const tot = list.reduce((s, e) => s + Math.max(1, e.troops), 0) || 1;
    for (const e of list) {
      // 追这条船的拦截船：chases 里 (target id, chaser id) 成对存放
      let isChaser = false;
      for (let i = 0; i < this.chaseLen; i += 2) if (this.chases[i] === id && this.chases[i + 1] === e.oid) isChaser = true;
      const k = nm(e.po);
      const a = (rec.by[k] ||= { n: 0, share: 0, maxTroops: 0, chaser: 0 });
      a.n++; a.share += d * Math.max(1, e.troops) / tot; a.maxTroops = Math.max(a.maxTroops, e.troops); if (isChaser) a.chaser = 1;
    }
  }
  return r;
};
const remove0 = g.removeBoat.bind(g);
g.removeBoat = function (b) {
  const id = this.bId[b];
  const rec = recs.get(id);
  if (rec) { rec.fate = this.bTroops[b] === 0 ? 'destroyed' : 'landed'; rec.end = this.t; rec.left = this.bTroops[b]; done.push(rec); recs.delete(id); }
  return remove0(b);
};
while (m.tick());
for (const rec of recs.values()) { rec.end = g.t; rec.left = ''; done.push(rec); }
done.sort((a, b) => a.launch - b.launch);
const rows = ['launch,bot,troops0,t0,t1,hits,lost,fate,end,left,by'];
console.log(`# ${mid} 本队船只的海战记录（只列挨过打或装兵 >= ${minTroops} 的船）`);
console.log(' 出海拍 号        装兵   首次挨打  末次挨打  次数   被扣兵  结局(拍)        对手船（玩家/队:同处射程的次数:按兵力摊的扣兵:对手船兵力最大:是否点名拦截）');
let nDes = 0, lostDes = 0;
for (const r of done) {
  const by = Object.entries(r.by).sort((a, b) => b[1].share - a[1].share).map(([k, a]) => `${k}:${a.n}:${Math.round(a.share)}:${a.maxTroops}:${a.chaser ? '拦截' : '路过'}`).join(' | ');
  rows.push([r.launch, label[r.p], r.troops0, r.t0, r.t1, r.hits, r.lost, r.fate, r.end, r.left, JSON.stringify(by)].join(','));
  if (r.fate === 'destroyed') { nDes++; lostDes += r.troops0; }
  if (r.hits || r.troops0 >= minTroops) console.log(`${String(r.launch).padStart(7)} ${label[r.p].padEnd(8)} ${String(r.troops0).padStart(7)} ${String(r.t0).padStart(8)} ${String(r.t1).padStart(8)} ${String(r.hits).padStart(5)} ${String(r.lost).padStart(8)}  ${(r.fate + '@' + r.end).padEnd(15)} ${by}`);
}
fs.writeFileSync(path.join(OUT, 'boat_fight.csv'), rows.join('\n') + '\n');
console.log(`# 被打沉 ${nDes} 条，装兵合计 ${lostDes}；全部船海战扣兵合计 ${done.reduce((s, r) => s + r.lost, 0)}`);
