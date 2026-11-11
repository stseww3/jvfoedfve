// shadow_diag.mjs — 影子策略的「为什么」诊断：把策略源码里关键判定的中间量按原公式重算一遍并打印。
// 每个函数注明它照抄的源码位置（行号以 v27-team-c116-vb.js 为准；va/vc/c110 同名函数结构相同、行号略有偏移）。
// 只读：不发指令、不改策略对象的记忆（除 floors() 自带的 avgNb 缓存）。
const NEUTRAL = 512;
const iV = (a, b) => Math.floor((a + 0.5) / b);
const f = (n) => { if (!Number.isFinite(n)) return String(n); n = Math.round(n); const a = Math.abs(n); return a >= 1e7 ? (n / 1e6).toFixed(1) + 'M' : a >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : a >= 1e4 ? (n / 1e3).toFixed(1) + 'k' : String(n); };

// 核心期之前（t < coreFrom）：General.act → Style.pickTarget（L1144~1176）逐个邻居的放行/拒绝原因
export function diagPre(pol, g, nm) {
  const P = pol.p, me = pol.me, bal = g.bal[me], T = Math.max(1, g.terr[me]);
  const out = [];
  let fl;
  try { fl = pol.floors(g); } catch (e) { return ['    floors 出错 ' + String(e).slice(0, 80)]; }
  const min = pol.minCmd(g);
  let active = 0;
  const base = g.slotBase(me);
  for (let i = g.atkCount[me] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== NEUTRAL) active++;
  const idle = pol.idle ? pol.idle(g) : false;
  out.push(`    [核心期前] 闲置线 idleCap×100×地=${f(P.idleCap * 100 * T)}（idle=${idle}） held=${!!pol.held} 在打的非无主目标 ${active}/${P.maxTargets} 最小指令 ${f(min)} 单价上限 maxCost=${P.maxCost} AI 单价上限 botMax=${P.botMax} 邻居均兵 ${f(fl.avgNb)}`);
  for (const q of pol.nb) {
    if (!g.alive[q] || !g.terr[q]) continue;
    const person = pol.person(g, q);
    const perPx = pol.price(g, q);
    const why = [];
    if (!g.hasAttack(me, q) && (active >= P.maxTargets || !g.hasFreeSlot(me))) why.push('目标数已满/没有空槽');
    let allow = true;
    try { allow = pol.allow(g, q); } catch (e) { allow = 'ERR'; }
    if (!allow) {
      if (!person) why.push(`allow=false（L2112：botOk=${pol.botOk ? pol.botOk(g, q) : '?'}，单价 ${perPx.toFixed(1)} ${perPx <= P.botMax ? '≤' : '>'} botMax ${P.botMax}，且未到闲置线）`);
      else why.push(`allow=false（L2113~2118：held=${!!pol.held} food=${pol.food ? pol.food(g, q) : '?'} motive=${pol.motive ? pol.motive(g, q) : '?'}）`);
    }
    if (perPx > P.maxCost) why.push(`单价 ${perPx.toFixed(1)} > maxCost`);
    let floor = NaN, avail = NaN, need = NaN, send = NaN, wf = NaN, pf = NaN;
    try {
      floor = pol.floorFor(g, q, fl.floorAt(perPx));
      avail = bal - floor;
      if (!person && pol.winFloor) { wf = pol.winFloor(g, q); pf = pol.peopleFloor(g); }
      const ms = pol.minShare(g, q);
      if (avail <= ms * bal || avail < min) why.push(`可用兵不足：余额 ${f(bal)} − 底线 ${f(floor)} = ${f(avail)}（需 > ${f(Math.max(ms * bal, min))}）`);
      need = pol.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
      if (need <= 0) why.push('在途兵已够');
      send = pol.amount(g, q, avail, need, min);
      if (!(send >= min)) why.push(`amount=${f(send)} < 最小指令`);
    } catch (e) { why.push('诊断出错 ' + String(e).slice(0, 60)); }
    out.push(`      ${nm(q)} 地 ${g.terr[q]} 兵 ${f(g.bal[q])} 接触 ${pol.cnt[q]} 单价 ${perPx.toFixed(1)} 需 ${f(need)} 底线 ${f(floor)}${Number.isFinite(wf) ? `（winFloor ${f(wf)}，peopleFloor ${f(pf)}）` : ''} → ${why.length ? '不打：' + why.join('；') : '可打，拟出 ' + f(send)}`);
  }
  if (!pol.nb.length) out.push('      没有任何非队友邻居（nb=0）');
  for (const l of diagWinFloor(pol, g, nm)) out.push(l);
  return out;
}

