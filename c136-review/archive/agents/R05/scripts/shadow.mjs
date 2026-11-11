#!/usr/bin/env node
// shadow.mjs — 影子策略：在逐拍重演出来的真实局面上，每拍调用线上同一份策略源码（Policy.act），
//   但它下的指令不落地（真实指令仍来自录像），记录它「此刻想下什么」以及走到了哪个函数的哪一行返回。
//   用途：把局内决策追到具体函数与分支；对照「零延迟的策略想做的」和「录像里真正落地的」。
//   注意：影子是零延迟视角；真实客户端落后时，真实决策是在更旧的局面上做的 → 结论标「推断」。
//
// 先跑一次：node --expose-internals shadow_prep.cjs <va|vb|vc|c110>
// 用法：
//   node shadow.mjs <matchId> --bots talon5,sora_w [--t0 0 --t1 3000]      # 每号每 300 拍一行：各出口路径计数 + 影子指令数
//        [--win 300]            汇总窗口长度
//        [--dump 1205,1210]     打印这些拍的完整探针轨迹
//        [--nb 900,1200]        打印这些拍每个号的邻居报价表（price / botOk / allow / 目标底线）
//        [--cold]               不从头跑策略内部状态，只在 [t0,t1] 内调用（快，但内部记忆不连续）
//        [--json FILE]          把逐拍记录写成 JSON
//        [--match]              下发对账：影子想发的指令数 vs 策略自报 cmds= vs 录像真正执行的；并给每条已执行指令找
//                               「目标、比例完全相同的最近一次影子决策」，得到这条指令的陈旧度（执行拍 − 决策拍）
//        [--quiet]              不打每号每窗口的出口路径表
//        [--don-probe 5200,5300] 在这些拍、对每个号复刻 tryDonateToTeammate 的候选循环（只读），逐个候选队友打印它在哪一行被跳过
//                               （常数与行号按版本取 Va/Vb；用 --mids tryDonateToTeammate 的行命中数交叉核对）
//        [--offers 1600,2400]   在这些拍、对每个号打印 buyLand 的报价表（worth / cheap / over 与每条报价的每格价、标志位、safeAt），
//                               标出 L5359 价格门收口的位置（只在专门的冷启动探针里用）
//        [--unlock]             对照影子：每拍调用前把 isNoFullSend 清回 false（看「没被误锁」时同一局面下决策差在哪）
//        [--mids tryDonateToTeammate]  对名字含该串的函数，按号×窗口统计「出口行」和「途中 continue/break 行」各命中多少个决策拍
//        [--tc 600:1500]        决策拍分类：对窗口内每个号的每个决策拍记一行（写进 --json 的 tc[]）：四周有什么（中立边/机器人/敌方真人/队友）、
//                               有没有过得了留底的机器人目标（与 --floor 同一套复刻）、safeFinite 占存兵、留底由谁定、当拍影子发了什么。
//                               tick_attrib.py 用它把 600–1500 的每个决策拍归到「没目标 / 留底锁 / 发了没落地 / 发了迟到落空 / 发了有效」。
//        [--per-tick N]         适配层受理口径：每个号每拍最多受理 N 条指令，超出的返回 false（不计入「影子想发」）。
//                               默认 1：按 1 条/拍受理时影子指令数与策略自报 cmds= 逐号相等（A065：2055 对 2054，10 号里 9 号全等；
//                               不限时 2096）。--per-tick 0 = 不限。汇总行 [每拍限 N 条] 列出同一拍被挤掉的指令及挤掉它的指令。
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { simulate, DATA, NEUTRAL, bare } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const T0 = +val('--t0', 0), T1 = +val('--t1', 1e9), WIN = +val('--win', 300);
const dumpT = new Set(String(val('--dump', '')).split(',').filter(Boolean).map(Number));
const nbT = new Set(String(val('--nb', '')).split(',').filter(Boolean).map(Number));
const cold = args.includes('--cold');
const midsFn = val('--mids', '');
const unlock = args.includes('--unlock');
const PER_TICK = +val('--per-tick', 1);
const DROPS = [];
const donT = new Set(String(val('--don-probe', '')).split(',').filter(Boolean).map(Number));
const offT = new Set(String(val('--offers', '')).split(',').filter(Boolean).map(Number));
// tryDonateToTeammate 各版本的常数与行号（Va：v27-team-c116-va.js；Vb：v27-team-c116-vb.js）
const DONC = {
  va: { pofC: 72, pofI: 66, pofF: 94, reqB: 82, lSelf: 4342, lHigh: 4417, lNoNb: 4452, lDoom: 4455, lA: 4465, lB: 4480 },
  vb: { pofC: 44, pofI: 34, pofF: 92, reqB: 58, lSelf: 4343, lHigh: 4420, lNoNb: 4453, lDoom: 4456, lA: 4466, lB: 4481 },
};
function donProbe(g, pol, me, tag) {
  const C = DONC[ver] || DONC.vb;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  let myIn = 0, myOut = 0;
  for (const a of g.attackersOf(me)) if (!g.isBot(a) && !pol.isTeammate(g, a)) myIn += g.attackTroopsOn(a, me);
  const sbMe = g.slotBase(me);
  for (let i = 0; i < g.atkCount[me]; i++) { const tg = g.atkTarget[sbMe + i]; if (tg >= 0 && tg < g.humans && !g.isBot(tg) && !pol.isTeammate(g, tg)) myOut += g.atkTroops[sbMe + i]; }
  const enemyHumanNbs = (pol.nb || []).filter((p) => g.alive[p] && pol.person(g, p));
  let anyEnemyNb = enemyHumanNbs.length > 0;
  if (!anyEnemyNb && pol.cnt) for (let p = 0; p < g.humans; p++) if (p !== me && g.alive[p] && !pol.isTeammate(g, p) && (pol.cnt[p] ?? 0) > 0) { anyEnemyNb = true; break; }
  const boxedIn = !anyEnemyNb && (pol.nb || []).length === 0 && pol.neutral === 0;
  const coast = (g.coast?.[me]?.length ?? 0) > 0;
  const prodOptFloor = boxedIn ? (coast ? C.pofC * L : C.pofI * L) : Math.max(C.pofF * L, pol.safeAt(g, -1));
  const emergDefFloor = boxedIn ? (coast ? 32 * L : 22 * L) : Math.max(88 * L, pol.safeAt(g, -1));
  let maxSquadTerr = 0, topSquadId = -1, maxRandomTeamTerr = 0, fronts = 0;
  for (let p = 0; p < g.humans; p++) {
    if (!g.alive[p] || !pol.isTeammate(g, p)) continue;
    if (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) { if (g.terr[p] > maxSquadTerr) { maxSquadTerr = g.terr[p]; topSquadId = p; } }
    else if (!g.isBot(p) && g.terr[p] > maxRandomTeamTerr) maxRandomTeamTerr = g.terr[p];
  }
  for (let p = 0; p < g.humans; p++) if (g.alive[p] && pol.isTeammate(g, p) && (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) && g.terr[p] >= 150) { if (pol.peopleOf(g, p).some((o) => g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0)) fronts++; }
  console.log(`\n-- 调度候选 ${tag} t=${g.t} 地 ${L} 兵 ${B} 密度 ${dMe.toFixed(0)}｜boxedIn=${boxedIn} 有海岸=${coast}｜自己被真人打 ${myIn} 自己在打真人 ${myOut}${myIn > 0 || myOut > 0.08 * B ? `（→ L${C.lSelf} 直接返回）` : ''}｜prodOptFloor=${Math.round(prodOptFloor)} emergDefFloor=${Math.round(emergDefFloor)}｜编队最大号 ${maxSquadTerr} 格（22% = ${Math.round(0.22 * maxSquadTerr)}）陆上接敌的兄弟 ${fronts} 个`);
  for (let p = 0; p < g.humans; p++) {
    if (p === me || !g.alive[p] || !pol.isTeammate(g, p) || (!pol.isOurSquadBot(g, p) && !pol.isBossNpl(g, p)) || g.terr[p] < (fronts <= 2 ? 150 : 1200)) continue;
    const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
    let why = '';
    if (dAlly >= (boxedIn ? 142 : 115)) why = `L${C.lHigh} 受赠方密度已高`;
    let inH = 0, outH = 0;
    for (const a of g.attackersOf(p)) if (!g.isBot(a) && !pol.isTeammate(g, a)) inH += g.attackTroopsOn(a, p);
    const sbP = g.slotBase(p);
    for (let i = 0; i < g.atkCount[p]; i++) { const tg = g.atkTarget[sbP + i]; if (tg >= 0 && tg < g.humans && !g.isBot(tg) && !pol.isTeammate(g, tg)) outH += g.atkTroops[sbP + i]; }
    let enemyNbs = 0, botNbs = 0, minD = Infinity, prey = false;
    for (const o of pol.peopleOf(g, p)) {
      if (o !== me && g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0) {
        const dd = g.bal[o] / Math.max(1, g.terr[o]);
        if (!g.isBot(o)) { enemyNbs++; if (dd < minD) minD = dd; if (dd < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) prey = true; }
        else { botNbs++; if (dd < minD) minD = dd; if (dd < 35) prey = true; }
      }
    }
    if (enemyNbs === 0 && botNbs > 0) enemyNbs = botNbs;
    const allyCoast = (g.coast?.[p]?.length ?? 0) > 0;
    const beach = enemyNbs > 0 && fronts <= 2 && boxedIn;
    const doomed = !beach && (inH > 1.65 * Bp || (g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inH > 0.45 * Bp));
    const underFire = inH > 0 && (inH >= 0.06 * Bp || dAlly < 88);
    const activePush = outH >= 0.06 * Bp && dAlly < 96;
    const preyOpen = enemyNbs > 0 && (prey || minD < 0.70 * dAlly) && dAlly < 96;
    if (!why && enemyNbs === 0 && inH === 0 && outH === 0 && (!boxedIn || !allyCoast || dMe < 105 || dAlly > 112)) why = `L${C.lNoNb} 受赠方无敌邻、无战事${boxedIn && allyCoast ? `（沿海例外需 自己密度 ≥105 且 对方 ≤112）` : ''}`;
    if (!why && doomed) why = `L${C.lDoom} 判为弃子（被真人打 ${inH} > ${inH > 1.65 * Bp ? '1.65×兵' : '0.45×兵 且地 < 22%×最大号'}）`;
    if (!why && underFire) {
      const reqD = boxedIn ? (coast ? 42 : 30) : 102;
      if (dMe < reqD || B <= 1.12 * emergDefFloor || (!boxedIn && dMe < dAlly + 16)) why = `L${C.lA} A 类门槛不够（自己密度 ${dMe.toFixed(0)} 需 ≥${reqD}${!boxedIn ? `且 ≥ 对方+16` : ''}；兵需 > ${Math.round(1.12 * emergDefFloor)}）`;
      else why = '★ A 类 defense_dispatch 候选';
    } else if (!why) {
      const reqD = boxedIn ? C.reqB : 108;
      const maxAllyD = boxedIn ? (activePush || preyOpen || enemyNbs > 0 ? 140 : 128) : 96;
      if (dMe < reqD || dAlly > maxAllyD || B <= 1.14 * prodOptFloor || (!boxedIn && dMe < dAlly + 16)) why = `L${C.lB} B 类门槛不够（自己密度 ${dMe.toFixed(0)} 需 ≥${reqD}；兵需 > ${Math.round(1.14 * prodOptFloor)}；对方密度 ${dAlly.toFixed(0)} 需 ≤${maxAllyD}）`;
      else why = `★ B 类 ${activePush || preyOpen ? 'offense_dispatch' : 'yield_opt_dispatch'} 候选${enemyNbs === 0 && inH === 0 && outH === 0 ? '（对方无敌邻、无战事：走沿海例外）' : ''}`;
    }
    console.log(`   → ${R0.tag(p)} 地 ${Lp} 兵 ${Bp} 密度 ${dAlly.toFixed(0)}｜被真人打 ${inH}（${(inH / Math.max(1, Bp)).toFixed(2)}×兵）在打真人 ${outH}｜敌邻 ${enemyNbs}｜${why}`);
  }
}
// buyLand 报价探针（t≥1500 的主循环；行号按 Vb：L5350-5359 价格门、L5414-5447 留底）。只读：照抄 buyLand 开头的几个量，
// 再调用策略自己的 offers(g)（已按 rankC 从便宜到贵排好），逐个报价打印 每格价 c、c÷worth、吃掉需要的兵、各标志位、safeAt。
// 第一条「c ≥ worth 且 c ≥ cheap 且 不 over」的报价就是 L5359 收口的地方（break：它和它后面的报价都不再看）。
// 注意：offers(g) 里会读策略的记忆（集火目标、记仇对象），所以只在专门的冷启动探针里用，不和出口统计混跑。
function offersProbe(g, pol, me, tag) {
  const P = pol.p;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  const dMedOther = pol.otherHumanMedDens(g);
  const m = P.maxW * pol.winRatio(g.t);
  const refDens = dMedOther !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMedOther) : dMe;
  const worth = m * refDens;
  const over = P.surplus > 0 && B > 100 * L;
  const cheap = P.growth > 0 ? 0.1 / pol.baseRate(g) : 0;
  const offers = pol.offers(g);
  const humanNb = (pol.nb || []).filter((q) => g.alive[q] && pol.person(g, q)).length;
  console.log(`\n-- 报价 ${tag} t=${g.t} 地 ${L} 兵 ${B} 密度 ${dMe.toFixed(1)}｜其他真人密度中位 ${dMedOther === null ? '-' : dMedOther.toFixed(1)} m=${m.toFixed(2)} refDens=${refDens.toFixed(1)} worth=${worth.toFixed(1)} cheap=${cheap.toFixed(1)} over=${over}｜真人邻居 ${humanNb} 个，报价 ${offers.length} 条`);
  // safeAt 的拆解（botSkip=0、postKill=0、killW=1 时 V17.safeAt = max(safeFinite, dpKeep)，Policy.safeAt 再封顶 oppFloorCap×地）：
  // safeFinite（L2500-2510）取相邻「机器人」（AI 机器人或已离场的真人，game.js isBot L215-217）里 threatOf.minOther 的最大值；
  // dpKeep（L2459-2464）=（最强真人邻居的存兵 + 它打我的在途兵 − 1.5×地）÷1.78
  {
    const nameOf = (q) => (q >= R0.H ? '机器人#' + q : R0.tag(q) + (g.isBot(q) ? '〔已离场〕' : ''));
    let sfBest = 0, sfVia = -1, sfMin = 0;
    for (const q of pol.nb || []) {
      if (g.alive[q] === 0 || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
      const th = pol.threatOf(g, q);
      if (th.neutral || !Number.isFinite(th.minOther)) continue;
      const v = th.minOther - g.attackTroopsOn(me, q);
      if (v > sfBest) { sfBest = v; sfVia = q; sfMin = th.minOther; }
    }
    let sfOwner = -1;
    if (sfVia >= 0) for (let o = 0; o < g.bal.length; o++) { if (o !== me && o !== sfVia && g.alive[o] && g.bal[o] + g.attackTroopsOn(o, sfVia) === sfMin) { sfOwner = o; break; } }
    let dkM = 0, dkWho = -1;
    for (const q of pol.nb || []) if (g.alive[q] && pol.person(g, q)) { const v = g.bal[q] + g.attackTroopsOn(q, me); if (v > dkM) { dkM = v; dkWho = q; } }
    const dk = Math.max(0, (dkM - 1.5 * g.terr[me]) / 1.78);
    let sAll = NaN;
    try { sAll = pol.safeAt(g, -1); } catch {}
    const sfTxt = sfVia < 0 ? '0（没有符合条件的相邻机器人/离场号）' : `${Math.round(sfBest)}（经 ${nameOf(sfVia)}；它「最弱的其它邻居」是 ${sfOwner < 0 ? '?' : nameOf(sfOwner) + (sfOwner < R0.H && pol.isTeammate(g, sfOwner) ? '〔我方号〕' : '')}，存兵+在途 ${Math.round(sfMin)}）`;
    console.log(`   [safeAt 拆解] safeAt(-1)=${Math.round(sAll)}｜safeFinite=${sfTxt}｜dpKeep=${Math.round(dk)}（最强真人邻居 ${dkWho < 0 ? '无' : nameOf(dkWho) + ' ' + Math.round(dkM)}）｜封顶 ${P.oppFloorCap}×地=${Math.round(P.oppFloorCap * L)}｜定值的是 ${sAll >= P.oppFloorCap * L - 1 ? '封顶' : sfBest >= dk ? (sfBest > 0 ? 'safeFinite' : '无') : 'dpKeep'}｜存兵 ${B}${B - Math.floor(12 * B / 1024) - sAll <= 0 ? ' ≤ 留底：对谁都没有可用兵' : ''}`);
  }
  let broke = false;
  for (const o of offers) {
    const q = o.q;
    const gate = o.c >= worth && o.c >= cheap && !over;
    let safe = NaN;
    try { safe = pol.safeAt(g, q); } catch {}
    const flags = [o.person ? '真人' : '非真人', o.nearCollapse ? '将垮' : '', o.bleeding ? '失血' : '', o.pulseMode ? '脉冲' : '', o.onMe ? '正打我' : '', o.isCrowdedHard ? '硬骨头' : '', o.isAgg ? '记仇' : '', o.isDoorSea ? '海门' : ''].filter(Boolean).join('/');
    // 复刻 L5414-5452 的留底：safe（L5415-5418 封顶）、价格预算 budget 与 minKeep（L5422-5427）、over（L5440-5443，
    // isSoleHealthyBuffer 按 false 取）、keep=max(keep,safe)（L5444）、avail（L5446）、非真人的 want 与 chunk×B（L5450-5452）
    const fee = Math.floor(12 * B / 1024);
    let safe2 = safe;
    if (!o.person || o.nearCollapse || (P.bleedSafeCap > 0 && (o.bleeding || o.tD < 0.45))) {
      const capPerPx = o.person && o.nearCollapse && (o.inAtk ?? 0) < 0.02 * B && ((o.c < 0.25 * worth && o.need <= 0.10 * B) || (g.bal[q] <= 0.05 * B && o.c < 25)) ? Math.min(P.oppFloorCap, P.collapseFloorCap ?? 85) : P.oppFloorCap;
      safe2 = Math.min(safe2, capPerPx * L);
    }
    let keep = Infinity, budget = NaN, minKeep = NaN;
    if (o.c < cheap) keep = 0;
    if (o.c < worth) {
      const worthOwn = P.ownWorthMinKeep > 0 && g.t >= P.ownWorthFrom && !o.nearCollapse ? m * dMe : worth;
      budget = Math.max(0, (worthOwn * L - fee * m - o.c * L) / (1 + m));
      minKeep = o.person && (o.nearCollapse || (P.bleedDiscount < 1 && o.bleeding) || (P.thinDiscount < 1 && o.tD < P.thinMaxTD)) ? (0.70 * o.c * L) / m : (o.c * L) / m;
      keep = Math.min(keep, P.post > 0 ? Math.max(minKeep, B - fee - budget) : minKeep);
    }
    if (over) keep = Math.min(keep, (dMe >= 122 ? 0.82 : P.hold) * 100 * L);
    const keepPrice = keep;
    keep = Math.max(keep, safe2);
    const avail = B - fee - keep;
    const want = 1.25 * o.need + 3 * (pol.cnt?.[q] ?? 0);
    const tail = !o.person ? `；非真人：want=${Math.round(want)}，chunk×存兵=${Math.round(P.chunk * B)} → ${avail <= 0 ? 'L5447 跳过' : (Math.min(avail, want) < want && Math.min(avail, want) < P.chunk * B) ? 'L5452 跳过' : 'L5453 发 ' + Math.round(Math.min(avail, want))}` : (avail <= 0 ? ' → L5447 跳过' : '');
    const note = broke ? '（价格门已收口，不看）' : gate ? '← L5359 价格门在此收口' : `过价格门；价格预算 budget=${Math.round(budget)}、价格留底=${Math.round(keepPrice)}；safeAt=${Math.round(safe)}（封顶后 ${Math.round(safe2)}）→ 留底 ${Math.round(keep)}（${keep === safe2 && safe2 > keepPrice ? 'safeAt 定' : '价格预算定'}），可用 ${Math.round(avail)}${tail}`;
    console.log(`   ${q >= R0.H ? '机器人#' + q : R0.tag(q)} 地 ${g.terr[q]} 兵 ${g.bal[q]} 密度 ${(g.bal[q] / Math.max(1, g.terr[q])).toFixed(1)} 接触 ${pol.cnt?.[q] ?? '?'}｜每格价 c=${o.c.toFixed(1)}（${(o.c / Math.max(1e-9, worth)).toFixed(2)}×worth）吃掉需 ${Math.round(o.need)}（${(o.need / Math.max(1, B)).toFixed(2)}×存兵）tD=${(o.tD ?? NaN).toFixed(2)} 新暴露真人 ${o.newNbs ?? '-'}｜${flags}｜${note}`);
    if (gate) broke = true;
  }
}
const MIDS = new Map(); // `${bot}|${win}` → { n, exit: Map(line→拍数), mid: Map(line→拍数) }
const num = +mid.slice(1);
const ver = mid[0] === 'B' ? 'c110' : num <= 17 ? 'va' : num <= 95 ? 'vb' : 'vc';
const stratFile = `/tmp/c136-r05/strat/${ver}.mjs`;
if (!fs.existsSync(stratFile)) { console.error(`缺 ${stratFile}：先跑 node --expose-internals shadow_prep.cjs ${ver}`); process.exit(2); }
const fmap = JSON.parse(fs.readFileSync(`/tmp/c136-r05/strat/${ver}.map.json`, 'utf8'));
const startName = new Map(Object.entries(fmap).map(([k, [s]]) => [s, k]));

