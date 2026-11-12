// 调试：某个号的地在给定拍上分成几块（4 邻接的连通块），每块多大、贴着谁、贴着多少格水/山。
// 用来回答「一个 2 万多格的空壳为什么登陆后只吃到几百格前线就断了」：进攻只能沿相邻的格推进，
// 目标的地如果被水/山切成几块，登陆的那一块吃完，前线就没有了（引擎 endAttack：和目标不再相邻 → 槽里的兵退回）。
// 用法：node dbg/land-parts.mjs <mid> <席位号> <t1,t2,...> [--min 50]
//   每个采样拍：目标总地、连通块个数；≥min 格的块按大小列出：格数、外接框、邻格归属（各真人/AI/无主地/水/山 的格数）
import { resim } from '../resim.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const seat = +args[1];
const ticks = new Set(String(args[2] || '').split(',').map(Number));
const minSz = args.includes('--min') ? +args[args.indexOf('--min') + 1] : 50;
const until = Math.max(...ticks) + 1;
const P_INNER = 16;
const out = [];
let names = null, H = 0, teams = null, sq = null;
const R = resim(mid, {
  until,
  onState: (g) => {
    if (!ticks.has(g.t)) return;
    const W = g.W, Hh = g.H, N = W * Hh;
    const px = g.px, own = g.own;
    const comp = new Int32Array(N).fill(-1);
    const parts = [];
    const stack = [];
    for (let s = 0; s < N; s++) {
      if (comp[s] !== -1 || px[s] < P_INNER || own[s] !== seat) continue;
      const id = parts.length;
      const part = { n: 0, x0: 1e9, x1: -1, y0: 1e9, y1: -1, nbr: new Map(), water: 0, rock: 0, free: 0 };
      comp[s] = id;
      stack.push(s);
      while (stack.length) {
        const p = stack.pop();
        part.n++;
        const x = p % W, y = (p / W) | 0;
        if (x < part.x0) part.x0 = x;
        if (x > part.x1) part.x1 = x;
        if (y < part.y0) part.y0 = y;
        if (y > part.y1) part.y1 = y;
        const nbs = [x > 0 ? p - 1 : -1, x < W - 1 ? p + 1 : -1, y > 0 ? p - W : -1, y < Hh - 1 ? p + W : -1];
        for (const c of nbs) {
          if (c < 0) continue;
          const v = px[c];
          if (v >= P_INNER) {
            if (own[c] === seat) {
              if (comp[c] === -1) { comp[c] = id; stack.push(c); }
            } else part.nbr.set(own[c], (part.nbr.get(own[c]) || 0) + 1);
          } else if (g.passable && g.passable(c)) part.free++;
          else if (g.map && g.map.type && g.map.type[c] !== undefined && g.blocked && g.blocked(c)) part.rock++;
          else part.water++;
        }
      }
      parts.push(part);
    }
    out.push([g.t, g.terr[seat], g.bal[seat], parts]);
  },
});
names = R.names; H = R.H; teams = R.teams;
sq = new Map(Object.entries(R.squad).filter(([, s]) => s.id >= 0 && !s.mismatch).map(([b, s]) => [s.id, b]));
const nm = (q) => (sq.has(q) ? sq.get(q) : q < H ? `${(names[q] || '?').slice(0, 12)}#${q}T${teams[q]}` : `AI${q}`);
console.log(`# ${mid} ${nm(seat)} 的地分成几块（land-parts.mjs；4 邻接连通块；只列 ≥${minSz} 格的块；邻格 = 块的外沿一圈，按归属数格）`);
for (const [t, terr, bal, parts] of out) {
  parts.sort((a, b) => b.n - a.n);
  const big = parts.filter((p) => p.n >= minSz);
  console.log(`t=${t} 地 ${terr} 兵 ${bal}：连通块 ${parts.length} 个，其中 ≥${minSz} 格的 ${big.length} 个；最大的 3 块 ${parts.slice(0, 3).map((p) => p.n).join('、')} 格`);
  for (const p of big.slice(0, 12)) {
    const nb = [...p.nbr].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([q, n]) => `${nm(q)}×${n}`).join(' ');
    console.log(`    ${p.n} 格 框 x${p.x0}~${p.x1} y${p.y0}~${p.y1} | 外沿：${nb || '没有别人的地'}｜无主地 ${p.free}｜水/山 ${p.water + p.rock}`);
  }
}
