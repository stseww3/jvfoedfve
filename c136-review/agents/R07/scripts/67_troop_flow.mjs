#!/usr/bin/env node
// 67_troop_flow.mjs — R07：逐条指令的真实效果 + 兵力流水账（我方每个号、每个时间窗）。
//
// 做法：用统筹的干净模拟器（resim）重演录像，在 Game.attack / donate / boat / chase 等方法外面包一层，
// 记下每条录像指令执行前后的余额（=这一条真正花了多少：发出的兵 + 手续费；没生效的指令余额不变）。
// 每一拍结算（tick）前后的余额差单独记为「拍内净变化」：利息、地租、退回的兵记正，挨打掉的兵记负。
// 这样一个号在任一时间窗里：期末余额 = 期初余额 − 进攻(兵+费) − 捐出(到账+费) + 收捐 + 拍内净变化，各项都是引擎给出的整数。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/67_troop_flow.mjs <matchId> [--win 900] [--cuts t1,t2,…]
// 输出：out/<matchId>/cmd_effect.tsv（我方每条指令：拍、号、种类、pct、目标、执行前后余额、花掉的兵、手续费、是否生效、目标当时领土/余额）
//       [--tag name] 只换 troop_flow 的文件名（troop_flow_<name>.txt），用来对某个窗口另切一刀而不覆盖主表
//       out/<matchId>/troop_flow.txt（A. 全队分阶段流水；B. 每号分阶段流水；C. 每号对每个目标的进攻合计；D. 捐款税合计）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
if (!mid) { console.error('用法：67_troop_flow.mjs <matchId> [--win 900] [--cuts t1,t2,…]'); process.exit(2); }
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
// 船落在没人占的水 / 边界 / 山格时按线上规则处理（见 r07simfix.mjs；来自 R01 的 resim_lib_r01.mjs）
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const { NEUTRAL, iV } = SIM;

const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');
const realBots = new Set();
for (const ln of logText) { const m = /^\d+\t\[([A-Za-z0-9_]+)\] /.exec(ln); if (m) realBots.add(m[1]); }
const idOf = new Map();
for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { idOf.set(b, p); break; }
const botOf = new Map([...idOf].map(([b, p]) => [p, b]));
const pname = (g, q) => q >= NEUTRAL ? '无主地' : q < H ? `${(names[q] || '').trim().slice(0, 18)}#${q}[T${g.teams ? g.teams[q] : 0}]` : `AI#${q}`;

const proto = SIM.Game.prototype;
const eff = []; // 每条我方指令
const tickNet = new Map(); // bot -> [{t, d}]
const recvRows = []; // 我方号收到的捐款（含非我方捐的）
function wrap(kind, tgtIdx) {
  const orig = proto[kind];
  if (typeof orig !== 'function') return;
  proto[kind] = function (...a) {
    const p = a[a.length - 1];
    const isMine = Number.isInteger(p) && botOf.has(p) && a.length >= (kind === 'recall' || kind === 'retreat' ? 2 : 3);
    const tg = kind === 'donate' ? a[1] : null;
    const toMine = kind === 'donate' && Number.isInteger(tg) && botOf.has(tg);
    if (!isMine && !toMine) return orig.apply(this, a);
    const g = this;
    const b0 = isMine ? g.bal[p] : 0;
    const tb0 = toMine ? g.bal[tg] : 0;
    let target = kind === 'attack' ? Math.min(a[1], NEUTRAL) : kind === 'donate' ? a[1] : kind === 'retreat' ? Math.min(a[0], NEUTRAL) : -1;
    const tTerr = target >= 0 && target < NEUTRAL ? g.terr[target] : 0, tBal = target >= 0 && target < NEUTRAL ? g.bal[target] : 0;
    const tAlive = target >= 0 && target < NEUTRAL ? g.alive[target] : 1;
    const ok = orig.apply(this, a);
    if (isMine) {
      const b1 = g.bal[p];
      const pct = kind === 'recall' || kind === 'retreat' ? 0 : a[0];
      const k = kind === 'attack' ? 12 : kind === 'donate' ? 64 : 32;
      const fee = b1 < b0 ? iV(k * b0, 1024) : 0;
      eff.push({ t: g.t, bot: botOf.get(p), kind, pct, target, tname: kind === 'attack' || kind === 'donate' || kind === 'retreat' ? pname(g, target) : '', b0, b1, spent: b0 - b1, fee: Math.min(fee, b0 - b1), troops: Math.max(0, b0 - b1 - fee), ok: ok ? 1 : 0, terr: g.terr[p], tTerr, tBal, tAlive, tHuman: target >= 0 && target < H ? 1 : 0 });
    }
    if (toMine) recvRows.push({ t: g.t, to: botOf.get(tg), from: Number.isInteger(p) ? (botOf.get(p) || pname(g, p)) : '?', amt: g.bal[tg] - tb0 });
    return ok;
  };
}
for (const k of ['attack', 'donate', 'boat', 'boatTo', 'chase', 'recall', 'retreat']) wrap(k);

