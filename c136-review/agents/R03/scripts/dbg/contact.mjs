// 调试：给定拍上，某几个号对同一个目标的「接触面」和 offers 里的接触惩罚（影子重演，不改策略）。
// 用法：node dbg/contact.mjs <mid> <bot[,bot…]> <目标席位号> <t1,t2,…>
// Vb（src/strategy/v27-team-c116-vb.js）：
//   analyze L380-398   cnt[q] = 自己边界格四邻里属于 q 的不同格子数（陆上接触面）
//   offers  L5097-5100 left = peak[q]/4；share = min(1, cnt[q]/border[q].length)；baseGain = max(1, Lq − left + left×shareW×share)；c = (rawNeed + fee)/baseGain
//           L5175-5178 steps = 0.75×Lq/max(1, cnt[q])；cnt[q] < 25 且 steps > contactStepsMax 且对方不濒死、没有在打我：
//                      c ×= 1 + contactPenalty×min(400, steps − contactStepsMax)
// 每个号一行：余额/地/密度、目标 地/余额/密度、cnt、目标边界格数、share、steps、惩罚系数（不满足条件时 1）、
//             当拍 offers 里这个目标的 c 与 need、worth（= maxW×winRatio×自己密度，buyLand L5350-5353）。
import { shadow } from '../shadow.mjs';

const [mid, botsArg, tgArg, ticksArg] = process.argv.slice(2);
const want = new Set(String(botsArg || '').split(','));
const q = +tgArg;
const ticks = new Set(String(ticksArg || '').split(',').map(Number));
const until = Math.max(...ticks) + 1;
const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : String(Math.round(x * 10) / 10));
const rows = new Map();
const hooked = new WeakSet();
const last = new WeakMap();

shadow(mid, {
  quiet: true,
  until,
  trace: (g, b, pol, ctx) => {
    if (!want.has(b.bot)) return;
    if (!hooked.has(pol)) {
      hooked.add(pol);
      const orig = pol.offers;
      pol.offers = function (...a) {
        const r = orig.apply(this, a);
        last.set(this, { t: a[0].t, list: r });
        return r;
      };
    }
    if (!ticks.has(g.t)) return;
    const me = b.me, P = pol.p;
    const B = g.bal[me], L = Math.max(1, g.terr[me]);
    const Lq = g.terr[q], Bq = g.bal[q];
    const cnt = pol.cnt ? pol.cnt[q] : 0;
    const bq = g.border[q] ? g.border[q].length : 0;
    const share = Math.min(1, cnt / Math.max(1, bq));
    const steps = (0.75 * Lq) / Math.max(1, cnt);
    const pen = cnt < 25 && steps > P.contactStepsMax ? 1 + P.contactPenalty * Math.min(400, steps - P.contactStepsMax) : 1;
    const lo = last.get(pol);
    const off = lo && lo.list ? lo.list.find((o) => o.q === q) : null;
    const offTxt = off ? `offers（${lo.t} 拍）c=${off.c.toFixed(1)} need=${k(off.need)}${off.nearCollapse ? ' 濒死' : ''}${off.bleeding ? ' 失血' : ''}` : 'offers 里没有它';
    if (!rows.has(g.t)) rows.set(g.t, []);
    rows.get(g.t).push(`${b.bot}: 兵 ${k(B)} 地 ${L} 密 ${(B / L).toFixed(1)} | ${ctx.names[q]}#${q} 地 ${Lq} 兵 ${k(Bq)} 密 ${(Bq / Math.max(1, Lq)).toFixed(1)} | cnt=${cnt} 对方边界 ${bq} share=${share.toFixed(3)} steps=${steps.toFixed(0)} 接触惩罚 ×${pen.toFixed(2)}（contactStepsMax=${P.contactStepsMax} contactPenalty=${P.contactPenalty}） | ${offTxt}`);
  },
});
console.log(`# ${mid} 对席位 ${q} 的接触面与接触惩罚（contact.mjs；cnt = analyze 里自己边界格四邻属于它的格数；惩罚按 offers L5175-5178 的条件代入，不含濒死/在打我两个豁免）`);
for (const [t, list] of [...rows].sort((a, b) => a[0] - b[0])) {
  console.log(`t=${t}`);
  for (const s of list) console.log('  ' + s);
}
