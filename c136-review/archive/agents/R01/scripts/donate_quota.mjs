#!/usr/bin/env node
// donate_quota.mjs — 捐兵的“引擎报价”账：日志里每条捐兵行（c110 的 [HL-DONATE]、c116 的 [HL-DISPATCH]）在引擎里能不能收。
//
// 引擎（src/sim/sim/game.js）对“给真人捐兵”有三道闸：
//   1) 容量 receiverRoom L340–345：接收方余额不能超过 150 × 领土；
//   2) 额度 bookDonation L370–376：每个真人一个累计额度 donQuota[q]，全场一个上限 donCap（开局 15，每 100 拍在 t%100==99 时
//      +4（t<1071）/ +6（<2142）/ +8（<3213）/ +10，L379–383）；一次捐 v 兵的花费 donationCost L348–357 =
//      2 + 100v/(k·uw)（uw = 1 + 陆地/300；k = 1（t<357）、4（<714）、10（<1071）、30（<2142）、100（<3213）），
//      3213 拍起 = 4 + 100v/softCap(q)（softCap = 100 × 领土）；
//   3) 免额度 donationFree L360–362：4284 拍起，或者接收方是 isBot（内置 AI、离场壳）。
// 被拒的捐兵 donate() 返回 false，一兵不动。15 局的录像里 1608 条捐兵指令重演全部成功（0 条被拒），
// 即录像只留下了成功的捐兵；日志里有、录像里没有的捐兵行，本脚本看它们在“该到的那几拍”引擎报价是不是 0。
//
// 用法：node scripts/donate_quota.mjs <局号> [--replay <同局A包>] [--log <日志包>] [--win 800] [--scan 300]
// 依赖：out/<局号>/replay_cmds.csv（replay_cmds.mjs）。输出：out/<局号>/donate_quota.csv、donate_quota.json + 屏幕小结。
// 对每条日志行（号 p、本地拍 t、对象 q、pct）：
//   落地的（录像里同号、同对象、同 pct、落地拍在 [t, t+win] 的第一条没用过的指令）：记落地那一拍执行前的 容量/已用额度/上限/这一笔的花费；
//   没落地的：在 t+7、t+14、t+21、t+28 拍（指令执行前）各取一次报价 donateQuote(pct, q, p)，并从 t+7 到 t+scan 每 7 拍取一次，
//   记被拒的次数和原因（容量 / 额度 / 对象已死 / 自己已死或已离场 / 不是队友）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps } from './resim_lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUNDLES = '/agent/repos/c136-data/bundles';
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const rmid = opt('replay', mid), lmid = opt('log', mid);
const win = +opt('win', 800), scan = +opt('scan', 300);
const OUT = path.resolve(HERE, '..', 'out', mid);

const iV = (a, b) => Math.trunc(a / b);
const { me, alias } = readLogSnaps(lmid);
const seatOf = (lb) => (me[lb] !== undefined ? me[lb] : (alias && alias[lb] !== undefined ? me[alias[lb]] : undefined));

// 日志行
const lines = [];
for (const raw of fs.readFileSync(`${BUNDLES}/${lmid}/in_game.log`, 'utf8').split('\n')) {
  const mm = raw.match(/\[([^\]]+)\] \[HL-(DONATE|DISPATCH)\] t=(\d+) (.*?) ?pct=(\d+)\/1024 -> \w+=(\d+)/);
  if (!mm) continue;
  const p = seatOf(mm[1]);
  if (p === undefined) continue;
  lines.push({ bot: mm[1], p, t: +mm[3], branch: mm[4].trim(), pct: +mm[5], q: +mm[6], land: null });
}

