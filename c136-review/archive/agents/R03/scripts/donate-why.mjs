#!/usr/bin/env node
// donate-why.mjs — Policy.tryDonateToTeammate 每次被调用时「卡在哪一道闸」的机械计数。
//
// 做法：影子重放里给每个号的 tryDonateToTeammate 包一层；每次真调用之前，用下面这份照源码逐行抄写的判定
// （Vb：v27-team-c116-vb.js L4325-4518）先算一遍「会卡在哪 / 会捐给谁、哪一类、pct 多少」，再和真调用的结果对账。
// 对账一致率打印在最后；不一致的拍单列，结论只用一致的部分。
//
// 闸的名字（按源码顺序）：
//   t<1500 / terr<1200 / bal<30000 / cooldown12        L4329
//   slotPhase   每 25 拍只有 5 拍轮到自己              L4330-4331
//   busy        自己正被真人打，或自己对真人的在途兵 > 8% 余额   L4343
//   boss        走了给 boss 的分支                      L4358-4375
//   对每个候选受捐人（只有编队号 / boss，L4414）：
//     terrMin / quit / allyDense（受捐人密度 ≥ 142（被围）或 115）  L4414-4418
//     noFront   受捐人没有敌方邻居、也不在交战               L4453
//     doomed    L4455-4456
//     A:dMe / A:floor / A:gap     紧急防御档（受捐人正被打）不满足   L4463-4466
//     B:dMe / B:allyD / B:floor / B:gap  产出/进攻档不满足          L4479-4481
//   pct<180     选到了人，但能给的比例 < 180/1024              L4506
//   sent        调了 g.donate
// 另外单列一张表：轮到自己且不忙的调用里，「正在被真人打的候选受捐人」被判成什么。doomed 按 L4455 的两个分支分开记
// （x1.65 / small），因滩头豁免（L4451）而没被判 doomed 的记成「ok(滩头豁免:…)」等。
//
// 用法：
//   node donate-why.mjs <mid>                         全队全程计数，写 out/cache/<mid>-donwhy.json
//   node donate-why.mjs <mid> --bot sora_w --from 6600 --to 7500 [--all]   逐次调用明细（--all 连 slotPhase 也打印）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { shadow } from './shadow.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', 'cache');

