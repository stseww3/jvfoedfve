#!/usr/bin/env node
// arena_style.mjs — 对手模型按「滑块五档」的验收表：每档的点击密度、每 100 拍花掉余额的几成、手里的余额占比，
// 模型（arena 结果里 Crowd 的账，多局取中位）对实测（human-profile.json）。
//
// 用法：node sim-v2/tools/arena_style.mjs <arena 结果.json …> [--arm=baseline] [--phases=10]
import fs from 'node:fs';
import path from 'node:path';
import { SIMV2 } from '../lib/match.mjs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const armName = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const nPh = +(args.find((a) => a.startsWith('--phases=')) || '--phases=10').slice(9);
const prof = JSON.parse(fs.readFileSync(path.join(SIMV2, 'calib', 'human-profile.json'), 'utf8'));
const med = (a) => { const s = a.filter((x) => x !== null && Number.isFinite(x)).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null; };
const runs = files.map((f) => JSON.parse(fs.readFileSync(f, 'utf8'))).filter((r) => r.arms && r.arms[armName] && r.arms[armName].crowd).map((r) => r.arms[armName].crowd);
if (!runs.length) { console.error('没有可用的 arena 结果'); process.exit(1); }
const Q = [0, 1, 2, 3, 4];
console.log(`按滑块五档（低→高）：${runs.length} 局模型的中位 对 ${prof.matches.length} 局实测`);
for (let i = 0; i < Math.min(nPh, prof.phases.length); i++) {
  const P = prof.phases[i], g = P.byStyle.groups;
  if (g.length !== 5) continue;
  const rows = runs.map((r) => r.intensity[i]).filter((x) => x && x.cmds > 0);
  if (!rows.length) continue;
  console.log(`${P.phase.padEnd(10)} 实测  密度 ${g.map((x) => x.rate.toFixed(2)).join(' / ')}  花掉 ${g.map((x) => Math.round(100 * x.spend) + '%').join(' / ')}  余额占比 ${g.map((x) => Math.round(100 * x.balShare) + '%').join(' / ')}（另有本阶段没出手的人 ${Math.round(100 * P.byStyle.idle.balShare)}%）  每条 ${P.sentPerCmd} 兵`);
  console.log(`${''.padEnd(10)} 模型  密度 ${Q.map((q) => (med(rows.map((x) => x.byStyle[q].rate)) ?? 0).toFixed(2)).join(' / ')}  花掉 ${Q.map((q) => Math.round(100 * (med(rows.map((x) => x.byStyle[q].spend)) ?? 0)) + '%').join(' / ')}  余额占比 ${Q.map((q) => Math.round(100 * (med(rows.map((x) => x.byStyle[q].balShare)) ?? 0)) + '%').join(' / ')}  每条 ${med(rows.map((x) => x.sentPerCmd))} 兵`);
}
console.log(`连点占比（相邻两条只隔 1 个回合）：模型 ${runs.map((r) => r.burst7).join(' ')}`);
