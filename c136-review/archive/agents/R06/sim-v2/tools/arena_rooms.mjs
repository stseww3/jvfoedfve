#!/usr/bin/env node
// arena_rooms.mjs — 对手模型的出手强度按房间大小分开看（真人 ≤ 30 的小房间 / ≥ 60 的大房间 / 全部）：
// 每阶段 模型 / 同房间录像 的 每人每 100 拍生效指令数、其中打 AI 的、每 100 拍花掉余额的几成、其中花在 AI 身上的、
// 每条打 AI 指令的兵、人均余额。小房间里真人身边几乎全是 AI，大房间里是人挤人，两种处境下真人的打法差别很大。
// 用法：node sim-v2/tools/arena_rooms.mjs <arena 结果.json…> [--arm=baseline] [--to=1530]
import fs from 'node:fs';
import path from 'node:path';
import { SIMV2 } from '../lib/match.mjs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const to = +(args.find((a) => a.startsWith('--to=')) || '--to=99999').slice(5);
const P = JSON.parse(fs.readFileSync(path.join(SIMV2, 'calib', 'human-profile.json'), 'utf8')).phases;
const runs = files.map((f) => JSON.parse(fs.readFileSync(f, 'utf8'))).filter((r) => r.arms && r.arms[arm] && r.reality && r.reality.intensity);
const z = () => ({ c: 0, s: 0, a: 0, b: 0, ai: 0, aiS: 0 });
for (const [name, pick] of [['小房间（真人 ≤ 30）', (r) => r.room.humans <= 30], ['大房间（真人 ≥ 60）', (r) => r.room.humans >= 60], ['全部', () => true]]) {
  const T = P.map(() => ({ m: z(), r: z() }));
  let n = 0;
  for (const r of runs) {
    if (!pick(r)) continue;
    n++;
    const mi = r.arms[arm].crowd.intensity, ri = r.reality.intensity;
    P.forEach((p, i) => {
      for (const [X, I] of [[T[i].m, mi[i]], [T[i].r, ri[i]]]) {
        if (!I || !I.ratePerAlive100 || !I.spendPer100) continue;
        const alive = I.cmds / (I.ratePerAlive100 / 100), bal = I.sent / (I.spendPer100 / 100);
        X.c += I.cmds; X.s += I.sent; X.a += alive; X.b += bal; X.ai += I.okRateBy.ai * alive / 100; X.aiS += I.sentBy.ai;
      }
    });
  }
  console.log(`${name}：${n} 局。每格 = 模型 / 同房间录像`);
  console.log('阶段\t每人每 100 拍指令\t其中打 AI\t每 100 拍花掉余额\t其中花在 AI 上\t每条打 AI 的兵\t人均余额');
  P.forEach((p, i) => {
    const m = T[i].m, r = T[i].r;
    if (!m.a || !r.a || p.t0 >= to) return;
    const f = (x, d = 2) => x.toFixed(d), pc = (x) => (100 * x).toFixed(0) + '%';
    console.log(`${p.phase}\t${f(100 * m.c / m.a)} / ${f(100 * r.c / r.a)}\t${f(100 * m.ai / m.a)} / ${f(100 * r.ai / r.a)}\t${pc(100 * m.s / m.b)} / ${pc(100 * r.s / r.b)}\t${pc(100 * m.aiS / m.b)} / ${pc(100 * r.aiS / r.b)}\t${Math.round(m.aiS / Math.max(1, m.ai))} / ${Math.round(r.aiS / Math.max(1, r.ai))}\t${Math.round(m.b / m.a)} / ${Math.round(r.b / r.a)}`);
  });
}
