// 调试：Policy.buyLand 在有报价却没出手的决策拍上，逐项「只去掉这一道闸」重跑一遍，看是哪一道拦的。
// 用法：node dbg/buy-why.mjs <mid> <bot> <t0> <t1> [--every N]
// 每一行：拍、余额/地/密度、最便宜报价的字段、worth/over，以及所有「单独去掉它就会走到 send」的闸（逐项各跑一遍，全部列出）；
// 单项都放不出来时，再按项数递增试组合，列出第一组放得出来的：
//   none        原样重跑就走到 send（说明是 send 守卫或适配层拒的）
//   worth       把 maxW 放大（报价不再 ≥ worth）——L5359 的 break 或各分支里的 c >= worth 条件
//   soleBuffer  overHumanCap=0 —— L5361-5365「唯一健康真人缓冲」：B < overHumanCap*100*L 就 continue
//   crowded     crowdedHardCap=0 —— L5371-5374 拥挤目标 / L5437 围城收缩：B < crowdedHardCap*100*L 就 continue
//   absorb      absorbMode=0 —— L5376-5378 吸收模式
//   chunk       chunk=0 —— L5613 x < want 且 x < chunk*B 就 continue（以及 usePulseBlock 的 avail < chunk*B）
//   pulseMin    pulseMinShare=0 且 minCmd=0 —— 脉冲额太小（L5583/L5591/L5605）
//   safe        safeAt=0 —— L5414/L5444 的留底
//   hold        hold=0, overHumanKeep=0 —— L5440-5443 过软上限后的保留线
//   组合:a+b    单项都放不出来，a、b 一起去掉才走到 send（从两项起按项数递增找，列第一组）
//   -           单项和组合都放不出来
//   「不动价格线：…」只在 worth 单独能放、别的单项都不行时出现：不碰 worth，其余各闸要去掉哪几道才出手
// 只在实例上临时改参数/方法，跑完立即恢复；不改策略文件。
import { shadow } from '../shadow.mjs';

const args = process.argv.slice(2);
const [mid, bot, t0s, t1s] = args;
const t0 = +t0s, t1 = +t1s;
const evIdx = args.indexOf('--every');
const every = evIdx >= 0 ? +args[evIdx + 1] : 1;
const k = (x) => (typeof x !== 'number' ? String(x) : Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : (Math.round(x * 100) / 100).toString());
let wrapped = false, names = null, lastOffers = null, n = 0;
const tally = {};
const PATCHES = [
  ['none', () => () => {}],
  ['worth', (pol) => { const v = pol.p.maxW; pol.p.maxW = 1e6; return () => { pol.p.maxW = v; }; }],
  ['soleBuffer', (pol) => { const v = pol.p.overHumanCap; pol.p.overHumanCap = 0; return () => { pol.p.overHumanCap = v; }; }],
  ['crowded', (pol) => { const v = pol.p.crowdedHardCap; pol.p.crowdedHardCap = 0; return () => { pol.p.crowdedHardCap = v; }; }],
  ['absorb', (pol) => { const v = pol.p.absorbMode; pol.p.absorbMode = 0; return () => { pol.p.absorbMode = v; }; }],
  ['chunk', (pol) => { const v = pol.p.chunk; pol.p.chunk = 0; return () => { pol.p.chunk = v; }; }],
  ['pulseMin', (pol) => { const v = pol.p.pulseMinShare, m = pol.minCmd; pol.p.pulseMinShare = 0; pol.minCmd = () => 0; return () => { pol.p.pulseMinShare = v; if (Object.prototype.hasOwnProperty.call(pol, 'minCmd')) { if (m === Object.getPrototypeOf(pol).minCmd) delete pol.minCmd; else pol.minCmd = m; } }; }],
  ['safe', (pol) => { const had = Object.prototype.hasOwnProperty.call(pol, 'safeAt'), v = pol.safeAt; pol.safeAt = () => 0; return () => { if (had) pol.safeAt = v; else delete pol.safeAt; }; }],
  ['hold', (pol) => { const a = pol.p.hold, b2 = pol.p.overHumanKeep; pol.p.hold = 0; pol.p.overHumanKeep = 0; return () => { pol.p.hold = a; pol.p.overHumanKeep = b2; }; }],
];

const PATCH_BY = Object.fromEntries(PATCHES);
const ALL_GATES = ['worth', 'soleBuffer', 'crowded', 'safe', 'hold', 'chunk', 'pulseMin'];
const NO_PRICE = ['soleBuffer', 'crowded', 'safe', 'hold', 'chunk', 'pulseMin'];
function* subsets(pool, size, start = 0, acc = []) {
  if (acc.length === size) { yield acc.slice(); return; }
  for (let i = start; i < pool.length; i++) { acc.push(pool[i]); yield* subsets(pool, size, i + 1, acc); acc.pop(); }
}