// 录像里的捐兵指令（配对）
const rc = fs.readFileSync(path.join(OUT, 'replay_cmds.csv'), 'utf8').split('\n').slice(1).filter(Boolean).map((l) => {
  const c = l.match(/^(\d+),(\d+),(\d+),(\w+),(\d+),"(.*?)",(-?\d+),(-?\d+),"(.*)"$/);
  return c ? { tick: +c[2], kind: c[4], player: +c[5], dX: +c[7], dZ: +c[8] } : null;
}).filter((r) => r && r.kind === 'donate');
const used = new Set();
for (const ln of lines.slice().sort((a, b) => a.t - b.t)) {
  let best = -1;
  for (let i = 0; i < rc.length; i++) {
    const r = rc[i];
    if (used.has(i) || r.player !== ln.p || r.dX !== ln.pct || r.dZ !== ln.q || r.tick < ln.t || r.tick > ln.t + win) continue;
    if (best < 0 || r.tick < rc[best].tick) best = i;
  }
  if (best >= 0) { used.add(best); ln.land = rc[best].tick; }
}

const m = openMatch(mid, { replay: rmid });
const { g, H, names } = m;
const uw = 1 + iV(g.land, 300);
const nm = (p) => (p < H ? `${names[p]}#${p}` : `AI#${p}`);

// 报价：返回 {v0, room, used, cap, cost, free, quote, why}
const quote = (p, q, pct) => {
  const o = { v0: 0, room: 0, used: g.donQuota[q], cap: g.donCap, cost: 0, free: 0, quote: 0, why: '' };
  if (!g.alive[p]) { o.why = '自己已死'; return o; }
  if (!g.canAct(p)) { o.why = '自己不能动'; return o; }
  if (q >= 512 || !g.alive[q]) { o.why = '对象已死'; return o; }
  if (!g.isTeammate(p, q)) { o.why = '不是队友'; return o; }
  const B = g.bal[p], fee = iV(64 * B, 1024);
  o.v0 = Math.min(iV(B * (pct + 1), 1024), B - fee);
  o.room = g.receiverRoom(q, o.v0);
  o.free = g.donationFree(q) ? 1 : 0;
  if (o.room < 1) { o.why = '容量'; return o; }
  o.cost = g.donationCost(q, o.room);
  if (!o.free && o.used + o.cost > o.cap) { o.why = '额度'; return o; }
  o.quote = o.room; o.why = 'ok';
  return o;
};

// 探针表：tick -> [{ln, kind}]
const probes = new Map();
const addProbe = (t, ln, kind) => { if (!probes.has(t)) probes.set(t, []); probes.get(t).push({ ln, kind }); };
for (const ln of lines) {
  ln.at = {}; ln.scanN = 0; ln.scanRef = 0; ln.scanWhy = {};
  if (ln.land === null) {
    for (const d of [7, 14, 21, 28]) addProbe(ln.t + d, ln, 'at' + d);
    for (let d = 7; d <= scan; d += 7) addProbe(ln.t + d, ln, 'scan');
  }
}
// 落地的：执行前取状态
const landKey = new Map();
for (const ln of lines) if (ln.land !== null) { const k = `${ln.land}|${ln.p}|${ln.q}|${ln.pct}`; if (!landKey.has(k)) landKey.set(k, []); landKey.get(k).push(ln); }
m.preCmd = (c) => {
  if (c.id !== 2) return;
  const arr = landKey.get(`${g.t}|${c.player}|${c.dZ}|${c.dX}`);
  if (!arr || !arr.length) return;
  const ln = arr.shift();
  ln.pre = quote(c.player, c.dZ, c.dX);
  ln.pre.state = c.dZ < H ? g.state[c.dZ] : 2;
  ln.pre.b0 = g.bal[c.player]; ln.pre.r0 = g.bal[c.dZ];
  ln._cmd = c;
};
m.onCmd = (c, r) => {
  if (c.id !== 2) return;
  for (const ln of lines) if (ln._cmd === c) { ln.post = { ok: r ? 1 : 0, paid: ln.pre.b0 - g.bal[c.player], recv: g.bal[c.dZ] - ln.pre.r0, usedAfter: g.donQuota[c.dZ] }; ln._cmd = null; }
};

