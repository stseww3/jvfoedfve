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

// 捐款/调度门槛（Policy.tryDonateToTeammate L4325~4518 的入口判定）
export function diagDonate(pol, g, nm) {
  const P = pol.p, me = pol.me;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  const out = [];
  const gate = [];
  if (g.t < 1500) gate.push('t<1500');
  if (g.terr[me] < 1200) gate.push('地<1200');
  if (B < 30000) gate.push('余额<30000');
  if (g.t - (pol.lastDonateTick ?? -999) < 12) gate.push('距上次调度<12拍');
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
    out.push(`    [idleBoats L5022~5043 封死分支] 接敌兄弟 ${act} 个，密度 ${dMe.toFixed(0)}，海岸像素 ${g.coast[me].length}，保底 ${act >= 1 ? 92 : 68}×地=${f((act >= 1 ? 92 : 68) * L)} → ${why.length ? '不发船：' + why.join('；') : '会调用 boatOut（范围 2500，至多用 余额−保底 的 24%）'}`);
  } else {
    out.push(`    [idleBoats] 非封死分支（nb=${pol.nb.length} neut=${pol.neutral} mopUp=${mop}）；闲置线 idleCap×100×地=${f(P.idleCap * 100 * L)}，余额 ${f(B)}`);
  }
  return out;
}
