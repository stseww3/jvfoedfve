#!/usr/bin/env node
// freeze-scan.mjs — 开局阶段（t < dpEnd）「贴着内置 AI 却不买地」的机械计数。
//
// 源码依据（Vb：v27-team-c116-vb.js；Va/Vc 同构）：
//   Style.pickTarget L1144-1177：对每个邻居 avail = bal - floorFor(...)；avail <= minShare*bal 或 avail < minCmd 就跳过
//   V13.floorFor0   L2233-2237：t < dpEnd 且目标不是真人 → max(winFloor, peopleFloor)
//   Policy.winFloor L4562-4570：max(botPx*L/(winR*t), dpKeep, safeFinite)
//   V13.safeFinite  L2500-2510：对每个接壤的内置 AI，取它「除我之外最弱的邻居」的 余额+在途兵（Strategy.threatOf L417-443），
//                              再对所有 AI 取最大 —— 我的余额要高过这个数，AI 才不会挑我打。
// 当那个「最弱的别的邻居」是余额相近的队友时，余额低的一方 avail < 0，一条买地指令都发不出；余额高的一方只能花差额。
//
// 用法：node freeze-scan.mjs <mid> [--from 600] [--to 1500] [--quiet]
// 产出：out/cache/<mid>-freeze.json；标准输出一张逐号表。
// 每个决策拍（pickTarget 被调用的拍）归一类：
//   target   选到了目标（发令）
//   neutral  还有中立地可扩（走 expandNeutral，不算冻结）
//   noai     没有内置 AI 邻居
//   frozen   有 AI 邻居、没选到目标，且 safeFinite >= (1-minSend)*余额  ← 本脚本要数的
//   other    有 AI 邻居、没选到目标，原因不是 safeFinite（价格、槽位、在途已够、winFloor 第一项……）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { shadow } from './shadow.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', 'cache');
const NEUTRAL = 512, P_INNER = 16, T_LAND = 1;