// ---- 拍内余额变化的分类：利息地租 / 进攻结束退回的兵 / 内置 AI（含离开座位）送来的兵 / 自己的船靠回自己岸上
let ctx = 'other';
const cat = new Map(); // bot -> {eco, refund, giftIn, boatIn, giftOut, other}（本拍累计）
const catOf = (b) => { if (!cat.has(b)) cat.set(b, { eco: 0, refund: 0, giftIn: 0, boatIn: 0, giftOut: 0, other: 0 }); return cat.get(b); };
const origEco = proto.economyTick;
proto.economyTick = function () { ctx = 'eco'; origEco.call(this); ctx = 'other'; };
const origEnd = proto.endAttack;
proto.endAttack = function (p, a, troops) { const prev = ctx; ctx = 'refund'; origEnd.call(this, p, a, troops); ctx = prev; };
const origCancel = proto.cancelAttack;
proto.cancelAttack = function (p, target) { const prev = ctx; ctx = 'refund'; origCancel.call(this, p, target); ctx = prev; };
const isMineArr = new Uint8Array(4096);
for (const p of botOf.keys()) isMineArr[p] = 1;
const origAdd = proto.addBalance;
proto.addBalance = function (p, v) {
  if (!isMineArr[p] || this.spawnPhase) return origAdd.call(this, p, v);
  const b = botOf.get(p);
  const b0 = this.bal[p];
  const r = origAdd.call(this, p, v);
  const c = catOf(b);
  c[ctx in c ? ctx : 'other'] += this.bal[p] - b0;
  if (v > this.bal[p] - b0 + 1 && ctx !== 'eco') lostAtCap.push({ t: this.t, bot: b, ctx, want: v, got: this.bal[p] - b0 });
  return r;
};
const lostAtCap = []; // 顶到 150×领土硬上限、没加进余额的兵（退兵 / 收捐 / 船）
const gifts = []; // 内置 AI（含离开后被接管的座位）送兵
const origTransfer = proto.transfer;
proto.transfer = function (p, q, troops) {
  const g = this;
  const ai = p >= H || g.state[p] === 2;
  if (!ai || (!botOf.has(p) && !botOf.has(q))) return origTransfer.call(this, p, q, troops);
  const b0 = g.bal[p];
  const prev = ctx; ctx = 'giftIn';
  let v;
  try { v = origTransfer.call(this, p, q, troops); } finally { ctx = prev; }
  if (v > 0) {
    gifts.push({ t: g.t, from: p, fromName: botOf.get(p) || pname(g, p), to: q, toName: botOf.get(q) || pname(g, q), v, fee: b0 - g.bal[p] - v });
    if (botOf.has(p)) catOf(botOf.get(p)).giftOut += b0 - g.bal[p];
  }
  return v;
};
const landings = []; // 我方号的船靠岸
const origLandAt = proto.landAt;
proto.landAt = function (p, troops, c, at) {
  const g = this;
  if (!botOf.has(p)) return origLandAt.call(this, p, troops, c, at);
  const v = g.px[c];
  const tgt = v === SIM.T_LAND ? NEUTRAL : (v >= SIM.P_INNER ? g.own[c] : -1);
  const tb0 = tgt >= 0 && tgt < NEUTRAL ? g.bal[tgt] : 0;
  const prev = ctx; ctx = 'boatIn';
  try { origLandAt.call(this, p, troops, c, at); } finally { ctx = prev; }
  const kind = tgt === NEUTRAL ? '无主地' : tgt < 0 ? '没靠上岸' : tgt === p ? '自己的地' : !g.isEnemy(p, tgt) ? '队友的岸' : '敌方';
  landings.push({ t: g.t, bot: botOf.get(p), troops, x: c % g.W, y: Math.floor(c / g.W), kind, target: tgt, tname: tgt >= 0 ? pname(g, tgt) : '', delivered: kind === '队友的岸' ? g.bal[tgt] - tb0 : kind === '自己的地' ? troops : 0 });
};
const atkOn = new Map(); // bot -> [{t, from, troops}]（每 10 拍采样：谁在打我方号）
const origTick = proto.tick;
const samples = new Map(); // bot -> Map(t -> {bal, terr})
proto.tick = function () {
  const g = this;
  const before = new Map();
  if (!g.spawnPhase) for (const [b, p] of idOf) {
    before.set(b, g.bal[p]);
    if (!samples.has(b)) { samples.set(b, new Map()); samples.get(b).set(g.t, { bal: g.bal[p], terr: g.terr[p], alive: g.alive[p], left: 0 }); }
  }
  cat.clear();
  origTick.call(this);
  if (g.spawnPhase) return;
  for (const [b, p] of idOf) {
    if (!before.has(b)) continue;
    const dlt = g.bal[p] - before.get(b);
    if (!tickNet.has(b)) tickNet.set(b, []);
    const c = cat.get(b) || { eco: 0, refund: 0, giftIn: 0, boatIn: 0, giftOut: 0, other: 0 };
    // 挨打掉的兵 = 已知的加项 − 已知的减项 − 实际净变化
    const hit = c.eco + c.refund + c.giftIn + c.boatIn + c.other - c.giftOut - dlt;
    if (dlt !== 0 || hit !== 0) tickNet.get(b).push({ t: g.t, d: dlt, eco: c.eco, refund: c.refund + c.other, giftIn: c.giftIn, boatIn: c.boatIn, giftOut: c.giftOut, hit, left: g.state[p] === 2 ? 1 : 0, alive: g.alive[p] });
    if (g.t % 10 === 0 && g.alive[p]) {
      for (const q of g.attackersOf(p)) {
        if (!atkOn.has(b)) atkOn.set(b, []);
        atkOn.get(b).push({ t: g.t, from: q, name: pname(g, q), troops: g.attackTroopsOn(q, p) });
      }
    }
    if (!samples.has(b)) samples.set(b, new Map());
    samples.get(b).set(g.t, { bal: g.bal[p], terr: g.terr[p], alive: g.alive[p], left: g.state[p] === 2 ? 1 : 0 });
  }
};