const SH = (globalThis.__SH = { on: false, hits: [] });
const logs = [];
let curBot = null, curT = 0;
globalThis.window = {
  __hlLog: (s) => { if (curBot) logs.push({ t: curT, bot: curBot, s: String(s) }); },
  __tsbSquadSlot: 0, __quitPlayers: new Set(), __hlPerf: null,
};
const mod = await import(pathToFileURL(stratFile).href);
const { Policy, PARAMS } = mod;

// 每个号的槽位：日志 [HL-SPAWN*] me=X slot=Y（取最后一条）
const slotOf = new Map();
for (const line of fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n')) {
  const m = /\[HL-SPAWN[^\]]*\] me=(\d+) slot=(\d+)/.exec(line);
  if (m) slotOf.set(+m[1], +m[2]);
}

const want = args.includes('--bots') ? new Set(val('--bots', '').split(',')) : null;
const bots = []; // { p, name, policy, slot, rec: Map(win → {sig counts, cmds}) }
const botByP = new Map();
const ticksOut = [];

function callTree(hits) {
  // hits：-L 入口，0 出口，正数 = 行号（.5 = continue/break）。返回 [{fn, exit, depth, mids:[...]}]（按调用顺序）
  const out = [], st = [];
  for (const h of hits) {
    if (h < 0) { const node = { fn: startName.get(-h) || `@${-h}`, exit: null, depth: st.length, mids: [] }; out.push(node); st.push(node); }
    else if (h === 0) { st.pop(); }
    else if (st.length) { const top = st[st.length - 1]; if (Number.isInteger(h)) top.exit = h; else top.mids.push(Math.floor(h)); }
  }
  return out;
}
const short = (fn) => fn.replace(/^Policy\./, '').replace(/^(General|Style|V13|V17|Strategy)\./, '$1.');

