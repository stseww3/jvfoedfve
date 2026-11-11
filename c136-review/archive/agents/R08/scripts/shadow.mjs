// shadow.mjs — 「影子决策」：在真引擎逐拍重演（resim_r08.mjs）的每一拍，把干净策略源码原样跑一遍，
// 但它发出的指令只记录、不执行。得到「策略代码在这一拍的真实局面下想做什么」，再与录像里真正执行的指令对照。
//
// 用途：
//   1. 回答「为什么这一拍没出手 / 为什么出了这一手」——可在指定拍打印 pickTarget 的逐邻居门槛拆解（--trace）；
//   2. 检查内部状态（isNoFullSend、shadowQuota、cmds 计数）在真实余额轨迹下怎么演变；
//   3. 量化「客户端滞后」：影子在 t 拍发的指令，录像里哪一拍才执行。
//
// 局限（务必写进引用它的结论里）：
//   · 影子看不到客户端滞后——它代表「不滞后的客户端」；驱动层的 inflight 节流按「发过指令后 8 拍内不调用策略」近似（--guard，
//     依据策略文件头第 19~31 行对 strategyBot.afterTick 的包装；B043 上开启后影子 cmds 计数与真机 HL-TICK 的 cmds 计数基本逐条一致）；
//   · 影子指令不执行，所以内部计数（cmds、lastBoat 等）按「本地认为已发出」推进，与真机一致的前提是真机本地校验也通过；
//   · 影子从开局拍起连续带状态运行（--fresh 则每个探测拍新建实例，只看无状态门槛）。
//
// 用法：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/shadow.mjs <matchId>
//        [--replay-from <mid2>] [--peer <mid2> | --peer-tag <标签>] [--strategy c110|g09|c116-vb] [--bots 名1,名2|all]
//        [--until T] [--trace 名:t1,t2;名2:t3] [--quiet]
// 输出：out/<matchId>/shadow.json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');
const NEUTRAL = 512;
const T_LAND = 1, P_INNER = 16;   // sim/map.js L11、sim/game.js L11

function ensureStrategy(name) {
  const runDir = path.join(OUT, '_run');
  const dst = path.join(runDir, 'a', 'b', `v27-team-${name}.js`);
  const src = path.join(DATA, 'src/strategy', `v27-team-${name}.js`);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  const link = path.join(runDir, 'sim');
  if (!fs.existsSync(link)) fs.symlinkSync(path.join(DATA, 'src/sim/sim'), link);
  if (!fs.existsSync(dst) || fs.statSync(dst).size !== fs.statSync(src).size) fs.copyFileSync(src, dst);
  return dst;
}

const args = process.argv.slice(2);
const mid = args[0];
if (!mid) { console.error('用法见文件头'); process.exit(2); }
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const stratName = opt('strategy', args.includes('--side') && opt('side') === 'peer' ? 'c116-vb' : mid.startsWith('G') ? 'g09' : mid.startsWith('B') ? 'c110' : 'c116-vb');
const stratFile = ensureStrategy(stratName);
const { Policy } = await import(stratFile);
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));

const wantBots = opt('bots', 'all');
const side = opt('side', 'own');          // own：本编队；peer：同房另一支编队（策略用 --strategy 指定）
const censusUntil = +opt('census-until', 1800);
const censusEvery = +opt('census-every', 10);
const coreCensusUntil = +opt('core-census-until', 3000);   // 1500 拍后的买地口径普查（censusCore）做到哪一拍
const guardTicks = +opt('guard', 8);     // 模拟驱动层 inflight 节流：某拍发过指令后，接下来 guardTicks 拍内不调用策略（0=不模拟）
// --walk-every N：从 --walk-from（默认策略的 coreFrom）起每 N 拍对每个在线号重走一遍 buyLand（walkBuyLand，不发指令），逐报价记结论，
// 写进 bots[名].walks。要和 --tag 一起用（例如 --tag walk），不覆盖主产物；gatecensus.py 读它。
const walkEvery = +opt('walk-every', 0);
const walkFrom = +opt('walk-from', 0);
const traceSpec = {};
for (const part of String(opt('trace', '')).split(';').filter(Boolean)) {
  const i = part.lastIndexOf(':');
  traceSpec[part.slice(0, i)] = new Set(part.slice(i + 1).split(',').map(Number));
}
const fresh = args.includes('--fresh');
const bots = [];
const ownIds = new Set(), peerIds = new Set();
let names = null;
const traces = [];

const CMD_KEYS = ['attack', 'boatTo', 'boat', 'donate', 'retreat', 'recall', 'chase'];

