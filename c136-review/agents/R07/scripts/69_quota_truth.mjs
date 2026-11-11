#!/usr/bin/env node
// 69_quota_truth.mjs — R07：防喂兵配额的引擎真账。
// 干净模拟器按录像重演，挂钩 bookDonation（配额记账的唯一入口）：
//   · 每一次记账：拍、受捐方、数额、扣的点数、记账前累计、当时全场上限、成功与否、来源（捐款指令 / 船靠队友岸）、谁给的；
//   · 对 in_game.log 里每一条 [HL-DISPATCH]：发令拍之后 6~19 拍（本局实测的指令延迟范围可用 --lag 改）逐拍用引擎自己的
//     donationCost / donQuota / donCap / receiverRoom 重算「这条指令如果在这一拍落地会不会被收下」，给出能过的拍数和拒绝原因。
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/69_quota_truth.mjs <matchId> [--lag 6,19]
// 输出：out/<matchId>/quota_truth.txt（人读）、quota_book.tsv（逐次记账）、quota_logs.tsv（逐条日志的判定）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid) { console.error('用法：69_quota_truth.mjs <matchId> [--lag 6,19]'); process.exit(2); }
const [LAG0, LAG1] = opt('--lag', '6,19').split(',').map(Number);
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
const nm = (q) => botOf.get(q) || (q < H ? `${(names[q] || '').trim().slice(0, 16)}#${q}` : `AI#${q}`);

// ---- 日志里的调度
const logs = [];
logText.forEach((ln, i) => {
  const m = /\[([A-Za-z0-9_]+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)\/1024 -> ally=(\d+)/.exec(ln);
  if (m && idOf.has(m[1])) {
    const dm = /dMe=(-?\d+) dAlly=(-?\d+)/.exec(ln), bx = /boxedIn=(true|false)/.exec(ln);
    logs.push({ line: i + 1, bot: m[1], t: +m[2], kind: m[3], pct: +m[4], to: +m[5], dMe: dm ? +dm[1] : null, dAlly: dm ? +dm[2] : null, boxed: bx ? bx[1] === 'true' : null, ticks: [] });
  }
});
const byTick = new Map(); // 落地候选拍 -> logs
for (const L of logs) for (let k = LAG0; k <= LAG1; k++) { const T = L.t + k; if (!byTick.has(T)) byTick.set(T, []); byTick.get(T).push(L); }

const proto = SIM.Game.prototype;
const book = [];
let ctx = null; // {kind, from}
const origBook = proto.bookDonation;
proto.bookDonation = function (q, v) {
  const g = this;
  const free = g.donationFree(q);
  const before = g.donQuota[q], cap = g.donCap;
  const cost = free ? 0 : g.donationCost(q, v);
  const ok = origBook.call(this, q, v);
  if (botOf.has(q) || (ctx && botOf.has(ctx.from))) book.push({ t: g.t, to: q, toName: nm(q), from: ctx ? ctx.from : -1, fromName: ctx ? nm(ctx.from) : '?', kind: ctx ? ctx.kind : '?', v, cost, before, cap, ok: ok ? 1 : 0, free: free ? 1 : 0 });
  return ok;
};
const origDonate = proto.donate;
proto.donate = function (pct, q, p) {
  const prev = ctx; ctx = { kind: '捐款指令', from: p === undefined ? this.me : p };
  // 指令被引擎拒绝而且原因不是配额（受捐方已满 / 已死 / 不是队友）时 bookDonation 不会被调用，这里补一条
  const g = this, n0 = book.length, b0 = g.bal[ctx.from];
  let r;
  try { r = origDonate.call(this, pct, q, p); } finally { ctx = prev; }
  if (!r && book.length === n0 && (botOf.has(q) || botOf.has(p))) {
    const B = b0, fee = iV(64 * B, 1024);
    const want = Math.min(iV(B * (pct + 1), 1024), B - fee);
    const why = q >= NEUTRAL || !g.alive[q] ? '受捐方已出局' : !g.isTeammate(p, q) ? '不是队友' : g.receiverRoom(q, want) < 1 ? '受捐方已顶到 150×领土' : '其他';
    book.push({ t: g.t, to: q, toName: nm(q), from: p, fromName: nm(p), kind: '捐款指令', v: want, cost: 0, before: g.donQuota[q] || 0, cap: g.donCap, ok: 0, free: 0, why });
  }
  return r;
};
const origLandAt = proto.landAt;
proto.landAt = function (p, troops, c, at) {
  const prev = ctx; ctx = { kind: '船靠队友岸', from: p };
  try { return origLandAt.call(this, p, troops, c, at); } finally { ctx = prev; }
};
const capSeries = [];
const origTick = proto.tick;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase) return;
  if (g.t % 100 === 0) {
    // 一个额度全空的受捐方单笔最多能收多少兵：用引擎自己的 donationCost 二分反解（t<3213 与受捐方无关；之后看受捐方的 100×领土）
    const maxV = (q) => { let lo = 0, hi = 2e9; while (lo < hi) { const mid2 = Math.floor((lo + hi + 1) / 2); if (g.donationCost(q, mid2) <= g.donCap) lo = mid2; else hi = mid2 - 1; } return lo; };
    const live = [...botOf.keys()].filter((q) => g.alive[q] && g.terr[q] > 0).sort((a, b) => g.terr[b] - g.terr[a]);
    capSeries.push([g.t, g.donCap, live.length ? maxV(live[0]) : 0, live.length ? maxV(live[live.length - 1]) : 0, live.length ? g.terr[live[0]] : 0, live.length ? g.terr[live[live.length - 1]] : 0]);
  }
  const ls = byTick.get(g.t);
  if (!ls) return;
  for (const L of ls) {
    const p = idOf.get(L.bot), q = L.to;
    if (!g.alive[p] || !g.alive[q]) { L.ticks.push({ T: g.t, ok: 0, why: '一方已出局' }); continue; }
    const B = g.bal[p], fee = iV(64 * B, 1024);
    let v = Math.min(iV(B * (L.pct + 1), 1024), B - fee);
    const room = g.receiverRoom(q, v);
    if (room < 1) { L.ticks.push({ T: g.t, ok: 0, why: '受捐方已顶到 150×领土', v }); continue; }
    v = room;
    if (g.donationFree(q)) { L.ticks.push({ T: g.t, ok: 1, why: '免检', v }); continue; }
    const cost = g.donationCost(q, v), used = g.donQuota[q], cap = g.donCap;
    L.ticks.push({ T: g.t, ok: used + cost <= cap ? 1 : 0, why: cost > cap ? '单笔需点 > 全场上限' : used + cost > cap ? '需点 > 剩余额度' : '能过', v, cost, used, cap });
  }
};
const res = await resim(mid, {});
const v = res.validate || {};

