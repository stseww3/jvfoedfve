// 调试：在给定拍上打印每个号的海岸格数、能否发船、上一个决策拍的陆上邻居数与中立邻格数。
// 用法：node dbg/coast.mjs <mid> <t1,t2,...>
// 用来回答「被围的号有没有海岸、能不能走船」：引擎的 boatsAllowed 要求 coast[p].length !== 0。
import { shadow } from '../shadow.mjs';

const [mid, ticksArg] = process.argv.slice(2);
const ticks = new Set(String(ticksArg || '').split(',').map(Number));
const until = Math.max(...ticks) + 1;
const rows = new Map();
shadow(mid, {
  quiet: true,
  until,
  trace: (g, b, pol) => {
    if (!ticks.has(g.t)) return;
    const me = b.me;
    if (!rows.has(g.t)) rows.set(g.t, []);
    rows.get(g.t).push(`${b.bot}: 海岸 ${g.coast[me].length} 可发船 ${g.boatsAllowed(me) ? '是' : '否'} 在航 ${g.boatCount[me]} | 地 ${g.terr[me]} 兵 ${g.bal[me]} 密 ${(g.bal[me] / Math.max(1, g.terr[me])).toFixed(0)} | 陆邻 ${pol.nb ? pol.nb.length : '-'} 中立邻格 ${pol.neutral ?? '-'}`);
  },
});
for (const [t, list] of [...rows].sort((a, b) => a[0] - b[0])) {
  console.log(`t=${t}`);
  for (const s of list) console.log('  ' + s);
}
