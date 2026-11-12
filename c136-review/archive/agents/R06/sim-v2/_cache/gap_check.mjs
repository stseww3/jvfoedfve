// 录像里同一席位相邻两条指令的执行拍间隔分布（看页面两次发令之间最短隔多久）
import { loadMatch } from '../lib/match.mjs';
const mids = process.argv.slice(2);
for (const mid of mids) {
  const M = loadMatch(mid);
  const d = M.d, H = M.H;
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const sq = new Set(M.squad);
  let iw = 0, unit = 0;
  const last = new Map();
  const bands = [[0, 600], [600, 1500], [1500, 3000], [3000, 1e9]];
  const hist = bands.map(() => ({ ours: new Map(), others: new Map(), n: [0, 0] }));
  for (let iv = 0; iv < d.ja.length; iv++) {
    const jZ = d.ja[iv];
    if (d.jY[iv]) {
      const tick = unit - (jJ + 1);
      for (let a = iw; a < iw + jZ; a++) {
        const c = d.cmds[a];
        if (tick < 0 || c.player >= H || ![1, 2, 3].includes(c.id)) continue;
        const b = bands.findIndex(([x, y]) => tick >= x && tick < y);
        const h = hist[b];
        const mine = sq.has(c.player);
        const pv = last.get(c.player);
        if (pv !== undefined) {
          const g = Math.min(tick - pv, 70);
          const m = mine ? h.ours : h.others;
          m.set(g, (m.get(g) || 0) + 1);
          h.n[mine ? 0 : 1]++;
        }
        last.set(c.player, tick);
      }
      iw += jZ;
      unit += 1;
    } else unit += jZ;
  }
  console.log(`== ${mid}（我方 ${M.squad.length} 席）相邻两条指令的执行拍间隔：占比（0 = 同一回合）`);
  bands.forEach(([x, y], i) => {
    const h = hist[i];
    const f = (m, n) => [0, 7, 14, 21, 28, 35].map((g) => `${g}:${(100 * (m.get(g) || 0) / Math.max(1, n)).toFixed(0)}%`).join(' ');
    console.log(`  t=${x}~${y === 1e9 ? '' : y}  我方(${h.n[0]}) ${f(h.ours, h.n[0])}   其他真人(${h.n[1]}) ${f(h.others, h.n[1])}`);
  });
}
