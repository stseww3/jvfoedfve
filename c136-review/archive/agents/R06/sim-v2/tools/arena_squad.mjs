#!/usr/bin/env node
// arena_squad.mjs — 验收的另一半：模型里「我方」自己的走势对着同一局录像（人均地、兵密度、在场席位、陆攻的条数与出兵），
// 以及其余真人兵密度的分布（P10 / P25 / 中位 / P75 / P90）。对手模型再像，如果我方这一侧比录像强，「我方 ÷ 其余真人」照样偏高。
// 用法：node sim-v2/tools/arena_squad.mjs <结果.json…> [--arm=baseline] [--rooms]
import fs from 'node:fs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const rooms = args.includes('--rooms');
const CPS = [357, 630, 1071, 1530, 2142, 3210, 4284];
const med = (a) => { const s = a.filter((x) => Number.isFinite(x)).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : NaN; };
const f2 = (x) => (Number.isFinite(x) ? x.toFixed(2) : '-');
const agg = {}, dq = {}, seg = {};
for (const f of files) {
  const r = JSON.parse(fs.readFileSync(f, 'utf8'));
  const m = r.arms[arm];
  if (!m || !r.reality || !r.reality.cps) continue;
  let line = `${r.room.match}（真人 ${r.room.humans}，我方 ${r.room.squad.length}，停摆 ${Object.keys(r.room.squadHusks || {}).length}）`;
  for (const t of CPS) {
    const a = m.cps[t], b = r.reality.cps[t];
    if (!a || !b) continue;
    const A = (agg[t] ||= { land: [], dens: [], troops: [], alive: [], oLand: [], oDens: [], rel: [], ai: [] });
    A.land.push(a.squadPerSeat / b.squadPerSeat); A.dens.push(a.squadDensity / b.squadDensity);
    A.troops.push(a.squadPerSeat * a.squadDensity / (b.squadPerSeat * b.squadDensity)); A.alive.push(a.squadAlive - b.squadAlive);
    A.oLand.push(a.othersPerSeat / b.othersPerSeat); A.oDens.push(a.othersDensity / b.othersDensity); A.rel.push(a.relOthers / b.relOthers); A.ai.push(a.aiShare - b.aiShare);
    if (a.othersDQ && b.othersDQ) { const D = (dq[t] ||= { m: [[], [], [], [], []], r: [[], [], [], [], []] }); for (let i = 0; i < 5; i++) { D.m[i].push(a.othersDQ[i]); D.r[i].push(b.othersDQ[i]); } }
    line += ` | ${t}: 地 ${f2(a.squadPerSeat / b.squadPerSeat)} 密 ${f2(a.squadDensity / b.squadDensity)} 在场 ${a.squadAlive}/${b.squadAlive} 其余地 ${f2(a.othersPerSeat / b.othersPerSeat)}`;
  }
  if (rooms) console.log(line);
  const ms = m.atkSeg, rs = r.reality.squadAtkSeg;
  if (ms && rs) for (let i = 0; i < ms.length; i++) {
    const S = (seg[ms[i].t0] ||= { m: { neutral: 0, ai: 0, hum: 0, neutralSent: 0, aiSent: 0, humSent: 0 }, r: { neutral: 0, ai: 0, hum: 0, neutralSent: 0, aiSent: 0, humSent: 0 } });
    for (const k of Object.keys(S.m)) { S.m[k] += ms[i][k]; S.r[k] += rs[i][k]; }
  }
}
console.log('我方这一侧，模型 ÷ 同一局录像（各局中位数；在场是 模型 − 录像 的差）：');
console.log('断面\t局数\t我方人均地\t我方兵密度\t我方总兵\t我方在场差\t其余真人人均地\t其余真人兵密度\t我方÷其余\tAI 占陆地差');
for (const t of CPS) {
  const A = agg[t];
  if (!A) continue;
  console.log(`${t}\t${A.land.length}\t${f2(med(A.land))}\t${f2(med(A.dens))}\t${f2(med(A.troops))}\t${f2(med(A.alive))}\t${f2(med(A.oLand))}\t${f2(med(A.oDens))}\t${f2(med(A.rel))}\t${f2(med(A.ai))}`);
}
console.log('其余在场真人的兵密度分布（各局的 P10 / P25 / 中位 / P75 / P90，再取各局中位数）：模型 ｜ 录像');
for (const t of CPS) {
  const D = dq[t];
  if (!D) continue;
  console.log(`${t}\t${D.m.map((a) => med(a).toFixed(1)).join(' / ')} ｜ ${D.r.map((a) => med(a).toFixed(1)).join(' / ')}`);
}
console.log('我方生效的陆攻（各局合计）：时段起点 ｜ 无主地 条数 模型/录像 · 出兵（千）模型/录像 ｜ 内置 AI ｜ 真人席位');
const k3 = (x) => Math.round(x / 1000);
for (const t0 of Object.keys(seg).map(Number).sort((a, b) => a - b)) {
  const S = seg[t0];
  console.log(`${t0}\t${S.m.neutral}/${S.r.neutral} · ${k3(S.m.neutralSent)}/${k3(S.r.neutralSent)} ｜ ${S.m.ai}/${S.r.ai} · ${k3(S.m.aiSent)}/${k3(S.r.aiSent)} ｜ ${S.m.hum}/${S.r.hum} · ${k3(S.m.humSent)}/${k3(S.r.humSent)}`);
}
