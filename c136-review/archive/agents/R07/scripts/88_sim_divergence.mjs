#!/usr/bin/env node
// 88_sim_divergence.mjs — R07：干净模拟器（resim）和真引擎重放（60_truth.cjs）在哪一拍、从谁开始对不上。
//
// 背景：67 / 74 / 69 / 65 / 68 等脚本的逐条扣款、影子决策都跑在统筹的干净模拟器上；60_truth.cjs 跑的是线上客户端原样引擎。
// 多数局两者逐快照一致；个别局（如 A053）干净模拟器只对上一部分快照。本脚本给出分叉的起点和大小，
// 用来判断哪些时间窗里干净模拟器上的数字还能用。
//
// 用法（必须套重计算闸；需要先跑过 60_truth.cjs）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/88_sim_divergence.mjs <matchId>
// 输出：out/<matchId>/sim_divergence.txt（设 R07_NO_LANDFIX=1 时不启用船落点修正，写到 sim_divergence_nofix.txt）
//   A. 干净模拟器 vs traj.csv（我方号的日志快照）：一致行数、第一处不一致、每个号第一处不一致
//   B. 干净模拟器 vs 真引擎（全部真人，每 90 拍）：每个采样拍有多少真人的领土 / 余额不一致，最早不一致的是谁
//   C. 各队领土合计：真引擎 vs 干净模拟器（每 450 拍）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const mid = process.argv[2];
if (!mid) { console.error('用法：88_sim_divergence.mjs <matchId>'); process.exit(2); }
const OUT = path.join(HERE, '..', 'out', mid);
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
const FIX = await import(path.join(HERE, 'r07simfix.mjs'));
const fixed = FIX.applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));

const r = resim(mid, {});
const H = r.H;
const names = r.names;
const teams = r.teams;
const nm = (p) => `${String(names[p] || '').trim().slice(0, 18)}#${p}[T${teams[p]}]`;
const fmt = (n) => Number(n).toLocaleString('en-US');
const lines = [];
const P = (s) => lines.push(s);

P(`# ${mid} 干净模拟器（resim）与真引擎重放的分叉检查；真人 ${H} 个；干净模拟器重演到第 ${r.endTick} 拍；船落点修正（r07simfix.mjs）：${fixed ? '已启用' : '未启用（R07_NO_LANDFIX=1）'}`);
P(`# 船落在没人占的水 / 边界 / 山格：${FIX.oddLandings.length} 次` + (FIX.oddLandings.length ? '；' + FIX.oddLandings.slice(0, 40).map((o) => `t=${o.t} ${nm(o.p)} ${fmt(o.troops)} 兵→#${o.target}`).join('；') : ''));
const v = r.validate;
P('');
P('A. 干净模拟器 vs traj.csv（我方号每 90 拍的日志快照）');
P(`   ${v.rows} 行：领土一致 ${v.terrExact}，余额一致 ${v.balExact}，都一致 ${v.bothExact}`);
if (v.mism.length) {
  const first = v.mism[0];
  P(`   第一处不一致：t=${first[0]} ${first[1]} 领土 日志 ${fmt(first[2])} / 模拟 ${fmt(first[3])}，余额 日志 ${fmt(first[4])} / 模拟 ${fmt(first[5])}`);
  const perBot = new Map();
  for (const m of v.mism) if (!perBot.has(m[1])) perBot.set(m[1], m);
  P('   每个号第一处不一致：');
  for (const [b, m] of [...perBot].sort((a, b2) => a[1][0] - b2[1][0])) P(`     ${b}: t=${m[0]} 领土 ${fmt(m[2])} / ${fmt(m[3])}，余额 ${fmt(m[4])} / ${fmt(m[5])}`);
  const byT = new Map();
  for (const m of v.mism) byT.set(m[0], (byT.get(m[0]) || 0) + 1);
  P('   不一致的行数（按拍）：' + [...byT].map(([t, n]) => `${t}:${n}`).join(' '));
} else P('   全部一致。');

