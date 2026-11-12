#!/usr/bin/env node
// arena_people.mjs — 对手模型的「人与人之间」验收表（多局取中位；模型 = arena 结果里 Crowd 的账，对照 = human-profile.json 的实测 / 同房间录像）：
//   1. 到各时刻为止每人下过几条有兵的陆攻指令（一条没下的占比、P10/P25/中位/P75/P90、均值）
//   2. 出手节奏：相邻两条指令的间隔 ÷ 本人平均间隔 的分位、个人变异系数
//   3. 出手时的余额 ÷ 本人本阶段的平均余额
//   4. 其余在场真人的地在人与人之间的分布（各分位 ÷ 同房间录像的中位数）
// 用法：node sim-v2/tools/arena_people.mjs <arena 结果.json …> [--arm=baseline]
import fs from 'node:fs';
import path from 'node:path';
import { SIMV2 } from '../lib/match.mjs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const armName = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const prof = JSON.parse(fs.readFileSync(path.join(SIMV2, 'calib', 'human-profile.json'), 'utf8'));
const runs = files.map((f) => JSON.parse(fs.readFileSync(f, 'utf8'))).filter((r) => r.arms && r.arms[armName] && r.arms[armName].crowd);
if (!runs.length) { console.error('没有可用的 arena 结果'); process.exit(1); }
const med = (a) => { const s = a.filter((x) => x !== null && x !== undefined && Number.isFinite(x)).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
const f2 = (x) => (x === null || x === undefined ? '-' : (+x).toFixed(2));

console.log(`对手模型：人与人之间的分布（${runs.length} 局的中位）`);
console.log('1. 到各时刻为止每人下过的有兵陆攻指令数：一条没下 | P10/P25/中位/P75/P90 | 均值');
for (const T of Object.keys(prof.cmdCount || {})) {
  const R = prof.cmdCount[T];
  const rows = runs.map((r) => r.arms[armName].crowd.cmdCount && r.arms[armName].crowd.cmdCount[T]).filter(Boolean);
  if (!rows.length) continue;
  console.log(`  到 ${T} 拍\t模型 ${Math.round(100 * med(rows.map((x) => x.zero)))}% | ${[0, 1, 2, 3, 4].map((i) => med(rows.map((x) => x.q[i]))).join('/')} | ${f2(med(rows.map((x) => x.mean)))}\t实测 ${Math.round(100 * R.zero)}% | ${R.q.join('/')} | ${f2(R.mean)}`);
}
// 实测的节奏（tools/human_profile.mjs 的缓存里算的，20 局）：间隔 ÷ 本人平均间隔 的 P10/P25/中位/P75/P90、个人变异系数的中位
const RHYTHM_REAL = { '0~357': [[0.31, 0.52, 0.88, 1.16, 1.81], 0.48], '357~850': [[0.26, 0.49, 0.83, 1.29, 1.96], 0.61], '850~1530': [[0.23, 0.43, 0.76, 1.24, 1.93], 0.67] };
console.log('2. 出手节奏：间隔 ÷ 本人平均间隔 的 P10/P25/中位/P75/P90 | 个人变异系数的中位（「随时都可能点」是 0.11/0.29/0.69/1.39/2.30 | 约 0.8）');
for (const [k, [gq, cv]] of Object.entries(RHYTHM_REAL)) {
  const rows = runs.map((r) => r.arms[armName].crowd.rhythm && r.arms[armName].crowd.rhythm[k]).filter(Boolean);
  if (!rows.length) continue;
  console.log(`  ${k}\t模型 ${[0, 1, 2, 3, 4].map((i) => f2(med(rows.map((x) => x.gapQ[i])))).join('/')} | ${f2(med(rows.map((x) => x.cv[1])))}\t实测 ${gq.map(f2).join('/')} | ${f2(cv)}`);
}
// 实测：出手时余额 ÷ 本人本阶段平均余额（合计比；括号里按出兵比例加权），细阶段顺序
const CLICK_REAL = [[1.338, 1.601], [1.214, 1.368], [1.173, 1.267], [1.209, 1.311], [1.187, 1.287], [1.129, 1.137], [1.041, 1.089], [1.022, 1.088], [1.017, 1.074], [0.913, 0.808]];
console.log('3. 出手时的余额 ÷ 本人本阶段的平均余额（括号里按出兵比例加权）');
for (let i = 0; i < Math.min(CLICK_REAL.length, prof.phases.length); i++) {
  const rows = runs.map((r) => r.arms[armName].crowd.intensity[i]).filter((x) => x && x.clickBal);
  if (!rows.length) continue;
  console.log(`  ${prof.phases[i].phase}\t模型 ${f2(med(rows.map((x) => x.clickBal)))}（${f2(med(rows.map((x) => x.clickBalW)))}）\t实测 ${f2(CLICK_REAL[i][0])}（${f2(CLICK_REAL[i][1])}）`);
}
console.log('4. 其余在场真人的地：P10/P25/中位/P75/P90/最大 ÷ 同房间录像的中位数');
for (const t of [357, 630, 1071, 1530, 2142, 3210, 4284]) {
  const M = [[], [], [], [], [], []], R = [[], [], [], [], [], []];
  for (const r of runs) {
    const m = r.arms[armName].cps[t], x = r.reality && r.reality.cps[t];
    if (!m || !x || !m.othersQ || !x.othersQ || !(x.othersQ[2] > 0)) continue;
    for (let i = 0; i < 6; i++) { M[i].push(m.othersQ[i] / x.othersQ[2]); R[i].push(x.othersQ[i] / x.othersQ[2]); }
  }
  if (!M[0].length) continue;
  console.log(`  t=${t}（${M[0].length} 局）\t模型 ${M.map((a) => f2(med(a))).join('/')}\t录像 ${R.map((a) => f2(med(a))).join('/')}`);
}