function patch(g, b) {
  const p = b.id;
  const rec = (kind, a, b2, ok, extra) => { b.cmds.push([g.t, kind, a, b2, ok ? 1 : 0, extra ?? 0, g.bal[p], g.terr[p]]); return ok; };
  g.attack = (pct, target, who = p) => {
    let tg = Math.min(target, NEUTRAL);
    if (tg < NEUTRAL && g.alive[tg] === 0) tg = NEUTRAL;
    let ok = g.canAct(who) && who !== target;
    if (ok && tg < NEUTRAL && !g.isEnemy(who, tg)) ok = false;
    if (ok && !g.hasAttack(who, tg) && !g.hasFreeSlot(who)) ok = false;
    return rec(1, pct | 0, tg, ok);
  };
  g.boatTo = (pct, target, who = p, radius = 32) => {
    let ok = g.canAct(who) && g.boatsAllowed(who);
    let s = null;
    if (ok) { s = b.boatSpot.call(g, target, who, radius); ok = s !== null; }
    const o = ok && g.px[target] >= 5 ? g.own[target] : NEUTRAL;
    return rec(3, pct | 0, target, ok, o);
  };
  g.boat = (pct, water, dir, who = p) => rec(3, pct | 0, water, g.canAct(who) && g.boatsAllowed(who), -1);
  g.donate = (pct, q, who = p) => rec(2, pct | 0, q, !!(g.teamGame && g.canAct(who) && who !== q && q < NEUTRAL && g.alive[q] !== 0 && g.isTeammate(who, q)));
  g.retreat = (target, who = p) => rec(5, 0, Math.min(target, NEUTRAL), g.canAct(who) && g.hasAttack(who, Math.min(target, NEUTRAL)));
  g.recall = (id, who = p) => rec(4, 849, id, true);
  g.chase = (pct, id, who = p) => rec(4, pct | 0, id, true);
}
function unpatch(g) { for (const k of CMD_KEYS) delete g[k]; }