// truth_all.tsv: t p terr bal alive state
const truth = new Map();
const tp = path.join(OUT, 'truth_all.tsv');
if (!fs.existsSync(tp)) { console.error('缺 truth_all.tsv，先跑 60_truth.cjs'); process.exit(2); }
for (const ln of fs.readFileSync(tp, 'utf8').split('\n').slice(1)) {
  if (!ln) continue;
  const c = ln.split('\t');
  const t = +c[0], p = +c[1];
  if (p >= H) continue;
  if (!truth.has(t)) truth.set(t, new Map());
  truth.get(t).set(p, [+c[2], +c[3]]);
}
const idxOf = new Map(r.snapT.map((t, i) => [t, i]));
P('');
P('B. 干净模拟器 vs 真引擎（全部真人；truth_all.tsv 每 90 拍采样，只含真引擎里领土 >0 的玩家）');
P('t\t真引擎在场真人\t领土不一致\t余额不一致\t领土差绝对值合计\t余额差绝对值合计\t差得最多的三个（领土 真/模拟）');
let firstBad = null;
const teamRows = [];
for (const t of [...truth.keys()].sort((a, b) => a - b)) {
  const i = idxOf.get(t);
  if (i === undefined) continue;
  const tm = truth.get(t);
  let nT = 0, nB = 0, dT = 0, dB = 0;
  const worst = [];
  const seen = new Set();
  for (const [p, [te, ba]] of tm) {
    seen.add(p);
    const st = r.snapTerr[i][p], sb = r.snapBal[i][p];
    if (st !== te) { nT++; dT += Math.abs(st - te); worst.push([Math.abs(st - te), p, te, st]); }
    if (sb !== ba) { nB++; dB += Math.abs(sb - ba); }
  }
  for (let p = 0; p < H; p++) if (!seen.has(p) && r.snapTerr[i][p] > 0) { nT++; dT += r.snapTerr[i][p]; worst.push([r.snapTerr[i][p], p, 0, r.snapTerr[i][p]]); }
  worst.sort((a, b) => b[0] - a[0]);
  if ((nT || nB) && !firstBad) firstBad = { t, who: worst.slice(0, 5) };
  P(`${t}\t${tm.size}\t${nT}\t${nB}\t${fmt(dT)}\t${fmt(dB)}\t${worst.slice(0, 3).map((w) => `${nm(w[1])} ${fmt(w[2])}/${fmt(w[3])}`).join('；')}`);
  if (t % 450 === 0) {
    const a = new Map(), b = new Map();
    for (const [p, [te]] of tm) a.set(teams[p], (a.get(teams[p]) || 0) + te);
    for (let p = 0; p < H; p++) b.set(teams[p], (b.get(teams[p]) || 0) + r.snapTerr[i][p]);
    teamRows.push([t, [...new Set([...a.keys(), ...b.keys()])].sort((x, y) => x - y).map((k) => `T${k} ${fmt(a.get(k) || 0)}/${fmt(b.get(k) || 0)}`).join('  ')]);
  }
}
P('');
P(firstBad ? `   最早出现不一致的采样拍：t=${firstBad.t}（此前的采样拍全部真人逐个一致）` : '   全部采样拍、全部真人逐个一致。');
P('');
P('C. 各队真人领土合计：真引擎 / 干净模拟器（每 450 拍）');
for (const [t, s] of teamRows) P(`   t=${t}: ${s}`);

fs.writeFileSync(path.join(OUT, fixed ? 'sim_divergence.txt' : 'sim_divergence_nofix.txt'), lines.join('\n') + '\n');
console.log(lines.slice(0, 40).join('\n'));
console.log(`wrote ${path.join(OUT, fixed ? 'sim_divergence.txt' : 'sim_divergence_nofix.txt')}`);