const res = await resim(mid, {});
const v = res.validate || {};
const endT = res.endTick;

// ---- 明细
const cols = ['t', 'bot', 'kind', 'pct', 'target', 'tname', 'b0', 'b1', 'spent', 'fee', 'troops', 'ok', 'terr', 'tTerr', 'tBal', 'tAlive', 'tHuman'];
fs.writeFileSync(path.join(OUT, 'cmd_effect.tsv'), cols.join('\t') + '\n' + eff.map((e) => cols.map((c) => e[c]).join('\t')).join('\n') + '\n');

// ---- 分阶段
let cuts = opt('--cuts', null);
const win = +opt('--win', 900);
if (cuts) cuts = cuts.split(',').map(Number); else { cuts = []; for (let t = 0; t <= endT; t += win) cuts.push(t); }
if (cuts[0] !== 0) cuts.unshift(0);
if (cuts[cuts.length - 1] <= endT) cuts.push(endT + 1);
const L = [];
const P = (s = '') => L.push(s);
const fmt = (n) => Math.round(n).toLocaleString('en-US');
P(`# ${mid} 兵力流水账（干净模拟器重演；与 traj.csv 核对 ${v.bothExact}/${v.rows} 一致；终局拍 ${endT}）`);
P('# 口径：进攻兵 = 指令执行前后余额差 − 手续费（陆攻 12/1024，发船 32/1024）；捐出 = 到账 + 手续费（64/1024，按捐方全部余额）；');
P('#       拍内净变化 = 每拍结算前后的余额差之和（利息 + 地租 + 退回的兵 − 挨打掉的兵），拆成「正」和「负」两栏；');
P('#       期末 = 期初 − 进攻兵 − 进攻费 − 捐到账 − 捐款费 + 收捐 + 拍内正 − 拍内负（逐号逐窗核对，差额列在最后一栏，应为 0）。');
P('#       「拍内正」里除了利息地租，还含进攻结束退回的兵、内置 AI（含离开座位）送来的兵；「拍内负」里除了挨打掉的兵，还含离开座位被内置 AI 送走的兵——E 段把它们拆开。');
P('#       发船单列一栏（带走的兵 + 32/1024 手续费），核对式里和进攻一样从余额里减掉；船在海上掉的兵不在任何一栏（它已经从余额里扣掉了），见 G 段。');
const bots = [...idOf.keys()];
const firstCache = new Map();
const firstT0 = (b) => { if (!firstCache.has(b)) { const sm = samples.get(b); let m = Infinity; if (sm) for (const k of sm.keys()) if (k < m) m = k; firstCache.set(b, Number.isFinite(m) ? m : 0); } return firstCache.get(b); };
function stat(b, t0, t1) {
  const S = { atkN: 0, atkTroops: 0, atkFee: 0, atkFail: 0, donN: 0, donAmt: 0, donFee: 0, donFail: 0, recvN: 0, recv: 0, pos: 0, neg: 0, boatN: 0, boatTroops: 0, boatFee: 0 };
  for (const e of eff) {
    if (e.bot !== b || e.t < t0 || e.t >= t1) continue;
    if (e.kind === 'attack') { S.atkN++; if (e.spent > 0) { S.atkTroops += e.troops; S.atkFee += e.fee; } else S.atkFail++; }
    else if (e.kind === 'donate') { S.donN++; if (e.spent > 0) { S.donAmt += e.troops; S.donFee += e.fee; } else S.donFail++; }
    else if (e.spent > 0) { S.boatN++; S.boatTroops += e.troops; S.boatFee += e.fee; }
  }
  for (const r of recvRows) if (r.to === b && r.t >= t0 && r.t < t1) { S.recvN++; S.recv += r.amt; }
  S.eco = 0; S.refund = 0; S.giftIn = 0; S.boatIn = 0; S.giftOut = 0; S.hit = 0;
  const lo = Math.max(t0, firstT0(b));
  for (const x of tickNet.get(b) || []) if (x.t > lo && x.t <= t1) {
    if (x.d > 0) S.pos += x.d; else S.neg -= x.d;
    S.eco += x.eco; S.refund += x.refund; S.giftIn += x.giftIn; S.boatIn += x.boatIn; S.giftOut += x.giftOut; S.hit += x.hit;
  }
  S.resid2 = (S.pos - S.neg) - (S.eco + S.refund + S.giftIn + S.boatIn - S.giftOut - S.hit);
  const sm = samples.get(b) || new Map();
  const firstT = firstT0(b);
  const at = (t) => { let tt = Math.max(Math.min(t, endT), firstT); while (tt > firstT && !sm.has(tt)) tt--; return sm.get(tt) || { bal: 0, terr: 0, alive: 0 }; };
  const a = at(t0), z = at(t1);
  S.bal0 = a.bal; S.bal1 = z.bal; S.terr0 = a.terr; S.terr1 = z.terr; S.alive1 = z.alive; S.left1 = z.left;
  S.resid = S.bal1 - (S.bal0 - S.atkTroops - S.atkFee - S.donAmt - S.donFee - S.boatTroops - S.boatFee + S.recv + S.pos - S.neg);
  return S;
}
P('');
P('A. 全队分阶段（各号相加；收捐里含非我方号捐来的）');
P('阶段\t期初余额\t期末余额\t领土 期初→期末\t进攻 条/兵/费\t发船 条/兵/费\t捐款 条/到账/费\t收捐\t拍内正(利息等)\t拍内负(挨打)\t捐款费÷拍内正\t核对差');
const J = { phases: [], perBot: {}, targets: {} };
for (let i = 0; i + 1 < cuts.length; i++) {
  const t0 = cuts[i], t1 = cuts[i + 1];
  const T = { atkN: 0, atkTroops: 0, atkFee: 0, boatN: 0, boatTroops: 0, boatFee: 0, donN: 0, donAmt: 0, donFee: 0, recv: 0, pos: 0, neg: 0, bal0: 0, bal1: 0, terr0: 0, terr1: 0, resid: 0 };
  for (const b of bots) { const s = stat(b, t0, t1); for (const k of Object.keys(T)) T[k] += s[k] || 0; }
  P(`${t0}~${Math.min(t1, endT)}\t${fmt(T.bal0)}\t${fmt(T.bal1)}\t${fmt(T.terr0)}→${fmt(T.terr1)}\t${T.atkN}/${fmt(T.atkTroops)}/${fmt(T.atkFee)}\t${T.boatN}/${fmt(T.boatTroops)}/${fmt(T.boatFee)}\t${T.donN}/${fmt(T.donAmt)}/${fmt(T.donFee)}\t${fmt(T.recv)}\t${fmt(T.pos)}\t${fmt(T.neg)}\t${T.pos ? (100 * T.donFee / T.pos).toFixed(1) + '%' : '-'}\t${T.resid}`);
  J.phases.push({ t0, t1, ...T });
}
P('');
P('B. 每号分阶段');
P('号\t阶段\t余额 期初→期末\t领土 期初→期末\t进攻 条/兵/费(没生效)\t发船 条/兵/费\t捐出 条/到账/费\t收捐 条/额\t拍内正\t拍内负\t核对差');
for (const b of bots) {
  J.perBot[b] = [];
  for (let i = 0; i + 1 < cuts.length; i++) {
    const t0 = cuts[i], t1 = cuts[i + 1];
    const s = stat(b, t0, t1);
    if (!s.bal0 && !s.bal1 && !s.atkN && !s.donN) continue;
    P(`${b}\t${t0}~${Math.min(t1, endT)}\t${fmt(s.bal0)}→${fmt(s.bal1)}\t${fmt(s.terr0)}→${fmt(s.terr1)}${s.left1 ? '(已离开)' : !s.alive1 ? '(出局)' : ''}\t${s.atkN}/${fmt(s.atkTroops)}/${fmt(s.atkFee)}(${s.atkFail})\t${s.boatN}/${fmt(s.boatTroops)}/${fmt(s.boatFee)}\t${s.donN}/${fmt(s.donAmt)}/${fmt(s.donFee)}\t${s.recvN}/${fmt(s.recv)}\t${fmt(s.pos)}\t${fmt(s.neg)}\t${s.resid}`);
    J.perBot[b].push({ t0, t1, ...s });
  }
}
P('');
P('C. 每号对每个目标的进攻合计（只列花掉 ≥ 该号全部进攻兵 3% 的目标；无主地与内置 AI 各合并成一行）');
P('号\t目标\t条数\t首拍~末拍\t发出的兵\t手续费\t目标当时领土(首→末)\t目标当时密度(首→末)');
for (const b of bots) {
  const mine = eff.filter((e) => e.bot === b && e.kind === 'attack' && e.spent > 0);
  const tot = mine.reduce((a, e) => a + e.troops, 0) || 1;
  const by = new Map();
  for (const e of mine) {
    const key = e.target >= NEUTRAL ? '无主地' : e.tHuman ? e.tname : '内置 AI（合并）';
    if (!by.has(key)) by.set(key, []);
    by.get(key).push(e);
  }
  J.targets[b] = [];
  for (const [k, es] of [...by].sort((x, y) => y[1].reduce((a, e) => a + e.troops, 0) - x[1].reduce((a, e) => a + e.troops, 0))) {
    const tr = es.reduce((a, e) => a + e.troops, 0), fee = es.reduce((a, e) => a + e.fee, 0);
    if (tr < 0.03 * tot) continue;
    const f = es[0], l = es[es.length - 1];
    const dens = (e) => e.tTerr ? (e.tBal / e.tTerr).toFixed(0) : '-';
    P(`${b}\t${k}\t${es.length}\t${f.t}~${l.t}\t${fmt(tr)}\t${fmt(fee)}\t${k === '无主地' || k.startsWith('内置') ? '-' : `${fmt(f.tTerr)}→${fmt(l.tTerr)}`}\t${k === '无主地' || k.startsWith('内置') ? '-' : `${dens(f)}→${dens(l)}`}`);
    J.targets[b].push({ target: k, n: es.length, t0: f.t, t1: l.t, troops: tr, fee });
  }
}
P('');
P('D. 捐款税（全局，引擎实收）');
{
  const dn = eff.filter((e) => e.kind === 'donate' && e.spent > 0);
  const amt = dn.reduce((a, e) => a + e.troops, 0), fee = dn.reduce((a, e) => a + e.fee, 0);
  const atk = eff.filter((e) => e.kind === 'attack' && e.spent > 0);
  const aTr = atk.reduce((a, e) => a + e.troops, 0), aFee = atk.reduce((a, e) => a + e.fee, 0);
  let pos = 0, neg = 0;
  for (const b of bots) for (const x of tickNet.get(b) || []) { if (x.d > 0) pos += x.d; else neg -= x.d; }
  P(`  捐款 ${dn.length} 笔：到账 ${fmt(amt)}，手续费 ${fmt(fee)}（费/到账 ${(fee / Math.max(1, amt)).toFixed(3)}）`);
  P(`  进攻 ${atk.length} 条生效：发出的兵 ${fmt(aTr)}，手续费 ${fmt(aFee)}；没生效（余额没变）${eff.filter((e) => e.kind === 'attack' && e.spent === 0).length} 条`);
  P(`  全队全程拍内正（利息 + 地租 + 退回的兵）合计 ${fmt(pos)}，拍内负（挨打掉的兵）合计 ${fmt(neg)}；捐款手续费相当于拍内正的 ${(100 * fee / Math.max(1, pos)).toFixed(1)}%`);
  let eco = 0, refund = 0, hit = 0;
  for (const b of bots) for (const x of tickNet.get(b) || []) { eco += x.eco; refund += x.refund; hit += x.hit; }
  const bt = eff.filter((e) => (e.kind === 'boat' || e.kind === 'boatTo') && e.spent > 0);
  const bTr = bt.reduce((a, e) => a + e.troops, 0), bFee = bt.reduce((a, e) => a + e.fee, 0);
  P(`  全程利息地租 ${fmt(eco)}；三种手续费（捐款 ${fmt(fee)} + 进攻 ${fmt(aFee)} + 发船 ${fmt(bFee)}）= ${fmt(fee + aFee + bFee)}，相当于利息地租的 ${(100 * (fee + aFee + bFee) / Math.max(1, eco)).toFixed(1)}%（其中捐款费 ${(100 * fee / Math.max(1, eco)).toFixed(1)}%）`);
  P(`  进攻净消耗 = 发出的兵 ${fmt(aTr)} − 退回的兵 ${fmt(refund)} = ${fmt(aTr - refund)}（相当于利息地租的 ${(100 * (aTr - refund) / Math.max(1, eco)).toFixed(1)}%）；挨打掉的兵 ${fmt(hit)}（${(100 * hit / Math.max(1, eco)).toFixed(1)}%）`);
  J.total = { donN: dn.length, donAmt: amt, donFee: fee, atkN: atk.length, atkTroops: aTr, atkFee: aFee, boatN: bt.length, boatTroops: bTr, boatFee: bFee, pos, neg, eco, refund, hit };
}
// ---- E. 拍内变化的分类（全队分阶段）
P('');
P('E. 拍内余额变化分类（全队分阶段）：利息地租 / 进攻结束退回的兵 / 内置 AI 或离开座位送来的兵 / 船靠回自己岸 / 挨打掉的兵 / 离开座位送走的兵（含费）；最后一栏 = 分类合计与拍内净变化的差，应为 0');
P('阶段\t利息地租\t退回的兵\tAI送来\t船回岸\t挨打掉\t离开座位送走\t差');
J.split = [];
for (let i = 0; i + 1 < cuts.length; i++) {
  const t0 = cuts[i], t1 = cuts[i + 1];
  const T = { eco: 0, refund: 0, giftIn: 0, boatIn: 0, hit: 0, giftOut: 0, resid2: 0 };
  for (const b of bots) { const s = stat(b, t0, t1); for (const k of Object.keys(T)) T[k] += s[k] || 0; }
  P(`${t0}~${Math.min(t1, endT)}\t${fmt(T.eco)}\t${fmt(T.refund)}\t${fmt(T.giftIn)}\t${fmt(T.boatIn)}\t${fmt(T.hit)}\t${fmt(T.giftOut)}\t${T.resid2}`);
  J.split.push({ t0, t1, ...T });
}
// ---- E2. 每阶段收支小结：利息地租花到哪去了
P('');
P('E2. 每阶段收支小结（全队）：利息地租 → 进攻净消耗（发出 − 退回）/ 三种手续费 / 挨打掉 / 余额变化；领土净变化；每净增一格的花费 =（进攻净消耗 + 进攻费 + 发船兵费）÷ 领土净增');
P('阶段	利息地租	进攻净消耗	手续费(捐+攻+船)	手续费÷利息地租	挨打掉	余额变化	领土净变化	每净增一格的花费');
J.summary = [];
for (let i = 0; i + 1 < cuts.length; i++) {
  const t0 = cuts[i], t1 = cuts[i + 1];
  const T = { eco: 0, refund: 0, hit: 0, atkTroops: 0, atkFee: 0, donFee: 0, boatTroops: 0, boatFee: 0, bal0: 0, bal1: 0, terr0: 0, terr1: 0 };
  for (const b of bots) { const s = stat(b, t0, t1); for (const k of Object.keys(T)) T[k] += s[k] || 0; }
  const burn = T.atkTroops - T.refund, fees = T.donFee + T.atkFee + T.boatFee, dL = T.terr1 - T.terr0;
  const per = dL > 0 ? Math.round((burn + T.atkFee + T.boatTroops + T.boatFee) / dL) : null;
  P(`${t0}~${Math.min(t1, endT)}\t${fmt(T.eco)}\t${fmt(burn)}\t${fmt(fees)}\t${(100 * fees / Math.max(1, T.eco)).toFixed(1)}%\t${fmt(T.hit)}\t${fmt(T.bal1 - T.bal0)}\t${dL >= 0 ? '+' : ''}${fmt(dL)}\t${per === null ? '-' : fmt(per)}`);
  J.summary.push({ t0, t1, eco: T.eco, burn, fees, hit: T.hit, dBal: T.bal1 - T.bal0, dTerr: dL, perPx: per });
}
// ---- F. 内置 AI / 离开座位送兵、船靠岸、顶格损失
P('');
P(`F. 内置 AI（含离开后被接管的座位）送兵，涉及我方号的 ${gifts.length} 笔`);
{
  const by = new Map();
  for (const x of gifts) { const k = `${x.fromName} → ${x.toName}`; if (!by.has(k)) by.set(k, { n: 0, v: 0, fee: 0, t0: x.t, t1: x.t }); const o = by.get(k); o.n++; o.v += x.v; o.fee += x.fee; o.t1 = x.t; }
  for (const [k, o] of [...by].sort((a, b) => b[1].v - a[1].v).slice(0, 14)) P(`  ${k}：${o.n} 笔，到账 ${fmt(o.v)}，手续费 ${fmt(o.fee)}（t=${o.t0}~${o.t1}）`);
  for (const x of gifts.filter((x) => x.v >= 100000)) P(`  大额：t=${x.t} ${x.fromName} → ${x.toName} 到账 ${fmt(x.v)}，手续费 ${fmt(x.fee)}`);
}
P('');
P(`G. 我方号的船：发船 ${eff.filter((e) => (e.kind === 'boat' || e.kind === 'boatTo') && e.spent > 0).length} 条，靠岸 ${landings.length} 次`);
for (const e of eff.filter((e) => (e.kind === 'boat' || e.kind === 'boatTo') && e.spent > 0)) P(`  发船 t=${e.t} ${e.bot} pct=${e.pct}：带兵 ${fmt(e.troops)}，手续费 ${fmt(e.fee)}（发船前余额 ${fmt(e.b0)}，领土 ${fmt(e.terr)}，密度 ${(e.b0 / Math.max(1, e.terr)).toFixed(0)}）`);
for (const x of landings) P(`  靠岸 t=${x.t} ${x.bot}：带 ${fmt(x.troops)} 兵到 (${x.x},${x.y}) → ${x.kind}${x.tname ? ' ' + x.tname : ''}${x.kind === '队友的岸' ? `（到账 ${fmt(x.delivered)}）` : ''}`);
{
  // 合计：发船带走的兵、船费、靠岸时还剩的兵（海上每 5 拍掉 1/128）、靠到队友岸上被额度拒收的兵
  const bs = eff.filter((e) => (e.kind === 'boat' || e.kind === 'boatTo') && e.spent > 0);
  const carried = bs.reduce((a2, e) => a2 + e.troops, 0), bfee = bs.reduce((a2, e) => a2 + e.fee, 0);
  const arrived = landings.reduce((a2, x) => a2 + x.troops, 0);
  const mate = landings.filter((x) => x.kind === '队友的岸');
  const mateGot = mate.reduce((a2, x) => a2 + (x.delivered || 0), 0), mateAll = mate.reduce((a2, x) => a2 + x.troops, 0);
  const small = bs.filter((e) => e.fee > e.troops);
  P(`  合计：发船 ${bs.length} 条带兵 ${fmt(carried)}、船费 ${fmt(bfee)}（船费 ÷ 带兵 = ${(100 * bfee / Math.max(1, carried)).toFixed(1)}%）；靠岸 ${landings.length} 次、靠岸时还剩 ${fmt(arrived)}（已靠岸的船在海上掉的兵不超过 ${fmt(Math.max(0, carried - arrived))}，未靠岸的也算在内）；` +
    `靠在队友岸上 ${mate.length} 次：带 ${fmt(mateAll)}，到账 ${fmt(mateGot)}，被额度拒收丢掉 ${fmt(mateAll - mateGot)}；船费比带的兵还多的船 ${small.length} 条（带兵 ${fmt(small.reduce((a2, e) => a2 + e.troops, 0))}，船费 ${fmt(small.reduce((a2, e) => a2 + e.fee, 0))}）`);
  J.boatTotals = { n: bs.length, carried, fee: bfee, landings: landings.length, arrived, mateN: mate.length, mateAll, mateGot, feeOverTroopsN: small.length };
}
P('');
P(`H. 顶到 150×领土硬上限、没加进余额的兵（退兵 / AI 送兵 / 船；利息不计）：${lostAtCap.length} 次，合计 ${fmt(lostAtCap.reduce((a, x) => a + x.want - x.got, 0))}`);
for (const x of lostAtCap.sort((a, b) => (b.want - b.got) - (a.want - a.got)).slice(0, 8)) P(`  t=${x.t} ${x.bot}（${x.ctx === 'refund' ? '退兵' : x.ctx === 'giftIn' ? 'AI 送兵' : x.ctx === 'boatIn' ? '船' : x.ctx}）：应加 ${fmt(x.want)}，实加 ${fmt(x.got)}，丢 ${fmt(x.want - x.got)}`);
J.gifts = gifts; J.landings = landings; J.lostAtCap = lostAtCap;