// safeFinite（防人机留底 sb）是谁定的：逐个接壤的内置 AI 重做一遍 threatOf（c110 L464-490），取出「该 AI 除我之外最弱的邻居」。
// sb = max over 接壤 AI ( 该邻居的余额 + 它压在这个 AI 上的兵 − 我压在这个 AI 上的兵 )；返回定出 sb 的那个 AI 与那个邻居。
function sbSource(g, pol) {
  const me = pol.me, px = g.px, own = g.own, d = g.dir4;
  let best = null;
  for (const q of pol.nb) {
    if (g.alive[q] === 0 || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
    const B = g.border[q];
    const busyNeutral = g.hasAttack(q, NEUTRAL);
    let minOther = Infinity, who = -1, neutral = false;
    const seen = new Set();
    const n = B.length, step = n > 1024 ? Math.ceil(n / 1024) : 1;
    outer: for (let i = n - 1; i >= 0; i -= step) {
      const b0 = B[i];
      for (let k = 0; k < 4; k++) {
        const c = b0 + d[k], v = px[c];
        if (v === T_LAND) { if (!busyNeutral) { neutral = true; break outer; } continue; }
        if (v < P_INNER) continue;
        const o = own[c];
        if (o === q || o === me || seen.has(o)) continue;
        seen.add(o);
        if (g.hasAttack(q, o)) continue;
        const sv = g.bal[o] + g.attackTroopsOn(o, q);
        if (sv < minOther) { minOther = sv; who = o; }
      }
    }
    if (neutral || !Number.isFinite(minOther)) continue;
    const v = minOther - g.attackTroopsOn(me, q);
    if (!best || v > best.v) best = { v: Math.round(v), ai: q, who, whoBal: g.bal[who], whoTerr: g.terr[who] };
  }
  return best;
}
function whoCat(g, me, o) {
  if (o < 0) return 'none';
  if (o >= g.humans) return 'ai';
  if (ownIds.has(o)) return g.teams[o] === g.teams[me] ? 'squadSameTeam' : 'squadOtherTeam';
  if (peerIds.has(o)) return g.teams[o] === g.teams[me] ? 'peerSameTeam' : 'peerOtherTeam';
  return g.teams[o] === g.teams[me] ? 'teammate' : 'enemy';
}

// 口粮门槛普查：对「接壤的内置 AI」逐个按 pickTarget 的顺序过一遍门槛，记下最便宜那个 AI 被哪一关挡住。
function census(g, b) {
  const pol = b.pol, me = b.id, P = pol.p;
  try {
    pol.analyze(g);
    const fl = pol.floors(g);
    const bal = g.bal[me], min = pol.minCmd(g);
    let best = null, anyOk = 0, nAi = 0;
    const per = [];   // 逐个接壤的内置 AI：[号, 被哪一关挡住]（landcap.py 的逐格归因用）
    for (const q of pol.nb) {
      if (g.alive[q] === 0 || g.terr[q] === 0 || pol.person(g, q)) continue;
      const price = pol.price(g, q);
      nAi++;
      let why = 'ok';
      const allow = pol.allow(g, q);
      const need = pol.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
      const floor = pol.floorFor(g, q, fl.floorAt(price));
      const avail = bal - floor;
      if (!allow) why = pol.botOk && !pol.botOk(g, q) ? 'botOk(winWorth)' : 'allow';
      else if (price > P.maxCost) why = 'maxCost';
      else if (avail < min || avail <= pol.minShare(g, q) * bal) {
        const sb = pol.safeFinite ? pol.safeFinite(g) : 0;
        const dk = pol.dpKeep ? pol.dpKeep(g) : 0;
        const pf = pol.peopleFloor ? pol.peopleFloor(g) : 0;
        const top = Math.max(sb, dk, pf);
        const tag = floor <= 0 ? 'none' : Math.abs(floor - sb) < 1 ? 'sb' : Math.abs(floor - dk) < 1 ? 'dpKeep' : Math.abs(floor - pf) < 1 ? 'peopleFloor' : top < floor ? 'winPrice' : 'other';
        why = avail <= 0 ? `floor:${tag}` : `minShare(floor:${tag})`;
      } else if (need <= 0) why = 'need<=0';
      else if (!g.hasAttack(me, q) && !g.hasFreeSlot(me)) why = 'slots';
      if (why === 'ok') anyOk++;
      per.push([q, why]);
      if (best && price >= best.price) continue;
      best = { q, price: +price.toFixed(1), terr: g.terr[q], aiBal: g.bal[q], need: Math.round(need), floor: Math.round(floor), avail: Math.round(avail), why };
    }
    let src = null;
    if ((best && /floor:sb/.test(best.why)) || per.some((x) => /floor:sb/.test(x[1]))) { const sbs = sbSource(g, pol); if (sbs) src = [sbs.ai, sbs.who, whoCat(g, me, sbs.who), sbs.whoBal, sbs.whoTerr, sbs.v]; }
    b.census.push([g.t, bal, g.terr[me], pol.neutral, best ? best.q : -1, best ? best.price : 0, best ? best.terr : 0, best ? best.aiBal : 0, best ? best.need : 0, best ? best.floor : 0, best ? best.why : 'noAI', src, nAi, anyOk, per]);
  } catch (e) { if (b.errors.length < 20) b.errors.push([g.t, 'census ' + String(e).slice(0, 200)]); }
}

// 1500 拍后（coreFrom 起）的口粮门槛普查：按 Policy.buyLand（c110 L5250-5369）对「非真人邻居」的那条路逐关重算，
// 记下最便宜那个内置 AI 报价被哪一关挡住：
//   price   = 排在它前面（含它自己）已经有报价 c ≥ worth 且不 over → L5267 break
//   safe:*  = 可用兵 B − fee − max(keep, safe) ≤ 0，且起作用的是 safe（safeAt → safeFinite 即 sb / killKeep 等，非真人目标再按 oppFloorCap×L 封顶）
//   keep    = 同上但起作用的是按报价算的 keep（L5330-5335）
//   minCmd(want) = 吃光它所需 want = 1.25×need + 3×边界 本身就小于 minCmd（feeK×12/1024×余额）→ L5367 跳过
//   minCmd(avail) / chunk = 可用兵不够 minCmd，或不够 want 且小于 chunk×余额
//   attacking = 已经有兵压在它身上（L5364）
const iVf = (a, c) => Math.floor((a + 0.5) / c);
function censusCore(g, b) {
  const pol = b.pol, me = b.id, P = pol.p;
  try {
    pol.analyze(g);
    const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iVf(12 * B, 1024), dMe = B / L;
    const dMed = pol.otherHumanMedDens(g);
    const m = P.maxW * pol.winRatio(g.t);
    const refDens = dMed !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe;
    const worth = m * refDens, over = P.surplus > 0 && B > 100 * L, cheap = P.growth > 0 ? 0.1 / pol.baseRate(g) : 0;
    const minCmd = pol.minCmd(g);
    let nAi = 0, anyOk = 0, best = null, gated = false, nAiNb = 0;
    let sumNeed = 0, sumTerr = 0, sumBal = 0, maxWant = 0, nZero = 0;   // 所有非真人报价合计：吃光所需、格数、兵；单个最大的 want；0 兵的个数
    for (const q of pol.nb) if (g.alive[q] && g.terr[q] > 0 && !pol.person(g, q)) nAiNb++;
    for (const o of pol.offers(g)) {
      const { q, c, need, person } = o;
      if (c >= worth && c >= cheap && !over) gated = true;
      if (person || o.isDoorSea) continue;
      nAi++;
      sumNeed += Math.max(0, need); sumTerr += g.terr[q]; sumBal += g.bal[q];
      maxWant = Math.max(maxWant, 1.25 * need + 3 * pol.cnt[q]);
      if (g.bal[q] === 0) nZero++;
      let why, x = 0, want = 0, safe = 0, keep = Infinity, tag = '';
      if (gated) why = 'price';
      else {
        safe = Math.min(pol.safeAt(g, q), P.oppFloorCap * L);
        if (c < cheap) keep = 0;
        if (c < worth) {
          const worthOwn = P.ownWorthMinKeep > 0 && g.t >= P.ownWorthFrom && !o.nearCollapse ? m * dMe : worth;
          const budget = Math.max(0, (worthOwn * L - fee * m - c * L) / (1 + m));
          const minKeep = (c * L) / m;
          keep = Math.min(keep, P.post > 0 ? Math.max(minKeep, B - fee - budget) : minKeep);
        }
        if (over) keep = Math.min(keep, (o.isCrowdedHard ? 1.08 : P.hold) * 100 * L);
        const byKeep = keep >= safe;
        const avail = B - fee - Math.max(keep, safe);
        want = 1.25 * need + 3 * pol.cnt[q];
        x = Math.min(avail, want);
        if (avail <= 0) {
          if (byKeep) why = 'keep';
          else {
            const sf = pol.safeFinite ? pol.safeFinite(g) : 0;
            tag = Math.abs(safe - Math.min(sf, P.oppFloorCap * L)) < 1 ? (sf > P.oppFloorCap * L ? 'sb(cap)' : 'sb') : 'people';
            why = `safe:${tag}`;
          }
        } else if (g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) why = 'attacking';
        else if (x < minCmd) why = want < minCmd ? 'minCmd(want)' : 'minCmd(avail)';
        else if (x < want && x < P.chunk * B) why = 'chunk';
        else why = 'ok';
      }
      if (why === 'ok' || why === 'attacking') anyOk++;
      if (best && c >= best.c) continue;
      best = { q, c: +(+c).toFixed(1), terr: g.terr[q], aiBal: g.bal[q], need: Math.round(need), want: Math.round(want), x: Math.round(x), safe: Math.round(safe), keep: Number.isFinite(keep) ? Math.round(keep) : -1, why };
    }
    let src = null;
    if (best && /^safe:sb/.test(best.why)) { const sbs = sbSource(g, pol); if (sbs) src = [sbs.ai, sbs.who, whoCat(g, me, sbs.who), sbs.whoBal, sbs.whoTerr, sbs.v]; }
    b.census2.push([g.t, B, g.terr[me], nAiNb, nAi, anyOk, best ? best.q : -1, best ? best.c : 0, best ? best.terr : 0, best ? best.aiBal : 0, best ? best.need : 0, best ? best.want : 0, best ? best.x : 0,
      Math.round(minCmd), best ? best.safe : 0, best ? best.keep : 0, best ? best.why : (nAiNb ? 'noOffer' : 'noAI'), src, +worth.toFixed(1), over ? 1 : 0,
      Math.round(sumNeed), sumTerr, sumBal, Math.round(maxWant), nZero]);
  } catch (e) { if (b.errors.length < 20) b.errors.push([g.t, 'census2 ' + String(e).slice(0, 200)]); }
}

// 把 Policy.buyLand（c110 L5250-5534）的循环照抄一遍但不发指令：逐个报价记下每一关的数和结论，直到第一个会发出去的为止。
// 照抄范围：价格截断 L5265、唯一缓冲 L5267-5271、小目标手续费 L5273、拥挤硬顶 L5277-5280、吸波 L5282、留底 safe/keep L5322-5358、
// 非真人分支 L5363-5368、脉冲块三个分支（L5505-5519 nearCollapse/bleeding、L5521-5526 nearCollapse、L5528-5540 pulseMode）的金额与门槛、
// 末尾整笔 L5543-5548。没照抄的：海上门（isDoorSea，记为 doorSea 跳过）、窄边先发船（seaCore=0 时不生效）、零兵脉冲（只在离线生效）、
// 多圈对齐 alignMultiRing（只会把金额往下修，不改变「发不发」以外的结论，记 amount 时注明是修整前）。
const iV = (a, b) => Math.floor((a + 0.5) / b);   // 和引擎 game.js L30 的 iV 一致
function walkBuyLand(g, pol) {
  const P = pol.p, me = pol.me;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iV(12 * B, 1024);
  const dMe = B / L;
  const dMedOther = pol.otherHumanMedDens(g);
  const nHumans = pol.livingHumanCount(g);
  const humanNbCount = pol.nb.filter((p) => g.alive[p] && pol.person(g, p)).length;
  const m = P.maxW * pol.winRatio(g.t);
  const refDens = dMedOther !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMedOther) : dMe;
  const worth = m * refDens;
  const over = P.surplus > 0 && B > 100 * L;
  const cheap = P.growth > 0 ? 0.1 / pol.baseRate(g) : 0;
  const minCmd = pol.minCmd(g);
  const rows = [];
  for (const o of pol.offers(g)) {
    const { q, c, need, person } = o;
    const r = { q, name: q < g.humans ? names[q] : `AI${q}`, person: !!person, c: +(+c).toFixed(1), need: Math.round(need), cnt: pol.cnt[q] ?? 0, terr: g.terr[q], bal: g.bal[q] };
    for (const k of ['nearCollapse', 'bleeding', 'onMe', 'isCrowdedHard', 'isDoorSea', 'pulseMode', 'isAgg']) if (o[k]) r[k] = 1;
    rows.push(r);
    if (c >= worth && c >= cheap && !over) { r.v = 'break:price>=worth'; break; }
    const isSoleHealthyBuffer = person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1;
    if (isSoleHealthyBuffer && c >= worth && c >= cheap && B < P.overHumanCap * 100 * L) { r.v = 'skip:soleBuffer'; continue; }
    if (person && !o.isDoorSea && g.terr[q] < 250 && fee > 2 * need && c > 8 * worth && nHumans >= 3) { r.v = 'skip:tinyFee'; continue; }
    const hardCapMult = o.isCrowdedHard && c >= 2.15 * worth && g.bal[q] >= 0.55 * B ? 1.50 : P.crowdedHardCap;
    if (person && !o.isDoorSea && o.isCrowdedHard && c >= worth && c >= cheap && B < hardCapMult * 100 * L) { r.v = `skip:crowdedHard(<${hardCapMult}x100xL)`; continue; }
    if (P.absorbMode >= 1 && person && !o.isDoorSea && !o.nearCollapse && (o.inAtk ?? 0) >= P.absorbWaveMin * B) { r.v = 'skip:absorb'; continue; }
    if (o.isDoorSea) { r.v = 'skip:doorSea(没照抄)'; continue; }
    let safe = pol.safeAt(g, q);
    r.safeRaw = Math.round(safe);
    if (!person || o.nearCollapse || (P.bleedSafeCap > 0 && (o.bleeding || o.tD < 0.45))) {
      const capPerPx = person && o.nearCollapse && (o.inAtk ?? 0) < 0.02 * B && ((c < 0.25 * worth && need <= 0.10 * B) || (g.bal[q] <= 0.05 * B && c < 25)) ? Math.min(P.oppFloorCap, P.collapseFloorCap ?? 85) : P.oppFloorCap;
      safe = Math.min(safe, capPerPx * L);
    }
    let keep = Infinity;
    if (c < cheap) keep = 0;
    if (c < worth) {
      const worthOwn = P.ownWorthMinKeep > 0 && g.t >= P.ownWorthFrom && !o.nearCollapse ? m * dMe : worth;
      const budget = Math.max(0, (worthOwn * L - fee * m - c * L) / (1 + m));
      const minKeep = person && (o.nearCollapse || (P.bleedDiscount < 1 && o.bleeding) || (P.thinDiscount < 1 && o.tD < P.thinMaxTD)) ? (0.70 * c * L) / m : (c * L) / m;
      keep = Math.min(keep, P.post > 0 ? Math.max(minKeep, B - fee - budget) : minKeep);
    }
    const isSiegeShrink = P.siegeShrinkRatio > 0 && !pol.isNoFullSend && g.t >= P.leaderHardFrom && L < P.siegeShrinkRatio * (g.peak?.[me] ?? L) && nHumans >= 4 && person && !o.nearCollapse && !o.bleeding;
    if (isSiegeShrink && c >= worth && c >= cheap && B < P.crowdedHardCap * 100 * L) { r.v = 'skip:siegeShrink'; continue; }
    r.keepPrice = Number.isFinite(keep) ? Math.round(keep) : null;
    if (over) {
      const overKeepMult = isSoleHealthyBuffer ? P.overHumanKeep : isSiegeShrink ? P.siegeOverKeep : o.isCrowdedHard ? 1.08 : P.hold;
      keep = Math.min(keep, overKeepMult * 100 * L);
      r.overKeep = Math.round(overKeepMult * 100 * L);
    }
    keep = Math.max(keep, safe);
    const avail = B - fee - keep;
    r.safe = Math.round(safe); r.keep = Number.isFinite(keep) ? Math.round(keep) : null; r.avail = Number.isFinite(avail) ? Math.round(avail) : null;
    if (avail <= 0) { r.v = `skip:avail<=0(${keep === safe ? 'safe' : 'keep'})`; continue; }
    if (!person) {
      if (g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) { r.v = 'skip:attacking'; continue; }
      const want = 1.25 * need + 3 * pol.cnt[q];
      const x = Math.min(avail, want);
      r.want = Math.round(want); r.x = Math.round(x);
      if (x < minCmd) { r.v = `skip:x<minCmd(${minCmd})`; continue; }
      if (x < want && x < P.chunk * B) { r.v = 'skip:chunk'; continue; }
      r.v = 'SEND'; break;
    }
    const usePulseBlock = P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));
    const inAtk = o.inAtk ?? 0;
    const curAtk = g.attackTroopsOn(me, q);
    r.inAtk = Math.round(inAtk); r.curAtk = curAtk; r.pulse = usePulseBlock ? 1 : 0;
    const blockUndersized = (amt) => {
      if (P.counterClearMode === 6) return false;
      if (!(P.counterClearMode >= 1) || o.nearCollapse || !(inAtk > 0) || !(curAtk + amt <= 1.05 * inAtk)) return false;
      if (P.counterClearMode >= 3 && o.bleeding) return false;
      if (P.counterClearMode >= 4 && g.t < 3500) return false;
      return true;
    };
    const pulseMin = Math.max(minCmd, P.pulseMinShare * B);
    if (usePulseBlock) {
      if (g.t >= 3800 && (o.nearCollapse || o.bleeding || (P.aggMemMode === 2 && o.isAgg))) {
        if (curAtk >= 0.08 * B || curAtk >= 0.65 * need) { r.v = 'skip:pulseA:alreadyOn'; continue; }
        const targetSlot = Math.min(0.85 * need + 3 * pol.cnt[q], Math.floor(P.pulseFrac * B));
        let pulse = Math.min(avail, Math.max(targetSlot - curAtk, Math.floor(0.08 * B)));
        if (P.counterClearMode === 2 && !o.nearCollapse && inAtk > 0 && curAtk + pulse <= 1.05 * inAtk) pulse = Math.min(avail, Math.min(Math.floor(0.28 * B), Math.ceil(1.05 * inAtk - curAtk + 0.05 * B)));
        r.x = Math.round(pulse);
        if (blockUndersized(pulse)) { r.v = 'skip:pulseA:undersized'; continue; }
        if (pulse < pulseMin) { r.v = `skip:pulseA:<min(${Math.round(pulseMin)})`; continue; }
        r.v = 'SEND:pulseA'; break;
      }
      if (o.nearCollapse) {
        if (curAtk >= 0.04 * B || curAtk >= 0.30 * need) { r.v = 'skip:pulseB:alreadyOn'; continue; }
        const pulse = Math.min(avail, Math.max(Math.floor(P.pulseFrac * B), Math.min(avail, Math.floor(0.30 * need))));
        r.x = Math.round(pulse);
        if (pulse < pulseMin) { r.v = `skip:pulseB:<min(${Math.round(pulseMin)})`; continue; }
        r.v = 'SEND:pulseB'; break;
      }
      if (o.pulseMode) {
        if (curAtk >= 0.04 * B) { r.v = 'skip:pulseC:alreadyOn'; continue; }
        let capFrac = Math.floor(P.pulseFrac * B);
        if (P.counterClearMode === 2 && inAtk > 0) capFrac = Math.max(capFrac, Math.min(Math.floor(0.28 * B), Math.ceil(1.05 * inAtk - curAtk + 0.05 * B)));
        const want = Math.min(1.20 * need + 3 * pol.cnt[q], capFrac);
        const x = Math.min(avail, want);
        r.want = Math.round(want); r.x = Math.round(x);
        if (blockUndersized(x)) { r.v = 'skip:pulseC:undersized'; continue; }
        if (x < pulseMin) { r.v = `skip:pulseC:<min(${Math.round(pulseMin)})`; continue; }
        r.v = 'SEND:pulseC'; break;
      }
    }
    const want = 1.25 * need + 3 * pol.cnt[q];
    const x = Math.min(avail, want);
    r.want = Math.round(want); r.x = Math.round(x);
    if (x <= 0 || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) { r.v = x < want && x < P.chunk * B ? `skip:x<chunk(${Math.round(P.chunk * B)})` : 'skip:pplKill'; continue; }
    if (person && blockUndersized(x)) { r.v = 'skip:undersized'; continue; }
    r.v = 'SEND'; break;
  }
  return { B, L, fee, worth: +worth.toFixed(1), cheap: +cheap.toFixed(1), over, minCmd, nHumans, humanNbCount, rows };
}

