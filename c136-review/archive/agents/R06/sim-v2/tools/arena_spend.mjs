#!/usr/bin/env node
// arena_spend.mjs — 对手模型的「出手强度」验收表：各阶段、各类对象（无主地 / AI / 真人 / 船）
// 每个在场真人每 100 拍的生效指令数、每 100 拍花掉余额的几成、出手的兵（绝对数）。
// 模型 = arena 结果里 Crowd 的账；对照 = 同一批房间当年录像里其余真人的账（arena 的参照重放顺手记的），
// 外加 20 局实测的总平均（human-profile.json）。每格三个数：模型 / 同房间录像 / 20 局平均；多局取中位。
//
// 用法：node sim-v2/tools/arena_spend.mjs <arena 结果.json …> [--arm=baseline] [--rooms]（--rooms：逐房间列出打 AI 的兵和 AI 占地）
import fs from 'node:fs';
import path from 'node:path';
import { SIMV2 } from '../lib/match.mjs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const armName = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const prof = JSON.parse(fs.readFileSync(path.join(SIMV2, 'calib', 'human-profile.json'), 'utf8'));
const K = ['neutral', 'ai', 'hum', 'boat'];
const med = (a) => { const s = a.filter((x) => x !== null && x !== undefined && Number.isFinite(x)).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
const runs = files.map((f) => JSON.parse(fs.readFileSync(f, 'utf8'))).filter((r) => r.arms && r.arms[armName] && r.arms[armName].crowd);
if (!runs.length) { console.error('没有可用的 arena 结果'); process.exit(1); }
const f2 = (x) => (x === null ? '-' : x.toFixed(2)), pc = (x) => (x === null ? '-' : Math.round(100 * x) + '%');
console.log(`对手模型出手强度：${runs.length} 局的中位；每格 = 模型 / 同房间录像 / ${prof.matches.length} 局平均`);
console.log('阶段\t生效指令（每人每 100 拍）：无主地 · AI · 真人 · 船\t每 100 拍花掉余额：无主地 · AI · 真人 · 船 · 合计');
for (let i = 0; i < prof.phases.length; i++) {
  const P = prof.phases[i];
  const rows = runs.map((r) => r.arms[armName].crowd.intensity[i]).filter((x) => x && x.cmds > 0);
  const real = runs.map((r) => r.reality && r.reality.intensity && r.reality.intensity[i]).filter((x) => x && x.cmds > 0);
  if (!rows.length) continue;
  const rate = K.map((k) => `${f2(med(rows.map((x) => x.okRateBy[k])))}/${f2(med(real.map((x) => x.okRateBy[k])))}/${f2(P.okRateBy[k] ?? 0)}`).join(' · ');
  const sp = K.map((k) => `${pc(med(rows.map((x) => x.spendBy[k])))}/${pc(med(real.map((x) => x.spendBy[k])))}/${pc(P.spendBy[k] ?? 0)}`).join(' · ');
  console.log(`${P.phase}\t${rate}\t${sp} · ${pc(med(rows.map((x) => x.spendPer100)))}/${pc(med(real.map((x) => x.spendPer100)))}/${pc(P.spendPer100)}`);
}
if (args.includes('--rooms')) {
  console.log('逐房间（模型 / 录像）：各阶段其余真人打 AI 出手的兵（千）；630、1071、1530 拍内置 AI 占陆地');
  for (const r of runs) {
    const m = r.arms[armName], R = r.reality;
    if (!R || !R.intensity) continue;
    const cells = [];
    for (let i = 0; i < prof.phases.length; i++) {
      const a = m.crowd.intensity[i], b = R.intensity[i];
      if (!a || !b || (!a.cmds && !b.cmds) || prof.phases[i].t0 < 490 || prof.phases[i].t0 >= 1530) continue;
      cells.push(`${prof.phases[i].t0}: ${Math.round(a.sentBy.ai / 1000)}/${Math.round(b.sentBy.ai / 1000)}`);
    }
    const ai = [630, 1071, 1530].map((t) => (m.cps[t] && R.cps[t] ? `${t}: ${m.cps[t].aiShare.toFixed(2)}/${R.cps[t].aiShare.toFixed(2)}` : '')).join('  ');
    console.log(`  ${r.room.mid || r.room.name || '?'}\t${cells.join('  ')}\t| AI 占地 ${ai}`);
  }
}
