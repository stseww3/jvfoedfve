// formation_footprint.mjs — 阵形的「脚印」：一组出生点四周有多少陆地（不需要知道别的玩家在哪）。
//   给没有录像的那一盘用（拆盘局的 Y 盘）：点取 in_game.log 里每个号最后一条 [HL-SPAWN-BACKEND] 指派点。
//   输出：
//     1) 离任一点 ≤ R 格的陆地格数、占全图陆地的比例（R 取 --r）；
//     2) 只在这组点之间做最近点划分（Voronoi），每个点名下、且离它 ≤ --clip 格的陆地格数；
//     3) 外接框里的陆地；各点到图边的最近距离；
//     4) --others x,y;x,y…：再加一组「别人」的点（比如同图另一盘的真人出生点），做一次完整的最近点划分，给出这组点名下的陆地合计。
// 用法：node formation_footprint.mjs <matchId> [--pts x,y;x,y…] [--skip ryan_m] [--r 60,90,120,150,200] [--clip 150] [--others x,y;…]
import fs from 'node:fs';
import { simulate, P_INNER } from './sim_replay.mjs';
const { T_LAND } = await import('file:///agent/repos/c136-data/src/sim/sim/map.js');

const a = process.argv.slice(2);
const mid = a[0];
const val = (k, d) => (a.includes(k) ? a[a.indexOf(k) + 1] : d);
const RS = String(val('--r', '60,90,120,150,200')).split(',').map(Number);
const CLIP = +val('--clip', 150);
const skip = new Set(String(val('--skip', '')).split(',').filter(Boolean));
let pts = [];
if (a.includes('--pts')) {
  pts = val('--pts', '').split(';').map((s, i) => ({ name: `p${i}`, x: +s.split(',')[0], y: +s.split(',')[1] }));
} else {
  const last = new Map();
  for (const ln of fs.readFileSync(`/agent/repos/c136-data/bundles/${mid}/in_game.log`, 'utf8').split('\n')) {
    const m = /\[([A-Za-z0-9_ ]+)\] \[HL-SPAWN-BACKEND\] .*role=(\S+) -> \((\d+),(\d+)\)/.exec(ln);
    if (m) last.set(m[1], { name: m[1], role: m[2], x: +m[3], y: +m[4] });
  }
  pts = [...last.values()].filter((p) => !skip.has(p.name));
}
const others = a.includes('--others') ? val('--others', '').split(';').map((s) => ({ x: +s.split(',')[0], y: +s.split(',')[1] })) : [];
let W = 0, Hh = 0, land = null;
await simulate(mid, {
  maxTick: 1,
  onStart(g) {
    W = g.W; Hh = g.H; land = new Uint8Array(g.N);
    for (let c = 0; c < g.N; c++) land[c] = g.px[c] === T_LAND || g.px[c] >= P_INNER ? 1 : 0;
  },
});
let total = 0;
const within = RS.map(() => 0);
const cell = pts.map(() => 0), cellAll = pts.map(() => 0);
let ours = 0;
const x0 = Math.min(...pts.map((p) => p.x)), x1 = Math.max(...pts.map((p) => p.x)), y0 = Math.min(...pts.map((p) => p.y)), y1 = Math.max(...pts.map((p) => p.y));
let box = 0;
for (let y = 0; y < Hh; y++) {
  for (let x = 0; x < W; x++) {
    if (!land[y * W + x]) continue;
    total++;
    let best = -1, bd = Infinity;
    for (let i = 0; i < pts.length; i++) {
      const d = (pts[i].x - x) ** 2 + (pts[i].y - y) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    const dist = Math.sqrt(bd);
    for (let k = 0; k < RS.length; k++) if (dist <= RS[k]) within[k]++;
    if (dist <= CLIP) cell[best]++;
    if (x >= x0 && x <= x1 && y >= y0 && y <= y1) box++;
    if (others.length) {
      let od = Infinity;
      for (const o of others) { const d = (o.x - x) ** 2 + (o.y - y) ** 2; if (d < od) od = d; }
      if (bd <= od) { ours++; cellAll[best]++; }
    }
  }
}
console.log(`[阵形脚印] ${mid} 图 ${W}×${Hh} 陆地 ${total} 格｜点 ${pts.length} 个：` + pts.map((p) => `${p.name}(${p.x},${p.y})`).join(' '));
console.log('   离任一点 ≤R 格的陆地：' + RS.map((r, k) => `R=${r}: ${within[k]} 格（${(100 * within[k] / total).toFixed(1)}%）`).join('；'));
console.log(`   外接框 ${x0}–${x1} × ${y0}–${y1} 里的陆地 ${box} 格（${(100 * box / total).toFixed(1)}%；框面积 ${(x1 - x0 + 1) * (y1 - y0 + 1)} 格，陆地占 ${(100 * box / ((x1 - x0 + 1) * (y1 - y0 + 1))).toFixed(0)}%）`);
console.log(`   只在这组点之间划分、且离点 ≤${CLIP} 格：` + pts.map((p, i) => `${p.name} ${cell[i]}`).join('；') + `｜合计 ${cell.reduce((s, v) => s + v, 0)}（${(100 * cell.reduce((s, v) => s + v, 0) / total).toFixed(1)}%），每点中位 ${[...cell].sort((p, q) => p - q)[Math.floor(cell.length / 2)]}`);
console.log('   各点到图边的最近距离：' + pts.map((p) => `${p.name} ${Math.min(p.x, p.y, W - 1 - p.x, Hh - 1 - p.y)}`).join('；') + `｜人数 ${pts.length} 占 20 人的 ${(100 * pts.length / 20).toFixed(0)}%`);
if (others.length) {
  console.log(`   加上另一组 ${others.length} 个点做完整划分：这组点名下 ${ours} 格（${(100 * ours / total).toFixed(1)}%；人数占 ${(100 * pts.length / (pts.length + others.length)).toFixed(1)}% → 份额÷人数 ${(ours / total / (pts.length / (pts.length + others.length))).toFixed(2)}）｜每点：` + pts.map((p, i) => `${p.name} ${cellAll[i]}`).join('；'));
}