// 全程买地门槛普查（--walk-every）：一行 = [t, 余额, 领土, worth, over, 活着的真人数, 真人敌邻数, 压在我身上的真人进攻兵, 其中最大的那个进攻者, 贴着的无主地,
//   在途陆攻槽数, [[q, 是不是真人, 每格报价, 有没有在打我, 结论, safe 原值, avail, 对方余额, 对方领土, 接壤格数, 标记(1 快崩 | 2 流血 | 4 拥挤)] …]]
function censusWalk(g, b) {
  const pol = b.pol, me = b.id;
  try {
    pol.analyze(g);
    const w = walkBuyLand(g, pol);
    let inH = 0, top = -1, topTr = 0;
    for (const a of g.attackersOf(me)) {
      if (a >= g.humans || g.teams[a] === g.teams[me]) continue;
      const tr = g.attackTroopsOn(a, me);
      inH += tr;
      if (tr > topTr) { topTr = tr; top = a; }
    }
    let active = 0;
    const base = g.slotBase(me);
    for (let i = g.atkCount[me] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== NEUTRAL) active++;
    b.walks.push([g.t, w.B, w.L, w.worth, w.over ? 1 : 0, w.nHumans, w.humanNbCount, inH, top, pol.neutral, active,
      w.rows.map((r) => [r.q, r.person ? 1 : 0, r.c, r.onMe ? 1 : 0, r.v ?? null, r.safeRaw ?? null, r.avail ?? null, r.bal, r.terr, r.cnt,
        (r.nearCollapse ? 1 : 0) | (r.bleeding ? 2 : 0) | (r.isCrowdedHard ? 4 : 0)])]);
  } catch (e) { if (b.errors.length < 20) b.errors.push([g.t, 'walk ' + String(e).slice(0, 200)]); }
}

