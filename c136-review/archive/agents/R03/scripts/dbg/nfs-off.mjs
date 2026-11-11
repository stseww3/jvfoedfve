// 调试：isNoFullSend 这个标志对 Policy.buyLand 自己的闸有多大影响。
// buyLand L5428-5438 的「围城收缩」闸（isSiegeShrink）要求 !this.isNoFullSend；标志被翻成 true 之后这道闸不再生效。
// 做法：在每个决策拍真调用 buyLand 之前，先原样空跑一遍（send 换成记录器，不发令），再把 isNoFullSend 临时改成 false 空跑一遍，
//       两遍走到的 send（目标、兵数）不同就打印；跑完恢复现场。只改实例上的临时值，不改策略文件。
// 用法：node dbg/nfs-off.mjs <mid> <bot> <t0> <t1> [--all]     --all：两遍相同的出手拍也打印
// 每行：拍、余额/地/密度、引擎峰值 g.peak、地/峰值、在线真人数 | 原样：目标 兵 | 标志关掉：目标 兵（或「不出手」）| 最便宜报价 c / worth
import { shadow } from '../shadow.mjs';

const args = process.argv.slice(2);
const [mid, bot, t0s, t1s] = args;
const t0 = +t0s, t1 = +t1s;
const all = args.includes('--all');
const k = (x) => (typeof x !== 'number' ? String(x) : Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : Math.abs(x) >= 1e3 ? (x / 1e3).toFixed(1) + 'k' : (Math.round(x * 100) / 100).toString());
let wrapped = false, names = null, lastOffers = null;
const tally = { 决策拍: 0, 原样出手: 0, 关掉后不出手: 0, 关掉后改了目标或兵数: 0, 原样不出手而关掉后出手: 0 };
let savedTroops = 0;

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
      const t = gg.t;
      if (t < t0 || t > t1) return origBuy.call(this, gg);
      const me = this.me, B = gg.bal[me], L = Math.max(1, gg.terr[me]);
      const dry = (nfs) => {
        let hit = null;
        const hadSend = Object.prototype.hasOwnProperty.call(this, 'send'), send0 = this.send;
        const sb0 = this.sb, sbT0 = this.sbT, lo = lastOffers, nfs0 = this.isNoFullSend, cmds0 = this.cmds, boats0 = this.boats;
        const gk = ['boatTo', 'boat', 'attack', 'donate'];
        const gs = gk.map((x) => gg[x]);
        const hadG = gk.map((x) => Object.prototype.hasOwnProperty.call(gg, x));
        this.send = (g2, q, a, h) => { if (!hit) hit = { q, x: a }; return false; };
        gg.boatTo = () => { if (!hit) hit = { q: -3, x: 0 }; return false; };
        gg.boat = () => { if (!hit) hit = { q: -3, x: 0 }; return false; };
        gg.attack = () => false; gg.donate = () => false;
        this.sbT = -1;
        this.isNoFullSend = nfs;
        let offs = null;
        try { origBuy.call(this, gg); offs = lastOffers; } catch { hit = null; }
        this.isNoFullSend = nfs0;
        if (hadSend) this.send = send0; else delete this.send;
        gk.forEach((x, i) => { if (hadG[i]) gg[x] = gs[i]; else delete gg[x]; });
        this.sb = sb0; this.sbT = sbT0; lastOffers = lo; this.cmds = cmds0; this.boats = boats0;
        return { hit, offs };
      };
      const a = dry(this.isNoFullSend), c = dry(false);
      tally.决策拍++;
      const same = (!a.hit && !c.hit) || (a.hit && c.hit && a.hit.q === c.hit.q && Math.abs(a.hit.x - c.hit.x) < 1);
      if (a.hit) tally.原样出手++;
      if (a.hit && !c.hit) { tally.关掉后不出手++; savedTroops += a.hit.x; }
      else if (a.hit && c.hit && !same) tally.关掉后改了目标或兵数++;
      else if (!a.hit && c.hit) tally.原样不出手而关掉后出手++;
      if ((!same || (all && a.hit)) && this.isNoFullSend) {
        const who = (q) => (q === -3 ? '发船' : q >= gg.humans ? (q === 512 ? '中立' : `AI${q}`) : `${(names[q] || '').replace('[APEX] ', '').slice(0, 12)}#${q}`);
        const P = this.p, dMe = B / L;
        let worth = NaN;
        try {
          const dMed = this.otherHumanMedDens(gg);
          worth = P.maxW * this.winRatio(t) * (dMed !== null && t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe);
        } catch { /* 留 NaN */ }
        const o = (a.offs || [])[0];
        const peak = gg.peak ? gg.peak[me] : NaN;
        console.log(`t=${t} B=${k(B)} L=${L} 密=${dMe.toFixed(1)} 峰值=${peak} 地/峰=${(L / Math.max(1, peak)).toFixed(3)} 在线真人=${this.livingHumanCount(gg)} nfs=${this.isNoFullSend ? 1 : 0}`
          + ` | 原样：${a.hit ? `${who(a.hit.q)} ${k(a.hit.x)}` : '不出手'} | 标志关掉：${c.hit ? `${who(c.hit.q)} ${k(c.hit.x)}` : '不出手'}`
          + (o ? ` | 最便宜 ${who(o.q)} c=${(+o.c).toFixed(1)} worth=${worth.toFixed(1)} B/(100L)=${(B / (100 * L)).toFixed(3)}` : ''));
      }
      return origBuy.call(this, gg);
    };
  },
});
console.log('合计', JSON.stringify(tally), '关掉后不出手的那些拍原样想发的兵合计', k(savedTroops));
