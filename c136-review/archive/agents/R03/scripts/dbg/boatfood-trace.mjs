// 调试：影子策略里 boatFood 每次调用走到哪一步（用于核对「船」这条指令本地是否被接受的判定）
// 用法：node dbg/boatfood-trace.mjs <mid> <bot> <t0> <t1>
import { shadow } from '../shadow.mjs';
const [mid, bot, t0s, t1s] = process.argv.slice(2);
const t0 = +t0s, t1 = +t1s;
const rows = [];
const im = process.argv.indexOf('--isbot');
const rep = shadow(mid, { until: t1 + 1, quiet: true, isBotMode: im > 0 ? process.argv[im + 1] : null, trace: (g, b, pol) => {
  if (b.bot !== bot || g.t < t0 || g.t > t1 || g.t % 5) return;
  const P = pol.p, me = pol.me;
  const nbBots = [];
  for (const q of pol.nb) if (g.alive[q] && !pol.person(g, q)) nbBots.push([q, +pol.price(g, q).toFixed(2), g.terr[q], g.bal[q]]);
  let food = null;
  if (g.t % 15 === 0 || process.argv.includes('--every')) {
    try {
      const hit = pol.searchFood(g);
      if (hit) {
        const bal = g.bal[me];
        const { floorAt } = pol.floors(g);
        const floor = Math.max(pol.reserve(g, hit.price), floorAt(hit.price));
        const max = P.boatFrac * (bal - floor);
        const min = Math.max(60, P.feeK * Math.floor((32 * bal + 0.5) / 1024));
        food = { land: hit.land, owner: g.px[hit.land] >= 18 ? g.own[hit.land] : (g.px[hit.land] === 17 ? g.own[hit.land] : -1), px: g.px[hit.land], price: +(+hit.price).toFixed(2), cost: Math.round(hit.cost), eff: +(+hit.eff).toFixed(2), floor: Math.round(floor), max: Math.round(max), min: Math.round(min) };
      } else food = 'null';
    } catch (e) { food = String(e).slice(0, 100); }
  }
  rows.push({ t: g.t, food, neutral: pol.neutral, lastFood: pol.lastFood, lastBoat: pol.lastBoat, boatsAllowed: g.boatsAllowed(me), boatCount: g.boatCount[me], maxBoats: P.maxBoats, boatEvery: P.boatEvery, botMax: P.botMax, nb: [...pol.nb], nbBots });
} });
for (const r of rows) console.log(JSON.stringify(r));