function traceOne(g, b) {
  const pol = b.pol, me = b.id, P = pol.p;
  const o = { t: g.t, bot: b.name, terr: g.terr[me], bal: g.bal[me], cmds: pol.cmds, boats: pol.boats, lastBoat: pol.lastBoat,
    isNoFullSend: pol.isNoFullSend, shadowQuota: Math.round(pol.shadowQuota ?? 0), neutral: pol.neutral, held: !!pol.held, nb: [] };
  try {
    pol.analyze(g);
    const fl = pol.floors(g);
    o.cap = fl.cap; o.avgNb = Math.round(fl.avgNb);
    o.idle = g.bal[me] >= P.idleCap * fl.cap;
    o.minCmd = pol.minCmd(g);
    o.sb = pol.safeFinite ? Math.round(pol.safeFinite(g)) : null;
    o.dpKeep = pol.dpKeep ? Math.round(pol.dpKeep(g)) : null;
    o.peopleFloor = pol.peopleFloor ? Math.round(pol.peopleFloor(g)) : null;
    o.winWorth = pol.winWorth ? +pol.winWorth(g).toFixed(1) : null;
    o.floorNeutral = Math.round(Math.min(fl.floorAt(2), P.refN * fl.avgNb));
    let active = 0;
    const base = g.slotBase(me);
    for (let i = g.atkCount[me] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== NEUTRAL) active++;
    o.active = active; o.freeSlot = g.hasFreeSlot(me);
    for (const q of pol.nb) {
      const r = { q, name: q < g.humans ? names[q] : `AI${q}`, team: g.teams[q], terr: g.terr[q], bal: g.bal[q], cnt: pol.cnt[q] };
      try {
        r.person = pol.person(g, q);
        r.price = +pol.price(g, q).toFixed(1);
        r.allow = !!pol.allow(g, q);
        if (!r.person && pol.botOk) { r.botOk = !!pol.botOk(g, q); r.botPx = +pol.botPx(g, q).toFixed(1); }
        r.floor = Math.round(pol.floorFor(g, q, fl.floorAt(r.price)));
        r.avail = g.bal[me] - r.floor;
        r.minShare = Math.round(pol.minShare(g, q) * g.bal[me]);
        r.need = Math.round(pol.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q));
        r.onMe = g.attackTroopsOn(q, me); r.mine = g.attackTroopsOn(me, q);
        r.overMax = r.price > P.maxCost;
        if (r.avail > r.minShare && r.avail >= o.minCmd && r.need > 0) r.send = Math.round(pol.amount(g, q, r.avail, r.need, o.minCmd));
      } catch (e) { r.err = String(e).slice(0, 120); }
      o.nb.push(r);
    }
    if (g.t >= P.coreFrom && typeof pol.offers === 'function') {
      // 1500 拍后的买地口径（Policy.buyLand）：worth = maxW×winRatio(t)×参考密度；offers 按每格成本从低到高
      const B = g.bal[me], L = Math.max(1, g.terr[me]);
      const dMed = pol.otherHumanMedDens ? pol.otherHumanMedDens(g) : null;
      const m = P.maxW * pol.winRatio(g.t);
      const refDens = dMed !== null && g.t >= P.marketFrom ? Math.max(B / L, P.marketFloor * dMed) : B / L;
      o.core = { maxW: P.maxW, winRatio: +pol.winRatio(g.t).toFixed(3), dMe: +(B / L).toFixed(1), dMedOther: dMed === null ? null : +dMed.toFixed(1), worth: +(m * refDens).toFixed(1),
        cheap: P.growth > 0 ? +(0.1 / pol.baseRate(g)).toFixed(1) : 0, over: P.surplus > 0 && B > 100 * L, safeNone: Math.round(pol.safeAt(g, -1)) };
      o.offers = [];
      for (const of of pol.offers(g).slice(0, 6)) {
        const r = { q: of.q, name: of.q < g.humans ? names[of.q] : `AI${of.q}`, team: g.teams[of.q], c: +(+of.c).toFixed(1), need: Math.round(of.need), person: !!of.person };
        for (const k of ['nearCollapse', 'bleeding', 'onMe', 'isCrowdedHard', 'isDoorSea', 'newNbs', 'inAtk', 'tD']) if (of[k] !== undefined && of[k] !== false && of[k] !== 0) r[k] = typeof of[k] === 'number' ? +of[k].toFixed(2) : of[k];
        try { r.safe = Math.round(pol.safeAt(g, of.q)); } catch (e) { r.safe = null; }
        r.terr = g.terr[of.q]; r.bal = g.bal[of.q];
        o.offers.push(r);
      }
      o.walk = walkBuyLand(g, pol);
    }
  } catch (e) { o.err = String(e).slice(0, 200); }
  traces.push(o);
}