export function freezeScan(mid, opts = {}) {
  const from = opts.from ?? 600, to = opts.to ?? 1500;
  const from2 = opts.from2 ?? to, to2 = opts.to2 ?? Infinity;
  const per = {}; // bot -> { rows: [[t, cls, B, L, sb, bindQ, bindO, bindKind, nAi, amountPct]] }
  const per2 = {}; // bot -> { rows: [[t, cls, B, L, tgt, tgtPerson, x, c, need, sb, bindQ, bindO, bindKind]] }
  const wrapped = new Set();
  let names = null, squadIds = null, teamOf = null;

  const bindOf = (g, pol, skip = -1) => {
    // safeFinite 的 argmax：返回 { sb, q, o }
    const me = pol.me;
    let best = { sb: 0, q: -1, o: -1 };
    for (const q of pol.nb) {
      if (q === skip || !g.alive[q] || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
      const B = g.border[q], px = g.px, own = g.own, d = g.dir4;
      const busyNeutral = g.hasAttack(q, NEUTRAL);
      let minOther = Infinity, arg = -1, neutral = false;
      const seen = new Set();
      const n = B.length, step = n > 1024 ? Math.ceil(n / 1024) : 1;
      for (let i = n - 1; i >= 0 && !neutral; i -= step) {
        for (let k = 0; k < 4; k++) {
          const c = B[i] + d[k], v = px[c];
          if (v === T_LAND) { if (!busyNeutral) { neutral = true; break; } continue; }
          if (v < P_INNER) continue;
          const o = own[c];
          if (o === q || o === me || seen.has(o)) continue;
          seen.add(o);
          if (g.hasAttack(q, o)) continue;
          const s = g.bal[o] + g.attackTroopsOn(o, q);
          if (s < minOther) { minOther = s; arg = o; }
        }
      }
      if (neutral || !Number.isFinite(minOther)) continue;
      const need = minOther - g.attackTroopsOn(me, q);
      if (need > best.sb) best = { sb: need, q, o: arg };
    }
    return best;
  };

  const kindOf = (g, me, o) => {
    if (o < 0) return '-';
    if (o >= g.humans) return 'ai';
    if (squadIds.has(o)) return 'squad';
    if (g.isTeammate(me, o)) return 'mate';
    return 'enemy';
  };

  const rep = shadow(mid, { until: opts.post === false ? to + 1 : (Number.isFinite(to2) ? to2 + 1 : undefined), quiet: true, trace: (g, b, pol, ctx) => {
    if (!names) { names = ctx.names; squadIds = new Set(Object.values(ctx.squad).map((s) => s.id).filter((x) => x >= 0)); teamOf = ctx; }
    if (wrapped.has(b.bot)) return;
    wrapped.add(b.bot);
    per[b.bot] = { me: b.me, rows: [] };
    per2[b.bot] = { me: b.me, rows: [], lastT: -1 };
    // ---- 第二段（t >= coreFrom=1500）：Policy.buyLand 没出手的决策拍，按「去掉哪一项留底就会出手」分类 ----
    //   Policy.buyLand L5414 safe = this.safeAt(g, q)；L5444 keep = max(keep, safe)；L5446 avail = B - fee - keep
    //   V13.safeAt L2728-2738：safeFinite(g, 被买的 AI 跳过) 与 killKeep/dpKeep/peopleSafe 取大
    //   sent        buyLand 发了令
    //   slotTaken   同一拍前面已有一条指令被受理（页面每拍只收 1 条），buyLand 发什么都会被拒
    //   noOffer     没有任何陆上邻居（被围）
    //   blocked     buyLand 走到了 send，但被 Policy.send 的守卫或适配层拒掉
    //   frozenSF    只把 safeFinite 当 0 就会出手（卡在「接壤 AI 的最弱别的邻居」）
    //   frozenKeep  把整个 safeAt 当 0 才会出手（卡在对真人邻居的留底 killKeep/dpKeep/peopleSafe）
    //   priced      去掉全部留底也不出手（报价 ≥ worth、在途已够、数额太小……）
    const origBuy = pol.buyLand;
    if (typeof origBuy === 'function' && opts.post !== false) {
      pol.buyLand = function (gg) {
        const lastCmd0 = b.lastCmdT;
        const r = origBuy.call(this, gg);
        const t = gg.t;
        if (t < from2 || t >= to2 || per2[b.bot].lastT === t) return r;
        per2[b.bot].lastT = t;
        const me = this.me, B = gg.bal[me], L = gg.terr[me];
        const offers = b.lastOffers || [];
        let cls, tgt = -1, tp = 0, x = 0, c = -1, need = -1, sb = 0, bq = -1, bo = -1, bk = '-';
        const dry = (patch) => {
          let hit = null;
          const has = (k) => Object.prototype.hasOwnProperty.call(this, k);
          const keys = ['send', 'safeFinite', 'safeAt'];
          const saved = keys.map((k) => (has(k) ? this[k] : undefined));
          const sb0 = this.sb, sbT0 = this.sbT, lo = b.lastOffers;
          const gk = ['boatTo', 'boat', 'attack', 'donate'];
          const gs = gk.map((k) => gg[k]);
          this.send = (g2, q, a, h) => { if (!hit) hit = { q, x: h !== undefined ? h : a }; return false; };
          if (patch === 'sf') this.safeFinite = () => 0;
          if (patch === 'all') this.safeAt = () => 0;
          this.sbT = -1;
          gg.boatTo = (pct, landPix) => { if (!hit) hit = { q: -3, x: 0 }; return false; };
          gg.boat = () => { if (!hit) hit = { q: -3, x: 0 }; return false; };
          gg.attack = () => false; gg.donate = () => false;
          try { origBuy.call(this, gg); } catch { hit = null; }
          keys.forEach((k, i) => { if (saved[i] === undefined) delete this[k]; else this[k] = saved[i]; });
          gk.forEach((k, i) => { gg[k] = gs[i]; });
          this.sb = sb0; this.sbT = sbT0; b.lastOffers = lo;
          return hit;
        };
        if (r) cls = 'sent';
        else if (lastCmd0 === t) cls = 'slotTaken';
        else if (!offers.length) cls = 'noOffer';
        else {
          let h = dry('none');
          if (h) cls = 'blocked';
          else if ((h = dry('sf'))) cls = 'frozenSF';
          else if ((h = dry('all'))) cls = 'frozenKeep';
          else {
            // 去掉全部留底也不出手：再分三种（Policy.buyLand L5346-5359 的 worth/over/cheap 照原式重算）
            //   pricedHigh  最便宜的报价 ≥ worth 且没过软上限 → L5359 直接 break
            //   pulseWait   有报价进了循环，但我对它已有在途兵（脉冲间隔 L5575/L5589/L5595 的 curAtk 门槛）
            //   pricedOther 其余（拥挤/唯一缓冲/数额太小/吸收模式等分支）
            const P = this.p, dMe = B / Math.max(1, L);
            let worth = Infinity, over = false, cheap = 0;
            try {
              const dMed = this.otherHumanMedDens(gg);
              const m = P.maxW * this.winRatio(t);
              worth = m * (dMed !== null && t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe);
              over = P.surplus > 0 && B > 100 * L;
              cheap = P.growth > 0 ? 0.1 / this.baseRate(gg) : 0;
            } catch { /* 留默认值 */ }
            const o0 = offers[0];
            if (o0.c >= worth && o0.c >= cheap && !over) cls = 'pricedHigh';
            else if (offers.some((z) => (z.c < worth || z.c < cheap || over) && gg.attackTroopsOn(me, z.q) > 0)) cls = 'pulseWait';
            else cls = 'pricedOther';
            tgt = o0.q; tp = o0.person ? 1 : 0; c = +(+o0.c).toFixed(2); need = Math.round(o0.need); sb = Math.round(100 * worth) / 100;
          }
          if (h && h.q >= 0) {
            tgt = h.q; tp = this.person(gg, h.q) ? 1 : 0; x = Math.round(h.x);
            const o = offers.find((z) => z.q === h.q);
            if (o) { c = +(+o.c).toFixed(2); need = Math.round(o.need); }
          } else if (h) tgt = h.q;
          if (cls === 'frozenSF') {
            const bd = bindOf(gg, this, this.p.botSkip > 0 && tgt >= 0 && !tp ? tgt : -1);
            sb = Math.round(bd.sb); bq = bd.q; bo = bd.o; bk = kindOf(gg, me, bd.o);
          }
        }
        per2[b.bot].rows.push([t, cls, B, L, tgt, tp, x, c, need, sb, bq, bo, bk]);
        return r;
      };
    }
    const orig = pol.pickTarget;
    pol.pickTarget = function (gg, floorAt, maxCost) {
      const r = orig.call(this, gg, floorAt, maxCost);
      if (gg.t < from || gg.t >= to) return r;
      const me = this.me, B = gg.bal[me], L = gg.terr[me];
      let nAi = 0;
      for (const q of this.nb) if (gg.alive[q] && gg.terr[q] > 0 && gg.isBot(q)) nAi++;
      let cls, sb = 0, bq = -1, bo = -1, bk = '-', pct = -1, cfq = -2;
      if (r) { cls = 'target'; pct = Math.round((1000 * r.amount) / Math.max(1, B)) / 10; }
      else if (this.neutral > 0) cls = 'neutral';
      else if (nAi === 0) cls = 'noai';
      else {
        const bd = bindOf(gg, this);
        sb = Math.round(bd.sb); bq = bd.q; bo = bd.o; bk = kindOf(gg, me, bd.o);
        cls = bd.sb >= (1 - this.p.minSend) * B ? 'frozen' : 'other';
        if (cls === 'frozen') {
          // 反事实：同一拍、同一局面，只把 safeFinite 这一项当成 0，pickTarget 会不会选到目标、想发多少
          const sf = this.safeFinite, sb0 = this.sb, sbT0 = this.sbT;
          this.safeFinite = () => 0;
          this.sbT = -1;
          let cf = null;
          try { cf = orig.call(this, gg, floorAt, maxCost); } catch { cf = null; }
          delete this.safeFinite;
          if (this.safeFinite !== sf) this.safeFinite = sf;
          this.sb = sb0; this.sbT = sbT0;
          if (cf) pct = Math.round((1000 * cf.amount) / Math.max(1, B)) / 10;
          cfq = cf ? cf.q : -1;
        }
      }
      per[b.bot].rows.push([gg.t, cls, B, L, sb, bq, bo, bk, nAi, pct, cfq]);
      return r;
    };
  } });

  const out = { matchId: mid, from, to, strategy: rep.strategy, bots: {}, team: {} };
  const tot = { ticks: 0, target: 0, neutral: 0, noai: 0, frozen: 0, other: 0, frozenBy: { squad: 0, mate: 0, enemy: 0, ai: 0 }, frozenBalTicks: 0, frozenWould: 0 };
  for (const [bot, v] of Object.entries(per)) {
    const s = { me: v.me, ticks: v.rows.length, target: 0, neutral: 0, noai: 0, frozen: 0, other: 0, frozenBy: { squad: 0, mate: 0, enemy: 0, ai: 0 }, frozenBalTicks: 0, frozenWould: 0, frozenWouldPctSum: 0, minPctTargets: 0, firstFrozen: null, lastFrozen: null, binders: {}, B0: null, B1: null, L0: null, L1: null, spans: [] };
    let span = null;
    for (const [t, cls, B, L, sb, bq, bo, bk, nAi, pct, cfq] of v.rows) {
      s[cls]++;
      if (s.B0 === null) { s.B0 = B; s.L0 = L; }
      s.B1 = B; s.L1 = L;
      if (cls === 'target' && pct >= 0 && pct <= 4.8) s.minPctTargets++;
      if (cls === 'frozen') {
        if (cfq >= 0) { s.frozenWould++; s.frozenWouldPctSum += pct; }
        s.frozenBy[bk] = (s.frozenBy[bk] || 0) + 1;
        s.frozenBalTicks += B;
        if (s.firstFrozen === null) s.firstFrozen = t;
        s.lastFrozen = t;
        const nm = bo >= 0 ? (bo >= (rep.resim?.H ?? 1e9) ? `AI${bo}` : `${String(names[bo] || '').replace(/^\[[^\]]*\]\s*/, '').slice(0, 10)}#${bo}`) : '-';
        s.binders[nm] = (s.binders[nm] || 0) + 1;
        if (span && t - span.t1 <= 10) { span.t1 = t; span.B1 = B; span.n++; }
        else { span = { t0: t, t1: t, B0: B, B1: B, L0: L, n: 1, binder: nm, sb0: sb }; s.spans.push(span); }
      }
    }
    s.spans = s.spans.filter((x) => x.n >= 6).slice(0, 12);
    out.bots[bot] = s;
    for (const k of ['ticks', 'target', 'neutral', 'noai', 'frozen', 'other', 'frozenBalTicks', 'frozenWould']) tot[k] += s[k];
    for (const k of Object.keys(s.frozenBy)) tot.frozenBy[k] = (tot.frozenBy[k] || 0) + s.frozenBy[k];
  }
  out.team = tot;

  // ---- 第二段汇总 ----
  const H = rep.resim?.H ?? 1e9;
  const nmOf = (p) => (p < 0 ? '-' : p >= H ? `AI${p}` : `${String(names[p] || '').replace(/^\[[^\]]*\]\s*/, '').slice(0, 10)}#${p}`);
  const CLS = ['sent', 'slotTaken', 'noOffer', 'blocked', 'frozenSF', 'frozenKeep', 'pricedHigh', 'pulseWait', 'pricedOther'];
  const zero = () => ({ ticks: 0, ...Object.fromEntries(CLS.map((c) => [c, 0])), frozenSFBy: { squad: 0, mate: 0, enemy: 0, ai: 0 }, frozenSFBotTarget: 0, frozenSFPersonTarget: 0, frozenSFBalTicks: 0, frozenKeepBalTicks: 0, noOfferBalTicks: 0, pricedHighBalTicks: 0 });
  const post = { from: from2, to: Number.isFinite(to2) ? to2 : null, team: zero(), bots: {} };
  for (const [bot, v] of Object.entries(per2)) {
    const s = { me: v.me, ...zero(), binders: {}, spans: [], keepSpans: [], noOfferSpans: [], highSpans: [], t0: v.rows.length ? v.rows[0][0] : null, t1: v.rows.length ? v.rows[v.rows.length - 1][0] : null };
    let sp = null, ks = null, ns = null, hs = null;
    for (const [t, cls, B, L, tgt, tp, x, c, need, sb, bq, bo, bk] of v.rows) {
      s.ticks++; s[cls]++;
      if (cls === 'frozenSF') {
        s.frozenSFBy[bk] = (s.frozenSFBy[bk] || 0) + 1;
        if (tp) s.frozenSFPersonTarget++; else s.frozenSFBotTarget++;
        s.frozenSFBalTicks += B;
        const nm = nmOf(bo);
        s.binders[nm] = (s.binders[nm] || 0) + 1;
        if (sp && t - sp.t1 <= 10) { sp.t1 = t; sp.B1 = B; sp.n++; sp.binders[nm] = (sp.binders[nm] || 0) + 1; }
        else { sp = { t0: t, t1: t, n: 1, B0: B, B1: B, L0: L, target: nmOf(tgt), person: tp, c, need, x, sb0: sb, binder: nm, binders: { [nm]: 1 } }; s.spans.push(sp); }
      } else if (cls === 'frozenKeep') {
        s.frozenKeepBalTicks += B;
        if (ks && t - ks.t1 <= 10) { ks.t1 = t; ks.B1 = B; ks.n++; }
        else { ks = { t0: t, t1: t, n: 1, B0: B, B1: B, L0: L, target: nmOf(tgt), person: tp, c, need, x }; s.keepSpans.push(ks); }
      } else if (cls === 'noOffer') {
        s.noOfferBalTicks += B;
        if (ns && t - ns.t1 <= 10) { ns.t1 = t; ns.B1 = B; ns.n++; }
        else { ns = { t0: t, t1: t, n: 1, B0: B, B1: B, L0: L }; s.noOfferSpans.push(ns); }
      } else if (cls === 'pricedHigh') {
        s.pricedHighBalTicks += B;
        if (hs && t - hs.t1 <= 10) { hs.t1 = t; hs.B1 = B; hs.n++; hs.c1 = c; hs.w1 = sb; hs.target1 = nmOf(tgt); }
        else { hs = { t0: t, t1: t, n: 1, B0: B, B1: B, L0: L, target: nmOf(tgt), person: tp, c0: c, w0: sb, c1: c, w1: sb, target1: nmOf(tgt) }; s.highSpans.push(hs); }
      }
    }
    s.spans = s.spans.filter((z) => z.n >= 4);
    s.keepSpans = s.keepSpans.filter((z) => z.n >= 6);
    s.noOfferSpans = s.noOfferSpans.filter((z) => z.n >= 12);
    s.highSpans = s.highSpans.filter((z) => z.n >= 20);
    post.bots[bot] = s;
    for (const k of ['ticks', ...CLS, 'frozenSFBotTarget', 'frozenSFPersonTarget', 'frozenSFBalTicks', 'frozenKeepBalTicks', 'noOfferBalTicks', 'pricedHighBalTicks']) post.team[k] += s[k];
    for (const k of Object.keys(s.frozenSFBy)) post.team.frozenSFBy[k] = (post.team.frozenSFBy[k] || 0) + s.frozenSFBy[k];
  }
  out.post = post;
  return out;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const mid = args[0];
  const opt = (k, d) => (args.includes(`--${k}`) ? +args[args.indexOf(`--${k}`) + 1] : d);
  const r = freezeScan(mid, { from: opt('from', 600), to: opt('to', 1500), post: !args.includes('--no-post') });
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, `${mid}-freeze.json`), JSON.stringify(r));
  const k = (x) => (x >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : x >= 1e4 ? Math.round(x / 1e3) + 'k' : String(Math.round(x)));
  const T = r.team;
  console.log(`${mid} 开局买 AI 地的决策拍分类（t∈[${r.from},${r.to})，${r.strategy}）：共 ${T.ticks} 拍 → 选到目标 ${T.target}，扩中立 ${T.neutral}，无 AI 邻居 ${T.noai}，被 safeFinite 冻结 ${T.frozen}（卡在：编队友 ${T.frozenBy.squad}，路人队友 ${T.frozenBy.mate}，敌方真人 ${T.frozenBy.enemy}，AI ${T.frozenBy.ai}；其中去掉 safeFinite 这一项就能选到目标的 ${T.frozenWould}），其它没选到 ${T.other}`);
  if (!args.includes('--quiet')) {
    for (const [bot, s] of Object.entries(r.bots)) {
      const bind = Object.entries(s.binders).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([n, c]) => `${n}×${c}`).join(' ');
      console.log(`  ${bot.padEnd(7)} 拍 ${String(s.ticks).padStart(3)} 目标 ${String(s.target).padStart(3)}（其中最小额 ${String(s.minPctTargets).padStart(3)}） 中立 ${String(s.neutral).padStart(3)} 无AI ${String(s.noai).padStart(3)} 冻结 ${String(s.frozen).padStart(3)}（反事实可出手 ${String(s.frozenWould).padStart(3)}，平均想发余额的 ${s.frozenWould ? (s.frozenWouldPctSum / s.frozenWould).toFixed(0) : '-'}%） 其它 ${String(s.other).padStart(3)} | 兵 ${k(s.B0 ?? 0)}→${k(s.B1 ?? 0)} 地 ${s.L0}→${s.L1} | 冻结 ${s.firstFrozen ?? '-'}~${s.lastFrozen ?? '-'} 卡在 ${bind || '-'}`);
      for (const sp of s.spans.slice(0, 4)) console.log(`           连续冻结 ${sp.t0}~${sp.t1}（${sp.n} 个决策拍）兵 ${k(sp.B0)}→${k(sp.B1)} 地 ${sp.L0}，起点门槛 ${k(sp.sb0)}（${sp.binder}）`);
    }
  }
  const Q = r.post;
  if (Q && Q.team.ticks) {
    const U = Q.team;
    console.log(`${mid} 中后期 buyLand 决策拍分类（t≥${Q.from}）：共 ${U.ticks} 拍 → 出手 ${U.sent}，同拍名额已被占 ${U.slotTaken}，没有陆上邻居 ${U.noOffer}（这些拍上的平均余额 ${k(U.noOfferBalTicks / Math.max(1, U.noOffer))}），走到 send 被拒 ${U.blocked}，卡在 safeFinite ${U.frozenSF}（目标是 AI/空壳 ${U.frozenSFBotTarget}、真人 ${U.frozenSFPersonTarget}；卡在：编队友 ${U.frozenSFBy.squad}，路人队友 ${U.frozenSFBy.mate}，敌方真人 ${U.frozenSFBy.enemy}，AI ${U.frozenSFBy.ai}），卡在对真人邻居的留底 ${U.frozenKeep}（平均余额 ${k(U.frozenKeepBalTicks / Math.max(1, U.frozenKeep))}），最便宜的报价也高于 worth ${U.pricedHigh}，在等上一笔在途兵 ${U.pulseWait}，其它不出手 ${U.pricedOther}`);
    if (!args.includes('--quiet')) {
      for (const [bot, s] of Object.entries(Q.bots)) {
        if (!s.ticks) continue;
        const bind = Object.entries(s.binders).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([n, c]) => `${n}×${c}`).join(' ');
        console.log(`  ${bot.padEnd(7)} ${s.t0}~${s.t1} 拍 ${String(s.ticks).padStart(3)}：出手 ${s.sent} 名额被占 ${s.slotTaken} 被围 ${s.noOffer} send被拒 ${s.blocked} 卡safeFinite ${s.frozenSF}（${bind || '-'}） 卡真人留底 ${s.frozenKeep} 报价高于worth ${s.pricedHigh} 等在途 ${s.pulseWait} 其它 ${s.pricedOther}`);
        for (const sp of s.highSpans.slice(0, 6)) console.log(`           报价高于 worth ${sp.t0}~${sp.t1}（${sp.n} 拍）兵 ${k(sp.B0)}→${k(sp.B1)} 地 ${sp.L0}：最便宜 ${sp.target}${sp.person ? '（真人）' : ''} c=${sp.c0} 对 worth=${sp.w0} → 末 ${sp.target1} c=${sp.c1} 对 worth=${sp.w1}`);
        for (const sp of s.spans.slice(0, 6)) console.log(`           卡 safeFinite ${sp.t0}~${sp.t1}（${sp.n} 拍）兵 ${k(sp.B0)}→${k(sp.B1)} 地 ${sp.L0}：想买 ${sp.target}${sp.person ? '（真人）' : ''} c=${sp.c} need=${k(sp.need)} 想发 ${k(sp.x)}；门槛 ${k(sp.sb0)} 来自 ${Object.entries(sp.binders).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([n, c]) => `${n}×${c}`).join(' ')}`);
        for (const sp of s.keepSpans.slice(0, 5)) console.log(`           卡真人留底 ${sp.t0}~${sp.t1}（${sp.n} 拍）兵 ${k(sp.B0)}→${k(sp.B1)} 地 ${sp.L0}：想买 ${sp.target}${sp.person ? '（真人）' : ''} c=${sp.c} need=${k(sp.need)} 想发 ${k(sp.x)}`);
        for (const sp of s.noOfferSpans.slice(0, 5)) console.log(`           被围 ${sp.t0}~${sp.t1}（${sp.n} 拍）兵 ${k(sp.B0)}→${k(sp.B1)} 地 ${sp.L0}`);
      }
    }
  }
}
