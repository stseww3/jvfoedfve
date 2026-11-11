// coast_len.mjs — 我方号在指定拍的海岸格数（引擎 g.coast[p].length）、能不能出船（g.boatsAllowed(p)）、在途船数、地、兵、密度。
//   用来核对「没有海岸所以出不了船」（引擎 boats.js boatsAllowed L194-196 要求 coast[p].length !== 0）。
//   另给出同一拍全场在途船数（boatN），区分「没有海岸」与「全场船数已满」。
// 用法：node coast_len.mjs <matchId> --at 1500,2100,2700,3300 [--bots leo_tx,riku_x]
import { simulate } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const a = process.argv.slice(2);
const mid = a[0];
const val = (k, d) => (a.includes(k) ? a[a.indexOf(k) + 1] : d);
const at = new Set(String(val('--at', '1500,2100,2700,3300')).split(',').map(Number));
const only = val('--bots', '') ? new Set(val('--bots', '').split(',')) : null;
const tMax = Math.max(...at);
let sq = null;
await simulate(mid, {
  maxTick: tMax + 1,
  onStart(g, info) { sq = squadIds(mid, info.names, info.H).squad; },
  onTick(g, t) {
    if (!at.has(t)) return;
    const parts = [];
    for (const [p, bot] of sq) {
      if (only && !only.has(bot)) continue;
      if (!g.alive[p]) { parts.push(`${bot} 已阵亡`); continue; }
      const L = g.terr[p], B = g.bal[p];
      parts.push(`${bot} 海岸 ${g.coast[p]?.length ?? 0} 格、可出船 ${g.boatsAllowed(p) ? '是' : '否'}、在途船 ${g.boatCount[p]}｜${L} 格/${Math.round(B / 1000)}k/密度 ${(B / Math.max(1, L)).toFixed(0)}`);
    }
    console.log(`t=${t}（全场在途船 ${g.boatN}）：` + parts.join('；'));
  },
});