// ---- I. 捐款去向：每阶段谁收了多少；同一阶段里「又收又捐」的中转号；300 拍内来回倒手
P('');
P('I. 捐款去向（引擎执行的捐款指令；只算我方号之间）');
{
  const dn = eff.filter((e) => e.kind === 'donate' && e.spent > 0 && botOf.has(e.target));
  J.donFlow = [];
  for (let i = 0; i + 1 < cuts.length; i++) {
    const t0 = cuts[i], t1 = cuts[i + 1];
    const ds = dn.filter((e) => e.t >= t0 && e.t < t1);
    if (!ds.length) continue;
    const inBy = new Map(), outBy = new Map();
    for (const e of ds) {
      const to = botOf.get(e.target);
      if (!inBy.has(to)) inBy.set(to, { n: 0, amt: 0 });
      inBy.get(to).n++; inBy.get(to).amt += e.troops;
      if (!outBy.has(e.bot)) outBy.set(e.bot, { n: 0, amt: 0, fee: 0 });
      outBy.get(e.bot).n++; outBy.get(e.bot).amt += e.troops; outBy.get(e.bot).fee += e.fee;
    }
    const recv = [...inBy].sort((a, b) => b[1].amt - a[1].amt).map(([k, o]) => `${k} ${o.n} 笔 ${fmt(o.amt)}`).join('；');
    const relay = [...inBy].filter(([k]) => outBy.has(k)).map(([k, o]) => `${k} 收 ${fmt(o.amt)} / 捐出 ${fmt(outBy.get(k).amt)} + 费 ${fmt(outBy.get(k).fee)}`).join('；');
    P(`  ${t0}~${Math.min(t1, endT)}：${ds.length} 笔，到账 ${fmt(ds.reduce((a, e) => a + e.troops, 0))}，手续费 ${fmt(ds.reduce((a, e) => a + e.fee, 0))} | 收方：${recv}`);
    if (relay) P(`      同一阶段又收又捐的号：${relay}`);
    J.donFlow.push({ t0, t1, n: ds.length, amt: ds.reduce((a, e) => a + e.troops, 0), fee: ds.reduce((a, e) => a + e.fee, 0), recv: Object.fromEntries(inBy), out: Object.fromEntries(outBy) });
  }
  // 来回倒手：X→Y 之前 300 拍内有 Y→X
  let ppN = 0, ppAmt = 0, ppFee = 0;
  const ex = [];
  for (const e of dn) {
    const to = botOf.get(e.target);
    const back = dn.filter((x) => x.bot === to && botOf.get(x.target) === e.bot && x.t < e.t && x.t >= e.t - 300);
    if (back.length) { ppN++; ppAmt += e.troops; ppFee += e.fee; if (ex.length < 6) ex.push(`${back[back.length - 1].t} ${to}→${e.bot} ${fmt(back[back.length - 1].troops)}，${e.t} ${e.bot}→${to} ${fmt(e.troops)}`); }
  }
  const tot = dn.reduce((a, e) => a + e.troops, 0);
  P(`  300 拍内来回倒手（X→Y 之前 300 拍内有过 Y→X）：${ppN} 笔，到账 ${fmt(ppAmt)}（占全部到账的 ${(100 * ppAmt / Math.max(1, tot)).toFixed(1)}%），手续费 ${fmt(ppFee)}` + (ex.length ? `；例：${ex.join('；')}` : ''));
  // 转手：某号收到捐款后 300 拍内又捐出去（不论给谁）
  let rlN = 0, rlAmt = 0, rlFee = 0;
  for (const e of dn) {
    const got = dn.filter((x) => botOf.get(x.target) === e.bot && x.t < e.t && x.t >= e.t - 300);
    if (got.length) { rlN++; rlAmt += e.troops; rlFee += e.fee; }
  }
  P(`  转手（捐出之前 300 拍内自己刚收过捐款）：${rlN} 笔，到账 ${fmt(rlAmt)}（占 ${(100 * rlAmt / Math.max(1, tot)).toFixed(1)}%），手续费 ${fmt(rlFee)}`);
  J.pingpong = { n: ppN, amt: ppAmt, fee: ppFee }; J.relay = { n: rlN, amt: rlAmt, fee: rlFee };
}