const t0 = Date.now();
let actMs = 0;
const out = resim(mid, {
  until: opt('until', null) ? +opt('until') : undefined,
  replayFrom: opt('replay-from', null), peer: opt('peer', null), peerTag: opt('peer-tag', null),
  onStart: (g, ctx) => {
    names = ctx.names;
    g.online = true;
    g.names = ctx.names;
    for (const s of Object.values(ctx.squad)) if (s.id >= 0) ((side === 'peer') !== !!s.peer ? peerIds : ownIds).add(s.id);
    for (const [name, s] of Object.entries(ctx.squad)) {
      if (s.id < 0 || (side === 'peer') !== !!s.peer) continue;
      if (wantBots !== 'all' && !wantBots.split(',').includes(name)) continue;
      bots.push({ name, id: s.id, pol: new Policy({}, s.id), cmds: [], logs: [], errors: [], flags: [], locks: [], census: [], census2: [], guard: [], walks: [], lastFlag: null, nAct: 0, lastCmdTick: -999,
        win: null, boatSpot: Object.getPrototypeOf(g).boatSpot ?? g.boatSpot });
    }
    for (const b of bots) b.win = { __hlLog: (s) => b.logs.push([g.t, String(s).slice(0, 400)]) };
    for (const b of bots) {
      const pol = b.pol;
      if (typeof pol.send !== 'function' || !('shadowQuota' in pol)) continue;
      const orig = pol.send.bind(pol);
      pol.send = (gg, target, troops, hint) => {
        const balBefore = gg.bal[pol.me];
        const guarded = pol.p.quotaGuardMode > 0 && pol.isNoFullSend && troops > 2 && pol.shadowQuota < Math.min(0.55 * troops, 0.06 * balBefore);
        const n0 = b.cmds.length;
        const ok = hint === undefined ? orig(gg, target, troops) : orig(gg, target, troops, hint);
        if (guarded) b.guard.push([gg.t, target, Math.round(troops), Math.round(pol.shadowQuota), balBefore, ok ? 1 : 0, b.cmds.length > n0 ? b.cmds[b.cmds.length - 1][2] : -1]);
        return ok;
      };
    }
  },
  onTick: (g) => {
    if (g.spawnPhase) return;
    const a = Date.now();
    for (const b of bots) {
      const p = b.id;
      if (!g.alive[p] || g.state[p] === 2) continue;
      globalThis.window = b.win;
      if (fresh && traceSpec[b.name]?.has(g.t)) b.pol = new Policy({}, p);
      if (guardTicks > 0 && g.t - b.lastCmdTick < guardTicks) continue;
      patch(g, b);
      const n0 = b.cmds.length;
      const pc0 = b.pol.pendingQuotaCheck ? { ...b.pol.pendingQuotaCheck } : null;
      const was = !!b.pol.isNoFullSend;
      try { b.pol.act(g); b.nAct++; } catch (e) { if (b.errors.length < 20) b.errors.push([g.t, String(e && e.stack ? e.stack.split('\n').slice(0, 3).join(' | ') : e).slice(0, 300)]); }
      if (b.cmds.length > n0) b.lastCmdTick = g.t;
      if (!was && b.pol.isNoFullSend) {
        let inc = 0;
        for (const q of g.attackersOf(p)) inc += g.attackTroopsOn(q, p);
        b.locks.push({ t: g.t, pc: pc0, bal: g.bal[p], terr: g.terr[p], actualSent: pc0 ? Math.max(0, pc0.bal0 - g.bal[p] - pc0.fee) : null, incoming: inc });
      }
      const f = `${b.pol.isNoFullSend ? 1 : 0}`;
      if (f !== b.lastFlag) { b.flags.push([g.t, b.pol.isNoFullSend ? 1 : 0, Math.round(b.pol.shadowQuota ?? 0)]); b.lastFlag = f; }
      if (traceSpec[b.name]?.has(g.t)) traceOne(g, b);
      if (g.t % censusEvery === 0 && g.t >= 300 && g.t <= censusUntil) census(g, b);
      if (g.t % censusEvery === 0 && g.t >= b.pol.p.coreFrom && g.t <= coreCensusUntil && typeof b.pol.offers === 'function') censusCore(g, b);
      if (walkEvery > 0 && g.t % walkEvery === 0 && g.t >= Math.max(walkFrom, b.pol.p.coreFrom ?? 0) && typeof b.pol.offers === 'function') censusWalk(g, b);
      unpatch(g);
    }
    globalThis.window = undefined;
    actMs += Date.now() - a;
  },
});

