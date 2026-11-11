// bot_fate.mjs — 指定的几个 AI 机器人（或任意玩家 id）的地最后被谁拿走、什么时候拿的。
//   逐拍精确重放（sim_replay.mjs，只读）：每拍对比全图归属，凡是上一拍属于被跟踪 id、这一拍换了主人的格子，记到新主人名下。
//   输出：每个被跟踪 id 的 峰值地 / 各采样拍的 地、兵 / 被拿走的格数按拿地方汇总（含首末拍）/ 地归零的拍。
// 用法：node bot_fate.mjs <matchId> --ids 127,417,374,338 [--t0 0 --t1 2400] [--at 800,900,1000,1100,1200,1300,1400,1500]
import { simulate, P_INNER, NEUTRAL } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const a = process.argv.slice(2);
const mid = a[0];
const val = (k, d) => (a.includes(k) ? a[a.indexOf(k) + 1] : d);
const ids = String(val('--ids', '')).split(',').filter(Boolean).map(Number);
const T0 = +val('--t0', 0), T1 = +val('--t1', 2400);
const at = String(val('--at', '800,900,1000,1100,1200,1300,1400,1500')).split(',').map(Number);
const track = new Set(ids);
let R = null, prev = null;
const takers = new Map(ids.map((i) => [i, new Map()]));
const snap = new Map(ids.map((i) => [i, []]));
const peak = new Map(ids.map((i) => [i, { terr: 0, t: 0 }]));
const zeroAt = new Map();
const k = (v) => (v >= 1e6 ? (v / 1e6).toFixed(2) + 'M' : v >= 1e4 ? Math.round(v / 1e3) + 'k' : String(v));

await simulate(mid, {
  maxTick: T1 + 1,
  onStart(g, info) {
    R = info;
    R.sq = squadIds(mid, info.names, info.H).squad;
  },
  onTick(g, t) {
    const N = g.N, own = g.own, px = g.px;
    if (!prev) { prev = new Int16Array(N).fill(-1); }
    for (const i of ids) {
      const p = peak.get(i);
      if (g.terr[i] > p.terr) { p.terr = g.terr[i]; p.t = t; }
      if (at.includes(t)) snap.get(i).push(`${t}: ${g.terr[i]} 格/${k(g.bal[i])}`);
      if (p.terr > 0 && g.terr[i] === 0 && !zeroAt.has(i)) zeroAt.set(i, t);
    }
    if (t >= T0) {
      for (let c = 0; c < N; c++) {
        const o = px[c] >= P_INNER ? own[c] : -1;
        const q = prev[c];
        if (q !== o) {
          if (q >= 0 && track.has(q)) {
            const key = o < 0 ? NEUTRAL : o;
            const m = takers.get(q);
            const e = m.get(key) || { n: 0, t0: t, t1: t };
            e.n++; e.t1 = t;
            m.set(key, e);
          }
          prev[c] = o;
        }
      }
    } else {
      for (let c = 0; c < N; c++) prev[c] = px[c] >= P_INNER ? own[c] : -1;
    }
  },
});
const nm = (i) => {
  if (i === NEUTRAL) return '变中立';
  const s = R.sq.get(i);
  if (s) return `我方 ${s}#${i}`;
  if (i < R.H) return `${String(R.names[i] || '').slice(0, 14)}#${i}`;
  return `机器人#${i}`;
};
console.log(`[机器人去向] ${mid} 跟踪 id ${ids.join(',')}｜t=${T0}–${T1}`);
for (const i of ids) {
  const m = [...takers.get(i).entries()].sort((x, y) => y[1].n - x[1].n);
  const tot = m.reduce((s, [, e]) => s + e.n, 0);
  console.log(`  #${i}（${i < R.H ? '真人 ' + R.names[i] : '机器人'}）峰值 ${peak.get(i).terr} 格@${peak.get(i).t}｜地归零 ${zeroAt.has(i) ? 't=' + zeroAt.get(i) : '没有（到 t=' + T1 + '）'}｜${snap.get(i).join('；')}`);
  console.log(`     被拿走 ${tot} 格：` + m.map(([q, e]) => `${nm(q)} ${e.n}（${e.t0}–${e.t1}）`).join('、'));
}