export function explainDonate(pol, g, emergencyOnly = false) {
  const me = pol.me;
  const win = globalThis.window;
  const res = { stop: null, boxedIn: null, coast: null, dMe: null, cand: [], pick: null };
  if (!g.teams || !(g.teams[me] > 0) || typeof g.donate !== 'function') { res.stop = 'noTeam'; return res; }
  if (g.t < 1500) { res.stop = 't<1500'; return res; }
  if (g.terr[me] < 1200) { res.stop = 'terr<1200'; return res; }
  if (g.bal[me] < 30000) { res.stop = 'bal<30000'; return res; }
  if (g.t - (pol.lastDonateTick ?? -999) < 12) { res.stop = 'cooldown12'; return res; }
  const mySlot = typeof win !== 'undefined' && Number.isInteger(win.__tsbSquadSlot) ? win.__tsbSquadSlot : (me % 10);
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  res.dMe = dMe;
  const slotOk = emergencyOnly || ((g.t / 5) | 0) % 5 === (mySlot % 5);

  let myHumanInAtk = 0, myHumanOutAtk = 0;
  for (const a of g.attackersOf(me)) {
    if (!g.isBot(a) && !pol.isTeammate(g, a)) myHumanInAtk += g.attackTroopsOn(a, me);
  }
  const sbMe = g.slotBase(me);
  for (let i = 0; i < g.atkCount[me]; i++) {
    const tgt = g.atkTarget[sbMe + i];
    if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !pol.isTeammate(g, tgt)) myHumanOutAtk += g.atkTroops[sbMe + i];
  }
  const busy = myHumanInAtk > 0 || myHumanOutAtk > 0.08 * B;

  const enemyHumanNbs = pol.nb.filter((p) => g.alive[p] && pol.person(g, p));
  let anyEnemyNb = enemyHumanNbs.length > 0;
  if (!anyEnemyNb && pol.cnt) {
    for (let p = 0; p < g.humans; p++) {
      if (p !== me && g.alive[p] && !pol.isTeammate(g, p) && (pol.cnt[p] ?? 0) > 0) { anyEnemyNb = true; break; }
    }
  }
  const boxedIn = !anyEnemyNb && pol.nb.length === 0 && pol.neutral === 0;
  const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
  res.boxedIn = boxedIn; res.coast = hasExposedCoast; res.anyEnemyNb = anyEnemyNb; res.nb = pol.nb.length; res.neutral = pol.neutral;
  res.myIn = myHumanInAtk; res.myOut = myHumanOutAtk;
  if (!slotOk) { res.stop = 'slotPhase'; res.busy = busy; }
  else if (busy) { res.stop = 'busy'; }

  const bossId = pol.findBossId(g);
  if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100 && (!win.ao?.iD || win.ao.iD(bossId))) {
    const dBoss = g.bal[bossId] / Math.max(1, g.terr[bossId]);
    let bossInAtk = 0;
    for (const a of g.attackersOf(bossId)) bossInAtk += g.attackTroopsOn(a, bossId);
    const bossFloor = bossInAtk > 0 ? (boxedIn ? 40 * L : 72 * L) : (boxedIn ? 75 * L : 88 * L);
    if ((bossInAtk > 0 || dBoss < 112) && B > 1.15 * bossFloor) {
      const maxPct = Math.floor(((B - bossFloor) * 1024) / B);
      const pct = Math.min(maxPct, boxedIn ? 260 : 180);
      if (pct >= 120) { if (!res.stop) res.stop = 'boss'; res.pick = { target: bossId, kind: 'boss', pct }; return res; }
    }
  }

  const sb0 = pol.sb, sbT0 = pol.sbT;
  let safeM1 = 0;
  if (!boxedIn) { try { safeM1 = pol.safeAt(g, -1); } catch { safeM1 = 0; } }
  pol.sb = sb0; pol.sbT = sbT0;
  const prodOptFloor = boxedIn ? (hasExposedCoast ? 44 * L : 34 * L) : Math.max(92 * L, safeM1);
  const emergDefFloor = boxedIn ? (hasExposedCoast ? 32 * L : 22 * L) : Math.max(88 * L, safeM1);
  res.prodOptFloor = prodOptFloor; res.emergDefFloor = emergDefFloor;

  let maxSquadTerr = 0, topSquadId = -1, maxRandomTeamTerr = 0;
  for (let p = 0; p < g.humans; p++) {
    if (!g.alive[p] || !pol.isTeammate(g, p)) continue;
    if (typeof win !== 'undefined' && win.__quitPlayers && win.__quitPlayers.has(p)) continue;
    if (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) {
      if (g.terr[p] > maxSquadTerr) { maxSquadTerr = g.terr[p]; topSquadId = p; }
    } else if (!g.isBot(p) && g.terr[p] > maxRandomTeamTerr) {
      maxRandomTeamTerr = g.terr[p];
    }
  }
  let bestTarget = -1, bestScore = -Infinity, bestKind = 'prod_opt', bestFloor = prodOptFloor;
  let totalSquadLandFronts = 0;
  for (let p = 0; p < g.humans; p++) {
    if (g.alive[p] && pol.isTeammate(g, p) && (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) && g.terr[p] >= 150) {
      const nbs = pol.peopleOf(g, p);
      if (nbs.some((o) => g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0)) totalSquadLandFronts++;
    }
  }
  res.fronts = totalSquadLandFronts;

  for (let p = 0; p < g.humans; p++) {
    if (p === me || !g.alive[p] || !pol.isTeammate(g, p) || (!pol.isOurSquadBot(g, p) && !pol.isBossNpl(g, p))) continue;
    const row = { p, why: null };
    res.cand.push(row);
    if (g.terr[p] < (totalSquadLandFronts <= 2 ? 150 : 1200)) { row.why = 'terrMin'; continue; }
    if (typeof win !== 'undefined' && win.__quitPlayers && win.__quitPlayers.has(p)) { row.why = 'quit'; continue; }
    const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
    row.dAlly = dAlly;
    if (dAlly >= (boxedIn ? 142 : 115)) { row.why = 'allyDense'; continue; }
    let inHumanAtk = 0, outHumanAtk = 0;
    for (const a of g.attackersOf(p)) {
      if (!g.isBot(a) && !pol.isTeammate(g, a)) inHumanAtk += g.attackTroopsOn(a, p);
    }
    const sbP = g.slotBase(p);
    for (let i = 0; i < g.atkCount[p]; i++) {
      const tgt = g.atkTarget[sbP + i];
      if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !pol.isTeammate(g, tgt)) outHumanAtk += g.atkTroops[sbP + i];
    }
    const allyNbs = pol.peopleOf(g, p);
    let enemyNbs = 0, botNbs = 0, minEnemyDens = Infinity, hasBleedingPrey = false;
    for (const o of allyNbs) {
      if (o !== me && g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0) {
        const doDens = g.bal[o] / Math.max(1, g.terr[o]);
        if (!g.isBot(o)) {
          enemyNbs++;
          if (doDens < minEnemyDens) minEnemyDens = doDens;
          if (doDens < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) hasBleedingPrey = true;
        } else {
          botNbs++;
          if (doDens < minEnemyDens) minEnemyDens = doDens;
          if (doDens < 35) hasBleedingPrey = true;
        }
      }
    }
    if (enemyNbs === 0 && botNbs > 0) enemyNbs = botNbs;
    const allyHasCoast = (g.coast?.[p]?.length ?? 0) > 0;
    const isBeachhead = enemyNbs > 0 && totalSquadLandFronts <= 2 && boxedIn;
    const isCrownContender = (p === topSquadId && enemyNbs > 0 && maxRandomTeamTerr >= 0.70 * maxSquadTerr) || isBeachhead;
    row.enemyNbs = enemyNbs; row.inAtk = inHumanAtk; row.outAtk = outHumanAtk;
    if (enemyNbs === 0 && inHumanAtk === 0 && outHumanAtk === 0 && (!boxedIn || !allyHasCoast || dMe < 105 || dAlly > 112)) { row.why = 'noFront'; continue; }
    // L4455 的两个分支分开记：x1.65 = 被压 > 1.65×余额；small = t≥4500 且领土 < 0.22×编队最大号 且 被压 > 0.45×余额
    const doomedBig = inHumanAtk > 1.65 * Bp;
    const doomedSmall = g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inHumanAtk > 0.45 * Bp;
    const isDoomedPocket = !isBeachhead && (doomedBig || doomedSmall);
    if (doomedBig || doomedSmall) row.doomedBy = doomedBig ? 'x1.65' : 'small';
    row.beachhead = isBeachhead;
    if (isDoomedPocket) { row.why = 'doomed'; continue; }
    const underFire = inHumanAtk > 0 && (inHumanAtk >= 0.06 * Bp || dAlly < 88);
    const activePush = outHumanAtk >= 0.06 * Bp && dAlly < 96;
    const hasPreyOpening = enemyNbs > 0 && (hasBleedingPrey || minEnemyDens < 0.70 * dAlly) && dAlly < 96;
    row.underFire = underFire;
    if (emergencyOnly && !underFire) { row.why = 'emergencyOnly'; continue; }
    if (underFire) {
      const reqD = boxedIn ? (hasExposedCoast ? 42 : 30) : 102;
      row.reqD = reqD;
      if (dMe < reqD) { row.why = 'A:dMe'; continue; }
      if (B <= 1.12 * emergDefFloor) { row.why = 'A:floor'; continue; }
      if (!boxedIn && dMe < dAlly + 16) { row.why = 'A:gap'; continue; }
      const score = 5000 + (inHumanAtk / Math.max(1, Bp)) * 1200 + (105 - dAlly) * 20 + Math.min(2200, Lp / 18);
      row.why = 'ok'; row.kind = 'defense_dispatch'; row.score = score;
      if (score > bestScore) { bestScore = score; bestTarget = p; bestKind = 'defense_dispatch'; bestFloor = emergDefFloor; }
    } else {
      const reqD = boxedIn ? 58 : 108;
      const maxAllyD = boxedIn ? (activePush || hasPreyOpening || enemyNbs > 0 ? 140 : 128) : 96;
      row.reqD = reqD;
      if (dMe < reqD) { row.why = 'B:dMe'; continue; }
      if (dAlly > maxAllyD) { row.why = 'B:allyD'; continue; }
      if (B <= 1.14 * prodOptFloor) { row.why = 'B:floor'; continue; }
      if (!boxedIn && dMe < dAlly + 16) { row.why = 'B:gap'; continue; }
      const score = (activePush || hasPreyOpening ? 2500 : 1000) +
        (isCrownContender ? 1800 : 0) +
        (outHumanAtk / Math.max(1, Bp)) * 1200 +
        (hasBleedingPrey ? 500 : 0) +
        (100 - dAlly) * 18 +
        enemyNbs * 80 +
        Math.min(3500, Lp / 14);
      row.why = 'ok'; row.kind = activePush || hasPreyOpening ? 'offense_dispatch' : 'yield_opt_dispatch'; row.score = score;
      if (score > bestScore) { bestScore = score; bestTarget = p; bestKind = row.kind; bestFloor = prodOptFloor; }
    }
  }
  if (bestTarget < 0) {
    if (!res.stop) {
      // 没有任何候选过关：取「走得最远」的那个候选的原因（有敌邻/在交战的优先）
      const order = ['B:gap', 'A:gap', 'B:floor', 'A:floor', 'B:allyD', 'B:dMe', 'A:dMe', 'emergencyOnly', 'doomed', 'noFront', 'allyDense', 'quit', 'terrMin'];
      let best = null;
      for (const r of res.cand) if (!best || order.indexOf(r.why) < order.indexOf(best.why)) best = r;
      res.stop = best ? best.why : 'noCandidate';
    }
    return res;
  }
  const maxSurplus = Math.max(0, B - bestFloor);
  const maxSafePct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
  const idealPct = bestKind === 'defense_dispatch' ? (boxedIn ? 380 : 240) : (boxedIn ? 320 : 220);
  const pct = Math.min(maxSafePct, idealPct);
  res.pick = { target: bestTarget, kind: bestKind, pct };
  if (!res.stop) res.stop = pct < 180 ? 'pct<180' : 'sent';
  return res;
}