// ---- 日志 ↔ 真实记账配对：同捐方、同受捐方、落地拍在 t+LAG0..t+LAG1 内、成功的捐款指令，先到先配
const okBook = book.filter((b) => b.kind === '捐款指令' && b.ok);
// 指令按先后到达：一笔成功的记账对应「同捐方、同受捐方、发令拍最晚且不晚于落地前 5 拍」的那条日志（更早的日志是先落地、先被拒的）
for (const L of logs) L.exec = null;
let unpaired = 0;
for (const b of okBook) {
  if (!botOf.has(b.from)) continue;
  let best = null;
  for (const L of logs) {
    if (L.exec || idOf.get(L.bot) !== b.from || L.to !== b.to) continue;
    if (L.t > b.t - 5 || L.t < b.t - 45) continue;
    if (!best || L.t > best.t) best = L;
  }
  if (best) best.exec = b; else unpaired++;
}
for (const L of logs) {
  const okN = L.ticks.filter((x) => x.ok).length;
  L.okN = okN; L.n = L.ticks.length;
  const whys = new Map();
  for (const x of L.ticks) if (!x.ok) whys.set(x.why, (whys.get(x.why) || 0) + 1);
  L.why = [...whys].sort((a, b) => b[1] - a[1]).map(([k]) => k)[0] || '';
  L.cls = L.exec ? '已执行' : okN === 0 ? (L.why || '全窗口都过不了') : okN === L.n ? '整个窗口都能过却没执行' : '窗口里部分拍能过（卡在换档/额度边界）';
}
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const P = [];
P.push(`# ${mid} 防喂兵配额真账（干净模拟器重演，核对 ${v.bothExact}/${v.rows}；落地窗口取发令拍 +${LAG0}~+${LAG1}）`);
P.push(`A. 全场上限 donCap：${capSeries.filter((x, i) => i % 5 === 0 || i === capSeries.length - 1).map(([t, c]) => `${t}:${c}`).join(' ')}`);
P.push('A2. 一个额度全空的受捐方单笔最多能收多少兵（引擎 donationCost 反解；t<3213 与受捐方无关，之后按「我方领土最大的号 / 最小的号」各给一个）：');
P.push('    ' + capSeries.filter(([t]) => t < 4284 && (t % 300 === 0 || t === 1000 || t === 1100 || t === 2100 || t === 2200 || t === 3200 || t === 3300)).map(([t, c, a, b, ta, tb]) => t < 3213 ? `${t}: 上限 ${c} 点 → ${a.toLocaleString('en-US')} 兵` : `${t}: 上限 ${c} 点 → ${a.toLocaleString('en-US')}（${ta.toLocaleString('en-US')} 格的号）/ ${b.toLocaleString('en-US')}（${tb.toLocaleString('en-US')} 格的号）`).join('；'));
P.push('');
P.push(`B. 记账流水（受捐方或捐方是我方号）：${book.length} 次，其中成功 ${book.filter((b) => b.ok).length}、被拒 ${book.filter((b) => !b.ok).length}`);
{
  const by = new Map();
  for (const b of book) { const k = `${b.kind}${b.ok ? '·成功' : '·被拒'}${b.free ? '·免检' : ''}${b.why ? '·' + b.why : ''}`; if (!by.has(k)) by.set(k, { n: 0, v: 0, cost: 0, t0: b.t, t1: b.t }); const o = by.get(k); o.n++; o.v += b.v; o.cost += b.cost; o.t1 = b.t; }
  for (const [k, o] of by) P.push(`   ${k}：${o.n} 次，数额合计 ${fmt(o.v)}，点数合计 ${o.cost}（t=${o.t0}~${o.t1}）`);
  const rej = book.filter((b) => !b.ok);
  if (rej.length) { P.push('   被拒明细（最多 12 条）：'); for (const b of rej.slice(0, 12)) P.push(`     t=${b.t} ${b.fromName}→${b.toName} ${b.kind} 数额 ${fmt(b.v)} 需点 ${b.cost} 已用 ${b.before} 上限 ${b.cap}${b.why ? ' ' + b.why : ''}`); }
  const boats = book.filter((b) => b.kind === '船靠队友岸');
  if (boats.length) { P.push(`   船靠队友岸占用配额：${boats.length} 次`); for (const b of boats.slice(0, 12)) P.push(`     t=${b.t} ${b.fromName}→${b.toName} 数额 ${fmt(b.v)} 需点 ${b.cost} 已用 ${b.before} 上限 ${b.cap} ${b.ok ? '成功' : '被拒（兵没了）'}`); }
}
P.push('');
P.push('C. 每个受捐方（我方号）在有配额期（t<4284）的累计点数：成功记账的点数合计 / 最后一次记账时的全场上限');
{
  const by = new Map();
  for (const b of book) { if (b.free || !b.ok || !botOf.has(b.to)) continue; if (!by.has(b.toName)) by.set(b.toName, { n: 0, cost: 0, v: 0, cap: 0, mine: 0, other: 0 }); const o = by.get(b.toName); o.n++; o.cost += b.cost; o.v += b.v; o.cap = b.cap; if (botOf.has(b.from)) o.mine += b.cost; else o.other += b.cost; }
  for (const [k, o] of [...by].sort((a, b) => b[1].cost - a[1].cost)) P.push(`   ${k}：${o.n} 笔 ${fmt(o.v)} 兵，用掉 ${o.cost} 点（我方号给的 ${o.mine}，别的队友给的 ${o.other}）/ 上限 ${o.cap}`);
}
P.push('');
P.push(`D. [HL-DISPATCH] 日志 ${logs.length} 条逐条判定（我方成功记账 ${okBook.filter((b) => botOf.has(b.from)).length} 笔，没找到对应日志的 ${unpaired} 笔）`);
{
  const by = new Map();
  for (const L of logs) { if (!by.has(L.cls)) by.set(L.cls, []); by.get(L.cls).push(L); }
  for (const [k, ls] of [...by].sort((a, b) => b[1].length - a[1].length)) {
    const amt = ls.reduce((a, L) => a + (L.exec ? L.exec.v : (L.ticks[0]?.v || 0)), 0);
    P.push(`   ${k}：${ls.length} 条（t=${ls[0].t}~${ls[ls.length - 1].t}），数额合计 ${fmt(amt)}`);
  }
  const odd = logs.filter((L) => L.cls.startsWith('整个窗口') || L.cls.startsWith('窗口里部分'));
  if (odd.length) {
    P.push('   能过却没执行 / 部分拍能过 的明细（最多 30 条）：');
    for (const L of odd.slice(0, 30)) {
      const a = L.ticks[0] || {}, z = L.ticks[L.ticks.length - 1] || {};
      P.push(`     L${L.line} t=${L.t} ${L.bot}→${nm(L.to)} ${L.kind} pct=${L.pct}：窗口 ${L.n} 拍里 ${L.okN} 拍能过；首拍 需点 ${a.cost ?? '-'} 已用 ${a.used ?? '-'} 上限 ${a.cap ?? '-'}，末拍 需点 ${z.cost ?? '-'} 已用 ${z.used ?? '-'} 上限 ${z.cap ?? '-'}`);
    }
  }
}
// ---- 倒挂（捐方密度 < 收方密度）与围死号占比
{
  const inv = logs.filter((L) => L.dMe !== null && L.dMe < L.dAlly);
  const invEx = inv.filter((L) => L.exec);
  P.push('');
  P.push(`D2. 调度时捐方密度低于收方（日志里的 dMe < dAlly）：${inv.length}/${logs.length} 条，其中引擎执行 ${invEx.length} 条，到账 ${fmt(invEx.reduce((a, L) => a + L.exec.v, 0))}` + (invEx.length ? `；例：${invEx.slice(0, 5).map((L) => `L${L.line} t=${L.t} ${L.bot}(${L.dMe})→${nm(L.to)}(${L.dAlly}) ${fmt(L.exec.v)}`).join('；')}` : ''));
  const bx = logs.filter((L) => L.boxed === true);
  P.push(`    捐方 boxedIn=true 的日志 ${bx.length}/${logs.length} 条（执行 ${bx.filter((L) => L.exec).length} 条）；种类：${[...new Set(logs.map((L) => L.kind))].map((k) => `${k} ${logs.filter((L) => L.kind === k).length}（执行 ${logs.filter((L) => L.kind === k && L.exec).length}）`).join('、')}`);
  const ex = logs.filter((L) => L.exec);
  const q = (arr, f) => { const a = arr.map(f).sort((x, y) => x - y); return a.length ? `${a[0]}~${a[a.length - 1]}（中位 ${a[a.length >> 1]}）` : '-'; };
  P.push(`    执行的 ${ex.length} 条里：捐方密度 ${q(ex, (L) => L.dMe)}，收方密度 ${q(ex, (L) => L.dAlly)}`);
}
// ---- E. 「能过却没执行」的再核对：同一个捐方在窗口内有没有另一条捐款被收下（策略同一时间只有一条在途？）
P.push('');
P.push('E. 「整个窗口都能过却没执行」的日志：同一捐方在发令拍 ±20 拍内被引擎收下的其他指令（看是不是被别的指令顶掉）');
{
  const cmdsPath = path.join(OUT, 'cmds.tsv');
  let cmds = [];
  if (fs.existsSync(cmdsPath)) {
    const rows = fs.readFileSync(cmdsPath, 'utf8').trim().split('\n');
    const hdr = rows[0].split('\t');
    cmds = rows.slice(1).map((r) => Object.fromEntries(r.split('\t').map((x, i) => [hdr[i], x])));
  }
  for (const L of logs.filter((L) => L.cls.startsWith('整个窗口')).slice(0, 30)) {
    const p = idOf.get(L.bot);
    const near = cmds.filter((c) => +c.p === p && Math.abs(+c.tick - L.t) <= 20).map((c) => `${c.tick}:${c.kind}${c.kind === 'donate' ? '→' + nm(+c.b) : ''}`);
    P.push(`   L${L.line} t=${L.t} ${L.bot}→${nm(L.to)}：${near.length ? near.join(' ') : '附近没有任何被收下的指令'}`);
  }
}
const txt = P.join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'quota_truth.txt'), txt);
const bc = ['t', 'fromName', 'toName', 'kind', 'v', 'cost', 'before', 'cap', 'ok', 'free', 'why'];
fs.writeFileSync(path.join(OUT, 'quota_book.tsv'), bc.join('\t') + '\n' + book.map((b) => bc.map((c) => b[c] ?? '').join('\t')).join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'quota_logs.tsv'), 'line\tt\tbot\tto\tkind\tpct\tcls\tokN\tn\texecT\texecV\twhy\n' + logs.map((L) => [L.line, L.t, L.bot, nm(L.to), L.kind, L.pct, L.cls, L.okN, L.n, L.exec ? L.exec.t : '', L.exec ? L.exec.v : '', L.why].join('\t')).join('\n') + '\n');
process.stdout.write(txt.split('\n').slice(0, 60).join('\n') + '\n');