// winFloor（L4562~4570）= max(项1 = mult×botPx×地/(winR×t)，项2 = dpKeep，项3 = sb = safeFinite(g))。
// safeFinite（L2500~2510）对每个 AI 邻居 q 取 threatOf(g,q).minOther（L417~444）：q 的所有「别的」邻居里 余额+正在打 q 的兵 最小的那个。
// 这里照抄 threatOf 的循环，把那个「最弱的别的邻居」是谁打印出来（队友 / 外队真人 / AI）。
export function diagWinFloor(pol, g, nm) {
  const P = pol.p, me = pol.me, L = Math.max(1, g.terr[me]);
  const out = [];
  if (!pol.winFloor || !pol.safeFinite) return out;
  let dp = NaN, sb = NaN;
  try { dp = pol.dpKeep(g); sb = pol.safeFinite(g); } catch (e) { return ['    winFloor 诊断出错 ' + String(e).slice(0, 80)]; }
  out.push(`    [winFloor 拆解] 项2 dpKeep=${f(dp)} 项3 sb=safeFinite=${f(sb)}（余额 ${f(g.bal[me])}）`);
  for (const q of pol.nb) {
    if (!g.alive[q] || !g.isBot(q)) continue;
    let t1 = NaN;
    try { const mult = pol.contested && pol.contested(g, q) ? P.sharedBotMult : 1.0; t1 = (mult * pol.botPx(g, q) * L) / (P.winR * Math.max(1, g.t)); } catch (e) { t1 = NaN; }
    const skip = !g.hasFreeSlot(q) ? '（它没有空槽，safeFinite 跳过）' : g.hasAttack(q, me) ? '（它已经在打我，safeFinite 跳过）' : '';
    const B = g.border[q], px = g.px, own = g.own, d = g.dir4;
    const busyNeutral = g.hasAttack(q, NEUTRAL);
    let neutral = false, best = -1, bestS = Infinity;
    const seen = new Set();
    const n = B.length, step = n > 1024 ? Math.ceil(n / 1024) : 1;
    for (let i = n - 1; i >= 0 && !neutral; i -= step) {
      const b = B[i];
      for (let k = 0; k < 4; k++) {
        const c = b + d[k], v = px[c];
        if (v === 1) { if (!busyNeutral) { neutral = true; break; } continue; }
        if (v < 16) continue;
        const o = own[c];
        if (o === q || o === me || seen.has(o)) continue;
        seen.add(o);
        if (g.hasAttack(q, o)) continue;
        const s2 = g.bal[o] + g.attackTroopsOn(o, q);
        if (s2 < bestS) { bestS = s2; best = o; }
      }
    }
    const kind = best < 0 ? '' : g.isTeammate(me, best) ? '队友' : g.isBot(best) ? 'AI' : '外队真人';
    out.push(`      AI ${nm(q)} 地 ${g.terr[q]} 兵 ${f(g.bal[q])}：项1=${f(t1)}；` + (neutral ? '它还贴着无主地且没在打无主地 → 不计入 sb' : best < 0 ? '除我之外没有别的邻居（minOther=∞）→ 不计入 sb' : `它别的邻居 ${seen.size} 个，最弱的是 ${kind} ${nm(best)}（余额 ${f(g.bal[best])} + 正在打它的兵 ${f(g.attackTroopsOn(best, q))} = ${f(bestS)}）→ 我要留 ${f(bestS - g.attackTroopsOn(me, q))}`) + skip);
  }
  return out;
}

