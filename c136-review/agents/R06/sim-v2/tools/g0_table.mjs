// g0_table.mjs — 把一批 checkpoint 结果文件排成「真局 ↔ 模拟对照臂」的签名对照表（G0 自检用）。
// 用法：node sim-v2/tools/g0_table.mjs <结果.json …> [--md]
//   每个结果文件一行：局、窗口、策略、通道；每个签名给「模拟 / 真局」两个数。
import fs from 'node:fs';

const args = process.argv.slice(2);
const md = args.includes('--md');
const arm = (args.find((a) => a.startsWith('--arm=')) || '--arm=baseline').slice(6);
const files = args.filter((a) => !a.startsWith('--'));
const pc = (v) => (v === null || v === undefined ? '-' : (100 * v).toFixed(0) + '%');
const k = (v) => (v === null || v === undefined ? '-' : Math.abs(v) >= 1000 ? (v / 1000).toFixed(1) + 'k' : String(Math.round(v * 1000) / 1000));
const rows = [];
for (const f of files) {
  let r;
  try { r = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { continue; }
  const h = r.history, b = r.arms[arm];
  if (!b) continue;
  rows.push([
    r.match, `${r.t0}~${r.t1}`, b.strategy.replace('v27-team-', ''), r.channelSpec,
    `${b.recorded} / ${h.recorded}`,
    `${pc(b.dupShare)} / ${pc(h.dupShare)}`,
    `${b.batches} / ${h.batches}`,
    `${b.dumpBatches} / ${h.dumpBatches}`,
    `${pc(b.batchShare)} / ${pc(h.batchShare)}`,
    `${pc(b.gapShare[0])} / ${pc(h.gapShare[0])}`,
    `${pc(b.atkVoidRate)} / ${pc(h.atkVoidRate)}`,
    `${pc(b.rerouteRate)} / ${pc(h.rerouteRate)}`,
    `${pc(b.atkNeutralShare)} / ${pc(h.atkNeutralShare)}`,
    `${b.don.arrived ? pc(b.quotaRejectRate) + '(' + b.don.arrived + ')' : '-'} / ${h.don.arrived ? h.don.arrived + '成' : '-'}`,
    `${k(b.relTerr1)} / ${k(h.relTerr1)}`,
    `${b.alive1} / ${h.alive1}`,
  ]);
}
const head = ['局', '窗口', '策略', '通道', '进录像条数', '重复单占比', '同拍批', '清仓批', '同拍批占比', '同回合连发占比', '陆攻落空率', '目标已死改道率', '陆攻记成无主地占比', '配额拒单率(到达)/真局成交', '人均相对领土', '存活席位'];
if (md) {
  console.log('| ' + head.join(' | ') + ' |');
  console.log('|' + head.map(() => '---').join('|') + '|');
  for (const r of rows) console.log('| ' + r.join(' | ') + ' |');
} else {
  console.log(head.join('\t'));
  for (const r of rows) console.log(r.join('\t'));
}
console.log(md ? '\n每格：模拟对照臂 / 真局。' : '每格：模拟对照臂 / 真局');