// 额度表（纯引擎数学）：各时刻的 donCap、除数、一个额度没用过的真人一次最多能收多少
const ledgerTicks = [400, 700, 1000, 1070, 1100, 1500, 1800, 2100, 2141, 2200, 2700, 3200, 3212, 3300, 3900, 4283];
const ledger = [];
const seatQuota = []; // 本队席位各时刻的已用额度
const squadSeats = [...new Set(Object.values(me))].sort((a, b) => a - b);
const lastT = Math.max(...lines.map((l) => (l.land ?? l.t) + scan), 4300);
while (g.t <= lastT) {
  const ps = probes.get(g.t);
  if (ps) for (const { ln, kind } of ps) {
    const o = quote(ln.p, ln.q, ln.pct);
    if (kind === 'scan') { ln.scanN++; if (o.why !== 'ok') { ln.scanRef++; ln.scanWhy[o.why] = (ln.scanWhy[o.why] || 0) + 1; } }
    else ln.at[kind] = o;
  }
  if (ledgerTicks.includes(g.t)) {
    const t = g.t;
    const D = t >= 3213 ? null : (t < 357 ? 1 : t < 714 ? 4 : t < 1071 ? 10 : t < 2142 ? 30 : 100) * uw;
    const base = t >= 3213 ? 4 : 2;
    const maxFresh = D === null ? null : Math.max(0, Math.ceil((g.donCap - base + 1) * D / 100) - 1);
    ledger.push({ t, cap: g.donCap, div: D, maxFresh });
    for (const p of squadSeats) if (g.alive[p]) seatQuota.push({ t, p, used: g.donQuota[p], cap: g.donCap, state: g.state[p], terr: g.terr[p], bal: g.bal[p] });
  }
  if (!m.tick()) break;
}

// 输出
const csv = ['bot,p,t,branch,pct,q,qname,land,why7,why14,why21,why28,scanN,scanRefused,scanWhy,v0,room,used,cap,cost,free,qstate,paid,recv,usedAfter'];
for (const ln of lines) {
  const a = ln.land === null ? (ln.at.at7 || {}) : ln.pre || {};
  csv.push([ln.bot, ln.p, ln.t, ln.branch, ln.pct, ln.q, JSON.stringify(nm(ln.q)), ln.land ?? '',
    ln.at.at7?.why ?? '', ln.at.at14?.why ?? '', ln.at.at21?.why ?? '', ln.at.at28?.why ?? '', ln.scanN, ln.scanRef,
    JSON.stringify(Object.entries(ln.scanWhy).map(([k, v]) => `${k}:${v}`).join('|')),
    a.v0 ?? '', a.room ?? '', a.used ?? '', a.cap ?? '', a.cost ?? '', a.free ?? '', ln.pre?.state ?? '', ln.post?.paid ?? '', ln.post?.recv ?? '', ln.post?.usedAfter ?? ''].join(','));
}
fs.writeFileSync(path.join(OUT, 'donate_quota.csv'), csv.join('\n') + '\n');

