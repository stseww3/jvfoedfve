// 调试：某个号在某一拍对某个目标的「相邻边界格」明细（边界格/前线格各多少）与当前进攻槽
// 用法：node dbg/attack-state.mjs <mid> <bot> <t0> <t1> <target>
import { shadow } from '../shadow.mjs';
const [mid, bot, t0s, t1s, tgs] = process.argv.slice(2);
const t0 = +t0s, t1 = +t1s, target = +tgs;
const P_INNER = 16;
shadow(mid, { until: t1 + 1, quiet: true, trace: (g, b, pol) => {
  if (b.bot !== bot || g.t < t0 || g.t > t1) return;
  const me = b.me, B = g.border[me], d = g.dir4, px = g.px, own = g.own;
  const hist = {};
  let adj = 0;
  for (let i = 0; i < B.length; i++) {
    const c0 = B[i];
    let touch = false;
    for (let k = 0; k < 4; k++) { const c = c0 + d[k]; if (target === 512 ? px[c] === 1 : (px[c] >= P_INNER && own[c] === target)) touch = true; }
    if (touch) { adj++; hist[px[c0]] = (hist[px[c0]] || 0) + 1; }
  }
  const sb = g.slotBase(me);
  const atk = [];
  for (let i = 0; i < g.atkCount[me]; i++) atk.push([g.atkTarget[sb + i], g.atkTroops[sb + i]]);
  console.log(JSON.stringify({ t: g.t, bal: g.bal[me], terr: g.terr[me], border: B.length, front: g.front[me].length, adjToTarget: adj, pxTypeHist: hist, attacks: atk, hasAttack: g.hasAttack(me, target), freeSlot: g.hasFreeSlot(me), nb: [...pol.nb], cntT: pol.cnt[target] }));
} });
