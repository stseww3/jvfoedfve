#!/usr/bin/env node
// arena_flow.mjs — 地的流向：相邻两个断面之间，每个陆地格的归属从哪一类到了哪一类（无主地 / 内置 AI / 其余真人 / 我方）。
// 模型和同一局录像各一张 4×4 表；这里把各局加起来（也可以 --rooms 逐局列），单位：占全图陆地的千分之几。
// 用法：node sim-v2/tools/arena_flow.mjs <arena 结果.json…> [--arm=baseline] [--rooms] [--small | --big]（只看真人 ≤ 30 / ≥ 60 的房间）
import fs from 'node:fs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const rooms = args.includes('--rooms'), small = args.includes('--small'), big = args.includes('--big');
const NAMES = ['无主地', '内置AI', '其余真人', '我方'];
const sum = {};
let n = 0;
for (const f of files) {
  const r = JSON.parse(fs.readFileSync(f, 'utf8'));
  const m = r.arms[arm];
  if (!m || !m.flows || !r.reality || !r.reality.flows) continue;
  if (small && r.room.humans > 30) continue;
  if (big && r.room.humans < 60) continue;
  n++;
  for (const k of Object.keys(m.flows)) {
    const a = m.flows[k], b = r.reality.flows[k];
    if (!a || !b) continue;
    const S = (sum[k] ||= { m: [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], r: [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], rooms: 0 });
    S.rooms++;
    // 每局按自己的陆地总数折成千分比再相加（大图小图权重一样）
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { S.m[i][j] += 1000 * a[i][j] / r.room.land; S.r[i][j] += 1000 * b[i][j] / r.room.land; }
    if (rooms) {
      const g = (F, i, j) => (1000 * F[i][j] / r.room.land).toFixed(0);
      console.log(`${r.room.match}（真人 ${r.room.humans}）${k}：其余真人 ← 无主地 ${g(a, 0, 2)}/${g(b, 0, 2)}，← AI ${g(a, 1, 2)}/${g(b, 1, 2)}，→ AI ${g(a, 2, 1)}/${g(b, 2, 1)}，← 我方 ${g(a, 3, 2)}/${g(b, 3, 2)}，→ 我方 ${g(a, 2, 3)}/${g(b, 2, 3)}；我方 ← 无主地 ${g(a, 0, 3)}/${g(b, 0, 3)}，← AI ${g(a, 1, 3)}/${g(b, 1, 3)}，→ AI ${g(a, 3, 1)}/${g(b, 3, 1)}；AI ← 无主地 ${g(a, 0, 1)}/${g(b, 0, 1)}`);
    }
  }
}
console.log(`地的流向（${n} 局的平均；单位：全图陆地的千分之几；每格 = 模型 / 录像）`);
for (const k of Object.keys(sum)) {
  const S = sum[k];
  console.log(`\n${k}（${S.rooms} 局）\t到→ ${NAMES.join('\t')}`);
  for (let i = 0; i < 4; i++) console.log(`从 ${NAMES[i]}\t${[0, 1, 2, 3].map((j) => `${(S.m[i][j] / S.rooms).toFixed(1)} / ${(S.r[i][j] / S.rooms).toFixed(1)}`).join('\t')}`);
  const net = (F, x) => { let v = 0; for (let i = 0; i < 4; i++) if (i !== x) v += F[i][x] - F[x][i]; return (v / S.rooms).toFixed(1); };
  console.log(`净增：${NAMES.map((nm, x) => `${nm} ${net(S.m, x)} / ${net(S.r, x)}`).join('；')}`);
}
