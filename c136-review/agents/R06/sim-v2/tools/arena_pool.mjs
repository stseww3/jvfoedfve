#!/usr/bin/env node
// arena_pool.mjs — 对手模型的出手强度，各局相加（按人·拍加权，不是各局中位数）：
// 每阶段 模型 / 同房间录像 的 每人每 100 拍生效指令（无主地 · AI · 真人 · 船）、每 100 拍花掉余额的百分之几（分四类 + 合计）、
// 每条指令的兵 ÷ 人均余额（分三类陆攻）、人均余额之比。
// 人均余额之比一路往下掉 = 模型里的其余真人把兵花得比真人多（或者赚得少），后面就挡不住我方。
// 用法：node sim-v2/tools/arena_pool.mjs <arena 结果.json…> [--arm=baseline] [--small | --big]
import fs from 'node:fs';
import path from 'node:path';
import { SIMV2 } from '../lib/match.mjs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const small = args.includes('--small'), big = args.includes('--big');
const P = JSON.parse(fs.readFileSync(path.join(SIMV2, 'calib', 'human-profile.json'), 'utf8')).phases;
const K = ['neutral', 'ai', 'hum', 'boat'];
const z = () => ({ alive: 0, bal: 0, c: [0, 0, 0, 0], s: [0, 0, 0, 0] });
const agg = P.map(() => ({ m: z(), r: z() }));
let n = 0;
for (const f of files) {
  const r = JSON.parse(fs.readFileSync(f, 'utf8'));
  if (!r.arms || !r.arms[arm] || !r.reality || !r.reality.intensity) continue;
  if (small && r.room.humans > 30) continue;
  if (big && r.room.humans < 60) continue;
  n++;
  P.forEach((p, i) => {
    for (const [X, I] of [[agg[i].m, r.arms[arm].crowd.intensity[i]], [agg[i].r, r.reality.intensity[i]]]) {
      if (!I || !I.ratePerAlive100 || !I.spendPer100) continue;
      const alive = I.cmds / (I.ratePerAlive100 / 100), bal = I.sent / (I.spendPer100 / 100);
      X.alive += alive; X.bal += bal;
      K.forEach((k, j) => { X.c[j] += I.okRateBy[k] * alive / 100; X.s[j] += I.sentBy[k]; });
    }
  });
}
console.log(`${n} 局相加（按人·拍加权）${small ? '，只看真人 ≤ 30 的小房间' : big ? '，只看真人 ≥ 60 的大房间' : ''}。每格 = 模型 / 同房间录像`);
console.log('阶段\t每人每 100 拍指令：无主地 · AI · 真人 · 船\t每 100 拍花掉余额（%）：无主地 · AI · 真人 · 船 · 合计\t每条的兵 ÷ 人均余额（%）：无主地 · AI · 真人\t人均余额 模型 ÷ 录像');
P.forEach((p, i) => {
  const m = agg[i].m, r = agg[i].r;
  if (!m.alive || !r.alive) return;
  const rate = K.map((k, j) => `${(100 * m.c[j] / m.alive).toFixed(2)}/${(100 * r.c[j] / r.alive).toFixed(2)}`).join(' · ');
  const sp = (X, j) => (1e4 * X.s[j] / X.bal).toFixed(1);
  const spend = K.map((k, j) => `${sp(m, j)}/${sp(r, j)}`).join(' · ');
  const tot = (X) => (1e4 * X.s.reduce((a, b) => a + b, 0) / X.bal).toFixed(1);
  const per = (X, j) => (X.c[j] > 0 ? (100 * (X.s[j] / X.c[j]) / (X.bal / X.alive)).toFixed(1) : '-');
  const perCmd = [0, 1, 2].map((j) => `${per(m, j)}/${per(r, j)}`).join(' · ');
  console.log(`${p.phase}\t${rate}\t${spend} · ${tot(m)}/${tot(r)}\t${perCmd}\t${(m.bal / m.alive / (r.bal / r.alive)).toFixed(2)}`);
});