// V13.safeFinite（L2500~2510）取到最大值的那个内置 AI，以及它「最弱的别的邻居」（threatOf L417~444 的 minOther 是谁）。
// 返回 { val, ref }：ref = 'squad:编号'（编队号）/ 'ally:编号'（同队真人）/ 'enemy:编号'（敌方真人）/ 'ai:编号'。
export function safeFiniteRef(pol, g, ourSet) {
  const me = pol.me;
  let top = -Infinity, who = -1;
  for (const q of pol.nb) {
    if (g.alive[q] === 0 || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
    const B = g.border[q], px = g.px, own = g.own, d = g.dir4;
    const busyNeutral = g.hasAttack(q, NEUTRAL);
    let neutral = false, best = -1, bestS = Infinity;
    const seen = new Set();
    const n = B.length, step = n > 1024 ? Math.ceil(n / 1024) : 1;
    for (let i = n - 1; i >= 0 && !neutral; i -= step) {
      const b = B[i];
      for (let k = 0; k < 4; k++) {
        const c = b + d[k], v = px[c];
        if (v === 1) { if (!busyNeutral) { neutral = true; break; } continue; }
        if (v < 16) continue;
        const o = own[c];
        if (o === q || o === me || seen.has(o)) continue;
        seen.add(o);
        if (g.hasAttack(q, o)) continue;
        const s2 = g.bal[o] + g.attackTroopsOn(o, q);
        if (s2 < bestS) { bestS = s2; best = o; }
      }
    }
    if (neutral || best < 0) continue;
    const keep = bestS - g.attackTroopsOn(me, q);
    if (keep > top) { top = keep; who = best; }
  }
  let ref = '';
  if (who >= 0) ref = (ourSet && ourSet.has(who) ? 'squad:' : g.isTeammate(me, who) ? 'ally:' : g.isBot(who) ? 'ai:' : 'enemy:') + who;
  return { val: who >= 0 ? Math.max(0, top) : 0, ref };
}


// 核心期之前，贴着内置 AI 却没出手的那一拍：对「底线最低的那个 AI 邻居」，底线是被哪一项顶住的。
// 返回 { bind, ref, floor, avail, need }：
//   bind = 't1'（项1 = mult×botPx×地/(winR×t)）| 'dp'（项2 dpKeep）| 'sb'（项3 safeFinite）| 'pf'（peopleFloor）| 'ok'（底线没卡住，是别的原因）
//   ref  = bind 为 sb 时，给出 safeFinite 取到最大值的那个 AI 的「最弱的别的邻居」：'squad:号'（我方编队的号）、'ally:号'（同队其他真人）、
//          'enemy:号'（外队真人）、'ai:号'（另一个内置 AI）；其余情况为空串。
//   floor / avail / need = 那个 AI 的底线、余额 − 底线、出手至少要有的可用兵（max(minShare×余额, 最小指令)）。
// 公式照抄 V13.floorFor0 L2233~2241（核心期前、打内置 AI：max(winFloor, peopleFloor)）、winFloor L4562~4570、safeFinite L2500~2510、threatOf L417~444。
export function floorBind(pol, g, ourSet) {
  const P = pol.p, me = pol.me, L = Math.max(1, g.terr[me]), bal = g.bal[me];
  let fl;
  try { fl = pol.floors(g); } catch (e) { return null; }
  const min = pol.minCmd(g);
  let bestQ = -1, bestF = Infinity;
  for (const q of pol.nb) {
    if (!g.alive[q] || !g.terr[q] || pol.person(g, q)) continue;
    let f0 = NaN;
    try { f0 = pol.floorFor(g, q, fl.floorAt(pol.price(g, q))); } catch (e) { f0 = NaN; }
    if (Number.isFinite(f0) && f0 < bestF) { bestF = f0; bestQ = q; }
  }
  if (bestQ < 0) return null;
  const q0 = bestQ;
  let ms = 0;
  try { ms = pol.minShare(g, q0); } catch (e) { ms = 0; }
  const need = Math.max(ms * bal, min), avail = bal - bestF;
  if (avail > ms * bal && avail >= min) return { bind: 'ok', ref: '', floor: bestF, avail, need };
  let t1 = NaN, dp = NaN, sb = NaN, pf = NaN;
  try {
    const mult = pol.contested && pol.contested(g, q0) ? P.sharedBotMult : 1.0;
    t1 = (mult * pol.botPx(g, q0) * L) / (P.winR * Math.max(1, g.t));
    dp = pol.dpKeep(g); sb = pol.safeFinite(g); pf = pol.peopleFloor ? pol.peopleFloor(g) : 0;
  } catch (e) { return { bind: '?', ref: '', floor: bestF, avail, need }; }
  const terms = [['t1', t1], ['dp', dp], ['sb', sb], ['pf', pf]].filter((x) => Number.isFinite(x[1]));
  terms.sort((a, b) => b[1] - a[1]);
  const bind = terms.length ? terms[0][0] : '?';
  let ref = '';
  if (bind === 'sb') ref = safeFiniteRef(pol, g, ourSet).ref;
  return { bind, ref, floor: bestF, avail, need };
}

// 核心期（t ≥ coreFrom）：Policy.buyLand（L5342~5619）开头的几个量 + 每条报价的底线/可用兵
export function diagCore(pol, g, nm, offers) {
  const P = pol.p, me = pol.me;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iV(12 * B, 1024), dMe = B / L;
  const out = [];
  let dMed = null, m = NaN, worth = NaN, cheap = NaN;
  try {
    dMed = pol.otherHumanMedDens ? pol.otherHumanMedDens(g) : null;
    m = P.maxW * pol.winRatio(g.t);
    const refDens = dMed !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe;
    worth = m * refDens;
    cheap = P.growth > 0 ? 0.1 / pol.baseRate(g) : 0;
  } catch (e) { out.push('    buyLand 头部量出错 ' + String(e).slice(0, 80)); }
  const over = P.surplus > 0 && B > 100 * L;
  out.push(`    [buyLand L5350~5354] 每像素值 worth=${worth.toFixed(1)}（m=${m.toFixed(3)}，其他真人密度中位 ${dMed === null ? '无' : dMed.toFixed(1)}） 便宜线 cheap=${cheap.toFixed(1)} 超软上限 over=${over}（余额 ${f(B)} vs 100×地 ${f(100 * L)}）`);
  let list = offers;
  if (!list) { try { list = pol.offers(g); } catch (e) { out.push('    offers 出错 ' + String(e).slice(0, 80)); list = []; } }
  if (!list.length) out.push(`    报价单为空（L5072 offers 只遍历非队友陆上邻居 this.nb：nb=${pol.nb.length}）`);
  for (const o of list.slice(0, 6)) {
    let safe = NaN;
    try { safe = pol.safeAt(g, o.q); } catch (e) { /* ignore */ }
    const person = o.person !== undefined ? o.person : pol.person(g, o.q);
    let capped = safe;
    if (!person || o.nearCollapse || (P.bleedSafeCap > 0 && (o.bleeding || o.tD < 0.45))) capped = Math.min(safe, P.oppFloorCap * L);
    const stop = o.c >= worth && o.c >= cheap && !over;
    out.push(`      ${nm(o.q)}${person ? '(真人)' : ''} 地 ${g.terr[o.q]} 兵 ${f(g.bal[o.q])} 单价 c=${o.c.toFixed(1)} 需 ${f(o.need)} 底线 safeAt=${f(safe)}→封顶后 ${f(capped)}（${(capped / L).toFixed(0)}×地） 余额−费−底线=${f(B - fee - capped)}${o.nearCollapse ? ' 濒崩' : ''}${o.bleeding ? ' 流血' : ''}${o.pulseMode ? ' 脉冲' : ''}${o.onMe ? ' 正打我' : ''}${o.isCrowdedHard ? ' 拥挤硬目标' : ''}${stop ? ' ⇒ c≥worth 且不便宜且未超上限：到此为止（L5359 break）' : ''}`);
  }
  return out;
}

// 核心期这一拍没有对真人出手时，Policy.buyLand（L5356~5617）在每条报价上是被哪一道门拦下的。
// 只照抄判定条件，不发指令、不发船。返回 [[目标, 标签], …]，顺序同报价单；标签：
//   price   L5359  c ≥ worth 且不便宜、余额没过 100×地：整张报价单到此为止
//   sole    L5361~5365 唯一的真人邻居、对方健康、打穿会露出新真人：余额 < overHumanCap×100×地 之前不打
//   tiny    L5367  对方地 < 250、手续费 > 2×所需、单价 > 8×worth
//   crowded L5371~5374 「拥挤硬目标」：余额 < crowdedHardCap×100×地 之前不打
//   absorb  L5376  对方正大举打我，先吃下这一波
//   doorSea L5380  隔海的门口目标（走船，另算）
//   siege   L5429~5441 自己缩到峰值的 siegeShrinkRatio 以下
//   floor   L5446~5447 余额 − 手续费 − 要留的兵 ≤ 0
//   inflight L5575/L5589/L5596 已有在途的兵
//   small   L5583/L5591/L5605 这一发 < max(最小指令, pulseMinShare×余额)
//   chunk   L5612  不走脉冲、兵不够一次打穿且 < chunk×余额
//   send    这些门都过了（若这一拍仍没有意图：被 send 的守卫拦了，或 tryDonate / 发船先返回）
export function coreGate(pol, g, offers, ourSet = null) {
  const P = pol.p, me = pol.me;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iV(12 * B, 1024), dMe = B / L;
  const dMed = pol.otherHumanMedDens(g);
  const nHumans = pol.livingHumanCount(g);
  const humanNbCount = pol.nb.filter((p) => g.alive[p] && pol.person(g, p)).length;
  const m = P.maxW * pol.winRatio(g.t);
  const refDens = dMed !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe;
  const worth = m * refDens;
  const over = P.surplus > 0 && B > 100 * L;
  const cheap = P.growth > 0 ? 0.1 / pol.baseRate(g) : 0;
  const res = [];
  for (const o of offers) {
    const { q, c, need, person } = o;
    if (c >= worth && c >= cheap && !over) { res.push([q, 'price']); break; }
    const sole = person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1;
    if (sole && c >= worth && c >= cheap && B < P.overHumanCap * 100 * L) { res.push([q, 'sole']); continue; }
    if (person && !o.isDoorSea && g.terr[q] < 250 && fee > 2 * need && c > 8 * worth && nHumans >= 3) { res.push([q, 'tiny']); continue; }
    if (person && !o.isDoorSea && o.isCrowdedHard && c >= worth && c >= cheap && B < P.crowdedHardCap * 100 * L) { res.push([q, 'crowded']); continue; }
    if (P.absorbMode >= 1 && person && !o.isDoorSea && !o.nearCollapse && (o.inAtk ?? 0) >= P.absorbWaveMin * B) { res.push([q, 'absorb']); continue; }
    if (o.isDoorSea) { res.push([q, 'doorSea']); continue; }
    let safe = pol.safeAt(g, q);
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
    if (isSiegeShrink && c >= worth && c >= cheap && B < P.crowdedHardCap * 100 * L) { res.push([q, 'siege']); continue; }
    if (over) {
      const overKeepMult = dMe >= 122 ? 0.82 : sole ? P.overHumanKeep : P.hold;
      keep = Math.min(keep, overKeepMult * 100 * L);
    }
    const keepPrice = keep;
    keep = Math.max(keep, safe);
    const avail = B - fee - keep;
    if (avail <= 0) {
      // 是哪一项把可用兵压到 0：keep = 价格预算要留的兵（L5420~5427）；否则是 safeAt（L4543~4560 → V17.safeAt L2728）：
      // sf = safeFinite（botSkip=0 时不排除要买的这个 AI，也不排除队友）、dp = killW×dpKeep、cap = 被 oppFloorCap×地 截住
      // empty = 余额扣掉手续费已经是 0
      let det = 'keep';
      if (B - fee <= 0) det = 'empty';
      else if (safe >= keepPrice) {
        let sfv = NaN, dpv = NaN;
        try { sfv = pol.safeFinite(g, P.botSkip > 0 && q >= 0 && !person ? q : -1); dpv = (P.killW ?? 0) * pol.dpKeep(g); } catch (e) { sfv = NaN; }
        const capped = safe >= P.oppFloorCap * L - 1e-6;
        if (!Number.isFinite(sfv)) det = '?';
        else if (sfv >= dpv) det = (capped ? 'cap+' : '') + 'sf/' + (safeFiniteRef(pol, g, ourSet).ref || '-');
        else det = (capped ? 'cap+' : '') + 'dp';
      }
      res.push([q, 'floor', det]);
      continue;
    }
    if (!person) {
      const want = 1.25 * need + 3 * pol.cnt[q];
      const x = Math.min(avail, want);
      if (x <= 0 || (x < want && x < P.chunk * B)) { res.push([q, 'chunk']); continue; }
      res.push([q, 'send']);
      break;
    }
    const usePulseBlock = P.pulseFrac > 0 && (!over || o.nearCollapse || o.bleeding || need > 0.30 * B || avail < P.chunk * B);
    const curAtk = g.attackTroopsOn(me, q);
    const minPulse = Math.max(pol.minCmd(g), P.pulseMinShare * B);
    if (usePulseBlock) {
      if (g.t >= 3800 && (o.nearCollapse || o.bleeding || (P.aggMemMode === 2 && o.isAgg))) {
        if (curAtk >= 0.08 * B || curAtk >= 0.65 * need) { res.push([q, 'inflight']); continue; }
        const targetSlot = Math.min(0.85 * need + 3 * pol.cnt[q], Math.floor(P.pulseFrac * B));
        const pulse = Math.min(avail, Math.max(targetSlot - curAtk, Math.floor(0.08 * B)));
        if (pulse < minPulse) { res.push([q, 'small']); continue; }
        res.push([q, 'send']);
        break;
      }
      if (o.nearCollapse) {
        if (curAtk >= 0.04 * B || curAtk >= 0.30 * need) { res.push([q, 'inflight']); continue; }
        const pulse = Math.min(avail, Math.max(Math.floor(P.pulseFrac * B), Math.min(avail, Math.floor(0.30 * need))));
        if (pulse < minPulse) { res.push([q, 'small']); continue; }
        res.push([q, 'send']);
        break;
      }
      if (o.pulseMode) {
        if (curAtk >= 0.04 * B) { res.push([q, 'inflight']); continue; }
        const want = Math.min(1.20 * need + 3 * pol.cnt[q], Math.floor(P.pulseFrac * B));
        const x = Math.min(avail, want);
        if (x < minPulse) { res.push([q, 'small']); continue; }
        res.push([q, 'send']);
        break;
      }
    }
    const want = 1.25 * need + 3 * pol.cnt[q];
    const x = Math.min(avail, want);
    if (x <= 0 || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) { res.push([q, 'chunk']); continue; }
    res.push([q, 'send']);
    break;
  }
  return res;
}

// tryDonateToTeammate 里随版本变的常数（逐项对过 diff：Va↔Vb 的 L4382~4383 / L4478 / L4502~4505，Vb↔Vc 的 L4329 / L4383~4387 / L4464~4466 / L4479~4481 / L4503~4506）
//   prodBox / emBox / defReqBox / genMaxBox 都是 [有海岸, 没海岸]；defGapAlways / genGapAlways：密度差条件对封死号是否也生效
const DON = {
  va: { minBal: 30000, cool: 12, prodBox: [72, 66], prodFront: 94, emBox: [32, 22], defReqBox: [42, 30], defMaxAlly: Infinity, gap: 16, gapAlways: false, genReqBox: 82, genMaxBox: [140, 128], genMaxFront: 96, pctDef: [260, 190], pctGen: [225, 170], minPct: 128 },
  vb: { minBal: 30000, cool: 12, prodBox: [44, 34], prodFront: 92, emBox: [32, 22], defReqBox: [42, 30], defMaxAlly: Infinity, gap: 16, gapAlways: false, genReqBox: 58, genMaxBox: [140, 128], genMaxFront: 96, pctDef: [380, 240], pctGen: [320, 220], minPct: 180 },
  vc: { minBal: 35000, cool: 24, prodBox: [76, 70], prodFront: 94, emBox: [58, 48], defReqBox: [68, 58], defMaxAlly: 85, gap: 15, gapAlways: true, genReqBox: 96, genMaxBox: [94, 88], genMaxFront: 88, pctDef: [260, 190], pctGen: [220, 170], minPct: 150 },
};
let DV = DON.vb, DVNAME = 'vb';
export function setDiagVersion(ver) {
  if (DON[ver]) { DV = DON[ver]; DVNAME = ver; return true; }
  DVNAME = ver + '（调度诊断仍按 Vb 的常数，未核对）';
  return false;
}

// 捐款/调度门槛（Policy.tryDonateToTeammate L4325~4518 的入口判定）
export function diagDonate(pol, g, nm) {
  const P = pol.p, me = pol.me;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  const out = [];
  const gate = [];
  if (g.t < 1500) gate.push('t<1500');
  if (g.terr[me] < 1200) gate.push('地<1200');
  if (B < DV.minBal) gate.push('余额<' + DV.minBal);
  if (g.t - (pol.lastDonateTick ?? -999) < DV.cool) gate.push('距上次调度<' + DV.cool + '拍');
  let anyEnemyNb = false;
  for (const q of pol.nb) if (g.alive[q] && !pol.isTeammate(g, q) && pol.person(g, q)) anyEnemyNb = true;
  const boxedIn = !anyEnemyNb && pol.nb.length === 0 && pol.neutral === 0;
  out.push(`    [tryDonateToTeammate L4329~4354] 入口门槛：${gate.length ? '不过（' + gate.join('，') + '）' : '过'}；boxedIn=${boxedIn}（nb=${pol.nb.length} neut=${pol.neutral}）；本号密度 ${dMe.toFixed(1)}`);
  // 候选队友一览：同队我方号的密度、是否有敌邻
  const rows = [];
  for (let p = 0; p < g.humans; p++) {
    if (p === me || !g.alive[p] || !pol.isTeammate(g, p)) continue;
    if (!(pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p))) continue;
    const dA = g.bal[p] / Math.max(1, g.terr[p]);
    let enemyNbs = 0;
    try { enemyNbs = pol.peopleOf(g, p).filter((o) => g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0).length; } catch (e) { enemyNbs = -1; }
    const inAtk = g.attackersOf(p).filter((a) => !pol.isTeammate(g, a)).reduce((s, a) => s + g.attackTroopsOn(a, p), 0);
    rows.push(`${nm(p)} 地${g.terr[p]} 密度${dA.toFixed(0)} 敌邻${enemyNbs} 被攻${f(inAtk)} 配额${g.donQuota[p]}/${g.donCap}`);
  }
  out.push('      我方队友：' + rows.join('；'));
  // 逐个候选照抄 L4414~4496 的分类与打分（Vb / Vc 行号，Va 少一行；随版本变的常数在 DON 表里；只读）
  try {
    const hasExposedCoast = (g.coast?.[me]?.length ?? 0) > 0;
    const prodOptFloor = boxedIn ? (hasExposedCoast ? DV.prodBox[0] * L : DV.prodBox[1] * L) : Math.max(DV.prodFront * L, pol.safeAt(g, -1));
    const emergDefFloor = boxedIn ? (hasExposedCoast ? DV.emBox[0] * L : DV.emBox[1] * L) : Math.max(88 * L, pol.safeAt(g, -1));
    let maxSquadTerr = 0, topSquadId = -1, maxRandomTeamTerr = 0, fronts = 0;
    for (let p = 0; p < g.humans; p++) {
      if (!g.alive[p] || !pol.isTeammate(g, p)) continue;
      if (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) { if (g.terr[p] > maxSquadTerr) { maxSquadTerr = g.terr[p]; topSquadId = p; } }
      else if (!g.isBot(p) && g.terr[p] > maxRandomTeamTerr) maxRandomTeamTerr = g.terr[p];
    }
    for (let p = 0; p < g.humans; p++) {
      if (g.alive[p] && pol.isTeammate(g, p) && (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) && g.terr[p] >= 150) {
        if (pol.peopleOf(g, p).some((o) => g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0)) fronts++;
      }
    }
    out.push(`      底线：一般调度留 ${f(prodOptFloor)}（${(prodOptFloor / L).toFixed(0)}×地），救急调度留 ${f(emergDefFloor)}（${(emergDefFloor / L).toFixed(0)}×地）；编队最大领土 ${maxSquadTerr}（「弃子线」= 0.22×它 = ${Math.round(0.22 * maxSquadTerr)}）；有陆上战线的我方号 ${fronts} 个`);
    const cls = [];
    let best = null;
    for (let p = 0; p < g.humans; p++) {
      if (p === me || !g.alive[p] || !pol.isTeammate(g, p) || (!pol.isOurSquadBot(g, p) && !pol.isBossNpl(g, p))) continue;
      if (g.terr[p] < (fronts <= 2 ? 150 : 1200)) { cls.push(`${nm(p)}：地太小，跳过`); continue; }
      const Lp = Math.max(1, g.terr[p]), Bp = g.bal[p], dAlly = Bp / Lp;
      if (dAlly >= (boxedIn ? 142 : 115)) { cls.push(`${nm(p)}：密度 ${dAlly.toFixed(0)} 已够高，跳过`); continue; }
      let inH = 0, outH = 0;
      for (const a of g.attackersOf(p)) if (!g.isBot(a) && !pol.isTeammate(g, a)) inH += g.attackTroopsOn(a, p);
      const sbP = g.slotBase(p);
      for (let i = 0; i < g.atkCount[p]; i++) { const tgt = g.atkTarget[sbP + i]; if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !pol.isTeammate(g, tgt)) outH += g.atkTroops[sbP + i]; }
      let enemyNbs = 0, botNbs = 0, minEnemyDens = Infinity, prey = false;
      for (const o of pol.peopleOf(g, p)) {
        if (o !== me && g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0) {
          const dd = g.bal[o] / Math.max(1, g.terr[o]);
          if (!g.isBot(o)) { enemyNbs++; if (dd < minEnemyDens) minEnemyDens = dd; if (dd < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) prey = true; }
          else { botNbs++; if (dd < minEnemyDens) minEnemyDens = dd; if (dd < 35) prey = true; }
        }
      }
      if (enemyNbs === 0 && botNbs > 0) enemyNbs = botNbs;
      const allyHasCoast = (g.coast?.[p]?.length ?? 0) > 0;
      const isBeachhead = enemyNbs > 0 && fronts <= 2 && boxedIn;
      const crown = (p === topSquadId && enemyNbs > 0 && maxRandomTeamTerr >= 0.70 * maxSquadTerr) || isBeachhead;
      if (enemyNbs === 0 && inH === 0 && outH === 0 && (!boxedIn || !allyHasCoast || dMe < 105 || dAlly > 112)) { cls.push(`${nm(p)}：没有敌邻也没在打/挨打，跳过（L4453）`); continue; }
      const doomed = !isBeachhead && (inH > 1.65 * Bp || (g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inH > 0.45 * Bp));
      if (doomed) { cls.push(`${nm(p)}：**判为弃子，跳过**（L4455：被攻 ${f(inH)} ${inH > 1.65 * Bp ? '> 1.65×余额' : '> 0.45×余额'} ${f(Bp)}，地 ${Lp} ${Lp < 0.22 * maxSquadTerr ? '< 弃子线' : ''}）`); continue; }
      const underFire = inH > 0 && (inH >= 0.06 * Bp || dAlly < 88);
      const push = outH >= 0.06 * Bp && dAlly < 96;
      const opening = enemyNbs > 0 && (prey || minEnemyDens < 0.70 * dAlly) && dAlly < 96;
      if (underFire) {
        const reqD = boxedIn ? (hasExposedCoast ? DV.defReqBox[0] : DV.defReqBox[1]) : 102;
        const gapOn = DV.gapAlways || !boxedIn;
        if (dMe < reqD || dAlly >= DV.defMaxAlly || B <= 1.12 * emergDefFloor || (gapOn && dMe < dAlly + DV.gap)) { cls.push(`${nm(p)}：在挨打（${f(inH)}），但我不够格（我密度 ${dMe.toFixed(0)}，要求 ≥${reqD}${gapOn ? '且比对方高 ' + DV.gap : ''}${Number.isFinite(DV.defMaxAlly) ? `；对方密度 ${dAlly.toFixed(0)} 要求 <${DV.defMaxAlly}` : ''}，余额要 > ${f(1.12 * emergDefFloor)}）`); continue; }
        const score = 5000 + (inH / Math.max(1, Bp)) * 1200 + (105 - dAlly) * 20 + Math.min(2200, Lp / 18);
        cls.push(`${nm(p)}：救急候选，得分 ${score.toFixed(0)} = 5000 + 被攻比 ${((inH / Math.max(1, Bp)) * 1200).toFixed(0)} + 密度差 ${((105 - dAlly) * 20).toFixed(0)} + 领土项 ${Math.min(2200, Lp / 18).toFixed(0)}`);
        if (!best || score > best.score) best = { p, score, kind: 'defense_dispatch', floor: emergDefFloor };
      } else {
        const reqD = boxedIn ? DV.genReqBox : 108;
        const maxAllyD = boxedIn ? (push || opening || enemyNbs > 0 ? DV.genMaxBox[0] : DV.genMaxBox[1]) : DV.genMaxFront;
        if (dMe < reqD || dAlly > maxAllyD || B <= 1.14 * prodOptFloor || ((DV.gapAlways || !boxedIn) && dMe < dAlly + DV.gap)) { cls.push(`${nm(p)}：一般候选，但不够格（我密度 ${dMe.toFixed(0)} 要求 ≥${reqD}；对方密度 ${dAlly.toFixed(0)} 要求 ≤${maxAllyD}；余额要 > ${f(1.14 * prodOptFloor)}）`); continue; }
        const score = (push || opening ? 2500 : 1000) + (crown ? 1800 : 0) + (outH / Math.max(1, Bp)) * 1200 + (prey ? 500 : 0) + (100 - dAlly) * 18 + enemyNbs * 80 + Math.min(3500, Lp / 14);
        cls.push(`${nm(p)}：${push || opening ? '进攻' : '增产'}候选，得分 ${score.toFixed(0)}（领土项 ${Math.min(3500, Lp / 14).toFixed(0)}）`);
        if (!best || score > best.score) best = { p, score, kind: push || opening ? 'offense_dispatch' : 'yield_opt_dispatch', floor: prodOptFloor };
      }
    }
    for (const c of cls) out.push('        ' + c);
    if (best) {
      const maxSafePct = Math.floor((Math.max(0, B - best.floor) * 1024) / Math.max(1, B));
      const ideal = best.kind === 'defense_dispatch' ? (boxedIn ? DV.pctDef[0] : DV.pctDef[1]) : (boxedIn ? DV.pctGen[0] : DV.pctGen[1]);
      const pct = Math.min(maxSafePct, ideal);
      out.push(`      ⇒ 选中 ${nm(best.p)}（${best.kind}），比例 min(${maxSafePct}, ${ideal}) = ${pct}/1024${pct < DV.minPct ? '，低于 ' + DV.minPct + ' 不发（L4506）' : `，捐后我方密度约 ${((B * (1 - pct / 1024) - B * 0.0625) / L).toFixed(0)}`}`);
    } else out.push('      ⇒ 没有合格的收款人');
  } catch (e) { out.push('      调度候选诊断出错 ' + String(e).slice(0, 100)); }
  return out;
}