const landed = lines.filter((l) => l.land !== null), miss = lines.filter((l) => l.land === null);
console.log(`== ${mid} 捐兵的引擎报价账（日志 ${lmid}，录像 ${rmid}）：地图陆地 ${g.land}，uw = ${uw}`);
console.log(`-- 表 1 额度上限（纯引擎数学）：拍 | donCap | 花费的除数 k·uw | 一个额度没用过的真人一次最多能收（兵）`);
for (const r of ledger) console.log(`   t=${String(r.t).padStart(4)} cap=${String(r.cap).padStart(3)} 除数=${r.div === null ? '100×对象领土' : r.div} 最多 ${r.maxFresh === null ? '(cap−4)×对象领土' : r.maxFresh}`);
console.log(`-- 表 2 日志捐兵行 ${lines.length} 条：落地 ${landed.length}，没落地 ${miss.length}`);
const cls = (ln) => {
  const w = [ln.at.at7?.why, ln.at.at14?.why, ln.at.at21?.why, ln.at.at28?.why];
  if (w.every((x) => x && x !== 'ok')) return '四个时点都被拒';
  if (w.some((x) => x && x !== 'ok')) return '部分时点被拒';
  return '四个时点都能收';
};
const byCls = {};
for (const ln of miss) { const k = cls(ln); (byCls[k] = byCls[k] || []).push(ln); }
for (const [k, arr] of Object.entries(byCls)) {
  const why = {};
  for (const ln of arr) for (const x of [ln.at.at7?.why, ln.at.at14?.why, ln.at.at21?.why, ln.at.at28?.why]) if (x && x !== 'ok') why[x] = (why[x] || 0) + 1;
  console.log(`   没落地 · ${k}：${arr.length} 条（时点上的原因计数 ${JSON.stringify(why)}）`);
}
for (const ln of miss) {
  const a = ln.at.at7 || {};
  console.log(`   没落地 ${ln.bot.padEnd(13)} t=${String(ln.t).padStart(4)} ${ln.branch.padEnd(20)} pct=${String(ln.pct).padStart(3)} → ${nm(ln.q).padEnd(18)} | t+7/14/21/28：${[7, 14, 21, 28].map((d) => ln.at['at' + d]?.why ?? '-').join(' / ')} | t+7 时 想捐 ${a.v0} 容量 ${a.room} 已用 ${a.used}/${a.cap} 这笔花费 ${a.cost} | 到 t+${scan} 共 ${ln.scanN} 个回合里被拒 ${ln.scanRef}（${Object.entries(ln.scanWhy).map(([k, v]) => `${k} ${v}`).join('、')}）`);
}
// 落地的：容量截断、额度用掉多少
let capCut = 0, capCutLost = 0, toFree = 0, quotaPaid = 0;
for (const ln of landed) {
  if (!ln.pre || !ln.post) continue;
  if (ln.pre.room < ln.pre.v0) { capCut++; capCutLost += ln.pre.v0 - ln.pre.room; }
  if (ln.pre.free) toFree++; else quotaPaid += ln.pre.cost;
}
console.log(`-- 表 3 落地的 ${landed.length} 条：对象免额度（离场壳 / 4284 拍以后）${toFree} 条；占额度的 ${landed.length - toFree} 条共花额度 ${quotaPaid} 点；被容量截断（到账 < 想捐）${capCut} 条，少到账 ${capCutLost} 兵`);
const tight = landed.filter((l) => l.pre && !l.pre.free).map((l) => ({ l, left: l.pre.cap - l.post.usedAfter })).sort((a, b) => a.left - b.left).slice(0, 8);
for (const { l, left } of tight) console.log(`   ${l.bot.padEnd(13)} t=${l.t} 落地 ${l.land} → ${nm(l.q).padEnd(18)} 到账 ${l.post.recv} 花费 ${l.pre.cost} 之后已用 ${l.post.usedAfter}/${l.pre.cap}（剩 ${left} 点）`);
console.log(`-- 表 4 本队席位的已用额度（拍：号=已用/上限；只列用过的）`);
for (const t of ledgerTicks) {
  const rows = seatQuota.filter((r) => r.t === t && r.used > 0);
  if (rows.length) console.log(`   t=${t} ` + rows.map((r) => `${names[r.p]}${r.state === 2 ? '(壳)' : ''}=${r.used}/${r.cap}`).join('  '));
}
fs.writeFileSync(path.join(OUT, 'donate_quota.json'), JSON.stringify({ mid, land: g.land, uw, lines: lines.length, landed: landed.length, missed: miss.length,
  missClass: Object.fromEntries(Object.entries(byCls).map(([k, v]) => [k, v.length])),
  missWhy7: miss.reduce((o, l) => { const w = l.at.at7?.why ?? '-'; o[w] = (o[w] || 0) + 1; return o; }, {}),
  landedFree: toFree, landedQuotaPts: quotaPaid, capCut, capCutLost, ledger }));
console.log(`# 已写 out/${mid}/donate_quota.csv、donate_quota.json`);
