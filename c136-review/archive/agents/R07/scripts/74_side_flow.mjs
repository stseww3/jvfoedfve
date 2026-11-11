#!/usr/bin/env node
// 74_side_flow.mjs — R07：全场真人（不只我方号）的兵力流水账，按「我方号 / 本队其他真人 / 每个敌队的真人」分组、分阶段对照。
// 用来回答：同一段时间里，对手的兵花在哪、我们的兵花在哪；谁在攒、谁在打、每一格地花了多少。
//
// 做法同 67_troop_flow.mjs：用统筹的干净模拟器（resim）重演录像，包住 Game.attack / donate / boat / boatTo / chase，
// 记每条指令执行前后的余额；economyTick / endAttack / cancelAttack / transfer / landAt 里的 addBalance 按来源分类；
// 每拍结算前后的余额差减去已知加项 = 挨打掉的兵。所有数字都是引擎给出的整数。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/74_side_flow.mjs <matchId> --cuts 0,990,1800,… [--top 6] [--tag name]
// 输出：out/<matchId>/side_flow[_<tag>].txt / .json；out/<matchId>/humans_cmd.tsv（全场真人每条指令的真实效果）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid) { console.error('用法：74_side_flow.mjs <matchId> --cuts 0,990,… [--top 6] [--tag name]'); process.exit(2); }
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
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '').trim()) : [];
const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');
const realBots = new Set();
for (const ln of logText) { const m = /^\d+\t\[([A-Za-z0-9_]+)\] /.exec(ln); if (m) realBots.add(m[1]); }
const botOf = new Map();
for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].toLowerCase().endsWith(b.toLowerCase())) { botOf.set(p, b); break; }
const TOP = +opt('--top', 6);
const tag = opt('--tag', '');

const proto = SIM.Game.prototype;
const eff = [];
let teamsSeen = null;
const tgtType = (g, q) => q >= NEUTRAL ? 'N' : q >= H ? 'A' : g.state[q] === 2 ? 'L' : 'H';
for (const kind of ['attack', 'donate', 'boat', 'boatTo', 'chase']) {
  const orig = proto[kind];
  if (typeof orig !== 'function') continue;
  proto[kind] = function (...a) {
    const p = a[a.length - 1];
    const g = this;
    if (!Number.isInteger(p) || p < 0 || p >= H || g.spawnPhase) return orig.apply(this, a);
    const b0 = g.bal[p];
    const target = kind === 'attack' ? Math.min(a[1], NEUTRAL) : kind === 'donate' ? a[1] : -1;
    const tt = kind === 'attack' ? tgtType(g, target) : kind === 'donate' ? 'D' : 'B';
    const tTerr = target >= 0 && target < NEUTRAL ? g.terr[target] : 0, tBal = target >= 0 && target < NEUTRAL ? g.bal[target] : 0;
    const ok = orig.apply(this, a);
    const b1 = g.bal[p];
    const k = kind === 'attack' ? 12 : kind === 'donate' ? 64 : 32;
    const spent = b0 - b1;
    const fee = spent > 0 ? Math.min(iV(k * b0, 1024), spent) : 0;
    eff.push({ t: g.t, p, kind, pct: a[0], tt, target, b0, b1, spent, fee, troops: spent - fee, terr: g.terr[p], tTerr, tBal, recv: kind === 'donate' && target >= 0 && target < NEUTRAL ? g.bal[target] - tBal : 0, left: g.state[p] === 2 ? 1 : 0 });
    return ok;
  };
}
let ctx = 'other';
const mk = () => ({ eco: 0, refund: 0, giftIn: 0, boatIn: 0, giftOut: 0, other: 0 });
let cat = new Array(H).fill(null);
const catOf = (p) => cat[p] || (cat[p] = mk());
const origEco = proto.economyTick;
proto.economyTick = function () { ctx = 'eco'; origEco.call(this); ctx = 'other'; };
const origEnd = proto.endAttack;
proto.endAttack = function (p, a, troops) { const prev = ctx; ctx = 'refund'; origEnd.call(this, p, a, troops); ctx = prev; };
const origCancel = proto.cancelAttack;
proto.cancelAttack = function (p, target) { const prev = ctx; ctx = 'refund'; origCancel.call(this, p, target); ctx = prev; };
const origAdd = proto.addBalance;
proto.addBalance = function (p, v) {
  if (p >= H || this.spawnPhase) return origAdd.call(this, p, v);
  const b0 = this.bal[p];
  const r = origAdd.call(this, p, v);
  const c = catOf(p);
  c[ctx in c ? ctx : 'other'] += this.bal[p] - b0;
  return r;
};
const origTransfer = proto.transfer;
proto.transfer = function (p, q, troops) {
  const g = this;
  const b0 = p < H ? g.bal[p] : 0;
  const prev = ctx; ctx = 'giftIn';
  let v;
  try { v = origTransfer.call(this, p, q, troops); } finally { ctx = prev; }
  if (v > 0 && p < H) catOf(p).giftOut += b0 - g.bal[p];
  return v;
};
const origLandAt = proto.landAt;
proto.landAt = function (p, troops, c, at) {
  const prev = ctx; ctx = 'boatIn';
  try { return origLandAt.call(this, p, troops, c, at); } finally { ctx = prev; }
};
// 每个真人逐拍：余额、领土、分类净变化（只在有变化的拍记）
const tickRows = Array.from({ length: H }, () => []);
const snap = Array.from({ length: H }, () => new Map()); // t -> [bal, terr, alive, state]
const origTick = proto.tick;
const before = new Float64Array(H);
proto.tick = function () {
  const g = this;
  if (!g.spawnPhase) for (let p = 0; p < H; p++) { before[p] = g.bal[p]; if (!snap[p].size) snap[p].set(g.t, [g.bal[p], g.terr[p], g.alive[p], g.state[p]]); }
  cat = new Array(H).fill(null);
  const wasSpawn = g.spawnPhase;
  origTick.call(this);
  if (g.spawnPhase || wasSpawn) return;
  if (!teamsSeen && g.teams) teamsSeen = Array.from(g.teams).slice(0, H);
  for (let p = 0; p < H; p++) {
    const dlt = g.bal[p] - before[p];
    const c = cat[p];
    if (dlt !== 0 || c) {
      const cc = c || mk();
      const hit = cc.eco + cc.refund + cc.giftIn + cc.boatIn + cc.other - cc.giftOut - dlt;
      tickRows[p].push([g.t, dlt, cc.eco, cc.refund + cc.other, cc.giftIn, cc.boatIn, cc.giftOut, hit]);
    }
    snap[p].set(g.t, [g.bal[p], g.terr[p], g.alive[p], g.state[p]]);
  }
};
const res = await resim(mid, {});
const v = res.validate || {};
const endT = res.endTick;
const teams = teamsSeen || new Array(H).fill(0);

