// 调试：某个号在给定拍上「贴着自己边界的无主陆地」和「searchFood 找到的海对面落点」各自所在的无主连通块有多大。
// 用来回答：neutral>0 时没吃的那一两格中立地是什么（孤立小块还是一大片的边），以及 boatFood 的落点后面有多少无主地可拿。
// 用法：node dbg/neutral-comp.mjs <mid> <bot> <t1,t2,...> [--mask N]
//   --mask N：把贴边的、所在无主连通块 ≤ N 格的无主地临时遮掉后再调一次 searchFood（搜完还原），并按 boatFood 的预算式判断会不会发船。
// 不改策略：只读 g.px / g.own / pol.neutral / pol.searchFood(g)；--mask 对 g.px 的改动在同一次回调里还原。
import { shadow } from '../shadow.mjs';

const [mid, bot, ticksArg] = process.argv.slice(2);
const mi = process.argv.indexOf('--mask');
const MASK = mi > 0 ? +process.argv[mi + 1] : 0;
const ticks = new Set(String(ticksArg || '').split(',').map(Number));
const until = Math.max(...ticks) + 1;
const T_LAND = 1, P_INNER = 16;

const compOf = (g, s) => {
  const px = g.px, d = g.dir4, N = g.N;
  const seen = new Set([s]);
  const q = [s];
  let touchMe = 0;
  const owners = new Map();
  for (let h = 0; h < q.length && q.length < 200000; h++) {
    const a = q[h];
    for (let k = 0; k < 4; k++) {
      const n = a + d[k];
      if (n < 0 || n >= N) continue;
      const v = px[n];
      if (v === T_LAND) {
        if (!seen.has(n)) { seen.add(n); q.push(n); }
      } else if (v >= P_INNER) {
        const o = g.own[n];
        owners.set(o, (owners.get(o) ?? 0) + 1);
      }
    }
  }
  return { size: q.length, owners };
};

shadow(mid, {
  quiet: true,
  until,
  trace: (g, b, pol, ctx) => {
    if (b.bot !== bot || !ticks.has(g.t)) return;
    const me = pol.me, W = g.W ?? g.map.w ?? 0;
    const xy = (p) => (W ? `(${p % W},${Math.floor(p / W)})` : `#${p}`);
    const nm = (o) => (o === me ? '自己' : ctx.names?.[o] ? `${String(ctx.names[o]).slice(0, 12)}#${o}` : `AI${o}`);
    const fmtOwners = (m) => [...m.entries()].sort((a, c) => c[1] - a[1]).slice(0, 6).map(([o, n]) => `${nm(o)}×${n}`).join(' ');
    // 贴着自己边界的无主陆地格
    const mine = new Set();
    for (const list of [g.border[me]]) {
      for (let i = 0; i < list.length; i++) {
        for (let k = 0; k < 4; k++) {
          const n = list[i] + g.dir4[k];
          if (g.px[n] === T_LAND) mine.add(n);
        }
      }
    }
    const done = new Set();
    const parts = [];
    for (const s of mine) {
      if (done.has(s)) continue;
      const c = compOf(g, s);
      // 把同一块里的其它边界格标掉
      done.add(s);
      parts.push(`${xy(s)} 所在无主块 ${c.size} 格，四周：${fmtOwners(c.owners)}`);
      if (parts.length >= 6) break;
    }
    let food = '（没调）';
    try {
      const hit = pol.searchFood(g);
      if (!hit) food = '无落点';
      else if (g.px[hit.land] === T_LAND) {
        const c = compOf(g, hit.land);
        food = `落点 ${xy(hit.land)} 无主，所在无主块 ${c.size} 格，四周：${fmtOwners(c.owners)}；eff=${(+hit.eff).toFixed(2)}`;
      } else food = `落点 ${xy(hit.land)} 属 ${nm(g.own[hit.land])}；eff=${(+hit.eff).toFixed(2)}`;
    } catch (e) { food = String(e).slice(0, 80); }
    let masked = '';
    if (MASK) {
      // 把贴边的小块无主地（所在连通块 ≤ MASK 格）临时改成 T_MOUNTAIN 再搜一次：searchFood 一遇到 eff≈2 的落点就停，
      // 不遮掉的话看不到「没有这一格时海上还有什么」。搜完立刻还原。
      const hidden = [];
      for (const s of mine) {
        const c = compOf(g, s);
        if (c.size <= MASK) hidden.push(s);
      }
      for (const s of hidden) g.px[s] = 5;
      try {
        const hit = pol.searchFood(g);
        if (!hit) masked = '无落点';
        else {
          const bal = g.bal[me], P = pol.p;
          const { floorAt } = pol.floors(g);
          const floor = Math.max(pol.reserve(g, hit.price), floorAt(hit.price));
          const max = P.boatFrac * (bal - floor);
          const min = Math.max(60, P.feeK * Math.floor((32 * bal + 0.5) / 1024));
          const where = g.px[hit.land] === T_LAND
            ? (() => { const c = compOf(g, hit.land); return `无主，所在无主块 ${c.size} 格，四周：${fmtOwners(c.owners)}`; })()
            : `属 ${nm(g.own[hit.land])}（地 ${g.terr[g.own[hit.land]]} 兵 ${g.bal[g.own[hit.land]]}）`;
          masked = `落点 ${xy(hit.land)} ${where}；eff=${(+hit.eff).toFixed(2)}（botMax ${P.botMax}） cost=${Math.round(hit.cost)} 留底=${Math.round(floor)} 可装=${Math.round(max)} 最小船=${Math.round(min)} → ${hit.eff > P.botMax ? '不发（eff 高）' : max < min ? '不发（可装 < 最小船）' : '会发'}`;
        }
      } catch (e) { masked = String(e).slice(0, 80); }
      for (const s of hidden) g.px[s] = T_LAND;
      masked = ` | 遮掉 ${hidden.length} 格（≤${MASK} 格的小块）后 searchFood：${masked}`;
    }
    console.log(`t=${g.t} ${bot} 余额 ${g.bal[me]} 地 ${g.terr[me]} neutral=${pol.neutral} 贴边无主格 ${mine.size} 个：${parts.join('；') || '-'} | searchFood：${food}${masked}`);
  },
});