// 闲置发船门槛（Policy.idleBoats L5019~5070）
export function diagBoats(pol, g, nm) {
  const P = pol.p, me = pol.me;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  const out = [];
  const boxed = pol.nb.length === 0 && pol.neutral === 0 && g.teams && g.teams[me] > 0;
  let mop = false;
  try { mop = pol.isMopUp ? pol.isMopUp(g) : false; } catch (e) { /* ignore */ }
  if (boxed && !mop) {
    let act = 0;
    for (let p = 0; p < g.humans; p++) {
      if (p !== me && g.alive[p] && pol.isTeammate(g, p) && (pol.isOurSquadBot(g, p) || pol.isBossNpl(g, p)) && g.terr[p] >= 500) {
        let nbs = [];
        try { nbs = pol.peopleOf(g, p); } catch (e) { /* ignore */ }
        if (nbs.some((o) => g.alive[o] && !pol.isTeammate(g, o) && g.terr[o] > 0)) act++;
      }
    }
    const why = [];
    if (act >= 1 && dMe < 115) why.push(`有 ${act} 个兄弟号在陆上接敌且本号密度 ${dMe.toFixed(0)} < 115（L5031 直接返回）`);
    if (!g.boatsAllowed(me)) why.push(`boatsAllowed=false（海岸像素 ${g.coast[me].length}，在航 ${g.boatCount[me]} 条）`);
    if (g.boatCount[me] >= 6) why.push('在航船已 6 条');
    if (g.t - (pol.lastBoat ?? -999) < Math.min(P.boatEvery, 18)) why.push('发船冷却中');
    out.push(`    [idleBoats L5022~5043 封死分支] 接敌兄弟 ${act} 个，密度 ${dMe.toFixed(0)}，海岸像素 ${g.coast[me].length}，保底 ${act >= 1 ? 92 : 68}×地=${f((act >= 1 ? 92 : 68) * L)} → ${why.length ? '不发船：' + why.join('；') : '会调用 boatOut（范围 2500）'}`);
    if (!why.length) {
      // 复刻 boatOut（基类 L999~1015 + V13 包装 L2325~2330）：找得到落点吗？够不够最小船量？
      const oldRange = P.boatRange, oldFrac = P.boatFrac;
      let hit = null, err = '';
      try {
        P.boatRange = 2500; P.boatFrac = Math.max(oldFrac, 0.24);
        hit = pol.searchWater(g);
      } catch (e) { err = String(e && e.message || e); }
      const frac = Math.max(oldFrac, 0.24);
      P.boatRange = oldRange; P.boatFrac = oldFrac;
      if (err) out.push(`      searchWater 出错：${err}`);
      else if (!hit) out.push(`      searchWater 在 2500 像素水程内找不到任何可登陆的非队友陆地（水面只通到自己/队友的岸，或根本不通外海）→ boatOut 返回 false，不发船`);
      else {
        let fl = 0;
        try { const { floorAt } = pol.floors(g); fl = Math.max(Math.min(floorAt(hit.price), 85 * L), (act >= 1 ? 92 : 68) * L); } catch (e) { fl = (act >= 1 ? 92 : 68) * L; }
        let idleNow = false;
        try { idleNow = pol.idle(g); } catch (e) { /* ignore */ }
        if (P.idleSafe > 0 && idleNow) fl = Math.max(fl, P.idleSafe * 100 * L + Math.floor((32 * B) / 1024));
        const max = frac * (B - fl);
        const min = P.boatFee > 0 && hit.neutral ? 60 : Math.max(60, P.feeK * Math.floor((32 * B) / 1024));
        const o = hit.neutral ? -1 : g.own[hit.land];
        const tgt = hit.neutral ? `无主地（连片 ${hit.size} 格）` : `${nm(o)} 地 ${g.terr[o]} 兵 ${f(g.bal[o])}`;
        const cnt = g.boatCount[me] >= P.maxBoats ? `；但在航船 ${g.boatCount[me]} 条 ≥ maxBoats ${P.maxBoats}` : '';
        out.push(`      searchWater 落点：${tgt}，单价 ${hit.price.toFixed(1)}，折算 ${hit.eff.toFixed(1)}；可装 ${frac}×(余额−保底 ${f(fl)}) = ${f(max)}，最小船量 ${f(min)}（feeK ${P.feeK}×船手续费）→ ${max < min ? '不够最小船量，不发船（L1008）' : '够，发船'}${cnt}`);
      }
    }
  } else {
    out.push(`    [idleBoats] 非封死分支（nb=${pol.nb.length} neut=${pol.neutral} mopUp=${mop}）；闲置线 idleCap×100×地=${f(P.idleCap * 100 * L)}，余额 ${f(B)}`);
    // 两个发船入口各自的门（Policy.idleBoats L5058~5069 → V13.boatFood L2001~2021 / General.boatOut L999~1015）
    if (!mop) {
      const why = [];
      if (!(P.boatFood > 0)) why.push('boatFood 参数为 0');
      if (pol.neutral > 0) why.push('身边还有无主地（L2003）');
      if (!g.boatsAllowed(me) || g.boatCount[me] >= P.maxBoats) why.push(`不能发船或在航船 ${g.boatCount[me]} 条 ≥ maxBoats ${P.maxBoats}（L2004）`);
      let cheapNb = null;
      for (const q of pol.nb) {
        if (!g.alive[q] || pol.person(g, q)) continue;
        let pr = Infinity;
        try { pr = pol.price(g, q); } catch (e) { /* ignore */ }
        if (pr <= P.botMax && (!cheapNb || pr < cheapNb.pr)) cheapNb = { q, pr };
      }
      if (cheapNb) why.push(`陆上邻居里有单价 ≤ botMax ${P.botMax} 的内置 AI：${nm(cheapNb.q)} 地 ${g.terr[cheapNb.q]} 兵 ${f(g.bal[cheapNb.q])} 单价 ${cheapNb.pr.toFixed(1)}（L2005 直接返回，不找海对面的地）`);
      let hit = null;
      if (!why.length) {
        try { hit = pol.searchFood(g); } catch (e) { hit = null; }
        if (!hit) why.push('searchFood 找不到落点');
        else if (hit.eff > P.botMax) why.push(`searchFood 最好的落点折算 ${hit.eff.toFixed(1)} > botMax ${P.botMax}（L2008）`);
        else {
          // L2010~2014：可装 = boatFrac×(余额 − max(reserve, floorAt))，不够最小船量就不发
          let fl = NaN;
          try { const { floorAt } = pol.floors(g); fl = Math.max(pol.reserve(g, hit.price), floorAt(hit.price)); } catch (e) { fl = NaN; }
          const max = P.boatFrac * (B - fl), min = Math.max(60, P.feeK * iV(32 * B, 1024));
          if (Number.isFinite(fl) && max < min) why.push(`searchFood 落点 ${g.px[hit.land] === 1 ? '无主地' : nm(g.own[hit.land])} 折算 ${hit.eff.toFixed(1)}，但可装 boatFrac×(余额 ${f(B)} − 底线 ${f(fl)}) = ${f(max)} < 最小船量 ${f(min)}（L2014）`);
        }
      }
      out.push(`      boatFood（吃海对面的无主地 / 内置 AI，最小船量 = feeK×船手续费 = 余额的 12.5%）：${why.length ? '不发：' + why.join('；') : `会发，落点 ${g.px[hit.land] === 1 ? '无主地' : nm(g.own[hit.land])}，折算 ${hit.eff.toFixed(1)}（冷却另计）`}`);
      const why2 = [];
      if (pol.neutral > 0) why2.push('身边还有无主地（L5059）');
      if (pol.nb.length && B < P.idleCap * 100 * L) why2.push(`有陆上邻居且余额 < 闲置线 ${f(P.idleCap * 100 * L)}（L5060）`);
      if (!g.boatsAllowed(me) || g.boatCount[me] >= P.maxBoats) why2.push(`不能发船或在航船已满`);
      out.push(`      boatOut（把 boatFrac×(余额−底线) 装船去最便宜的落点）：${why2.length ? '不发：' + why2.join('；') : '门都过（冷却另计）'}`);
    }
  }
  return out;
}