const cols = ['t', 'p', 'name', 'team', 'squad', 'kind', 'pct', 'tt', 'target', 'b0', 'b1', 'spent', 'fee', 'troops', 'terr', 'tTerr', 'tBal', 'recv', 'left'];
fs.writeFileSync(path.join(OUT, 'humans_cmd.tsv'), cols.join('\t') + '\n' + eff.map((e) => cols.map((c) => c === 'name' ? names[e.p] : c === 'team' ? teams[e.p] : c === 'squad' ? (botOf.has(e.p) ? 1 : 0) : e[c]).join('\t')).join('\n') + '\n');

let cuts = (opt('--cuts', '') || '').split(',').filter(Boolean).map(Number);
if (!cuts.length) for (let t = 0; t <= endT; t += 900) cuts.push(t);
if (cuts[0] !== 0) cuts.unshift(0);
if (cuts[cuts.length - 1] <= endT) cuts.push(endT + 1);
const at = (p, t) => { const sm = snap[p]; let tt = Math.min(t, endT); while (tt > 0 && !sm.has(tt)) tt--; return sm.get(tt) || [0, 0, 0, 0]; };
function stat(p, t0, t1) {
  const S = { atkN: 0, atkNn: 0, atkNa: 0, atkNh: 0, tN: 0, tA: 0, tH: 0, atkFee: 0, boatN: 0, boatTroops: 0, boatFee: 0, donN: 0, donAmt: 0, donFee: 0, recvN: 0, recv: 0, eco: 0, refund: 0, giftIn: 0, boatIn: 0, giftOut: 0, hit: 0, net: 0, bigN: 0, bigTroops: 0, pctH: [] };
  for (const e of eff) {
    if (e.t < t0 || e.t >= t1) continue;
    if (e.kind === 'donate' && e.target === p && e.recv > 0) { S.recvN++; S.recv += e.recv; }
    if (e.p !== p || e.spent <= 0) continue;
    if (e.kind === 'attack') {
      S.atkN++; S.atkFee += e.fee;
      if (e.tt === 'N') { S.atkNn++; S.tN += e.troops; } else if (e.tt === 'H') { S.atkNh++; S.tH += e.troops; S.pctH.push(e.pct); if (e.pct >= 300) { S.bigN++; S.bigTroops += e.troops; } } else { S.atkNa++; S.tA += e.troops; }
    } else if (e.kind === 'donate') { S.donN++; S.donAmt += e.spent - e.fee; S.donFee += e.fee; }
    else { S.boatN++; S.boatTroops += e.troops; S.boatFee += e.fee; }
  }
  for (const x of tickRows[p]) if (x[0] > t0 && x[0] <= t1) { S.net += x[1]; S.eco += x[2]; S.refund += x[3]; S.giftIn += x[4]; S.boatIn += x[5]; S.giftOut += x[6]; S.hit += x[7]; }
  const a = at(p, t0), z = at(p, t1);
  S.bal0 = a[0]; S.terr0 = a[1]; S.alive0 = a[2] && a[3] !== 2 ? 1 : 0; S.bal1 = z[0]; S.terr1 = z[1]; S.alive1 = z[2] && z[3] !== 2 ? 1 : 0;
  S.resid = S.bal1 - (S.bal0 - (S.tN + S.tA + S.tH) - S.atkFee - S.boatTroops - S.boatFee - S.donAmt - S.donFee + S.recv + S.net);
  return S;
}
const add = (A, B) => { for (const k of Object.keys(B)) { if (k === 'pctH') A.pctH = (A.pctH || []).concat(B.pctH); else A[k] = (A[k] || 0) + B[k]; } return A; };
const squadTeams = new Set([...botOf.keys()].map((p) => teams[p]));
const groupOf = (p) => botOf.has(p) ? '我方号' : squadTeams.has(teams[p]) ? `T${teams[p]} 其他真人` : `T${teams[p]} 真人`;
const groups = [...new Set(Array.from({ length: H }, (_, p) => groupOf(p)))].sort((a, b) => (a === '我方号' ? -1 : b === '我方号' ? 1 : a.localeCompare(b)));
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const med = (a) => { if (!a.length) return '-'; const s = [...a].sort((x, y) => x - y); return s[s.length >> 1]; };
const L = [];
const P = (s = '') => L.push(s);
P(`# ${mid} 全场真人分组流水账（干净模拟器重演；与 traj.csv 核对 ${v.bothExact}/${v.rows} 一致；终局拍 ${endT}；真人 ${H} 个）`);
P('# 分组：我方号 / 和我方同队的其他真人 / 每个敌队的真人。离开后被内置 AI 接管的席位仍算在原来的组里（它送走的兵记在「送走」）。');
P('# 口径：进攻兵 = 指令执行前后余额差 − 手续费（陆攻 12/1024，发船 32/1024，捐款 64/1024，都按发令时全部余额）；');
P('#       进攻净消耗 = 发出的兵（打无主地 + 打内置 AI + 打真人）− 进攻结束退回的兵；挨打掉 = 每拍结算的余额差里扣掉利息地租、退兵、收到的兵之后的缺口；');
P('#       每净增一格 =（进攻净消耗 + 进攻费 + 发船兵费）÷ 领土净增（净增 ≤ 0 记「-」）。逐人逐窗核对差额见最后一栏（应为 0）。');
const J = { cuts, groups: {}, players: {} };
P('');
P('A. 分组 × 阶段');
P('阶段\t组\t在场 期初→期末\t领土 期初→期末\t余额 期初→期末\t密度 期初→期末\t利息地租\t进攻 条(无主/AI/真人)\t发兵 无主地/内置AI/真人\t退回\t进攻净消耗\t手续费 攻/船/捐\t捐款 笔/到账\t挨打掉\t每净增一格\t核对差');
const perPhase = [];
for (let i = 0; i + 1 < cuts.length; i++) {
  const t0 = cuts[i], t1 = cuts[i + 1] - (i + 2 === cuts.length ? 1 : 0);
  const label = `${t0}~${i + 2 === cuts.length ? endT : cuts[i + 1]}`;
  const row = {};
  for (const gname of groups) {
    const G = { n0: 0, n1: 0 };
    for (let p = 0; p < H; p++) {
      if (groupOf(p) !== gname) continue;
      const S = stat(p, t0, t1);
      add(G, S);
      G.n0 += S.alive0 && S.terr0 > 0 ? 1 : 0; G.n1 += S.alive1 && S.terr1 > 0 ? 1 : 0;
    }
    const sent = G.tN + G.tA + G.tH, burn = sent - G.refund, dTerr = G.terr1 - G.terr0;
    const per = dTerr > 0 ? Math.round((burn + G.atkFee + G.boatTroops + G.boatFee) / dTerr) : '-';
    P(`${label}\t${gname}\t${G.n0}→${G.n1}\t${fmt(G.terr0)}→${fmt(G.terr1)}\t${fmt(G.bal0)}→${fmt(G.bal1)}\t${(G.bal0 / Math.max(1, G.terr0)).toFixed(0)}→${(G.bal1 / Math.max(1, G.terr1)).toFixed(0)}\t${fmt(G.eco)}\t${G.atkN}(${G.atkNn}/${G.atkNa}/${G.atkNh})\t${fmt(G.tN)}/${fmt(G.tA)}/${fmt(G.tH)}\t${fmt(G.refund)}\t${fmt(burn)}\t${fmt(G.atkFee)}/${fmt(G.boatFee)}/${fmt(G.donFee)}\t${G.donN}/${fmt(G.donAmt)}\t${fmt(G.hit)}\t${per}\t${G.resid}`);
    row[gname] = { n0: G.n0, n1: G.n1, terr0: G.terr0, terr1: G.terr1, bal0: G.bal0, bal1: G.bal1, eco: G.eco, atkN: G.atkN, atkNn: G.atkNn, atkNa: G.atkNa, atkNh: G.atkNh, tN: G.tN, tA: G.tA, tH: G.tH, refund: G.refund, burn, atkFee: G.atkFee, boatFee: G.boatFee, donFee: G.donFee, donN: G.donN, donAmt: G.donAmt, hit: G.hit, boatN: G.boatN, boatTroops: G.boatTroops, perPx: per, bigN: G.bigN, bigTroops: G.bigTroops, pctHmed: med(G.pctH || []), resid: G.resid };
  }
  perPhase.push({ label, t0, t1, row });
}
J.phases = perPhase;
P('');
P('B. 打真人的指令：单条有多重（pct 是发令时余额的千分比 ×1.024；「重手」= pct ≥ 300，即一条押上约三成以上余额）');
P('阶段\t组\t打真人 条数\tpct 中位数\t重手 条数\t重手发兵\t重手占打真人发兵\t发船 条/兵');
for (const ph of perPhase) for (const gname of groups) {
  const r = ph.row[gname];
  if (!r.atkNh && !r.boatN) continue;
  P(`${ph.label}\t${gname}\t${r.atkNh}\t${r.pctHmed}\t${r.bigN}\t${fmt(r.bigTroops)}\t${r.tH > 0 ? (100 * r.bigTroops / r.tH).toFixed(0) + '%' : '-'}\t${r.boatN}/${fmt(r.boatTroops)}`);
}
// 逐人：全程 + 领土峰值最高的非我方真人逐阶段
const peak = new Array(H).fill(0);
for (let p = 0; p < H; p++) for (const s of snap[p].values()) if (s[1] > peak[p]) peak[p] = s[1];
const order = Array.from({ length: H }, (_, p) => p).filter((p) => peak[p] > 0).sort((a, b) => peak[b] - peak[a]);
P('');
P('C. 逐人全程合计（按领土峰值排；我方号标 *）');
P('玩家\t组\t领土峰值\t利息地租\t进攻 条(无主/AI/真人)\t发兵 无主地/内置AI/真人\t退回\t进攻净消耗\t手续费 攻/船/捐\t捐出 笔/到账\t收捐 笔/到账\t挨打掉\t重手 条/兵\t核对差');
for (const p of order) {
  const S = stat(p, 0, endT);
  const burn = S.tN + S.tA + S.tH - S.refund;
  P(`${botOf.has(p) ? '*' : ''}${names[p].slice(0, 18)}#${p}\t${groupOf(p)}\t${fmt(peak[p])}\t${fmt(S.eco)}\t${S.atkN}(${S.atkNn}/${S.atkNa}/${S.atkNh})\t${fmt(S.tN)}/${fmt(S.tA)}/${fmt(S.tH)}\t${fmt(S.refund)}\t${fmt(burn)}\t${fmt(S.atkFee)}/${fmt(S.boatFee)}/${fmt(S.donFee)}\t${S.donN}/${fmt(S.donAmt)}\t${S.recvN}/${fmt(S.recv)}\t${fmt(S.hit)}\t${S.bigN}/${fmt(S.bigTroops)}\t${S.resid}`);
  J.players[p] = { name: names[p], group: groupOf(p), peak: peak[p], eco: S.eco, atkN: S.atkN, tN: S.tN, tA: S.tA, tH: S.tH, refund: S.refund, burn, atkFee: S.atkFee, boatFee: S.boatFee, donFee: S.donFee, donN: S.donN, donAmt: S.donAmt, recvN: S.recvN, recv: S.recv, hit: S.hit, bigN: S.bigN, bigTroops: S.bigTroops };
}
const topOthers = order.filter((p) => !botOf.has(p)).slice(0, TOP);
P('');
P(`D. 领土峰值最高的 ${topOthers.length} 个非我方真人，逐阶段`);
P('玩家\t阶段\t领土 期初→期末\t余额 期初→期末\t密度 期初→期末\t利息地租\t进攻 条(无主/AI/真人)\t发兵 无主地/内置AI/真人\t退回\t手续费合计\t捐出 笔/到账\t收捐 笔/到账\t挨打掉\t重手 条/兵');
for (const p of topOthers) for (let i = 0; i + 1 < cuts.length; i++) {
  const t0 = cuts[i], t1 = cuts[i + 1] - (i + 2 === cuts.length ? 1 : 0);
  const S = stat(p, t0, t1);
  if (!S.terr0 && !S.terr1) continue;
  P(`${names[p].slice(0, 18)}#${p}[T${teams[p]}]\t${t0}~${i + 2 === cuts.length ? endT : cuts[i + 1]}\t${fmt(S.terr0)}→${fmt(S.terr1)}\t${fmt(S.bal0)}→${fmt(S.bal1)}\t${(S.bal0 / Math.max(1, S.terr0)).toFixed(0)}→${(S.bal1 / Math.max(1, S.terr1)).toFixed(0)}\t${fmt(S.eco)}\t${S.atkN}(${S.atkNn}/${S.atkNa}/${S.atkNh})\t${fmt(S.tN)}/${fmt(S.tA)}/${fmt(S.tH)}\t${fmt(S.refund)}\t${fmt(S.atkFee + S.boatFee + S.donFee)}\t${S.donN}/${fmt(S.donAmt)}\t${S.recvN}/${fmt(S.recv)}\t${fmt(S.hit)}\t${S.bigN}/${fmt(S.bigTroops)}`);
}
{
  // E. 真人打真人的发兵矩阵（全程；按「进攻方 → 目标」合计；目标在发令那一拍是真人席位）
  const mat = new Map();
  for (const e of eff) {
    if (e.kind !== 'attack' || !(e.spent > 0) || e.tt !== 'H') continue;
    const k = `${e.p}>${e.target}`;
    const m = mat.get(k) || { from: e.p, to: e.target, n: 0, troops: 0, fee: 0, t0: e.t, t1: e.t, heavy: 0 };
    m.n++; m.troops += e.troops; m.fee += e.fee; m.t0 = Math.min(m.t0, e.t); m.t1 = Math.max(m.t1, e.t); if (e.pct >= 300) m.heavy++;
    mat.set(k, m);
  }
  const rowsE = [...mat.values()].sort((a, b) => b.troops - a.troops);
  const nm = (p) => `${botOf.has(p) ? '*' : ''}${names[p].slice(0, 18)}#${p}[T${teams[p]}]`;
  P('');
  P(`E. 真人打真人的发兵矩阵（全程 ${rowsE.length} 对；列出发兵最多的 ${Math.min(40, rowsE.length)} 对；我方号标 *）`);
  P('进攻方\t目标\t条数\t发兵合计\t手续费\t其中重手(pct≥300)条数\t第一条~最后一条');
  for (const m of rowsE.slice(0, 40)) P(`${nm(m.from)}\t${nm(m.to)}\t${m.n}\t${fmt(m.troops)}\t${fmt(m.fee)}\t${m.heavy}\t${m.t0}~${m.t1}`);
  const byTo = new Map(), byFrom = new Map();
  for (const m of rowsE) {
    const a = byTo.get(m.to) || { n: 0, troops: 0 }; a.n += m.n; a.troops += m.troops; byTo.set(m.to, a);
    const b = byFrom.get(m.from) || { n: 0, troops: 0 }; b.n += m.n; b.troops += m.troops; byFrom.set(m.from, b);
  }
  P('  按目标合计（挨了多少真人的兵）：' + [...byTo].sort((a, b) => b[1].troops - a[1].troops).slice(0, 20).map(([p, a]) => `${nm(p)} ${a.n} 条 ${fmt(a.troops)}`).join('；'));
  P('  按进攻方合计（往真人身上发了多少）：' + [...byFrom].sort((a, b) => b[1].troops - a[1].troops).slice(0, 20).map(([p, a]) => `${nm(p)} ${a.n} 条 ${fmt(a.troops)}`).join('；'));
  J.matrix = rowsE.map((m) => ({ from: names[m.from], to: names[m.to], n: m.n, troops: m.troops, fee: m.fee, heavy: m.heavy, t0: m.t0, t1: m.t1 }));
  // F. 我方号打过的每个真人：他身上的兵有多少是我方发的、多少是同队其他真人发的、多少是别的队发的；他后来怎么样
  const sqTeams = new Set([...botOf.keys()].map((q) => teams[q]));
  const tgts = [...new Set(rowsE.filter((m) => botOf.has(m.from)).map((m) => m.to))];
  const F = [];
  for (const q of tgts) {
    const o = { q, sq: 0, sqN: 0, mate: 0, mateN: 0, oth: 0, othN: 0, by: new Map(), mateBy: new Map(), t0: Infinity, t1: -Infinity };
    for (const m of rowsE) {
      if (m.to !== q) continue;
      if (botOf.has(m.from)) { o.sq += m.troops; o.sqN += m.n; o.by.set(m.from, (o.by.get(m.from) || 0) + m.troops); o.t0 = Math.min(o.t0, m.t0); o.t1 = Math.max(o.t1, m.t1); }
      else if (sqTeams.has(teams[m.from])) { o.mate += m.troops; o.mateN += m.n; o.mateBy.set(m.from, (o.mateBy.get(m.from) || 0) + m.troops); }
      else { o.oth += m.troops; o.othN += m.n; }
    }
    let peak = 0, tLeft = null, tGone = null, had = false;
    for (const [t, x] of snap[q]) { if (x[1] > peak) peak = x[1]; if (x[1] > 0) had = true; if (tLeft === null && x[3] === 2) tLeft = t; if (tGone === null && had && (!x[2] || x[1] === 0)) tGone = t; }
    o.peak = peak; o.tLeft = tLeft; o.tGone = tGone;
    F.push(o);
  }
  F.sort((a2, b2) => b2.sq - a2.sq);
  P('');
  P(`F. 我方号打过的真人（${F.length} 个；只算他还是真人席位时挨的兵）：我方发兵 / 同队其他真人发兵 / 别的队发兵；他的领土峰值、离开拍、出局拍`);
  for (const o of F) {
    const all = o.sq + o.mate + o.oth;
    P(`  ${nm(o.q)}：我方 ${o.sqN} 条 ${fmt(o.sq)}（${(100 * o.sq / Math.max(1, all)).toFixed(0)}%；${[...o.by].sort((a2, b2) => b2[1] - a2[1]).slice(0, 4).map(([p2, v2]) => `${names[p2].replace(/^.*\] /, '')} ${fmt(v2)}`).join('、')}；t=${o.t0}~${o.t1}）` +
      ` / 同队其他真人 ${o.mateN} 条 ${fmt(o.mate)}${o.mateBy.size ? `（${[...o.mateBy].sort((a2, b2) => b2[1] - a2[1]).slice(0, 3).map(([p2, v2]) => `${names[p2].slice(0, 14)} ${fmt(v2)}`).join('、')}）` : ''}` +
      ` / 别的队 ${o.othN} 条 ${fmt(o.oth)}；领土峰值 ${fmt(o.peak)}，${o.tLeft !== null && (o.tGone === null || o.tLeft < o.tGone) ? `t=${o.tLeft} 离开，` : ''}${o.tGone !== null ? `t=${o.tGone} 出局` : '活到终局'}`);
  }
  J.squadTargets = F.map((o) => ({ target: names[o.q], team: teams[o.q], squadN: o.sqN, squadTroops: o.sq, mateN: o.mateN, mateTroops: o.mate, otherN: o.othN, otherTroops: o.oth, peak: o.peak, tLeft: o.tLeft, tGone: o.tGone }));
}
const sfx = tag ? `_${tag}` : '';
fs.writeFileSync(path.join(OUT, `side_flow${sfx}.txt`), L.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, `side_flow${sfx}.json`), JSON.stringify(J));
process.stdout.write(L.slice(0, 8).join('\n') + `\n…（共 ${L.length} 行；指令 ${eff.length} 条）\n`);