// ---- 10 拍一桶的明细，供对账脚本用
{
  const rows = ['t0\tbot\teco\trefund\tgiftIn\tboatIn\tgiftOut\thit\tbal\tterr'];
  for (const b of bots) {
    const sm = samples.get(b) || new Map();
    const bk = new Map();
    for (const x of tickNet.get(b) || []) {
      const k = Math.floor((x.t - 1) / 10) * 10;
      if (!bk.has(k)) bk.set(k, { eco: 0, refund: 0, giftIn: 0, boatIn: 0, giftOut: 0, hit: 0 });
      const o = bk.get(k);
      o.eco += x.eco; o.refund += x.refund; o.giftIn += x.giftIn; o.boatIn += x.boatIn; o.giftOut += x.giftOut; o.hit += x.hit;
    }
    for (const [k, o] of [...bk].sort((a, b) => a[0] - b[0])) { const z = sm.get(Math.min(k + 10, endT)) || {}; rows.push([k, b, o.eco, o.refund, o.giftIn, o.boatIn, o.giftOut, o.hit, z.bal ?? '', z.terr ?? ''].join('\t')); }
  }
  fs.writeFileSync(path.join(OUT, 'tick_net.tsv'), rows.join('\n') + '\n');
}

// ---- DROP30 自动对账：digest.json 里每个「90 拍内余额跌 30% 以上」的窗口，用引擎真账拆开
{
  const dgPath = path.join(OUT, 'digest.json');
  if (fs.existsSync(dgPath)) {
    const dg = JSON.parse(fs.readFileSync(dgPath, 'utf8'));
    const notes = {};
    const R = [`# ${mid} DROP30 对账（每个窗口：余额变化 = −进攻(兵+费) −捐出(到账+费) −发船(兵+费) +收捐 +利息地租 +退回的兵 +AI送来 +船回岸 −挨打掉 −离开座位送走；差应为 0）`];
    for (const d of dg.drop30 || []) {
      const b = d.bot, t0 = d.t0, t1 = d.t1;
      if (!idOf.has(b)) continue;
      const s = stat(b, t0, t1);
      const parts = [];
      const es = eff.filter((e) => e.bot === b && e.t >= t0 && e.t < t1 && e.spent > 0);
      const grp = (kind) => { const by = new Map(); for (const e of es.filter((e) => e.kind === kind)) { const k = e.tname || '船'; if (!by.has(k)) by.set(k, { n: 0, tr: 0, fee: 0 }); const o = by.get(k); o.n++; o.tr += e.troops; o.fee += e.fee; } return [...by].sort((a, b) => b[1].tr - a[1].tr); };
      const short = (k) => k.replace(/\[T\d\]$/, '').replace(/^\[APEX\] /, '');
      const at = grp('attack');
      if (at.length) parts.push(`进攻 ${at.reduce((a, x) => a + x[1].n, 0)} 条共 ${fmt(s.atkTroops)} 兵 + 费 ${fmt(s.atkFee)}（${at.slice(0, 2).map(([k, o]) => `${short(k)} ${fmt(o.tr)}`).join('、')}）`);
      const dn = grp('donate');
      if (dn.length) parts.push(`捐出 ${dn.reduce((a, x) => a + x[1].n, 0)} 笔到账 ${fmt(s.donAmt)} + 费 ${fmt(s.donFee)}（→${dn.slice(0, 2).map(([k, o]) => `${short(k)} ${fmt(o.tr)}`).join('、')}）`);
      if (s.boatN) parts.push(`发船 ${s.boatN} 条带兵 ${fmt(s.boatTroops)} + 费 ${fmt(s.boatFee)}`);
      if (s.recv) parts.push(`收捐 ${s.recvN} 笔 ${fmt(s.recv)}`);
      if (s.hit > 0) {
        const who = new Map();
        for (const x of atkOn.get(b) || []) if (x.t >= t0 && x.t <= t1) who.set(x.name, Math.max(who.get(x.name) || 0, x.troops));
        const top = [...who].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([k, v]) => `${short(k)} 进攻槽峰值 ${fmt(v)}`).join('、');
        parts.push(`挨打掉 ${fmt(s.hit)} 兵${top ? `（${top}）` : ''}`);
      }
      if (s.giftOut) parts.push(`离开座位送走 ${fmt(s.giftOut)}`);
      if (s.refund) parts.push(`退回 ${fmt(s.refund)}`);
      if (s.giftIn) parts.push(`AI 送来 ${fmt(s.giftIn)}`);
      parts.push(`利息地租 +${fmt(s.eco)}`);
      const logN = d.donOutN || 0, exN = dn.reduce((a, x) => a + x[1].n, 0);
      if (logN !== exN) parts.push(`日志里这段有 ${logN} 条调度，引擎只执行 ${exN} 条`);
      const note = `${fmt(s.bal0)}→${fmt(s.bal1)}，领土 ${fmt(s.terr0)}→${fmt(s.terr1)}：` + parts.join('；') + (s.resid || s.resid2 ? `；核对差 ${s.resid}/${s.resid2}` : '');
      notes[`${b}@${t0}`] = note;
      R.push(`${b}@${t0}~${t1}\t${note}`);
    }
    fs.writeFileSync(path.join(OUT, 'drop30_recon.txt'), R.join('\n') + '\n');
    fs.writeFileSync(path.join(OUT, 'drop30_recon.json'), JSON.stringify(notes));
  }
}
const txt = L.join('\n') + '\n';
const tag = opt('--tag', '');
fs.writeFileSync(path.join(OUT, tag ? `troop_flow_${tag}.txt` : 'troop_flow.txt'), txt);
fs.writeFileSync(path.join(OUT, tag ? `troop_flow_${tag}.json` : 'troop_flow.json'), JSON.stringify(J));
process.stdout.write(txt.split('\n').slice(0, 40).join('\n') + '\n');