export function donateWhy(mid, opts = {}) {
  const per = {};
  const wrapped = new Set();
  let names = null;
  const detail = [];
  shadow(mid, { quiet: true, until: opts.until, trace: (g, b, pol, ctx) => {
    if (!names) names = ctx.names;
    if (wrapped.has(b.bot)) return;
    wrapped.add(b.bot);
    per[b.bot] = { me: b.me, calls: 0, agree: 0, disagree: [], stops: {}, byBand: {}, sentTo: {}, underAtk: {} };
    const orig = pol.tryDonateToTeammate;
    if (typeof orig !== 'function') return;
    pol.tryDonateToTeammate = function (gg, emergencyOnly = false) {
      const S = per[b.bot];
      let ex = null;
      try { ex = explainDonate(this, gg, emergencyOnly); } catch (e) { ex = { stop: 'ERR:' + e.message, cand: [] }; }
      let cap = null;
      const had = Object.prototype.hasOwnProperty.call(gg, 'donate'), d0 = gg.donate;
      gg.donate = function (pct, tgt, me2) { cap = { pct, tgt }; return d0.call(this, pct, tgt, me2); };
      let r;
      try { r = orig.call(this, gg, emergencyOnly); } finally { if (had) gg.donate = d0; else delete gg.donate; }
      S.calls++;
      const predictedCall = ex.stop === 'sent' || ex.stop === 'boss';
      const ok = predictedCall === !!cap && (!cap || (ex.pick && ex.pick.target === cap.tgt && ex.pick.pct === cap.pct));
      if (ok) S.agree++; else if (S.disagree.length < 20) S.disagree.push([gg.t, ex.stop, ex.pick, cap, r]);
      const key = (emergencyOnly ? 'E/' : '') + ex.stop;
      S.stops[key] = (S.stops[key] || 0) + 1;
      const band = gg.t < 2142 ? '1500-2141' : gg.t < 3213 ? '2142-3212' : gg.t < 4284 ? '3213-4283' : gg.t < 6000 ? '4284-5999' : gg.t < 8000 ? '6000-7999' : '8000+';
      const bb = (S.byBand[band] ||= {});
      // 「围/边」= 源码 L4355 的 boxedIn；在算到 boxedIn 之前就返回的（cooldown12 等）记「·」
      const key2 = `${ex.boxedIn === null ? '·' : ex.boxedIn ? '围' : '边'}:${key}`;
      bb[key2] = (bb[key2] || 0) + 1;
      if (cap) { const nm = names[cap.tgt] || String(cap.tgt); S.sentTo[nm] = (S.sentTo[nm] || 0) + 1; }
      // 轮到自己、自己不忙的调用里：正在被真人打的候选受捐人被判成什么（doomed 按 L4455 的两个分支分开；滩头豁免单列）
      if (!['slotPhase', 'busy', 'boss'].includes(ex.stop)) {
        for (const c of ex.cand || []) {
          if (!((c.inAtk ?? 0) > 0)) continue;
          const nm = names[c.p] || String(c.p);
          const kk = c.why === 'doomed' ? `doomed:${c.doomedBy}` : c.doomedBy && c.beachhead ? `${c.why}(滩头豁免:${c.doomedBy})` : c.why;
          const u = (S.underAtk[nm] ||= {});
          u[kk] = (u[kk] || 0) + 1;
        }
      }
      if (opts.bot === b.bot && gg.t >= (opts.from ?? 0) && gg.t <= (opts.to ?? Infinity) && (opts.all || ex.stop !== 'slotPhase')) {
        detail.push({ t: gg.t, emergencyOnly, ex, cap, r, B: gg.bal[b.me], L: gg.terr[b.me] });
      }
      return r;
    };
  } });
  return { per, detail, names };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const args = process.argv.slice(2);
  const mid = args[0];
  const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
  if (!mid) { console.error('用法：node donate-why.mjs <mid> [--bot B --from T --to T [--all]]'); process.exit(2); }
  const bot = opt('bot', null);
  const k = (x) => (Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? Math.round(x / 1e3) + 'k' : String(Math.round(x)));
  const R = donateWhy(mid, { bot, from: +opt('from', 0), to: +opt('to', 1e9), all: args.includes('--all'), until: bot ? +opt('to', 1e9) + 1 : undefined });
  if (bot) {
    for (const d of R.detail) {
      const ex = d.ex;
      const cands = ex.cand.filter((c) => c.why !== 'terrMin' && c.why !== 'quit').map((c) => `${(R.names[c.p] || c.p).replace(/^\[.*?\]\s*/, '').slice(0, 8)}:${c.why}${c.dAlly !== undefined ? `(密${c.dAlly.toFixed(0)} 敌邻${c.enemyNbs ?? '-'} 被压${k(c.inAtk ?? 0)}${c.underFire ? ' 受击' : ''})` : ''}`).join(' ');
      console.log(`t=${d.t}${d.emergencyOnly ? ' [紧急档]' : ''} B=${k(d.B)} L=${d.L} 密=${(ex.dMe ?? 0).toFixed(1)} 被围=${ex.boxedIn ? 1 : 0}(nb=${ex.nb} 中立=${ex.neutral} 有敌接壤=${ex.anyEnemyNb ? 1 : 0}) 海岸=${ex.coast ? 1 : 0} 留底 产出${k(ex.prodOptFloor ?? 0)}/紧急${k(ex.emergDefFloor ?? 0)} 前线号数=${ex.fronts ?? '-'} → ${ex.stop}${ex.pick ? ` [${R.names[ex.pick.target]} ${ex.pick.kind} pct=${ex.pick.pct}]` : ''} | 真调用：${d.cap ? `donate(pct=${d.cap.pct}, ${R.names[d.cap.tgt]})→${d.r}` : `未发（返回 ${d.r}）`} | ${cands}`);
    }
  } else {
    let calls = 0, agree = 0;
    const tot = {};
    for (const [bn, S] of Object.entries(R.per)) {
      calls += S.calls; agree += S.agree;
      for (const [kk, v] of Object.entries(S.stops)) tot[kk] = (tot[kk] || 0) + v;
    }
    const under = {};
    for (const S of Object.values(R.per)) {
      for (const [nm, u] of Object.entries(S.underAtk || {})) {
        const t = (under[nm] ||= {});
        for (const [kk, v] of Object.entries(u)) t[kk] = (t[kk] || 0) + v;
      }
    }
    const underTot = {};
    for (const u of Object.values(under)) for (const [kk, v] of Object.entries(u)) underTot[kk] = (underTot[kk] || 0) + v;
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, `${mid}-donwhy.json`), JSON.stringify({ matchId: mid, calls, agree, total: tot, underAtk: under, underAtkTotal: underTot, per: R.per }));
    console.log(`${mid} tryDonateToTeammate 调用 ${calls} 次；照抄判定与真调用一致 ${agree} 次（${calls ? (100 * agree / calls).toFixed(2) : '-'}%）`);
    console.log('  全队卡点：' + Object.entries(tot).sort((a, b) => b[1] - a[1]).map(([kk, v]) => `${kk} ${v}`).join('，'));
    const fmt = (u) => Object.entries(u).sort((a, b) => b[1] - a[1]).map(([kk, v]) => `${kk} ${v}`).join('，');
    console.log('  正在被真人打的候选受捐人被判成什么（只计轮到自己且不忙的调用；doomed:x1.65 = 被压 > 1.65×余额，doomed:small = t≥4500 且领土 < 0.22×编队最大号 且被压 > 0.45×余额）');
    console.log('    合计：' + (Object.keys(underTot).length ? fmt(underTot) : '无'));
    for (const [nm, u] of Object.entries(under)) console.log(`    ${nm}：${fmt(u)}`);
    for (const [bn, S] of Object.entries(R.per)) {
      console.log(`  ${bn.padEnd(7)} 调用 ${String(S.calls).padStart(5)} 一致 ${String(S.agree).padStart(5)} | ` + Object.entries(S.stops).sort((a, b) => b[1] - a[1]).map(([kk, v]) => `${kk} ${v}`).join('，') + (Object.keys(S.sentTo).length ? ` | 发给：${Object.entries(S.sentTo).map(([n, v]) => `${n}×${v}`).join(' ')}` : ''));
      for (const [band, bb] of Object.entries(S.byBand)) console.log(`           ${band}: ` + Object.entries(bb).sort((a, b) => b[1] - a[1]).map(([kk, v]) => `${kk} ${v}`).join('，'));
      if (S.disagree.length) console.log(`           不一致样本：` + S.disagree.slice(0, 5).map((d) => JSON.stringify(d)).join(' '));
    }
  }
}
