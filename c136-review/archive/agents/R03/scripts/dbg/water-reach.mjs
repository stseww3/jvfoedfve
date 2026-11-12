// 调试：给定拍上，某个号海岸挨着的那片水域（四连通水格）能通到谁的岸（影子重演，不改策略）。
// 用法：node dbg/water-reach.mjs <mid> <bot[,bot…]|squad> <t1,t2,…> [--range 2500]
// 用来回答「被围的号有岸却发不出船」：
//   Vb General.searchWater（L1024-1078）只从 coast[me]、border[me] 四邻的水格出发做广搜（最多走 boatRange 步；
//   被围分支 idleBoats L5038 把 boatRange 临时设成 2500），落点只能是 无主地，或 非本队、且不是自己陆上邻居 的人/AI 的地；
//   这片水域的岸上找不到这样的格子就返回空（idle-boats.mjs 里归成「找不到落点」）。
// 每个号、每个拍一行：出发水格数、走得到的水格数、最远步数；岸上的格子按归属分类计数，并给各类最近的水路步数：
//   自己 / 本队编队号 / 本队路人 / 敌方真人（逐个列名字）/ AI / 无主地。
import { shadow } from '../shadow.mjs';

const args = process.argv.slice(2);
const [mid, botsArg, ticksArg] = args;
const ri = args.indexOf('--range');
const RANGE = ri > 0 ? +args[ri + 1] : 2500;
const ticks = new Set(String(ticksArg || '').split(',').map(Number));
const until = Math.max(...ticks) + 1;
const T_LAND = 1, T_WATER = 2, P_INNER = 16;
const want = botsArg === 'squad' ? null : new Set(String(botsArg || '').split(','));
const rows = new Map();
let dist = null, queue = null;

shadow(mid, {
  quiet: true,
  until,
  trace: (g, b, pol, ctx) => {
    if (!ticks.has(g.t)) return;
    if (want && !want.has(b.bot)) return;
    const me = b.me, N = g.N, px = g.px, own = g.own, d = g.dir4;
    if (!dist || dist.length !== N) { dist = new Int32Array(N); queue = new Int32Array(N); }
    dist.fill(-1);
    let h = 0, t = 0;
    const seed = (list) => {
      for (let i = list.length - 1; i >= 0; i--) {
        for (let k = 0; k < 4; k++) {
          const c = list[i] + d[k];
          if (px[c] === T_WATER && dist[c] < 0) { dist[c] = 0; queue[t++] = c; }
        }
      }
    };
    seed(g.coast[me]);
    seed(g.border[me]);
    const seeds = t;
    const squadIds = new Set(Object.values(ctx.squad).map((s) => s.id));
    const myTeam = g.teams ? g.teams[me] : 0;
    const cls = new Map(); // 类别 -> { n, near }
    const seen = new Uint8Array(N);
    const bump = (key, dc) => {
      const r = cls.get(key) || { n: 0, near: Infinity };
      r.n++;
      if (dc < r.near) r.near = dc;
      cls.set(key, r);
    };
    let far = 0;
    while (h < t) {
      const c = queue[h++];
      const dc = dist[c];
      if (dc > far) far = dc;
      if (dc > RANGE) break;
      for (let k = 0; k < 4; k++) {
        const n = c + d[k];
        const v = px[n];
        if (v === T_WATER) {
          if (dist[n] < 0) { dist[n] = dc + 1; queue[t++] = n; }
        } else if (v === T_LAND) {
          if (!seen[n]) { seen[n] = 1; bump('无主地', dc); }
        } else if (v >= P_INNER) {
          if (seen[n]) continue;
          seen[n] = 1;
          const o = own[n];
          if (o === me) bump('自己', dc);
          else if (squadIds.has(o)) bump('本队编队号', dc);
          else if (o < g.humans && myTeam > 0 && g.teams[o] === myTeam) bump('本队路人', dc);
          else if (o < g.humans) bump(`敌方真人 ${ctx.names[o]}#${o}${pol.cnt && pol.cnt[o] > 0 ? '（陆上邻居）' : ''}`, dc);
          else bump('AI', dc);
        }
      }
    }
    const order = (k) => (k === '自己' ? 0 : k === '本队编队号' ? 1 : k === '本队路人' ? 2 : k === '无主地' ? 4 : k === 'AI' ? 5 : 3);
    const parts = [...cls].sort((a, b2) => order(a[0]) - order(b2[0]) || b2[1].n - a[1].n).map(([k, r]) => `${k} ${r.n} 格（最近 ${r.near} 步）`);
    if (!rows.has(g.t)) rows.set(g.t, []);
    rows.get(g.t).push(`${b.bot}: 海岸 ${g.coast[me].length} 格，出发水格 ${seeds}，走得到的水格 ${t}，最远 ${far} 步 | 岸上：${parts.length ? parts.join('；') : '（没有水格可走）'}`);
  },
});
console.log(`# ${mid} 各号海岸挨着的水域通到谁的岸（water-reach.mjs；广搜最多 ${RANGE} 步；「陆上邻居」= 当拍策略眼里与它陆上相接，searchWater 不把它当落点）`);
for (const [t, list] of [...rows].sort((a, b) => a[0] - b[0])) {
  console.log(`t=${t}`);
  for (const s of list) console.log('  ' + s);
}