// 发船选落点（General.searchWater L1020~1079）的候选清单：照抄它的水面广搜和折算公式，但不提前收工，
// 把每个可登陆对象（无主陆块 / 内置 AI / 真人）各自最好的落点都列出来，看它为什么选了这个、没选那个。
//   折算 eff：无主地 = 2×grow + 船手续费/连片格数；别人的地 = 单价×grow + 船手续费/(0.75×它的领土)，
//   单价 = 2 + 2×它的余额/(1 + 它的领土×10/16)，grow = exp(boatDecay×水程)。水程超过 boatRange 的不在候选里。
// range 给大一点（默认 2500）是为了看「超出 boatRange 的对象离多远」。
export function diagWater(pol, g, nm, range = 2500) {
  const P = pol.p, me = pol.me, N = g.N, px = g.px, own = g.own, d = g.dir4;
  const out = [];
  let comp = null;
  try { comp = pol.compSize(g); } catch (e) { return ['    [searchWater 候选] compSize 出错 ' + String(e).slice(0, 60)]; }
  const dist = new Int32Array(N).fill(-1), q = new Int32Array(N);
  let h = 0, t = 0;
  const seed = (list) => { for (let i = list.length - 1; i >= 0; i--) for (let k = 0; k < 4; k++) { const c = list[i] + d[k]; if (px[c] === 2 && dist[c] < 0) { dist[c] = 0; q[t++] = c; } } };
  seed(g.coast[me]); seed(g.border[me]);
  const fee = P.boatFee > 0 ? iV(32 * g.bal[me], 1024) : 0;
  const noBots = !!pol.botOk && g.bal[me] < P.idleCap * 100 * g.terr[me];
  const best = new Map(); // key -> {eff, dc, price, skip}
  const put = (key, v) => { const o = best.get(key); if (!o || v.eff < o.eff) best.set(key, v); };
  while (h < t) {
    const c = q[h++], dc = dist[c];
    if (dc > range) break;
    const grow = Math.exp(P.boatDecay * dc);
    for (let k = 0; k < 4; k++) {
      const n = c + d[k], v = px[n];
      if (v === 2) { if (dist[n] < 0) { dist[n] = dc + 1; q[t++] = n; } }
      else if (v === 1) put('N' + comp[n], { eff: 2 * grow + fee / Math.max(1, comp[n]), dc, price: 2, what: `无主地（连片 ${comp[n]} 格）`, skip: '' });
      else if (v >= 16) {
        const o = own[n];
        if (o === me) continue;
        let skip = '';
        if (g.teams && g.teams[me] > 0 && g.teams[o] === g.teams[me]) skip = '队友';
        else if (pol.cnt[o] > 0) skip = '已是陆上邻居（L1068 跳过）';
        else if (noBots && g.isBot(o) && !pol.botOk(g, o)) skip = '余额未到闲置线且 botOk=false';
        const price = 2 + (2 * g.bal[o]) / (1 + iV(10 * g.terr[o], 16));
        put('P' + o, { eff: price * grow + fee / Math.max(1, 0.75 * g.terr[o]), dc, price, what: `${nm(o)}${o < g.humans ? '(真人)' : ''} 地 ${g.terr[o]} 兵 ${f(g.bal[o])}`, skip });
      }
    }
  }
  const all = [...best.values()].sort((a, b) => a.eff - b.eff);
  const inR = all.filter((x) => x.dc <= P.boatRange && !x.skip);
  let hit = null;
  try { hit = pol.searchWater(g); } catch (e) { hit = null; }
  const hitTxt = !hit ? '无' : hit.neutral ? `无主地（连片 ${hit.size} 格）` : `${nm(own[hit.land])} 折算 ${hit.eff.toFixed(1)}`;
  out.push(`    [searchWater 候选 L1020~1079] 船手续费 ${f(fee)}，boatRange ${P.boatRange}，boatDecay ${P.boatDecay}；策略自己选的落点：${hitTxt}；范围内可选 ${inR.length} 个，折算最低的几个：`);
  for (const x of inR.slice(0, 4)) out.push(`      ${x.what} 水程 ${x.dc} 单价 ${x.price.toFixed(1)} 折算 ${x.eff.toFixed(1)}`);
  const hum = all.filter((x) => x.what.includes('(真人)'));
  for (const x of hum) {
    const rank = inR.indexOf(x);
    out.push(`      真人对象 ${x.what} 水程 ${x.dc} 单价 ${x.price.toFixed(1)} 折算 ${x.eff.toFixed(1)} → ${x.skip ? x.skip : x.dc > P.boatRange ? '超出 boatRange' : `范围内第 ${rank + 1} 名`}`);
  }
  if (!hum.length) out.push(`      水程 ${range} 以内没有任何真人的岸`);
  return out;
}
