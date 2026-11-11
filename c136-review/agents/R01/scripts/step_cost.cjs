// step_cost.cjs — 用线上客户端原文（总部的 engine_replay.cjs / live_game_js.js）按录像逐拍重放，量每一拍结算花多少毫秒。
// 用来回答“某一拍客户端集体停住，是不是这一拍本身算得慢”。
// 用法（在 agents/R01 下）：bash ../../tools/run-heavy.sh node scripts/step_cost.cjs <局号> [--until T] [--around T] [--span 30] [--top 8]
//   --until T   重放到第 T 拍为止（默认到录像结束或 95 秒时限）
//   --around T  另外打印 T−span … T+span 每一拍的耗时
//   --top N     列出最慢的 N 拍
//   --win W     另外按每 W 拍一窗打印：窗内每拍耗时的 中位 / 平均 / 最大（看哪一段对局本身算得重）
// 输出：总拍数、总用时、每拍耗时的 中位/p99/最大、最慢的 N 拍、窗口内逐拍耗时。
const path = require('path');
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? +args[i + 1] : d; };
const until = opt('--until', 1e9), around = opt('--around', -1), span = opt('--span', 30), top = opt('--top', 8), win = opt('--win', 0);
const t0 = Date.now();
const { api } = startReplay(mid);
const cost = [];
let lastT = -1;
const deadline = t0 + 95000;
while (true) {
  const a = process.hrtime.bigint();
  const [t, hx, st] = api.advance(1);
  const ms = Number(process.hrtime.bigint() - a) / 1e6;
  if (hx) continue;
  if (t === lastT) { if (st === 2) break; continue; }
  lastT = t;
  cost.push([t, ms]);
  if (t >= until || st === 2) break;
  if (Date.now() > deadline) { console.log(`# 时间到，停在第 ${t} 拍`); break; }
}
const sorted = cost.map((c) => c[1]).sort((x, y) => x - y);
const q = (p) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
console.log(`# ${mid} 线上客户端原文重放到第 ${lastT} 拍，${cost.length} 拍，用时 ${((Date.now() - t0) / 1000).toFixed(1)} 秒`);
console.log(`# 每拍结算耗时（毫秒）：中位 ${q(0.5).toFixed(2)}，p99 ${q(0.99).toFixed(2)}，最大 ${sorted[sorted.length - 1].toFixed(2)}`);
console.log(`# 最慢的 ${top} 拍：` + [...cost].sort((x, y) => y[1] - x[1]).slice(0, top).map((c) => `t=${c[0]}:${c[1].toFixed(1)}`).join(' '));
if (around >= 0) {
  const w = cost.filter((c) => c[0] >= around - span && c[0] <= around + span);
  console.log(`# t=${around - span}…${around + span} 逐拍耗时（毫秒）：` + w.map((c) => `${c[0]}:${c[1].toFixed(1)}`).join(' '));
  const ws = w.map((c) => c[1]);
  if (ws.length) console.log(`# 窗口内最大 ${Math.max(...ws).toFixed(2)} 毫秒（t=${w[ws.indexOf(Math.max(...ws))][0]}），合计 ${ws.reduce((x, y) => x + y, 0).toFixed(1)} 毫秒`);
}
if (win > 0) {
  const by = new Map();
  for (const [t, ms] of cost) { const k = Math.floor(t / win) * win; if (!by.has(k)) by.set(k, []); by.get(k).push(ms); }
  console.log(`# 按 ${win} 拍分窗：窗口起点 | 拍数 | 每拍耗时 中位 / 平均 / 最大（毫秒）`);
  for (const [k, v] of [...by.entries()].sort((x, y) => x[0] - y[0])) {
    const s2 = [...v].sort((x, y) => x - y);
    console.log(`   ${String(k).padStart(5)} | ${String(v.length).padStart(4)} | ${s2[s2.length >> 1].toFixed(2)} / ${(v.reduce((x, y) => x + y, 0) / v.length).toFixed(2)} / ${s2[s2.length - 1].toFixed(1)}`);
  }
}