const floorT = new Set(String(val('--floor', '')).split(',').filter(Boolean).map(Number));
const TC = args.includes('--tc') ? String(val('--tc')).split(':').map(Number) : null;
const tcOut = [];
function tickClass(g, b, p, B, t, cmds, tree) {
  const pol = b.policy;
  const r = { t, bot: b.name, B, L: g.terr[p], neut: pol.neutral | 0, nBot: 0, botLand: 0, nBotCheap: 0, nEH: 0, nMate: 0, busyBot: 0, busyNeut: g.hasAttack(p, NEUTRAL) ? 1 : 0, slots: g.atkCount[p], canHit: 0, sb: null, setter: '', need: null, cmds: cmds.map((c) => [c.k, c.q === undefined ? -1 : c.q, c.troops || 0]) };
  let best = null;
  for (const q of pol.nb || []) {
    if (!g.alive[q] || !g.terr[q]) continue;
    if (g.isBot(q)) {
      r.nBot++; r.botLand += g.terr[q];
      if (g.bal[q] <= 0.25 * g.terr[q] + 50) r.nBotCheap++;
      if (g.hasAttack(p, q)) r.busyBot++;
      try {
        if (!g.hasFreeSlot(q) || g.hasAttack(q, p)) continue;
        const th = pol.threatOf(g, q);
        if (th.neutral || !Number.isFinite(th.minOther)) continue;
        const tw = threatWho(g, pol, q);
        let who = tw.who;
        if (!(who >= 0 && g.bal[who] + g.attackTroopsOn(who, q) === th.minOther)) {
          who = -1;
          for (let o = 0; o < g.players; o++) if (o !== p && o !== q && g.alive[o] && g.bal[o] + g.attackTroopsOn(o, q) === th.minOther) { who = o; if (o < R0.H) break; }
        }
        const need = th.minOther - g.attackTroopsOn(p, q);
        if (!best || need > best.need) best = { need, q, who };
      } catch {}
    } else if (pol.isTeammate && pol.isTeammate(g, q)) r.nMate++;
    else r.nEH++;
  }
  try { r.sb = pol.safeFinite(g); } catch {}
  try {
    const fl = pol.floors(g); const minCmd = pol.minCmd(g);
    for (const q of pol.nb || []) {
      if (!g.alive[q] || !g.terr[q] || pol.person(g, q)) continue;
      if (!pol.allow(g, q)) continue;
      const price = pol.price(g, q);
      const avail = B - pol.floorFor(g, q, fl.floorAt(price));
      if (!(avail <= pol.minShare(g, q) * B || avail < minCmd)) r.canHit++;
    }
  } catch { r.canHit = -1; }
  if (best) {
    const w = best.who;
    r.need = best.need;
    r.setter = w < 0 ? '?' : globalThis.__SQ.has(w) ? '我方号' : w >= R0.H ? '机器人' : (g.teams && g.teams[p] > 0 && g.teams[w] === g.teams[p]) ? '路人队友' : '敌方真人';
  }
  const leaf = tree.length ? tree[tree.length - 1] : null;
  r.exit = leaf ? `${short(leaf.fn)}:${leaf.exit ?? 'end'}` : '';
  return r;
}
// 复刻 threatOf（策略 417–443 行）并返回「机器人 q 的其它邻居里最弱的是谁」
function threatWho(g, pol, q) {
  const B = g.border[q], px = g.px, own = g.own, d = g.dir4, me = pol.me;
  const busyNeutral = g.hasAttack(q, NEUTRAL);
  let minOther = Infinity, who = -1;
  const seen = new Set();
  const n = B.length, step = n > 1024 ? Math.ceil(n / 1024) : 1;
  for (let i = n - 1; i >= 0; i -= step) {
    const b = B[i];
    for (let k = 0; k < 4; k++) {
      const c = b + d[k], v = px[c];
      if (v === 1) { if (!busyNeutral) return { neutral: true, minOther: 0, who: -1 }; continue; }
      if (v < 2) continue;
      const o = own[c];
      if (o === q || o === me || seen.has(o)) continue;
      seen.add(o);
      if (g.hasAttack(q, o)) continue;
      const sv = g.bal[o] + g.attackTroopsOn(o, q);
      if (sv < minOther) { minOther = sv; who = o; }
    }
  }
  return { neutral: false, minOther, who };
}
const FL = { n: 0, locked: 0, fullLock: 0, setter: {}, botLand: 0, half: 0, halfSetter: {}, lowFloor: 0 };
// Policy.send 里「isNoFullSend 锁定后 shadowQuota 不够 → 不发」的两个 return false 行（Vb/Vc 3858、3861；Va 同行号；c110 没有这段）
const GUARD = new Set(ver === 'c110' ? [] : [3858, 3861]);
const R0 = { H: 512, names: [], tag: (q) => `${String(R0.names[q] ?? '').slice(0, 14)}#${q}` };
const R = simulate(mid, {
  maxTick: Math.min(T1, 1e9),
  onStart(g, { names, H }) {
    g.online = true;
    g.names = names;
    R0.H = H; R0.names = names;
    const sq = squadIds(mid, names, H).squad;
    globalThis.__SQ = new Set(sq.keys());
    for (const [p, name] of sq) {
      if (want && !want.has(name)) continue;
      bots.push({ p, name, policy: new Policy(PARAMS, p), slot: slotOf.has(p) ? slotOf.get(p) : p % 10, wins: new Map(), err: 0, issued: [], exec: [], lockT: -1, guard: 0 });
      botByP.set(p, bots[bots.length - 1]);
    }
  },
  onEvent(ev) {
    if (ev.type === 'leave') globalThis.window.__quitPlayers.add(ev.p);
    const b = botByP.get(ev.p);
    if (b && (ev.type === 'attack' || ev.type === 'boat' || ev.type === 'donate')) b.exec.push({ T: ev.t, k: ev.type, pct: ev.pct, q: ev.q, ok: !!ev.ok });
  },
  onTick(g, t) {
    if (cold && t < T0) return;
    for (const b of bots) {
      const p = b.p;
      if (!g.alive[p] || g.state[p] === 2) continue;
      const cmds = [];
      const recOn = t >= T0 && t <= T1;
      SH.on = recOn; SH.hits = [];
      curBot = b.name; curT = t;
      globalThis.window.__tsbSquadSlot = b.slot;
      const B = g.bal[p];
      const take = (c) => {
        if (PER_TICK > 0 && cmds.length >= PER_TICK) { DROPS.push({ t, bot: b.name, by: cmds[0], c }); return false; }
        cmds.push(c); return true;
      };
      g.attack = (pct, q, me) => take({ k: 'attack', pct, q, troops: Math.floor((B * (pct + 1)) / 1024) });
      g.donate = (pct, q, me) => take({ k: 'donate', pct, q, troops: Math.floor((B * (pct + 1)) / 1024) });
      g.boat = (pct, water, dir, me) => take({ k: 'boat', pct, q: -1, troops: Math.floor((B * (pct + 1)) / 1024) });
      g.boatTo = (pct, landPix, me, r) => take({ k: 'boatTo', pct, q: landPix >= 0 && g.px[landPix] >= 2 ? g.own[landPix] : NEUTRAL, troops: Math.floor((B * (pct + 1)) / 1024) });
      g.retreat = (q, me) => { cmds.push({ k: 'retreat', q }); return true; };
      g.recall = () => { cmds.push({ k: 'recall' }); return true; };
      g.chase = () => { cmds.push({ k: 'chase' }); return true; };
      let err = null;
      if (unlock) { b.policy.isNoFullSend = false; b.policy.pendingQuotaCheck = null; }
      try { b.policy.act(g); } catch (e) { err = e; b.err++; if (b.err <= 3) console.error(`影子策略异常 ${b.name} t=${t}: ${e.stack.split('\n').slice(0, 3).join(' | ')}`); }
      delete g.attack; delete g.donate; delete g.boat; delete g.boatTo; delete g.retreat; delete g.recall; delete g.chase;
      SH.on = false;
      for (const c of cmds) if (c.k === 'attack' || c.k === 'donate' || c.k === 'boat' || c.k === 'boatTo') b.issued.push({ t, k: c.k === 'boatTo' ? 'boat' : c.k, pct: c.pct, q: c.q });
      if (b.lockT < 0 && b.policy.isNoFullSend) b.lockT = t;
      if (!recOn) continue;
      const tree = callTree(SH.hits);
      if (!tree.length && !cmds.length) continue;
      for (const n of tree) if (n.fn === 'Policy.send' && n.exit !== null && GUARD.has(n.exit)) b.guard++;
      if (midsFn) {
        const key = `${b.name}|${Math.floor(t / WIN) * WIN}`;
        for (const n of tree) {
          if (!n.fn.includes(midsFn)) continue;
          if (!MIDS.has(key)) MIDS.set(key, { n: 0, exit: new Map(), mid: new Map() });
          const M = MIDS.get(key); M.n++;
          const ex = n.exit ?? 'end'; M.exit.set(ex, (M.exit.get(ex) || 0) + 1);
          for (const l of new Set(n.mids)) M.mid.set(l, (M.mid.get(l) || 0) + 1);
        }
      }
      // 决策签名：深度 0/1/2 的调用及其出口行
      const sig = tree.filter((n) => n.depth <= 3 && !/updateShadowQuota|tryPeaceVote|isMopUp|hold$|allow$|botOk$/.test(n.fn)).map((n) => `${short(n.fn)}:${n.exit ?? 'end'}`).join(' > ');
      const w = Math.floor(t / WIN) * WIN;
      if (!b.wins.has(w)) b.wins.set(w, { sig: new Map(), cmds: new Map(), n: 0 });
      const W = b.wins.get(w);
      if (tree.length) { W.n++; W.sig.set(sig, (W.sig.get(sig) || 0) + 1); }
      for (const c of cmds) { const key = `${c.k}→${c.q === NEUTRAL ? '中立' : c.q >= R0.H ? '机器人' : c.q === undefined ? '-' : R0.tag(c.q)}`; const e = W.cmds.get(key) || [0, 0]; e[0]++; e[1] += c.troops || 0; W.cmds.set(key, e); }
      if (cmds.length || dumpT.has(t)) ticksOut.push({ t, bot: b.name, bal: B, terr: g.terr[p], cmds, sig });
      if (TC && t >= TC[0] && t < TC[1] && (tree.length > 2 || cmds.length)) { try { tcOut.push(tickClass(g, b, p, B, t, cmds, tree)); } catch (e) { if (!globalThis.__tcErr) { globalThis.__tcErr = 1; console.error('决策拍分类异常', e.stack.split('\n').slice(0, 3).join(' | ')); } } }
      if (dumpT.has(t)) {
        console.log(`\n-- 轨迹 ${b.name} t=${t} 地 ${g.terr[p]} 兵 ${B} nb=${b.policy.nb?.length} neut=${b.policy.neutral} isNoFullSend=${b.policy.isNoFullSend} lastDonateTick=${b.policy.lastDonateTick}`);
        for (const n of tree) console.log(`   ${'  '.repeat(n.depth)}${n.fn} → 出口行 ${n.exit ?? '(自然结束)'}${n.mids.length ? `；途中 continue/break 行 ${n.mids.join(',')}` : ''}`);
        for (const c of cmds) console.log(`   影子指令 ${c.k} pct=${c.pct} → ${c.q === NEUTRAL ? '中立' : c.q} 约 ${c.troops} 兵`);
      }
      if (floorT.has(t)) {
        const pol = b.policy;
        let best = null, nBot = 0, nBotCheap = 0, botLand = 0;
        for (const q of pol.nb || []) {
          if (!g.alive[q] || !g.terr[q] || !g.isBot(q)) continue;
          nBot++; botLand += g.terr[q];
          if (g.bal[q] <= 0.25 * g.terr[q] + 50) nBotCheap++;
          if (!g.hasFreeSlot(q) || g.hasAttack(q, p)) continue;
          const th = pol.threatOf(g, q);
          if (th.neutral || !Number.isFinite(th.minOther)) continue;
          // 找出给出 minOther 的那个邻居：优先用复刻的扫描结果，对不上时按数值在全体玩家里找
          const tw = threatWho(g, pol, q);
          th.who = tw.who;
          if (!(tw.who >= 0 && g.bal[tw.who] + g.attackTroopsOn(tw.who, q) === th.minOther)) {
            th.who = -1;
            for (let o = 0; o < g.players; o++) if (o !== p && o !== q && g.alive[o] && g.bal[o] + g.attackTroopsOn(o, q) === th.minOther) { th.who = o; if (o < R0.H) break; }
          }
          const need = th.minOther - g.attackTroopsOn(p, q);
          if (!best || need > best.need) best = { need, q, who: th.who };
        }
        let sb = NaN, canHit = 0;
        try { sb = pol.safeFinite(g); } catch {}
        try {
          const fl = pol.floors(g); const minCmd = pol.minCmd(g);
          for (const q of pol.nb || []) {
            if (!g.alive[q] || !g.terr[q] || pol.person(g, q)) continue;
            if (!pol.allow(g, q)) continue;
            const price = pol.price(g, q);
            const avail = B - pol.floorFor(g, q, fl.floorAt(price));
            if (!(avail <= pol.minShare(g, q) * B || avail < minCmd)) canHit++;
          }
        } catch {}
        const whoTag = !best ? '-' : best.who < 0 ? '?' : (best.who >= R0.H ? `机器人#${best.who}` : `${R0.tag(best.who)}${globalThis.__SQ.has(best.who) ? '(我方号)' : ''}`);
        if (nBot > 0) {
          FL.n++;
          if (canHit === 0) {
            FL.locked++;
            const cls = !best ? '无(其它原因)' : best.who < 0 ? '?' : globalThis.__SQ.has(best.who) ? '我方号' : best.who < R0.H ? '其他真人' : '机器人';
            FL.setter[cls] = (FL.setter[cls] || 0) + 1;
            if (best && best.need >= B) FL.fullLock++;
            // 留底本身是否是卡住的原因：safeFinite ≥ 一半存兵才算「留底锁」；否则是别的门槛（开局 DP 预留、allow 等）
            if (sb >= 0.5 * B && best) {
              FL.half++;
              const w = best.who;
              const c2 = w < 0 ? '?' : globalThis.__SQ.has(w) ? '我方号' : w >= R0.H ? '机器人' : (g.teams && g.teams[p] > 0 && g.teams[w] === g.teams[p]) ? '路人队友' : '敌方真人';
              FL.halfSetter[c2] = (FL.halfSetter[c2] || 0) + 1;
            } else FL.lowFloor++;
          }
          FL.botLand += botLand;
        }
        if (!args.includes('--quiet')) console.log(`[留底] t=${t} ${b.name} 兵 ${B} 地 ${g.terr[p]}｜相邻机器人 ${nBot} 个（共 ${botLand} 格，其中几乎没兵的 ${nBotCheap} 个）｜safeFinite=${Math.round(sb)}（${sb >= B ? '≥ 全部存兵' : (100 * sb / Math.max(1, B)).toFixed(0) + '% 存兵'}）${best ? `由 机器人#${best.q}（地 ${g.terr[best.q]} 兵 ${g.bal[best.q]}）决定：它的其它邻居里最弱的是 ${whoTag} 兵 ${best.need}` : ''}｜此刻过得了留底的机器人目标 ${canHit} 个`);
      }
      if (donT.has(t)) { try { donProbe(g, b.policy, p, b.name); } catch (e) { console.log(`调度候选探针异常 ${b.name}: ${e.message}`); } }
      if (offT.has(t)) { try { offersProbe(g, b.policy, p, b.name); } catch (e) { console.log(`报价探针异常 ${b.name}: ${e.message}`); } }
      if (nbT.has(t)) {
        const pol = b.policy;
        console.log(`\n-- 邻居报价 ${b.name} t=${t} 地 ${g.terr[p]} 兵 ${B} 密度 ${(B / Math.max(1, g.terr[p])).toFixed(1)} neutral=${pol.neutral} idle=${pol.idle ? pol.idle(g) : '?'} held=${pol.held}`);
        let fl = null;
        try { fl = pol.floors(g); } catch {}
        const minCmd = pol.minCmd ? pol.minCmd(g) : NaN;
        let extra = '';
        try { extra = ` dpKeep=${Math.round(pol.dpKeep(g))} peopleFloor=${Math.round(pol.peopleFloor(g))} floorAt(2)=${fl ? Math.round(fl.floorAt(2)) : '?'} cap=${fl ? Math.round(fl.cap) : '?'} minCmd=${Math.round(minCmd)} floorK=${pol.floorK}`; } catch (e) { extra = ' (' + e.message + ')'; }
        console.log('  ' + extra);
        for (const q of pol.nb || []) {
          if (!g.alive[q] || !g.terr[q]) continue;
          let price = NaN, ok = '?', al = '?', elim = NaN, floor = NaN, ms = NaN, need = NaN, amt = NaN, wf = NaN;
          try { price = pol.price(g, q); } catch {}
          try { ok = pol.person(g, q) ? '-' : pol.botOk(g, q); } catch {}
          try { al = pol.allow(g, q); } catch {}
          try { elim = pol.elimCost(g, q); } catch {}
          try { floor = pol.floorFor(g, q, fl.floorAt(price)); } catch {}
          try { ms = pol.minShare(g, q); } catch {}
          try { wf = pol.winFloor ? pol.winFloor(g, q) : NaN; } catch {}
          try { need = elim + g.attackTroopsOn(q, p) - g.attackTroopsOn(p, q); amt = pol.amount(g, q, B - floor, need, minCmd); } catch {}
          const avail = B - floor;
          const why = !al ? 'allow=false' : price > pol.p.maxCost ? 'price>maxCost' : (avail <= ms * B || avail < minCmd) ? `可用兵不够（可用 ${Math.round(avail)} ≤ max(minShare×兵=${Math.round(ms * B)}, minCmd=${Math.round(minCmd)})）` : need <= 0 ? 'need<=0' : !(amt >= minCmd) ? 'send<minCmd' : `可打：发 ${Math.round(amt)}`;
          console.log(`   ${q >= R0.H ? '机器人#' + q : R0.tag(q)} 地 ${g.terr[q]} 兵 ${g.bal[q]} 密度 ${(g.bal[q] / Math.max(1, g.terr[q])).toFixed(1)} 接触 ${pol.cnt?.[q]}｜每格价 ${price.toFixed ? price.toFixed(1) : price} botOk ${ok} allow ${al}｜吃掉需 ${Math.round(need)}｜留底 ${Math.round(floor)}（winFloor ${Math.round(wf)}）→ ${why}`);
        }
      }
    }
    curBot = null;
  },
});

if (!args.includes('--quiet')) for (const b of bots) {
  console.log(`\n== 影子 ${b.name}#${b.p} 槽位 ${b.slot}（${ver}）异常 ${b.err} 次 ==`);
  for (const [w, W] of [...b.wins.entries()].sort((a, c) => a[0] - c[0])) {
    const sigs = [...W.sig.entries()].sort((a, c) => c[1] - a[1]).slice(0, 5).map(([s, n]) => `${n}×[${s}]`).join('  ');
    const cm = [...W.cmds.entries()].sort((a, c) => c[1][0] - a[1][0]).slice(0, 6).map(([k, [n, tr]]) => `${k}×${n}(${Math.round(tr / 1000)}k)`).join(' ');
    console.log(`t=${w}-${w + WIN - 1} 决策拍 ${W.n}｜影子指令 ${cm || '无'}｜${sigs}`);
  }
}
if (midsFn) {
  for (const [key, M] of [...MIDS.entries()].sort((a, c) => (a[0].split('|')[0] === c[0].split('|')[0] ? +a[0].split('|')[1] - +c[0].split('|')[1] : a[0] < c[0] ? -1 : 1))) {
    const f = (m) => [...m.entries()].sort((a, c) => c[1] - a[1]).map(([l, n]) => `${l}×${n}`).join(' ');
    console.log(`[分支命中 ${midsFn}] ${key.replace('|', ' t=')}–${+key.split('|')[1] + WIN - 1} 调用 ${M.n} 次｜出口行 ${f(M.exit)}｜途中 continue 行（按拍去重）${f(M.mid) || '无'}`);
  }
}
if (args.includes('--match')) {
  // 策略自报 cmds=（[HL-TICK] 每 90 拍一条）
  const real = new Map();
  for (const line of fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n')) {
    const m = /\[([^\]]+)\] \[HL-TICK\] t=(\d+) .*? cmds=(\d+)/.exec(line);
    if (m) { if (!real.has(m[1])) real.set(m[1], []); real.get(m[1]).push([+m[2], +m[3]]); }
  }
  const med = (a) => { if (!a.length) return NaN; const b = [...a].sort((x, y) => x - y); return b[b.length >> 1]; };
  const tot = { iss: 0, rep: 0, ex: 0, mt: 0, st: [], lost: 0 };
  const outRows = [];
  for (const b of bots) {
    const idx = new Map();
    for (const c of b.issued) { const k = `${c.k}|${c.k === 'boat' ? '' : c.q}|${c.pct}`; if (!idx.has(k)) idx.set(k, []); idx.get(k).push(c.t); }
    const stale = [], rows = [];
    let matched = 0;
    for (const e of b.exec) {
      const arr = idx.get(`${e.k}|${e.k === 'boat' ? '' : e.q}|${e.pct}`);
      let best = -1;
      if (arr) { let lo = 0, hi = arr.length - 1; while (lo <= hi) { const mi = (lo + hi) >> 1; if (arr[mi] <= e.T) { best = arr[mi]; lo = mi + 1; } else hi = mi - 1; } }
      e.t0 = best;
      if (best >= 0) { matched++; stale.push(e.T - best); }
    }
    const rl = real.get(b.name) || [];
    const lastLog = rl.length ? rl[rl.length - 1] : [0, 0];
    const issTill = b.issued.filter((c) => c.t <= lastLog[0]).length;
    const exTill = b.exec.filter((e) => e.T <= lastLog[0] + 14).length;
    // 每 300 拍：影子想发 / 录像执行 / 陈旧度中位
    const W = new Map();
    for (const c of b.issued) { const w = Math.floor(c.t / 300) * 300; if (!W.has(w)) W.set(w, { i: 0, e: 0, st: [] }); W.get(w).i++; }
    for (const e of b.exec) { const w = Math.floor(e.T / 300) * 300; if (!W.has(w)) W.set(w, { i: 0, e: 0, st: [] }); const x = W.get(w); x.e++; if (e.t0 >= 0) x.st.push(e.T - e.t0); }
    for (const [w, x] of [...W.entries()].sort((a, c) => a[0] - c[0])) rows.push(`${w}:${x.i}/${x.e}${x.st.length ? '/' + med(x.st) : ''}`);
    // 同拍 ≥3 条的批：它们对应的影子决策拍范围
    const byT = new Map();
    for (const e of b.exec) { if (!byT.has(e.T)) byT.set(e.T, []); byT.get(e.T).push(e); }
    const batches = [];
    for (const [T, arr] of byT) if (arr.length >= 3) { const ts = arr.map((e) => e.t0).filter((x) => x >= 0); batches.push(`${T}×${arr.length}${ts.length ? `←决策拍 ${Math.min(...ts)}–${Math.max(...ts)}（陈旧 ${T - Math.max(...ts)}–${T - Math.min(...ts)}）` : '←无匹配'}`); }
    console.log(`[下发对账] ${b.name}: 影子想发 ${issTill}（到最后一条日志 t=${lastLog[0]}；全程 ${b.issued.length}）｜策略自报 cmds=${lastLog[1]}｜录像执行 ${exTill}（全程 ${b.exec.length}）｜能对上影子决策 ${matched}/${b.exec.length}，陈旧度 中位 ${med(stale)} 最大 ${stale.length ? Math.max(...stale) : '-'} 拍，≥90 拍的 ${stale.filter((x) => x >= 90).length} 条｜isNoFullSend 首次置真 t=${b.lockT}，其后 send 因它拒发 ${b.guard} 次`);
    if (!args.includes('--brief')) {
      console.log(`    每 300 拍 影子想发/录像执行/陈旧度中位：${rows.join(' ')}`);
      if (batches.length) console.log(`    同拍连发批：${batches.join('；')}`);
    }
    tot.iss += issTill; tot.rep += lastLog[1]; tot.ex += exTill; tot.mt += matched; tot.st.push(...stale);
    outRows.push({ bot: b.name, shadowIssued: issTill, reportedCmds: lastLog[1], executed: exTill, executedAll: b.exec.length, matched, staleMedian: med(stale), staleMax: stale.length ? Math.max(...stale) : null, staleGE90: stale.filter((x) => x >= 90).length, lockT: b.lockT, guardRefusals: b.guard });
  }
  console.log(`[下发对账汇总] ${mid}: 影子想发 ${tot.iss}｜策略自报 ${tot.rep}｜录像执行 ${tot.ex}（${(100 * tot.ex / Math.max(1, tot.rep)).toFixed(0)}%）｜已执行指令能对上影子决策 ${tot.mt}，陈旧度中位 ${med(tot.st)} 拍、≥90 拍 ${tot.st.filter((x) => x >= 90).length} 条、≥300 拍 ${tot.st.filter((x) => x >= 300).length} 条`);
  if (args.includes('--match-json')) fs.writeFileSync(val('--match-json'), JSON.stringify({ mid, ver, bots: outRows }));
}
if (PER_TICK > 0) {
  const cls = (c) => (c.k === 'donate' ? '捐兵' : c.k !== 'attack' ? '出船' : c.q === NEUTRAL ? '打中立' : c.q >= R0.H ? '打机器人' : '打真人');
  const by = new Map(), perBot = new Map(), win = new Map();
  for (const d of DROPS) {
    const k = `${cls(d.by)}${d.by.k === 'attack' && d.by.q === NEUTRAL ? `(pct=${d.by.pct})` : ''} 挤掉 ${cls(d.c)}`;
    const e = by.get(k) || [0, 0]; e[0]++; e[1] += d.c.troops || 0; by.set(k, e);
    perBot.set(d.bot, (perBot.get(d.bot) || 0) + 1);
    if (cls(d.c) === '打真人') { const w = `${d.bot} ${Math.floor(d.t / 300) * 300}`; const x = win.get(w) || [0, 0, new Set()]; x[0]++; x[1] += d.c.troops || 0; x[2].add(R0.tag(d.c.q)); win.set(w, x); }
  }
  console.log(`[每拍限 ${PER_TICK} 条] ${mid}: 被挤掉的指令 ${DROPS.length} 条｜${[...by.entries()].sort((a, c) => c[1][0] - a[1][0]).map(([k, [n, tr]]) => `${k} ×${n}（想出 ${Math.round(tr / 1000)}k）`).join('；') || '无'}`);
  console.log(`    按号：${[...perBot.entries()].sort((a, c) => c[1] - a[1]).map(([k, n]) => `${k} ${n}`).join(' ') || '无'}`);
  const ws = [...win.entries()].sort((a, c) => c[1][0] - a[1][0]).slice(0, 12);
  if (ws.length) console.log(`    被挤掉的「打真人」按 号×300 拍（前 12）：${ws.map(([k, [n, tr, tg]]) => `${k}: ×${n}（${Math.round(tr / 1000)}k → ${[...tg].join('/')}）`).join('；')}`);
}
if (floorT.size) console.log(`[留底汇总] ${mid} 采样拍 ${[...floorT].join(',')}｜有相邻机器人的(号×拍)样本 ${FL.n}｜其中没有任何机器人目标过得了留底 ${FL.locked}（${(100 * FL.locked / Math.max(1, FL.n)).toFixed(0)}%），留底≥全部存兵 ${FL.fullLock}｜锁死样本里定留底的「最弱其它邻居」：${Object.entries(FL.setter).map(([k, v]) => `${k} ${v}`).join('，')}｜其中 safeFinite ≥ 一半存兵（留底是卡住的原因）${FL.half} 个，按定留底的邻居：${Object.entries(FL.halfSetter).map(([k, v]) => `${k} ${v}`).join('，')}；safeFinite < 一半存兵却仍无目标（别的门槛）${FL.lowFloor} 个`);
if (args.includes('--json')) { fs.writeFileSync(val('--json'), JSON.stringify({ mid, ver, ticks: ticksOut, logs, tc: tcOut, tcWin: TC })); console.log(`→ ${val('--json')}${TC ? `（决策拍分类 ${tcOut.length} 行，窗口 ${TC.join('–')}）` : ''}`); }