shadow(mid, {
  quiet: true,
  until: t1 + 1,
  trace: (g, b, pol, ctx) => {
    if (b.bot !== bot || wrapped) return;
    wrapped = true;
    names = ctx.names;
    const origOffers = pol.offers;
    pol.offers = function (gg) { const r = origOffers.call(this, gg); lastOffers = r; return r; };
    const origBuy = pol.buyLand;
    pol.buyLand = function (gg) {
      lastOffers = null;
      const r = origBuy.call(this, gg);
      const t = gg.t;
      if (t < t0 || t > t1) return r;
      const me = this.me, B = gg.bal[me], L = Math.max(1, gg.terr[me]);
      const offers = lastOffers || [];
      if (r || !offers.length) return r;
      if (n++ % every !== 0) return r;
      const dry = (mk) => {
        let hit = null;
        const hadSend = Object.prototype.hasOwnProperty.call(this, 'send'), send0 = this.send;
        const sb0 = this.sb, sbT0 = this.sbT, lo = lastOffers;
        const gk = ['boatTo', 'boat', 'attack', 'donate'];
        const gs = gk.map((x) => gg[x]);
        const hadG = gk.map((x) => Object.prototype.hasOwnProperty.call(gg, x));
        this.send = (g2, q, a, h) => { if (!hit) hit = { q, x: h !== undefined ? h : a }; return false; };
        gg.boatTo = () => { if (!hit) hit = { q: -3, x: 0 }; return false; };
        gg.boat = () => { if (!hit) hit = { q: -3, x: 0 }; return false; };
        gg.attack = () => false; gg.donate = () => false;
        this.sbT = -1;
        const undo = mk(this);
        try { origBuy.call(this, gg); } catch { hit = null; }
        undo();
        if (hadSend) this.send = send0; else delete this.send;
        gk.forEach((x, i) => { if (hadG[i]) gg[x] = gs[i]; else delete gg[x]; });
        this.sb = sb0; this.sbT = sbT0; lastOffers = lo;
        return hit;
      };
      const singles = [];
      for (const [name, mk] of PATCHES) { const h = dry(mk); if (h) singles.push([name, h]); if (name === 'none' && h) break; }
      const tryCombo = (combo) => dry((pol) => { const undos = combo.map((nm) => PATCH_BY[nm](pol)); return () => { for (let i = undos.length - 1; i >= 0; i--) undos[i](); }; });
      const firstCombo = (pool) => {
        for (let size = 2; size <= pool.length; size++) for (const combo of subsets(pool, size)) { const h = tryCombo(combo); if (h) return [combo, h]; }
        return null;
      };
      let cls = '-', hit = null, alt = '';
      if (singles.length) {
        cls = singles.map((x) => x[0]).join(','); hit = singles[0][1];
        // 价格线之外还有没有别的放法：只在「worth 单独能放」而别的单项都不行时才查
        if (cls === 'worth') { const c = firstCombo(NO_PRICE); alt = c ? ` | 不动价格线：${c[0].join('+')}（想发 ${k(c[1].x)}）` : ' | 不动价格线：放不出来'; }
      } else {
        const c = firstCombo(ALL_GATES);
        if (c) { cls = '组合:' + c[0].join('+'); hit = c[1]; }
      }
      tally[cls] = (tally[cls] || 0) + 1;
      const P = this.p, dMe = B / L;
      let worth = NaN, over = false;
      try {
        const dMed = this.otherHumanMedDens(gg);
        worth = P.maxW * this.winRatio(t) * (dMed !== null && t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe);
        over = P.surplus > 0 && B > 100 * L;
      } catch { /* 留 NaN */ }
      const o = offers[0];
      const flags = ['person', 'onMe', 'isCrowdedHard', 'nearCollapse', 'bleeding', 'pulseMode', 'isDoorSea', 'isAgg'].filter((f) => o[f]).join('/');
      const who = o.q >= gg.humans ? `AI${o.q}` : `${(names[o.q] || '').slice(0, 12)}#${o.q}`;
      console.log(`t=${t} B=${k(B)} L=${L} 密=${dMe.toFixed(1)} | 最便宜 ${who} c=${(+o.c).toFixed(1)} need=${k(o.need)} newNbs=${o.newNbs ?? '-'} inAtk=${k(o.inAtk ?? 0)} [${flags}] | worth=${worth.toFixed(1)} over=${over ? 1 : 0} 真人邻居数=${this.nb.filter((p) => gg.alive[p] && this.person(gg, p)).length} | 拦在：${cls}${hit && hit.q >= 0 ? `（去掉后想发 ${k(hit.x)}）` : ''}${alt}`);
      return r;
    };
  },
});
console.log('合计', JSON.stringify(tally));