const res = {
  matchId: mid, strategy: stratName, guardTicks, endTick: out.endTick, replayFrom: opt('replay-from', null) || mid,
  walkEvery,
  bots: Object.fromEntries(bots.map((b) => [b.name, { id: b.id, nAct: b.nAct, cmds: b.cmds, logs: b.logs, errors: b.errors, flags: b.flags, locks: b.locks, census: b.census, census2: b.census2, guard: b.guard, walks: b.walks,
    final: { cmds: b.pol.cmds, boats: b.pol.boats, isNoFullSend: !!b.pol.isNoFullSend } }])),
  traces,
};
fs.mkdirSync(path.join(OUT, mid), { recursive: true });
// --tag X：写到 shadow_X.json（例如 --guard 0 --tag g0 做「不模拟静默窗」的对照，不覆盖主产物）
const tag = opt('tag', null);
fs.writeFileSync(path.join(OUT, mid, tag ? `shadow_${tag}.json` : side === 'peer' ? 'shadow_peer.json' : 'shadow.json'), JSON.stringify(res));
if (tag) console.log(`  isNoFullSend 置位（${tag}，guard=${guardTicks}）：${bots.filter((b) => b.locks.length).map((b) => `${b.name}@${b.locks[0].t}`).join(' ') || '无'}（${bots.filter((b) => b.locks.length).length}/${bots.length} 个号）`);
console.log(`${mid}: 影子 ${bots.length} 个号，策略 ${stratName}，到 t=${out.endTick}，总耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s（策略 ${(actMs / 1000).toFixed(1)}s）`);
if (!args.includes('--quiet')) {
  for (const b of bots) {
    const k = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    for (const c of b.cmds) k[c[1]]++;
    console.log(`  ${b.name}(${b.id}) act=${b.nAct} 影子指令 陆攻${k[1]} 捐${k[2]} 船${k[3]} 撤${k[5]} | cmds计数=${b.pol.cmds} isNoFullSend=${b.pol.isNoFullSend} 置位拍=${b.flags.filter((f) => f[1]).map((f) => f[0]).join(',')} 报错${b.errors.length}${b.errors.length ? ' ' + b.errors[0][1].slice(0, 160) : ''}`);
  }
}
