#!/usr/bin/env node
// arena_table.mjs — 把 arena 结果文件里「模型 vs 同一局录像」的各断面走势排成表（对手模型验收用）。
// 用法：node sim-v2/tools/arena_table.mjs <结果.json…> [--arm=baseline] [--md]
import fs from 'node:fs';

const args = process.argv.slice(2);
const files = args.filter((a) => !a.startsWith('--'));
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const md = args.includes('--md');
const CPS = [357, 630, 1071, 1530, 2142, 3210, 4284, 6000];
const KEYS = [
  ['othersPerSeat', '其余真人人均地', 0],
  ['othersAliveShare', '其余真人在场占比', 2],
  ['othersDensity', '其余真人兵密度', 1],
  ['aiShare', '内置 AI 占陆地', 2],
  ['relOthers', '我方人均地 ÷ 其余真人人均地', 2],
  ['squadAlive', '我方在场席位', 0],
];
const rows = [];
const ratios = {};
for (const f of files) {
  const r = JSON.parse(fs.readFileSync(f, 'utf8'));
  const m = r.arms[arm];
  if (!m || !r.reality || !r.reality.cps) continue;
  for (const t of CPS) {
    const a = m.cps[t], b = r.reality.cps[t];
    if (!a || !b) continue;
    const row = [r.room.match, r.room.humans, r.channel, t];
    for (const [k, , d] of KEYS) {
      row.push(`${a[k] === null ? '-' : (+a[k]).toFixed(d)} / ${b[k] === null ? '-' : (+b[k]).toFixed(d)}`);
      if (k === 'othersPerSeat' || k === 'relOthers' || k === 'othersDensity') {
        if (a[k] > 0 && b[k] > 0) ((ratios[t] ||= {})[k] ||= []).push(a[k] / b[k]);
      } else if (a[k] !== null && b[k] !== null) ((ratios[t] ||= {})[k] ||= []).push(a[k] - b[k]);
    }
    rows.push(row);
  }
}
const head = ['局', '真人数', '通道', '断面', ...KEYS.map((k) => k[1] + '（模型 / 录像）')];
if (md) {
  console.log('| ' + head.join(' | ') + ' |');
  console.log('|' + head.map(() => '---').join('|') + '|');
  for (const r of rows) console.log('| ' + r.join(' | ') + ' |');
} else {
  console.log(head.join('\t'));
  for (const r of rows) console.log(r.join('\t'));
}
const med = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : NaN; };
const lo = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 4)] : NaN; };
const hi = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(3 * s.length / 4))] : NaN; };
console.log(md ? '\n汇总（各局 模型 ÷ 录像 的 P25 / 中位 / P75；占比类是 模型 − 录像 的差）：\n' : '汇总（各局 模型 ÷ 录像 的 P25 / 中位 / P75；占比类是 模型 − 录像 的差）：');
if (md) { console.log('| 断面 | 局数 | 其余真人人均地 | 其余真人兵密度 | 我方 ÷ 其余真人 | 其余真人在场占比（差） | 内置 AI 占陆地（差） |'); console.log('|---|---|---|---|---|---|---|'); }
for (const t of CPS) {
  const R = ratios[t];
  if (!R) continue;
  const f3 = (k, d = 2) => (R[k] ? `${lo(R[k]).toFixed(d)} / ${med(R[k]).toFixed(d)} / ${hi(R[k]).toFixed(d)}` : '-');
  if (md) console.log(`| ${t} | ${R.othersPerSeat ? R.othersPerSeat.length : 0} | ${f3('othersPerSeat')} | ${f3('othersDensity')} | ${f3('relOthers')} | ${f3('othersAliveShare')} | ${f3('aiShare')} |`);
  else console.log(`  t=${t}（${R.othersPerSeat ? R.othersPerSeat.length : 0} 局）：其余真人人均地 ${f3('othersPerSeat')}；兵密度 ${f3('othersDensity')}；我方 ÷ 其余真人 ${f3('relOthers')}；在场占比差 ${f3('othersAliveShare')}；AI 占陆地差 ${f3('aiShare')}`);
}
