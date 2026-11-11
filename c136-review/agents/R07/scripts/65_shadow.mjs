#!/usr/bin/env node
// 65_shadow.mjs — R07：在「按录像重演出来的真实局面」上影子运行我方策略源码，看它在每一拍会怎么决策、为什么。
//
// 原理：
//   1) 统筹提供的 /agent/repos/c136-data/src/tools/resim.mjs（干净模拟器 src/sim，512 个玩家）把 replay.txt 从头重演，
//      重演结果与我方日志快照逐点核对（本脚本会打印核对结果；对不上就不要引用影子结论）。
//   2) 每一拍结算后，把 src/strategy/ 里对应版本的策略源码（Policy 类，原文不改，只把两行 import 换成绝对路径）
//      对我方每个号各跑一次 act(g)。策略发出的指令被拦下、只记不执行——真正改变局面的仍然是录像里的指令。
//      所以影子策略看到的局面序列和真号当时看到的一样（同一个确定性引擎、同一拍号），它的记忆（冷却、计数等）
//      也随之演化；区别只在：真号有网络延迟/卡顿/掉线，影子没有；用到随机数的地方（开局选点、海上取样）不会一样。
//   3) 影子策略打印的 [HL-TICK]/[HL-OPENING]/[HL-DISPATCH]… 与真日志逐条比对 → 影子可信度（shadow_check.txt）。
//   4) --trace bot:t0:t1 逐决策拍打印 buyLand 的内部量：offers（每个邻居的单价 c、歼灭所需 need、各标记）、
//      地价 worth、安全底 safe、留底 keep、可用 avail、isNoFullSend/shadowQuota，以及影子最终发出的指令。
//      其中 worth/safe/keep/avail 是按源码 buyLand 的公式在脚本里重算的（行号见输出抬头），不是从策略内部读出来的。
//
// 用法（必须套重计算闸）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R07/scripts/65_shadow.mjs <matchId> [--until T]
//        [--bots a,b|all] [--trace bot:t0:t1[:every]]… [--ver va|vb|vc] [--quit engine|none]
//   --quit engine（默认）：把引擎里已离开（state=2）的真人放进 window.__quitPlayers（策略挑受捐方时会跳过它们）；none = 不设
// 输出：out/<matchId>/shadow_log.txt（影子日志）、shadow_cmds.tsv（影子指令）、shadow_check.txt（与真日志比对）、
//       shadow_coast.tsv（每 90 拍各号的海岸格数与能否出船，取自模拟器 g.coast / g.boatsAllowed）、
//       shadow_nofull.tsv（isNoFullSend 何时被锁上、之后挡掉了哪些出兵）、
//       shadow_trace_<bot>_<t0>_<t1>.txt（--trace）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DATA = '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const mid = args[0];
if (!mid) { console.error('用法：65_shadow.mjs <matchId> [--until T] [--bots a,b|all] [--trace bot:t0:t1[:every]] [--ver va|vb|vc]'); process.exit(2); }
const optAll = (k) => { const r = []; for (let i = 0; i < args.length; i++) if (args[i] === k) r.push(args[i + 1]); return r; };
const opt = (k, d) => { const r = optAll(k); return r.length ? r[0] : d; };
const OUT = path.join(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

// ---- 版本 → 源码文件（统筹广播 0002 的版本时间线）
const num = +mid.slice(1);
let ver = opt('--ver', null);
if (!ver) ver = mid[0] === 'A' ? (num <= 17 ? 'va' : num <= 95 ? 'vb' : 'vc') : mid[0] === 'G' ? 'g09' : 'c110';
const SRC = { va: 'v27-team-c116-va.js', vb: 'v27-team-c116-vb.js', vc: 'v27-team-c116.js', g09: 'v27-team-g09.js', c110: 'v27-team-c110.js' }[ver];
const srcPath = path.join(DATA, 'src/strategy', SRC);
let code = fs.readFileSync(srcPath, 'utf8');
const nImp = (code.match(/from "\.\.\/\.\.\/sim\/(index|map)\.js"/g) || []).length;
code = code.replace('from "../../sim/index.js"', `from "${DATA}/src/sim/sim/index.js"`).replace('from "../../sim/map.js"', `from "${DATA}/src/sim/sim/map.js"`);
const cacheDir = path.join(HERE, '..', 'out', '_cache');
fs.mkdirSync(cacheDir, { recursive: true });
const modPath = path.join(cacheDir, `strategy-${ver}.mjs`);
fs.writeFileSync(modPath, `// 由 65_shadow.mjs 生成：${SRC} 原文，只改了 ${nImp} 行 import 的路径\n` + code);

// ---- 影子日志收集（策略用 window.__hlLog 打日志）
let curBot = null, curT = 0;
const shadowLog = [];
globalThis.window = {
  __hlLog: (s) => { shadowLog.push({ bot: curBot, t: curT, text: String(s) }); },
  __tsbSquadSlot: 0,
};

Error.stackTraceLimit = 40;
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
// 船落在没人占的水 / 边界 / 山格时按线上规则处理（见 r07simfix.mjs；来自 R01 的 resim_lib_r01.mjs）
(await import(path.join(HERE, 'r07simfix.mjs'))).applyOddLandingFix(SIM);
const { resim } = await import(path.join(DATA, 'src/tools/resim.mjs'));
const LIB = await import(path.join(DATA, 'src/sim/tools/c102-replay-lib.mjs'));
const STR = await import(pathToFileURL(modPath).href);
const { Policy } = STR;
const { NEUTRAL, iV } = SIM;

// ---- 我方号、名字、slot
const d = LIB.decodeReplay(fs.readFileSync(path.join(DATA, 'bundles', mid, 'replay.txt'), 'utf8'));
const H = d.vu.humanCount;
const names = d.vu.playerNamesData ? Array.from(d.vu.playerNamesData).slice(0, H).map((s) => String(s ?? '')) : [];
const logText = fs.readFileSync(path.join(DATA, 'bundles', mid, 'in_game.log'), 'utf8').split('\n');
const realBots = new Set();
const slotOf = new Map();
for (const ln of logText) {
  const m = /^\d+\t\[([A-Za-z0-9_]+)\] (.*)$/.exec(ln);
  if (!m) continue;
  realBots.add(m[1]);
  const s = /\[HL-SPAWN(?:-BACKEND)?\] me=(\d+) slot=(\d+)/.exec(m[2]);
  if (s) slotOf.set(m[1], +s[2]);
}
const idOf = new Map();
for (const b of realBots) for (let p = 0; p < H; p++) if (names[p].trim().toLowerCase().endsWith(b.toLowerCase())) { idOf.set(b, p); break; }
let botSel = opt('--bots', 'all');
const bots = botSel === 'all' ? [...idOf.keys()] : botSel.split(',');
const until = +opt('--until', 1e9);
const traces = optAll('--trace').map((s) => { const [b, t0, t1, ev] = s.split(':'); return { bot: b, t0: +t0, t1: +t1, every: ev ? +ev : 0, lines: [] }; });

// ---- 影子策略实例
const idOfRev = new Map([...idOf].map(([b, pp]) => [pp, b]));
const pol = new Map();
for (const b of bots) {
  const me = idOf.get(b);
  if (me === undefined) continue;
  const p = new Policy({}, me);
  const origOffers = p.offers.bind(p);
  p.offers = (g) => { const r = origOffers(g); p.__offers = r; return r; };
  // 「不能全额发兵」保护（Policy.send 开头那段）：记下每次被它挡掉 / 改成 1 兵试探的出兵
  if (typeof p.send === 'function' && 'isNoFullSend' in p) {
    const origSend = p.send.bind(p);
    p.send = (g, target, troops, budgetHint) => {
      const B0 = g.bal[me];
      const guard = p.p.quotaGuardMode > 0 && p.isNoFullSend && troops > 2 && p.shadowQuota < Math.min(0.55 * troops, 0.06 * B0);
      const sq = Math.round(p.shadowQuota);
      const ok = budgetHint === undefined ? origSend(g, target, troops) : origSend(g, target, troops, budgetHint);
      if (!p.__sendTry || p.__sendTry.t !== g.t) p.__sendTry = { t: g.t, list: [] };
      p.__sendTry.list.push({ target, troops, ok, guard: !!guard });
      if (guard && target !== NEUTRAL) nfEvents.push([g.t, b, ok ? '改成1兵试探' : '挡掉', pname(g, target), Math.round(troops), sq, B0].join('\t'));
      return ok;
    };
  }
  if (typeof p.tryDonateToTeammate === 'function') {
    const origDon = p.tryDonateToTeammate.bind(p);
    p.tryDonateToTeammate = (g, em = false) => { const ret = origDon(g, em); p.__donTry = { t: g.t, ret, em }; return ret; };
  }
  // 船的门槛：idleBoats 有没有被叫到、boatOut 入口时的船数 / 上限、searchWater 找到的目标与航程
  if (typeof p.idleBoats === 'function' && typeof p.boatOut === 'function' && typeof p.searchWater === 'function') {
    const origIdle = p.idleBoats.bind(p);
    p.idleBoats = (g) => { p.__idle = { t: g.t, calls: [], lastBoat0: p.lastBoat }; return origIdle(g); };
    const origBoatOut = p.boatOut.bind(p);
    p.boatOut = (g, floorAt, maxEff) => {
      const st = { allowed: g.boatsAllowed(me), count: g.boatCount[me], maxBoats: p.p.maxBoats, range: p.p.boatRange, frac: p.p.boatFrac, bal: g.bal[me], maxEff, hit: undefined, dist: -1 };
      p.__boatCall = st;
      const ret = origBoatOut(g, floorAt, maxEff);
      st.ret = ret;
      if (st.hit) { try { st.floor = floorAt(st.hit.price); } catch (e) { st.floor = NaN; } }
      p.__boatCall = null;
      if (p.__idle && p.__idle.t === g.t) p.__idle.calls.push(st);
      return ret;
    };
    const origSW = p.searchWater.bind(p);
    p.searchWater = (g) => {
      const hit = origSW(g);
      const st = p.__boatCall;
      if (st) {
        st.hit = hit || null;
        if (hit && p.wdist) { let dd = -1; for (let k = 0; k < 4; k++) { const v = p.wdist[hit.land + g.dir4[k]]; if (v >= 0 && (dd < 0 || v < dd)) dd = v; } st.dist = dd + 1; }
      }
      return hit;
    };
  }
  pol.set(b, p);
}
const shadowCmds = [];
const coastRows = [];
const nfEvents = [];
const pname = (g, q) => (q === NEUTRAL ? '无主地' : q < H ? `${names[q]}#${q}[T${g.teams[q]}${g.state[q] === 2 ? '离' : ''}]` : `AI#${q}`);

// 按 buyLand 的源码公式重算每个报价的 安全底 / 留底 / 可用兵（Vb：L5350-5446；Va/Vc 行号略有出入，公式相同）
function evalOffers(g, p, lim = 6) {
  const me = p.me, P = p.p;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iV(12 * B, 1024), dMe = B / L;
  const dMedOther = typeof p.otherHumanMedDens === 'function' ? p.otherHumanMedDens(g) : null;
  const m = P.maxW * p.winRatio(g.t);
  const refDens = dMedOther !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMedOther) : dMe;
  const worth = m * refDens, over = P.surplus > 0 && B > 100 * L, cheap = P.growth > 0 ? 0.1 / p.baseRate(g) : 0;
  const rows = [];
  const nHumans = typeof p.livingHumanCount === 'function' ? p.livingHumanCount(g) : 99;
  const humanNbCount = p.nb.filter((x) => g.alive[x] && p.person(g, x)).length;
  for (const o of (p.__offers || []).slice(0, lim)) {
    const q = o.q;
    // buyLand 在算留底之前的几道「价高也不打」的闸（Vb：L5361-5374、L5428-5439）
    const pricey = o.c >= worth && o.c >= cheap;
    const soleBuffer = !!(o.person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1);
    const siegeShrink = !!(P.siegeShrinkRatio > 0 && !p.isNoFullSend && g.t >= P.leaderHardFrom && L < P.siegeShrinkRatio * ((g.peak && g.peak[me]) || L) && nHumans >= 4 && o.person && !o.nearCollapse && !o.bleeding);
    let gate = '';
    if (soleBuffer && pricey && B < P.overHumanCap * 100 * L) gate = '唯一缓冲';
    else if (o.person && !o.isDoorSea && g.terr[q] < 250 && fee > 2 * o.need && o.c > 8 * worth && nHumans >= 3) gate = '残块';
    else if (o.person && !o.isDoorSea && o.isCrowdedHard && pricey && B < P.crowdedHardCap * 100 * L) gate = '拥挤';
    else if (P.absorbMode >= 1 && o.person && !o.isDoorSea && !o.nearCollapse && (o.inAtk ?? 0) >= P.absorbWaveMin * B) gate = '吸收';
    else if (siegeShrink && pricey && B < P.crowdedHardCap * 100 * L) gate = '缩圈';
    let safe = p.safeAt(g, q);
    if (!o.person || o.nearCollapse || (P.bleedSafeCap > 0 && (o.bleeding || o.tD < 0.45))) {
      // Vb L5415-5417：目标濒死且几乎没兵时，安全底的上限从 oppFloorCap 换成 collapseFloorCap
      const capPerPx = o.person && o.nearCollapse && (o.inAtk ?? 0) < 0.02 * B && ((o.c < 0.25 * worth && o.need <= 0.10 * B) || (g.bal[q] <= 0.05 * B && o.c < 25))
        ? Math.min(P.oppFloorCap, P.collapseFloorCap ?? 85) : P.oppFloorCap;
      safe = Math.min(safe, capPerPx * L);
    }
    let keep = Infinity;
    if (o.c < cheap) keep = 0;
    if (o.c < worth) {
      const worthOwn = P.ownWorthMinKeep > 0 && g.t >= P.ownWorthFrom && !o.nearCollapse ? m * dMe : worth;
      const budget = Math.max(0, (worthOwn * L - fee * m - o.c * L) / (1 + m));
      const minKeep = o.person && (o.nearCollapse || (P.bleedDiscount < 1 && o.bleeding) || (P.thinDiscount < 1 && o.tD < P.thinMaxTD)) ? (0.70 * o.c * L) / m : (o.c * L) / m;
      keep = Math.min(keep, P.post > 0 ? Math.max(minKeep, B - fee - budget) : minKeep);
    }
    if (over) keep = Math.min(keep, (dMe >= 122 ? 0.82 : soleBuffer ? P.overHumanKeep : P.hold) * 100 * L);
    keep = Math.max(keep, safe);
    const avail = B - fee - keep;
    let verdict = o.c >= worth && o.c >= cheap && !over ? '价高' : gate ? gate : avail <= 0 ? '无可用' : '';
    let sz = null;
    if (!verdict) {
      sz = sizeOf(g, p, o, B, avail, over);
      verdict = sz.kind;
    }
    rows.push({ o, q, safe, keep, avail, verdict, soleBuffer, humanNbCount, sz });
  }
  return { B, L, fee, dMe, dMedOther, m, worth, over, cheap, rows };
}

// 过了比价和留底之后「发多少」的那一段（Vb：buyLand L5449-5617，c110 / c116 / Va / g09 同一段代码）：
//   在途：对这个目标已经压着的兵（curAtk）过了门槛就不再加（L5575 / L5589 / L5596）；
//   低于最小指令：算出来要发的兵 x < max(minCmd, pulseMinShare×B)，minCmd = feeK × 手续费（L474-476）——跳过这个报价（L5583 / L5591 / L5605）；
//   不够一条：非脉冲分支 x < want 且 x < chunk×B（L5612）。
// counterClearMode / exactRingMode / zeroPulseMode / narrowBoatFirstMode 在这几个版本的参数下都不改变发不发（6 / 0 / 0 / 0），这里不复刻。
function sizeOf(g, p, o, B, avail, over) {
  const P = p.p, me = p.me, q = o.q, need = o.need, cnt = p.cnt[q] ?? 0;
  const minSend = Math.max(typeof p.minCmd === 'function' ? p.minCmd(g) : 0, (P.pulseMinShare ?? 0) * B);
  const curAtk = typeof g.attackTroopsOn === 'function' ? g.attackTroopsOn(me, q) : 0;
  const inAtk = o.inAtk ?? 0;
  const r = (kind, x) => ({ kind, x: Math.round(x ?? 0), minSend: Math.round(minSend), curAtk: Math.round(curAtk) });
  if (!o.person) {
    const want = 1.25 * need + 3 * cnt, x = Math.min(avail, want);
    return r(x <= 0 || (x < want && x < P.chunk * B) ? '不够一条' : '', x);
  }
  const usePulseBlock = P.pulseFrac > 0 && (!over || o.nearCollapse || o.bleeding || need > 0.30 * B || avail < P.chunk * B);
  if (usePulseBlock) {
    if (g.t >= 3800 && (o.nearCollapse || o.bleeding || (P.aggMemMode === 2 && o.isAgg))) {
      if (curAtk >= 0.08 * B || curAtk >= 0.65 * need) return r('在途', 0);
      const targetSlot = Math.min(0.85 * need + 3 * cnt, Math.floor(P.pulseFrac * B));
      let pulse = Math.min(avail, Math.max(targetSlot - curAtk, Math.floor(0.08 * B)));
      if (P.counterClearMode === 2 && !o.nearCollapse && inAtk > 0 && curAtk + pulse <= 1.05 * inAtk) {
        pulse = Math.min(avail, Math.min(Math.floor(0.28 * B), Math.ceil(1.05 * inAtk - curAtk + 0.05 * B)));
      }
      return r(pulse < minSend ? '低于最小指令' : '', pulse);
    }
    if (o.nearCollapse) {
      if (curAtk >= 0.04 * B || curAtk >= 0.30 * need) return r('在途', 0);
      const pulse = Math.min(avail, Math.max(Math.floor(P.pulseFrac * B), Math.min(avail, Math.floor(0.30 * need))));
      return r(pulse < minSend ? '低于最小指令' : '', pulse);
    }
    if (o.pulseMode) {
      if (curAtk >= 0.04 * B) return r('在途', 0);
      let capFrac = Math.floor(P.pulseFrac * B);
      if (P.counterClearMode === 2 && inAtk > 0) capFrac = Math.max(capFrac, Math.min(Math.floor(0.28 * B), Math.ceil(1.05 * inAtk - curAtk + 0.05 * B)));
      const x = Math.min(avail, Math.min(1.20 * need + 3 * cnt, capFrac));
      return r(x < minSend ? '低于最小指令' : '', x);
    }
  }
  const want = 1.25 * need + 3 * cnt, x = Math.min(avail, want);
  return r(x <= 0 || (x < want && (x < P.chunk * B || (P.pplKill > 0 && o.person))) ? '不够一条' : '', x);
}

function classify(ev, cmdsNow, hadOffers) {
  if (cmdsNow.some((c) => c.kind === 'attack' && c.target !== NEUTRAL)) return '出手打人/bot';
  if (cmdsNow.some((c) => c.kind === 'attack')) return '只打无主地';
  if (cmdsNow.some((c) => c.kind === 'donate')) return '捐兵';
  if (cmdsNow.length) return '其他指令';
  if (!hadOffers) return '没走到 buyLand';
  if (!ev.rows.length) return '没有可打的邻居';
  const v = ev.rows[0].verdict;
  if (v === '唯一缓冲') return '过了软上限，但首选目标是唯一的真人邻居（isSoleHealthyBuffer：余额 < overHumanCap×100×领土 不打）';
  if (v === '拥挤') return '过了软上限，但首选目标判为 crowdedHard（余额 < crowdedHardCap×100×领土 不打）';
  if (v === '缩圈') return '过了软上限，但自己领土低于峰值的 siegeShrinkRatio（余额 < crowdedHardCap×100×领土 不打）';
  if (v === '残块' || v === '吸收') return '首选目标被前置闸跳过（残块 / 吸收波）';
  return v === '价高' ? '首选目标价高（c>=worth）' : v === '无可用' ? '首选目标无可用兵（avail<=0）' : v === '不够一条' ? '首选目标可用兵不够一条指令（avail<chunk*B）' : v === '在途' ? '首选目标已有在途进攻（curAtk 过门槛）' : v === '低于最小指令' ? '首选目标要发的兵低于最小指令（x < max(minCmd, pulseMinShare×B)）' : '有可用兵但没发（其他）';
}

function traceLine(g, b, p, tr, cmdsNow, ev) {
  const me = p.me, P = p.p;
  const { B, L, dMe, dMedOther, m, worth, over, cheap } = ev;
  const out = [];
  out.push(`t=${g.t} ${b} B=${B} L=${L} d=${dMe.toFixed(1)} nb=${p.nb.length} neut=${p.neutral} cmds=${p.cmds} noFull=${p.isNoFullSend ? 1 : 0} shQ=${Math.round(p.shadowQuota ?? 0)} | m=${m.toFixed(3)} worth=${worth.toFixed(1)} cheap=${cheap.toFixed(1)} over=${over ? 1 : 0} dMedOther=${dMedOther === null ? '-' : dMedOther.toFixed(1)} safe(-1)=${Math.round(p.safeAt(g, -1))}`);
  for (const r of ev.rows) {
    const o = r.o, q = r.q;
    out.push(`    → ${pname(g, q)} terr=${g.terr[q]} bal=${g.bal[q]} dq=${(g.bal[q] / Math.max(1, g.terr[q])).toFixed(1)} cnt=${p.cnt[q]} | c=${o.c.toFixed(1)} rankC=${(o.rankC ?? o.c).toFixed(1)} need=${Math.round(o.need)} tD=${(o.tD ?? 0).toFixed(2)} ${o.person ? '人' : '机'}${o.pulseMode ? ' pulse' : ''}${o.nearCollapse ? ' nearCollapse' : ''}${o.bleeding ? ' bleeding' : ''}${o.onMe ? ' onMe' : ''}${o.isCrowdedHard ? ' crowdedHard' : ''}${o.isAgg ? ' agg' : ''} | safe=${Math.round(r.safe)} keep=${Number.isFinite(r.keep) ? Math.round(r.keep) : 'Inf'} avail=${Number.isFinite(r.avail) ? Math.round(r.avail) : '-Inf'} chunkB=${Math.round(P.chunk * B)} pulseB=${Math.round(P.pulseFrac * B)} ${r.verdict === '价高' ? '价高(c>=worth)→break' : r.verdict === '无可用' ? '无可用(avail<=0)' : r.verdict === '唯一缓冲' ? `唯一真人邻居(B<${P.overHumanCap}×100×L)→continue` : r.verdict === '拥挤' ? `crowdedHard(B<${P.crowdedHardCap}×100×L)→continue` : r.verdict === '缩圈' ? `siegeShrink(B<${P.crowdedHardCap}×100×L)→continue` : r.verdict === '在途' ? `在途(curAtk=${r.sz.curAtk})→continue` : r.verdict === '低于最小指令' ? `低于最小指令(x=${r.sz.x}<${r.sz.minSend})→continue` : r.verdict === '不够一条' ? `不够一条(x=${r.sz ? r.sz.x : 0})→continue` : r.verdict}${r.sz && !r.verdict ? ` x=${r.sz.x}` : ''}${r.soleBuffer ? ' sole' : ''} hNb=${r.humanNbCount}`);
  }
  if (!ev.rows.length) out.push('    （offers 为空：没有可打的邻居）');
  for (const c of cmdsNow) out.push(`    ⇒ 影子指令 ${c.kind} pct=${c.pct} → ${c.targetName}（约 ${c.troops} 兵）${c.site ? ` 〔${c.site}〕` : ''}`);
  if (!cmdsNow.length) out.push('    ⇒ 本拍没有指令');
  tr.lines.push(...out);
}

// ---- t<dpEnd（1500）打内置 AI 的底线诊断：统筹广播 0004 的「winFloor → safeFinite 队友互锁」假设
// 复刻 V13.threatOf（L417-444），多返回一个「余额最小的那个其他邻居是谁」
function threatOwner(g, q, me) {
  const Bd = g.border[q], px = g.px, own = g.own, d = g.dir4;
  const busyNeutral = g.hasAttack(q, NEUTRAL);
  let minOther = Infinity, owner = -1;
  const seen = new Set();
  const n = Bd.length;
  const step = n > 1024 ? Math.ceil(n / 1024) : 1;
  for (let i = n - 1; i >= 0; i -= step) {
    const b = Bd[i];
    for (let k = 0; k < 4; k++) {
      const c = b + d[k];
      const v = px[c];
      if (v === SIM.T_LAND) { if (!busyNeutral) return { neutral: true, minOther: 0, owner: -1 }; continue; }
      if (v < SIM.P_INNER) continue;
      const o = own[c];
      if (o === q || o === me || seen.has(o)) continue;
      seen.add(o);
      if (g.hasAttack(q, o)) continue;
      const sv = g.bal[o] + g.attackTroopsOn(o, q);
      if (sv < minOther) { minOther = sv; owner = o; }
    }
  }
  return { neutral: false, minOther, owner };
}
const early = new Map(); // bot -> 统计
const earlyEx = [];
function earlyDiag(g, b, p, cmdsNow) {
  const P = p.p, me = p.me;
  if (!(g.t < (P.dpEnd ?? 1500)) || g.t < 300 || g.t % P.period !== 0) return;
  if (typeof p.winFloor !== 'function' || typeof p.floorFor !== 'function') return;
  const nbBots = p.nb.filter((q) => g.alive[q] && g.isBot(q) && g.terr[q] > 0);
  if (!nbBots.length) return;
  if (!early.has(b)) early.set(b, { dec: 0, fired: 0, neutralOnly: 0, idle: 0, cls: new Map(), idleBal: 0, sbMate: 0, sbMateBal: 0, t0: g.t, t1: g.t });
  const st = early.get(b);
  st.dec++; st.t1 = g.t;
  if (cmdsNow.some((c) => c.kind === 'attack' && c.target !== NEUTRAL)) { st.fired++; return; }
  if (cmdsNow.length) { st.neutralOnly++; return; }
  st.idle++;
  const B = g.bal[me], L = Math.max(1, g.terr[me]);
  st.idleBal += B;
  let floorAt = null;
  try { floorAt = p.floors(g).floorAt; } catch (e) { floorAt = null; }
  const min = p.minCmd(g);
  let best = null, anyAllowed = false;
  for (const q of nbBots) {
    let allow = true;
    try { allow = p.allow(g, q); } catch (e) { allow = true; }
    if (!allow) continue;
    anyAllowed = true;
    const perPx = p.price(g, q);
    const fl = p.floorFor(g, q, floorAt ? floorAt(perPx) : 0);
    const avail = B - fl;
    const pass = avail > p.minShare(g, q) * B && avail >= min;
    const mult = p.contested(g, q) ? P.sharedBotMult : 1.0;
    const terms = { 价格项: (mult * p.botPx(g, q) * L) / (P.winR * Math.max(1, g.t)), dpKeep: p.dpKeep(g), safeFinite: p.sb ?? 0, peopleFloor: p.peopleFloor(g) };
    if (!best || avail > best.avail) best = { q, avail, fl, pass, terms, perPx };
  }
  let cls;
  if (!anyAllowed) cls = '邻居 AI 都不让打（allow / botOk 没过：价格高于当拍地价或 winWorth）';
  else if (best.pass) cls = '过了底线但没发（need<=0 / 数额不到一条指令 / 没有空槽）';
  else {
    const top = Object.entries(best.terms).sort((a, c) => c[1] - a[1])[0][0];
    if (top === 'safeFinite') {
      // 参照的是谁
      let who = -1, sb = -1;
      for (const q of p.nb) {
        if (g.alive[q] === 0 || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
        const th = threatOwner(g, q, me);
        if (th.neutral || !Number.isFinite(th.minOther)) continue;
        const v = th.minOther - g.attackTroopsOn(me, q);
        if (v > sb) { sb = v; who = th.owner; }
      }
      const kind = who < 0 ? '未知' : idOfRev.has(who) ? '我方队友' : who >= H ? '另一个内置 AI' : g.isTeammate(me, who) ? '同队真人' : '敌方真人';
      cls = `safeFinite 底线卡住（参照的最弱邻居是${kind}）`;
      if (kind === '我方队友') { st.sbMate++; st.sbMateBal += B; if (best.perPx <= 3) { st.sbMateCheap = (st.sbMateCheap || 0) + 1; st.sbMateCheapTerr = (st.sbMateCheapTerr || 0) + g.terr[best.q]; } }
      if (earlyEx.length < 400 && g.t % 50 === 0) earlyEx.push(`  t=${g.t} ${b} B=${B} L=${L} | 最好的目标 ${pname(g, best.q)}（${g.terr[best.q]} 格 / ${g.bal[best.q]} 兵）每格 ${best.perPx.toFixed(1)} | 底线 ${Math.round(best.fl)} = max(价格项 ${Math.round(best.terms.价格项)}, dpKeep ${Math.round(best.terms.dpKeep)}, safeFinite ${Math.round(best.terms.safeFinite)}, peopleFloor ${Math.round(best.terms.peopleFloor)}) → 可用 ${Math.round(best.avail)} | safeFinite 参照 ${who >= 0 ? pname(g, who) : '?'}（${who >= 0 ? g.bal[who] : '?'} 兵）`);
    } else cls = `${top} 底线卡住`;
  }
  st.cls.set(cls, (st.cls.get(cls) || 0) + 1);
}
// ---- t<coreFrom（1500）、身边既没有内置 AI 也没有无主地的决策拍：开局逻辑（V13 Style.act → pickTarget → allow）为什么不打贴着的敌方真人
// 复刻 Style.floors（L819-831）与 defenseNeed / altOf（L899-941），多返回「defenseNeed 参照的是谁」
function altOwner(g, q, me) {
  const Bd = g.border[q], px = g.px, own = g.own, d = g.dir4;
  let minBal = Infinity, minPrice = Infinity, owner = -1;
  const seen = new Set();
  const n = Bd.length;
  const step = n > 1024 ? Math.ceil(n / 1024) : 1;
  for (let i = n - 1; i >= 0; i -= step) {
    const b = Bd[i];
    for (let k = 0; k < 4; k++) {
      const c = b + d[k];
      if (px[c] < SIM.P_INNER) continue;
      const o = own[c];
      if (o === q || o === me || seen.has(o)) continue;
      seen.add(o);
      const v = g.bal[o] + g.attackTroopsOn(o, q);
      if (v < minBal) { minBal = v; owner = o; }
      const price = 2 + (2 * g.bal[o]) / (1 + iV(10 * g.terr[o], 16));
      if (price < minPrice) minPrice = price;
    }
  }
  return { minBal, minPrice, owner };
}
function floorParts(g, p, perPx) {
  const P = p.p, me = p.me, T = g.terr[me], cap = 100 * T;
  const early = g.t < P.earlyEnd;
  let avgNb = 0;
  for (const o of p.nb) avgNb += g.bal[o];
  if (p.nb.length) avgNb /= p.nb.length; else avgNb = P.lonely * p.avgBotBalance(g);
  const reserveTerm = (early ? P.reserveEarly : P.reserve) * cap * Math.min(1, perPx / P.cRef);
  const refTerm = (early ? P.refEarly : P.ref) * avgNb;
  const bal = g.bal[me], k = 1 + iV(10 * T, 16);
  let need = 0, via = -1, who = -1, mode = '';
  for (const o of p.nb) {
    if (g.alive[o] === 0 || g.bal[o] < P.capMin * bal) continue;
    const a = altOwner(g, o, me);
    const sent = g.attackTroopsOn(me, o);
    let v, m, w = -1;
    if (a.minBal === Infinity) { v = g.bal[o] > 0 ? P.aloneK * g.bal[o] - sent : 0; m = 'alone'; w = o; }
    else { const x1 = a.minBal - sent, x2 = (P.denW * (a.minPrice - 2) * k) / 2; v = P.kDef * Math.max(x1, x2); m = x1 >= x2 ? 'minBal' : 'minPrice'; w = a.owner; }
    if (v > need) { need = v; via = o; who = w; mode = m; }
  }
  if (P.defPile !== 1 && p.attackedByOthers(g, me)) need *= P.defPile;
  const defNeed = Math.min(need, P.defCap * 100 * T);
  const refFloor = Math.max(refTerm, defNeed);
  const fk = p.floorK ?? 1;
  const f = fk * Math.min(P.keepCap * cap, Math.max(reserveTerm, refFloor));
  let bind;
  if (P.keepCap * cap <= Math.max(reserveTerm, refFloor)) bind = 'keepCap';
  else if (reserveTerm >= refFloor) bind = 'reserve';
  else if (defNeed >= refTerm) bind = defNeed < need ? 'defCap' : 'defenseNeed';
  else bind = 'ref';
  return { cap, avgNb, reserveTerm, refTerm, defNeed, via, who, mode, f, bind, kDef: P.kDef, keepCap: P.keepCap };
}
const earlyH = new Map();
const earlyHEx = [];
function earlyHumanDiag(g, b, p, cmdsNow) {
  const P = p.p, me = p.me;
  if (!(g.t < (P.coreFrom ?? 1500)) || g.t < 300 || g.t % P.period !== 0) return;
  if (typeof p.allow !== 'function' || typeof p.floorFor !== 'function') return;
  if (!g.alive[me] || g.terr[me] <= 0) return;
  const nbBots = p.nb.filter((q) => g.alive[q] && g.isBot(q) && g.terr[q] > 0);
  if (nbBots.length || p.neutral > 0) return;
  if (!earlyH.has(b)) earlyH.set(b, { dec: 0, cmd: 0, cls: new Map(), t0: g.t, t1: g.t, bal0: g.bal[me], bal1: g.bal[me], terr0: g.terr[me], terr1: g.terr[me], cheapest: new Map() });
  const st = earlyH.get(b);
  st.dec++; st.t1 = g.t; st.bal1 = g.bal[me]; st.terr1 = g.terr[me];
  if (cmdsNow.length) { st.cmd++; return; }
  const B = g.bal[me], L = Math.max(1, g.terr[me]);
  const hum = p.nb.filter((q) => g.alive[q] && !g.isBot(q) && g.terr[q] > 0 && !g.isTeammate(me, q));
  let cls;
  if (!hum.length) cls = '四周只有队友（没有任何可打的邻居）';
  else {
    let floorAt = null;
    try { floorAt = p.floors(g).floorAt; } catch (e) { floorAt = null; }
    const min = p.minCmd(g);
    let best = null, anyAllowed = false, why = new Map();
    let cheapQ = -1, cheapPx = Infinity;
    for (const q of hum) {
      const perPx = p.price(g, q);
      if (perPx < cheapPx) { cheapPx = perPx; cheapQ = q; }
      let allow = false;
      try { allow = p.allow(g, q); } catch (e) { allow = false; }
      if (!allow) {
        let r;
        if (p.held) r = 'held（本拍按兵不动）';
        else if (P.waitEnd && g.attackTroopsOn(q, me) > 0) r = 'waitEnd（对方正在打我）';
        else if (typeof p.duelOn === 'function' && p.duelOn(g) && !p.duelOk(g, q)) r = `duel（对方密度 > duelK×我的密度，且我没到 duelCap×100×领土）`;
        else if (P.reachBan > 0 && typeof p.outOfReach === 'function' && p.outOfReach(g, q)) r = 'reachBan（够不着）';
        else r = `没有动机（不是 food、单价 ${'>'} personMax=${P.personMax}、没有仇、自己没到 idleCap=${P.idleCap}×100×领土）`;
        why.set(r, (why.get(r) || 0) + 1);
        continue;
      }
      anyAllowed = true;
      const fAt = floorAt ? floorAt(perPx) : 0;
      const fl = p.floorFor(g, q, fAt);
      const avail = B - fl;
      const pass = avail > p.minShare(g, q) * B && avail >= min;
      let need = NaN;
      try { need = p.elimCost(g, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q); } catch (e) { need = NaN; }
      let f0 = NaN, ps = NaN;
      try { f0 = p.floorFor0(g, q, fAt); } catch (e) { f0 = NaN; }
      try { ps = P.safeP > 0 ? P.safeP * p.peopleSafe(g, q) : 0; } catch (e) { ps = NaN; }
      if (!best || avail > best.avail) best = { q, avail, fl, pass, perPx, need, f0, ps, fAt };
    }
    if (!anyAllowed) cls = '敌方真人邻居都不让打：' + [...why.entries()].sort((x, y) => y[1] - x[1])[0][0];
    else if (best.pass) {
      earlyHumanDiag.P = P;
      // pickTarget 里过了底线之后还有三道：need<=0、amount() 不到一条指令、没有空槽 / maxTargets
      let send = NaN;
      try { send = p.amount(g, best.q, best.avail, best.need, min); } catch (e) { send = NaN; }
      let active = 0; const sb0 = g.slotBase(me);
      for (let i = g.atkCount[me] - 1; i >= 0; i--) if (g.atkTarget[sb0 + i] !== NEUTRAL) active++;
      const noSlot = !g.hasAttack(me, best.q) && (active >= P.maxTargets || !g.hasFreeSlot(me));
      const tooDear = best.perPx > P.maxCost;
      cls = noSlot ? '让打、也过了底线，但没有空槽 / 已到 maxTargets' : tooDear ? `让打、也过了底线，但单价 > maxCost（${P.maxCost}）` : !(best.need > 0) ? '让打、也过了底线，但 need<=0' : !(send >= min) ? (P.preyKill > 0 && p.motive(g, best.q) === null && !(P.sendFrac * best.avail >= P.preyKill * best.need) ? '让打、也过了留底，但 sendFrac×可用兵 < preyKill×吃光它要的兵（amount0 L2349：一次吃不光就一个兵都不发）' : `让打、也过了底线，但 amount() 给出的数额不到一条指令（${Number.isFinite(send) ? Math.round(send) : send}）`) : '让打、也过了底线、数额也够，但没发（pickTarget 之外的原因）';
      best.send = send;
    } else {
      // 留底由哪一项定：floorFor = max(floorFor0, safeP×peopleSafe)
      let ref = '';
      if (best.ps >= best.f0 && best.ps > 0) {
        // 复刻 peopleSafe（L2280-2299）找出参照的是谁
        const q = best.q;
        const cands = [];
        for (const o of p.nb) if (o !== q && g.alive[o] && g.terr[o] > 0 && p.person(g, o)) cands.push(o);
        for (const o of p.peopleOf(g, q)) if (o !== me && g.terr[o] > 0 && !cands.includes(o)) cands.push(o);
        let needV = 0, who = -1, via = -1, kind = '';
        for (const Bc of cands) {
          const bB = g.bal[Bc];
          let w = Infinity, wo = -1;
          for (const o of p.peopleOf(g, Bc)) if (o !== me && o !== q && g.terr[o] > 0 && g.bal[o] < w) { w = g.bal[o]; wo = o; }
          const line = bB >= P.safeCapD * Math.max(1, g.terr[Bc]) ? Infinity : bB / P.safeRatio;
          const v = Math.min(w, line);
          if (v > needV) { needV = v; via = Bc; who = w <= line ? wo : Bc; kind = w <= line ? 'weakest' : 'line'; }
        }
        const whoKind = who < 0 ? '未知' : idOfRev.has(who) ? '我方队友' : g.isTeammate(me, who) ? '同队真人' : '敌方真人';
        ref = kind === 'weakest' ? `safeP×peopleSafe：参照「${via >= 0 ? (idOfRev.has(via) ? '我方队友' : '敌方真人') : '?'}邻居的另一个最弱邻居」= ${whoKind}的余额` : `safeP×peopleSafe：参照邻居自己的余额 ÷ safeRatio（${whoKind}）`;
        best.refWho = who; best.refVia = via;
      } else {
        const fp = floorParts(g, p, best.perPx);
        best.fp = fp;
        let dp = NaN, pf = NaN;
        try { dp = p.dpKeep(g); } catch (e) { dp = NaN; }
        try { pf = p.peopleFloor(g); } catch (e) { pf = NaN; }
        best.dp = dp; best.pf = pf;
        const near = (x, y) => Math.abs(x - y) <= 1 + 1e-6 * Math.abs(y);
        earlyHumanDiag.fChk = (earlyHumanDiag.fChk || 0) + 1;
        if (!near(fp.f, best.fAt)) earlyHumanDiag.fBad = (earlyHumanDiag.fBad || 0) + 1;
        if (near(best.f0, dp) && dp > 0 && !near(best.f0, best.fAt)) ref = 'dpKeep（最强的真人邻居全力打我时守得住的余额）';
        else if (near(best.f0, pf) && pf > 0 && !near(best.f0, best.fAt)) ref = 'peopleFloor';
        else if (near(best.f0, best.fAt) || near(best.f0, P.preyFloor * best.fAt)) {
          const pre = near(best.f0, best.fAt) ? '' : `preyFloor(${P.preyFloor})×`;
          if (fp.bind === 'defenseNeed') {
            const whoKind = fp.who < 0 ? '未知' : idOfRev.has(fp.who) ? '我方队友' : fp.who >= H ? '内置 AI' : g.isTeammate(me, fp.who) ? '同队真人' : '敌方真人';
            ref = fp.mode === 'alone' ? `${pre}defenseNeed：邻居没有别的邻居，按它自己的余额` : fp.mode === 'minPrice' ? `${pre}defenseNeed：按邻居的另一个邻居里最低的单价` : `${pre}defenseNeed = kDef(${fp.kDef})×「某个邻居的另一个最弱邻居」的余额，参照的是${whoKind}`;
            best.refWho = fp.who; best.refVia = fp.via;
          } else if (fp.bind === 'keepCap') ref = `${pre}keepCap(${fp.keepCap})×100×领土 封顶（邻居的参照余额更高）`;
          else if (fp.bind === 'defCap') ref = `${pre}defCap×100×领土 封顶的 defenseNeed`;
          else if (fp.bind === 'reserve') ref = `${pre}价格留底（reserve×100×领土×min(1, 单价/cRef)）`;
          else ref = `${pre}ref×邻居平均余额`;
        } else ref = 'floorFor0 的其他分支（foodRef×邻居均值 等）';
      }
      cls = `让打，但可用兵（余额 − 留底）不到 minSend×余额 或不到一条指令；留底由这一项定：${ref}`;
    }
    const key = cheapQ;
    const ce = st.cheapest.get(key) || { n: 0, pxMin: Infinity, pxMax: 0, terr0: g.terr[cheapQ], bal0: g.bal[cheapQ], terr1: 0, bal1: 0 };
    ce.n++; ce.pxMin = Math.min(ce.pxMin, cheapPx); ce.pxMax = Math.max(ce.pxMax, cheapPx); ce.terr1 = g.terr[cheapQ]; ce.bal1 = g.bal[cheapQ];
    st.cheapest.set(key, ce);
    if (earlyHEx.length < 400 && g.t % 100 === 0) earlyHEx.push(`  t=${g.t} ${b} B=${B} L=${L}（密度 ${(B / L).toFixed(1)}）| 最便宜的敌方真人 ${pname(g, cheapQ)}（${g.terr[cheapQ]} 格 / ${g.bal[cheapQ]} 兵）每格 ${cheapPx.toFixed(1)} | ${cls}${best ? `；底线 ${Math.round(best.fl)}（floorFor0 ${Math.round(best.f0)}、safeP×peopleSafe ${Math.round(best.ps)}${best.fp ? `、dpKeep ${Math.round(best.dp)}、peopleFloor ${Math.round(best.pf)}、floorAt ${Math.round(best.fAt)}〔价格留底 ${Math.round(best.fp.reserveTerm)}、ref×邻居均值 ${Math.round(best.fp.refTerm)}、defenseNeed ${Math.round(best.fp.defNeed)}、keepCap 封顶 ${Math.round(best.fp.keepCap * best.fp.cap)}〕` : ''}${best.refWho >= 0 && best.refWho !== undefined ? `，参照 ${pname(g, best.refWho)} 的 ${g.bal[best.refWho]} 兵（经由 ${pname(g, best.refVia)}）` : ''}）、可用 ${Math.round(best.avail)}、吃光要 ${Math.round(best.need)}${best.send !== undefined ? `、amount=${Number.isFinite(best.send) ? Math.round(best.send) : best.send}、minCmd=${Math.round(min)}` : ''}` : ''}`);
  }
  st.cls.set(cls, (st.cls.get(cls) || 0) + 1);
}
// ---- t>=dpEnd（1500）吃内置 AI 的诊断（统筹广播 0005-①②）：身边有内置 AI 的决策拍里，为什么没对它出手
// 按 buyLand 的循环顺序走到第一个非真人报价，用 evalOffers 重算的 worth / safe / keep / avail 归类；
// 留底由 safeFinite 定的那些，再用 threatOwner 找出参照的是谁（我方队友 / 同队真人 / 敌方真人 / 另一个内置 AI）。
const late = new Map();
const lateEx = [];
function lateDiag(g, b, p, cmdsNow) {
  const P = p.p, me = p.me;
  if (g.t < (P.dpEnd ?? 1500) || g.t % P.period !== 0) return;
  const nbBots = p.nb.filter((q) => q >= H && g.alive[q] && g.terr[q] > 0);
  if (!nbBots.length) return;
  if (!late.has(b)) late.set(b, { dec: 0, cls: new Map(), t0: g.t, t1: g.t });
  const st = late.get(b);
  st.dec++; st.t1 = g.t;
  const B = g.bal[me], L = Math.max(1, g.terr[me]);
  const add = (cls, r, extra) => {
    const c = st.cls.get(cls) || { n: 0, terr: 0, bal: 0, cSum: 0, wSum: 0, k: 0 };
    c.n++; c.bal += B;
    if (r) { c.terr += g.terr[r.q]; c.cSum += r.o.c; c.wSum += extra && extra.worth !== undefined ? extra.worth : 0; c.k++; }
    st.cls.set(cls, c);
    if (r && lateEx.length < 600 && g.t % 100 === 0 && !/出手|捐兵/.test(cls)) lateEx.push(`  t=${g.t} ${b} B=${B} L=${L} d=${(B / L).toFixed(1)} | ${pname(g, r.q)}（${g.terr[r.q]} 格 / ${g.bal[r.q]} 兵）每格 ${r.o.c.toFixed(1)}，出价 ${extra ? extra.worth.toFixed(1) : '?'}，need ${Math.round(r.o.need)} | safe ${Math.round(r.safe)} keep ${Number.isFinite(r.keep) ? Math.round(r.keep) : 'Inf'} avail ${Number.isFinite(r.avail) ? Math.round(r.avail) : '-Inf'} → ${cls}${extra && extra.note ? '：' + extra.note : ''}`);
  };
  if (cmdsNow.some((c) => c.kind === 'attack' && c.target >= H && c.target < NEUTRAL)) return add('出手打内置 AI');
  if (cmdsNow.some((c) => c.kind === 'attack' && c.target < H)) return add('本拍出手打了真人');
  if (cmdsNow.some((c) => c.kind === 'donate')) return add('本拍在捐兵');
  if (p.__offers === null) return add(cmdsNow.length ? '本拍只发了别的指令（无主地 / 船），没走到 buyLand' : '没走到 buyLand');
  const ev = evalOffers(g, p, 99);
  const tries = p.__sendTry && p.__sendTry.t === g.t ? p.__sendTry.list.filter((x) => x.target !== NEUTRAL) : [];
  for (const r of ev.rows) {
    const o = r.o;
    if (o.c >= ev.worth && o.c >= ev.cheap && !ev.over) {
      return add(o.person ? '排在前面的真人报价价高，循环到此结束' : '价高：AI 每格成本 ≥ 自己的出价（worth = m×自己的密度）', r, { worth: ev.worth });
    }
    const tried = tries.find((x) => x.target === r.q);
    if (tried && !tried.ok) return add(o.person ? (tried.guard ? '排在前面的真人报价被 isNoFullSend 挡掉，循环到此结束' : '排在前面的真人报价出兵没被接受，循环到此结束') : (tried.guard ? '对 AI 的出兵被 isNoFullSend 挡掉' : '对 AI 的出兵没被接受（没有空槽等）'), r, { worth: ev.worth });
    if (o.person) continue;
    if (r.avail <= 0) {
      let note = '', cls;
      if (r.keep > r.safe + 0.5) cls = '留底占满：价格留底（minKeep / budget）';
      else {
        let sf = 0;
        try { sf = p.safeFinite(g, P.botSkip > 0 ? r.q : -1); } catch (e) { sf = 0; }
        const capped = Math.min(sf, P.oppFloorCap * L);
        if (sf > 0 && capped >= r.safe - 0.5) {
          let who = -1, sb = -1;
          for (const q of p.nb) {
            if (g.alive[q] === 0 || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
            const th = threatOwner(g, q, me);
            if (th.neutral || !Number.isFinite(th.minOther)) continue;
            const v = th.minOther - g.attackTroopsOn(me, q);
            if (v > sb) { sb = v; who = th.owner; }
          }
          const kind = who < 0 ? '未知' : idOfRev.has(who) ? '我方队友' : who >= H ? '另一个内置 AI' : g.isTeammate(me, who) ? '同队真人' : '敌方真人';
          cls = `留底占满：safeFinite（参照的最弱邻居是${kind}）`;
          note = who >= 0 ? `参照 ${pname(g, who)}（${g.bal[who]} 兵）` : '';
        } else cls = '留底占满：真人邻居的兵（killKeep / peopleSafe）';
      }
      return add(cls, r, { worth: ev.worth, note });
    }
    const want = 1.25 * o.need + 3 * p.cnt[r.q];
    const x = Math.min(r.avail, want);
    if (x <= 0 || (x < want && x < P.chunk * ev.B)) return add('可用兵吃不下它、又不到一条指令的下限（x<want 且 x<chunk×余额）', r, { worth: ev.worth });
    return add('按公式该发却没有影子指令（已有别的指令 / 其他）', r, { worth: ev.worth });
  }
  const aiOff = (p.__offers || []).filter((o) => !o.person).length;
  if (!aiOff) {
    const q = nbBots.slice().sort((a, c) => g.terr[c] - g.terr[a])[0];
    if (lateEx.length < 600 && g.t % 100 === 0) lateEx.push(`  t=${g.t} ${b} B=${B} L=${L} d=${(B / L).toFixed(1)} | 邻居 ${pname(g, q)}（${g.terr[q]} 格 / ${g.bal[q]} 兵，接壤 ${p.cnt[q]} 格）不在 offers 里（offers ${p.__offers.length} 个）`);
    if (nbBots.every((x) => g.hasAttack(me, x))) return add('已经在打身边的内置 AI（在途的兵够吃，报价单不再列它）');
    return add('报价单里没有内置 AI（目标数已满 / 没有空槽 / 其他筛选）');
  }
  return add('报价单里有内置 AI，但前面的报价都没走到它');
}
// ---- 调度（Policy.tryDonateToTeammate）没发的原因：按源码的判定顺序逐行复刻（Vb L4325-4518；Va / Vc 只是常数不同），
// 只在每个号自己的相位拍（每 25 拍一次）记一行；复刻出的「捐给谁 / pct」与影子实际发出的捐款逐条比对（见 shadow_donor_gate.txt 抬头）。
const DK = {
  vb: { minBal: 30000, cool: 12, prodBox: [44, 34], prodFront: 92, emBox: [32, 22], emFront: 88, aReq: [42, 30, 102], aAllyMax: Infinity, gap: 16, gapBoxed: false, bReq: [58, 108], bMaxAlly: [140, 128, 96], ideal: [380, 240, 320, 220], minPct: 180 },
  va: { minBal: 30000, cool: 12, prodBox: [72, 66], prodFront: 94, emBox: [32, 22], emFront: 88, aReq: [42, 30, 102], aAllyMax: Infinity, gap: 16, gapBoxed: false, bReq: [82, 108], bMaxAlly: [140, 128, 96], ideal: [260, 190, 225, 170], minPct: 128 },
  vc: { minBal: 35000, cool: 24, prodBox: [76, 70], prodFront: 94, emBox: [58, 48], emFront: 88, aReq: [68, 58, 102], aAllyMax: 85, gap: 15, gapBoxed: true, bReq: [96, 108], bMaxAlly: [94, 88, 88], ideal: [260, 190, 220, 170], minPct: 150 },
}[ver];
const donRows = [];
const fireRows = [];
const donChk = { ok: 0, bad: 0, ex: [] };
function donDiag(g, b, p, cmdsNow, ld0) {
  if (!DK || g.t < 1500 || g.t % 5 !== 0 || typeof p.findBossId !== 'function') return;
  const me = p.me;
  const mySlot = Number.isInteger(window.__tsbSquadSlot) ? window.__tsbSquadSlot : me % 10;
  const phase = ((g.t / 5) | 0) % 5 === mySlot % 5;
  const called = p.__donTry && p.__donTry.t === g.t;
  const sent = cmdsNow.find((c) => c.kind === 'donate');
  if (!phase && !sent) return;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  const row = { t: g.t, donor: b, B, L, dMe, boxedIn: '', coast: '', reason: '', target: '', pct: '', kind: '', cands: [] };
  const fin = (reason) => {
    row.reason = reason;
    donRows.push(row);
    const want = reason.startsWith('SENT') ? `${row.target}/${row.pct}` : '';
    const got = sent ? `${idOfRev.get(sent.target) ?? sent.target}/${sent.pct}` : '';
    if (want === got) donChk.ok++; else { donChk.bad++; if (donChk.ex.length < 12) donChk.ex.push(`t=${g.t} ${b} 复刻=${reason}${want ? ' ' + want : ''} 影子=${got || '没捐'}`); }
  };
  if (!called) return fin(cmdsNow.some((c) => c.kind === 'attack' && c.target < H) ? 'D:nocall-atkH' : cmdsNow.some((c) => c.kind === 'attack' && c.target < NEUTRAL) ? 'D:nocall-atkAI' : cmdsNow.some((c) => c.kind === 'attack') ? 'D:nocall-neutral' : cmdsNow.length ? 'D:nocall-boat' : 'D:nocall-early');
  if (g.terr[me] < 1200) return fin('D:terr<1200');
  if (g.bal[me] < DK.minBal) return fin('D:bal<min');
  if (g.t - (ld0 ?? -999) < DK.cool) return fin('D:cooldown');
  let myIn = 0, myOut = 0;
  for (const a of g.attackersOf(me)) if (!g.isBot(a) && !p.isTeammate(g, a)) myIn += g.attackTroopsOn(a, me);
  const sbMe = g.slotBase(me);
  for (let i = 0; i < g.atkCount[me]; i++) { const tgt = g.atkTarget[sbMe + i]; if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !p.isTeammate(g, tgt)) myOut += g.atkTroops[sbMe + i]; }
  if (myIn > 0) return fin('D:meUnderFire');
  if (myOut > 0.08 * B) return fin('D:meAttacking');
  const enemyHumanNbs = p.nb.filter((q) => g.alive[q] && p.person(g, q));
  let anyEnemyNb = enemyHumanNbs.length > 0;
  if (!anyEnemyNb && p.cnt) for (let q = 0; q < g.humans; q++) if (q !== me && g.alive[q] && !p.isTeammate(g, q) && (p.cnt[q] ?? 0) > 0) { anyEnemyNb = true; break; }
  const boxedIn = !anyEnemyNb && p.nb.length === 0 && p.neutral === 0;
  const coast = (g.coast?.[me]?.length ?? 0) > 0;
  row.boxedIn = boxedIn ? 1 : 0; row.coast = coast ? 1 : 0;
  const bossId = p.findBossId(g);
  if (bossId >= 0 && g.alive[bossId] && g.terr[bossId] >= 100 && sent && sent.target === bossId) { row.target = String(bossId); row.pct = sent.pct; row.kind = 'boss'; row.reason = 'SENT:boss'; donRows.push(row); donChk.ok++; return; }
  const safeM1 = p.safeAt(g, -1);
  const prodOptFloor = boxedIn ? (coast ? DK.prodBox[0] * L : DK.prodBox[1] * L) : Math.max(DK.prodFront * L, safeM1);
  const emergDefFloor = boxedIn ? (coast ? DK.emBox[0] * L : DK.emBox[1] * L) : Math.max(DK.emFront * L, safeM1);
  const quit = typeof window !== 'undefined' && window.__quitPlayers ? window.__quitPlayers : null;
  let maxSquadTerr = 0, topSquadId = -1, maxRandomTeamTerr = 0;
  for (let q = 0; q < g.humans; q++) {
    if (!g.alive[q] || !p.isTeammate(g, q)) continue;
    if (quit && quit.has(q)) continue;
    if (p.isOurSquadBot(g, q) || p.isBossNpl(g, q)) { if (g.terr[q] > maxSquadTerr) { maxSquadTerr = g.terr[q]; topSquadId = q; } }
    else if (!g.isBot(q) && g.terr[q] > maxRandomTeamTerr) maxRandomTeamTerr = g.terr[q];
  }
  let fronts = 0;
  for (let q = 0; q < g.humans; q++) {
    if (g.alive[q] && p.isTeammate(g, q) && (p.isOurSquadBot(g, q) || p.isBossNpl(g, q)) && g.terr[q] >= 150) {
      const nbs = p.peopleOf(g, q);
      if (nbs.some((o) => g.alive[o] && !p.isTeammate(g, o) && g.terr[o] > 0)) fronts++;
    }
  }
  let bestTarget = -1, bestScore = -Infinity, bestKind = 'prod_opt', bestFloor = prodOptFloor;
  const cand = new Map();
  for (let q = 0; q < g.humans; q++) {
    if (q === me || !g.alive[q] || !p.isTeammate(g, q) || (!p.isOurSquadBot(g, q) && !p.isBossNpl(g, q))) continue;
    const nm = idOfRev.get(q) ?? `#${q}`;
    if (g.terr[q] < (fronts <= 2 ? 150 : 1200)) { cand.set(nm, 'C:small'); continue; }
    if (quit && quit.has(q)) { cand.set(nm, 'C:quit'); continue; }
    const Lp = Math.max(1, g.terr[q]), Bp = g.bal[q], dAlly = Bp / Lp;
    if (dAlly >= (boxedIn ? 142 : 115)) { cand.set(nm, 'C:dense'); continue; }
    let inH = 0, outH = 0;
    for (const a of g.attackersOf(q)) if (!g.isBot(a) && !p.isTeammate(g, a)) inH += g.attackTroopsOn(a, q);
    const sbP = g.slotBase(q);
    for (let i = 0; i < g.atkCount[q]; i++) { const tgt = g.atkTarget[sbP + i]; if (tgt >= 0 && tgt < g.humans && !g.isBot(tgt) && !p.isTeammate(g, tgt)) outH += g.atkTroops[sbP + i]; }
    const allyNbs = p.peopleOf(g, q);
    let enemyNbs = 0, botNbs = 0, minEnemyDens = Infinity, hasBleedingPrey = false;
    for (const o of allyNbs) {
      if (o !== me && g.alive[o] && !p.isTeammate(g, o) && g.terr[o] > 0) {
        const doDens = g.bal[o] / Math.max(1, g.terr[o]);
        if (!g.isBot(o)) { enemyNbs++; if (doDens < minEnemyDens) minEnemyDens = doDens; if (doDens < 45 || g.terr[o] <= 0.35 * (g.peak?.[o] ?? g.terr[o])) hasBleedingPrey = true; }
        else { botNbs++; if (doDens < minEnemyDens) minEnemyDens = doDens; if (doDens < 35) hasBleedingPrey = true; }
      }
    }
    if (enemyNbs === 0 && botNbs > 0) enemyNbs = botNbs;
    const allyHasCoast = (g.coast?.[q]?.length ?? 0) > 0;
    const isBeachhead = enemyNbs > 0 && fronts <= 2 && boxedIn;
    const isCrown = (q === topSquadId && enemyNbs > 0 && maxRandomTeamTerr >= 0.70 * maxSquadTerr) || isBeachhead;
    if (enemyNbs === 0 && inH === 0 && outH === 0 && (!boxedIn || !allyHasCoast || dMe < 105 || dAlly > 112)) { cand.set(nm, 'C:rear'); continue; }
    if (!isBeachhead && inH > 1.65 * Bp) { cand.set(nm, 'C:doomedA'); continue; }
    if (!isBeachhead && g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inH > 0.45 * Bp) { cand.set(nm, 'C:doomedB'); continue; }
    const underFire = inH > 0 && (inH >= 0.06 * Bp || dAlly < 88);
    const activePush = outH >= 0.06 * Bp && dAlly < 96;
    const hasPrey = enemyNbs > 0 && (hasBleedingPrey || minEnemyDens < 0.70 * dAlly) && dAlly < 96;
    if (underFire) {
      const reqD = boxedIn ? (coast ? DK.aReq[0] : DK.aReq[1]) : DK.aReq[2];
      if (dMe < reqD) { cand.set(nm, 'A:dMe'); continue; }
      if (dAlly >= DK.aAllyMax) { cand.set(nm, 'A:allyDense'); continue; }
      if (B <= 1.12 * emergDefFloor) { cand.set(nm, 'A:floor'); continue; }
      if ((DK.gapBoxed || !boxedIn) && dMe < dAlly + DK.gap) { cand.set(nm, 'A:gap'); continue; }
      const score = 5000 + (inH / Math.max(1, Bp)) * 1200 + (105 - dAlly) * 20 + Math.min(2200, Lp / 18);
      cand.set(nm, `ok:A:${Math.round(score)}`);
      if (score > bestScore) { bestScore = score; bestTarget = q; bestKind = 'defense_dispatch'; bestFloor = emergDefFloor; }
    } else {
      const reqD = boxedIn ? DK.bReq[0] : DK.bReq[1];
      const maxAllyD = boxedIn ? (activePush || hasPrey || enemyNbs > 0 ? DK.bMaxAlly[0] : DK.bMaxAlly[1]) : DK.bMaxAlly[2];
      if (dMe < reqD) { cand.set(nm, 'B:dMe'); continue; }
      if (dAlly > maxAllyD) { cand.set(nm, 'B:allyDense'); continue; }
      if (B <= 1.14 * prodOptFloor) { cand.set(nm, 'B:floor'); continue; }
      if ((DK.gapBoxed || !boxedIn) && dMe < dAlly + DK.gap) { cand.set(nm, 'B:gap'); continue; }
      const score = (activePush || hasPrey ? 2500 : 1000) + (isCrown ? 1800 : 0) + (outH / Math.max(1, Bp)) * 1200 + (hasBleedingPrey ? 500 : 0) + (100 - dAlly) * 18 + enemyNbs * 80 + Math.min(3500, Lp / 14);
      cand.set(nm, `ok:B:${Math.round(score)}`);
      if (score > bestScore) { bestScore = score; bestTarget = q; bestKind = activePush || hasPrey ? 'offense_dispatch' : 'yield_opt_dispatch'; bestFloor = prodOptFloor; }
    }
  }
  row.cands = [...cand].map(([k, v]) => `${k}=${v}`);
  if (bestTarget < 0) return fin('no-cand');
  const maxSurplus = Math.max(0, B - bestFloor);
  const maxSafePct = Math.floor((maxSurplus * 1024) / Math.max(1, B));
  const idealPct = bestKind === 'defense_dispatch' ? (boxedIn ? DK.ideal[0] : DK.ideal[1]) : (boxedIn ? DK.ideal[2] : DK.ideal[3]);
  const pct = Math.min(maxSafePct, idealPct);
  row.target = idOfRev.get(bestTarget) ?? String(bestTarget); row.pct = pct; row.kind = bestKind;
  if (pct < DK.minPct) return fin('PCT<min');
  return fin(`SENT:${bestKind}`);
}
// 每个决策拍：我方哪些号身上有敌方真人的进攻（协防打分里的 inHumanAtk），以及按 isDoomedPocket 的两个分支会不会被当成弃子
// ---- 船的门槛（t>=1500，四周没有可打的邻居也没有无主地的决策拍）：idleBoats 第一段（v27-team-c116-v*.js Policy.idleBoats）走到了哪一步
const boatRows = [];
function boatDiag(g, b, p, cmdsNow) {
  const P = p.p, me = p.me;
  if (g.t < 1500 || g.t % P.period !== 0 || typeof p.idleBoats !== 'function') return;
  if (!(p.nb && p.nb.length === 0 && p.neutral === 0)) return;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), dMe = B / L;
  const coastPx = g.coast[me] ? g.coast[me].length : 0;
  const row = { t: g.t, bot: b, bal: B, terr: g.terr[me], dMe, coastPx, boats: g.boatCount[me], reason: '', x: '', y: '', neutral: '', size: '', price: '', dist: '', floor: '', max: '', min: '', amount: '' };
  const sent = cmdsNow.find((c) => c.kind === 'boatTo' || c.kind === 'boat');
  const idle = p.__idle && p.__idle.t === g.t ? p.__idle : null;
  if (!g.boatsAllowed(me)) row.reason = coastPx ? 'no-boats-allowed' : 'no-coast';
  else if (!idle) {
    const c = cmdsNow[0];
    row.reason = c ? (c.kind === 'donate' ? 'nocall-donate' : c.kind === 'attack' ? 'nocall-attack' : 'nocall-' + c.kind) : 'nocall-early';
  } else if (!idle.calls.length) {
    let mop = false; try { mop = !!p.isMopUp(g); } catch (e) { mop = false; }
    if (mop) row.reason = 'mopup-nocall';
    else {
      let fb = 0;
      for (let q = 0; q < g.humans; q++) {
        if (q !== me && g.alive[q] && p.isTeammate(g, q) && (p.isOurSquadBot(g, q) || p.isBossNpl(g, q)) && g.terr[q] >= 500) {
          if (window.__quitPlayers && window.__quitPlayers.has(q)) continue;
          if (p.peopleOf(g, q).some((o) => g.alive[o] && !p.isTeammate(g, o) && g.terr[o] > 0)) fb++;
        }
      }
      if (fb >= 1 && dMe < 115) row.reason = 'frontBrother';
      else if (g.boatCount[me] >= 6) row.reason = 'count6';
      else if (g.t - idle.lastBoat0 < Math.min(P.boatEvery, 18)) row.reason = 'cooldown';
      else row.reason = 'idle-return-other';
    }
  } else {
    const st = idle.calls[idle.calls.length - 1];
    if (!st.allowed || st.count >= st.maxBoats) row.reason = `maxBoats(${st.count}/${st.maxBoats})`;
    else if (!st.hit) row.reason = 'nohit';
    else {
      const h = st.hit;
      row.x = h.land % g.W; row.y = (h.land / g.W) | 0; row.neutral = h.neutral ? 1 : 0; row.size = h.size; row.price = h.price.toFixed(1); row.dist = st.dist;
      row.floor = Math.round(st.floor);
      const max = st.frac * (st.bal - st.floor);
      const min = P.boatFee > 0 && h.neutral ? 60 : Math.max(60, P.feeK * iV(32 * st.bal, 1024));
      row.max = Math.round(max); row.min = Math.round(min);
      if (h.eff > st.maxEff) row.reason = 'eff>maxEff';
      else if (max < min) row.reason = 'max<min';
      else {
        const amount = h.neutral ? Math.min(max, Math.max(3 * h.size + 300, min)) : max;
        row.amount = Math.round(amount);
        row.reason = st.ret ? (h.neutral ? 'SENT:neutral' : 'SENT:enemy') : 'boatTo-refused';
      }
    }
  }
  if (sent && !row.reason.startsWith('SENT')) row.reason += '+sentElsewhere';
  boatRows.push(row);
}

function fireScan(g) {
  if (g.t < 1500 || g.t % 5 !== 0) return;
  let maxSquadTerr = 0;
  for (const [b, q] of idOf) if (g.alive[q] && g.state[q] !== 2 && g.terr[q] > maxSquadTerr) maxSquadTerr = g.terr[q];
  for (const [b, q] of idOf) {
    if (!g.alive[q] || g.state[q] === 2) continue;
    let inH = 0;
    for (const a of g.attackersOf(q)) if (a < H && !g.isBot(a) && g.isEnemy(q, a)) inH += g.attackTroopsOn(a, q);
    if (inH <= 0) continue;
    const Lp = Math.max(1, g.terr[q]), Bp = g.bal[q];
    fireRows.push([g.t, b, Lp, Bp, inH, (inH / Math.max(1, Bp)).toFixed(3), inH >= 0.06 * Bp || Bp / Lp < 88 ? 1 : 0, inH > 1.65 * Bp ? 1 : 0, g.t >= 4500 && Lp < 0.22 * maxSquadTerr && inH > 0.45 * Bp ? 1 : 0, maxSquadTerr].join('\t'));
  }
}
const quitMode = opt('--quit', 'engine');
const quitSet = new Set();
// ---- 钩子：每拍结算后跑影子
const proto = SIM.Game.prototype;
const origTick = proto.tick;
let gRef = null;
proto.tick = function () {
  origTick.call(this);
  const g = this;
  if (g.spawnPhase || g.over || g.t > until) return;
  gRef = g;
  if (!g.names) g.names = names;
  if (g.t % 90 === 0) for (const [b, me] of idOf) if (g.alive[me]) coastRows.push([g.t, b, g.terr[me], g.coast[me] ? g.coast[me].length : 0, g.boatsAllowed(me) ? 1 : 0, g.state[me] === 2 ? 1 : 0].join('\t'));
  // window.__quitPlayers：真号由桥接层维护（本包看不到它何时更新）；影子按引擎的「已离开」状态（state=2）近似
  if (quitMode === 'engine') { for (let q = 0; q < H; q++) if (g.state[q] === 2) quitSet.add(q); window.__quitPlayers = quitSet; }
  const onlineHad = Object.prototype.hasOwnProperty.call(g, 'online');
  const online0 = g.online;
  g.online = true;
  for (const [b, p] of pol) {
    const me = p.me;
    if (!g.alive[me] || g.state[me] === 2) continue;
    curBot = b; curT = g.t;
    window.__tsbSquadSlot = slotOf.has(b) ? slotOf.get(b) : me % 10;
    const cmdsNow = [];
    const rec = (kind, pct, target, extra) => {
      const B = g.bal[me];
      const c = { t: g.t, bot: b, kind, pct, target, targetName: kind === 'boat' || kind === 'boatTo' ? `水/岸#${target}` : pname(g, Math.min(target, NEUTRAL)), bal: B, terr: g.terr[me], troops: iV(B * (Math.min(1023, Math.max(0, pct | 0)) + 1), 1024), extra };
      const fr = [];
      for (const ln of (new Error().stack || '').split('\n').slice(2)) {
        const m = /at (?:async )?(?:new )?(\S+)? ?\(?[^()]*strategy-[a-z0-9]+\.mjs:(\d+):\d+\)?/.exec(ln);
        if (m) fr.push(`${(m[1] || '?').replace(/^.*\./, '')}:${+m[2] - 1}`);
        if (fr.length >= 4) break;
      }
      c.site = fr.join('<');
      cmdsNow.push(c); shadowCmds.push(c);
    };
    g.attack = (pct, target, pl = me) => {
      if (pl !== me) return false;
      const tg = Math.min(target, NEUTRAL);
      if (tg < NEUTRAL && g.alive[tg] && !g.isEnemy(me, tg)) return false;
      if (!g.hasAttack(me, tg < NEUTRAL && !g.alive[tg] ? NEUTRAL : tg) && !g.hasFreeSlot(me)) return false;
      rec('attack', pct, tg); return true;
    };
    g.donate = (pct, q, pl = me) => { if (pl !== me || !g.alive[q] || !g.isTeammate(me, q)) return false; rec('donate', pct, q); return true; };
    g.boat = (pct, water, dir, pl = me) => { if (!g.boatsAllowed(me)) return false; rec('boat', pct, water, dir); return true; };
    g.boatTo = (pct, target, pl = me, radius = 32) => { if (!g.boatsAllowed(me)) return false; rec('boatTo', pct, target, radius); return true; };
    g.chase = (pct, id, pl = me) => { rec('chase', pct, NEUTRAL, id); return true; };
    g.recall = (id, pl = me) => { rec('recall', 0, NEUTRAL, id); return true; };
    g.retreat = (target, pl = me) => { rec('retreat', 0, Math.min(target, NEUTRAL)); return true; };
    p.__offers = null;
    const ld0 = p.lastDonateTick;
    const nf0 = p.isNoFullSend, pc0 = p.pendingQuotaCheck ? { ...p.pendingQuotaCheck } : null;
    try { p.act(g); } catch (e) { shadowLog.push({ bot: b, t: g.t, text: `[SHADOW-ERROR] ${e && e.message}` }); }
    if (nf0 === false && p.isNoFullSend) {
      const B = g.bal[me];
      nfEvents.push([g.t, b, '锁上isNoFullSend', pc0 ? `待核对出兵:发令拍=${pc0.t - 1} 想发=${Math.round(pc0.want)} 发令时余额=${pc0.bal0} 手续费=${pc0.fee} 本拍余额=${B} 推算实发=${Math.max(0, pc0.bal0 - B - pc0.fee)}` : '无待核对记录', '', '', B].join('\t'));
    }
    delete g.attack; delete g.donate; delete g.boat; delete g.boatTo; delete g.chase; delete g.recall; delete g.retreat;
    try { earlyDiag(g, b, p, cmdsNow); } catch (e) { if (!earlyDiag.err) { earlyDiag.err = String(e && e.message); } }
    try { earlyHumanDiag(g, b, p, cmdsNow); } catch (e) { if (!earlyHumanDiag.err) { earlyHumanDiag.err = String(e && e.stack); } }
    try { lateDiag(g, b, p, cmdsNow); } catch (e) { if (!lateDiag.err) { lateDiag.err = String(e && e.message); } }
    try { donDiag(g, b, p, cmdsNow, ld0); } catch (e) { if (!donDiag.err) { donDiag.err = String(e && e.stack); } }
    try { boatDiag(g, b, p, cmdsNow); } catch (e) { if (!boatDiag.err) { boatDiag.err = String(e && e.stack); } }
    for (const tr of traces) {
      if (tr.bot !== b || g.t < tr.t0 || g.t > tr.t1) continue;
      const P = p.p;
      const decisionTick = g.t % P.period === 0;
      if (!decisionTick && !cmdsNow.length) continue;
      const ev = evalOffers(g, p);
      const cls = classify(ev, cmdsNow, p.__offers !== null);
      tr.stats = tr.stats || new Map();
      const st = tr.stats.get(cls) || { n: 0, t0: g.t, t1: g.t, availMin: Infinity, availMax: -Infinity, chunkMin: Infinity, chunkMax: -Infinity, ratioMin: Infinity, ratioMax: -Infinity };
      st.n++; st.t1 = g.t;
      if (ev.rows.length && Number.isFinite(ev.rows[0].avail)) {
        const a = ev.rows[0].avail, ck = P.chunk * ev.B;
        st.availMin = Math.min(st.availMin, a); st.availMax = Math.max(st.availMax, a);
        st.chunkMin = Math.min(st.chunkMin, ck); st.chunkMax = Math.max(st.chunkMax, ck);
        st.ratioMin = Math.min(st.ratioMin, a / ck); st.ratioMax = Math.max(st.ratioMax, a / ck);
      }
      const fired = cmdsNow.find((c) => c.kind === 'attack' && c.target !== NEUTRAL);
      if (fired) {
        const row = ev.rows.find((r) => r.q === fired.target);
        st.fireN = (st.fireN || 0) + 1;
        st.fireTroops = (st.fireTroops || 0) + (fired.troops || 0);
        if (ev.over) st.overN = (st.overN || 0) + 1;
        if (row && row.o.c >= ev.worth) {
          st.hiN = (st.hiN || 0) + 1;
          st.hiTroops = (st.hiTroops || 0) + (fired.troops || 0);
          const rt = row.o.c / Math.max(1e-9, ev.worth);
          st.hiMin = Math.min(st.hiMin ?? Infinity, rt); st.hiMax = Math.max(st.hiMax ?? -Infinity, rt);
        }
      }
      tr.stats.set(cls, st);
      if (tr.every && g.t % tr.every !== 0 && !cmdsNow.length) continue;
      if (p.__offers === null && !cmdsNow.length && g.t >= P.coreFrom) { tr.lines.push(`t=${g.t} ${b}（本拍没走到 buyLand）B=${g.bal[me]} L=${g.terr[me]} cmds=${p.cmds}`); continue; }
      traceLine(g, b, p, tr, cmdsNow, ev);
    }
  }
  if (onlineHad) g.online = online0; else delete g.online;
  try { fireScan(g); } catch (e) { if (!fireScan.err) fireScan.err = String(e && e.message); }
};

const t0 = Date.now();
const out = resim(mid, { until: Number.isFinite(until) ? until : undefined });
proto.tick = origTick;
const v = out.validate;

// ---- 与真日志比对
const real = { tick: new Map(), dis: new Map(), open: new Map() };
const reTick = /\[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+) dens=[\d.]+ nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)/;
const reDis = /\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)\/1024 -> ally=(\d+)/;
const reOpen = /\[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)\/(\d+)/;
const put = (store, bot, text) => {
  let m = reTick.exec(text);
  if (m) { store.tick.set(`${bot}@${m[1]}`, { terr: +m[2], bal: +m[3], nb: +m[4], neut: +m[5], cmds: +m[6], boats: +m[7] }); return; }
  m = reDis.exec(text);
  if (m) { store.dis.set(`${bot}@${m[1]}`, { kind: m[2], pct: +m[3], to: +m[4] }); return; }
  m = reOpen.exec(text);
  if (m) store.open.set(`${bot}@${m[1]}`, { cyc: +m[2], rings: +m[3], spend: +m[4], bal: +m[5] });
};
for (const ln of logText) { const m = /^\d+\t\[([A-Za-z0-9_]+)\] (.*)$/.exec(ln); if (m) put(real, m[1], m[2]); }
const sh = { tick: new Map(), dis: new Map(), open: new Map() };
for (const l of shadowLog) put(sh, l.bot, l.text);
const chk = [];
chk.push(`# ${mid} 影子运行（策略 ${SRC}；重演 ${out.endTick} 拍，用时 ${((Date.now() - t0) / 1000).toFixed(1)} 秒）`);
chk.push(`# 重演与 traj.csv 快照核对：${v.rows} 行，领土一致 ${v.terrExact}，余额一致 ${v.balExact}，都一致 ${v.bothExact}`);
{
  let n = 0, same = 0, nbSame = 0, neutSame = 0, cmdSame = 0, stateSame = 0;
  const perBot = new Map();
  for (const [k, r] of real.tick) {
    const s = sh.tick.get(k);
    const b = k.split('@')[0];
    if (!pol.has(b) || +k.split('@')[1] > until) continue;
    const pb = perBot.get(b) || { n: 0, miss: 0, nb: 0, neut: 0, cmds: 0, dCmds: [] };
    perBot.set(b, pb);
    n++; pb.n++;
    if (!s) { pb.miss++; continue; }
    if (s.terr === r.terr && s.bal === r.bal) stateSame++;
    if (s.nb === r.nb) { nbSame++; pb.nb++; }
    if (s.neut === r.neut) { neutSame++; pb.neut++; }
    if (s.cmds === r.cmds) { cmdSame++; pb.cmds++; }
    pb.dCmds.push(s.cmds - r.cmds);
    (pb.dT = pb.dT || []).push(+k.split('@')[1]);
    if (s.nb === r.nb && s.neut === r.neut && s.cmds === r.cmds) same++;
  }
  chk.push(`# HL-TICK 比对：真日志 ${n} 条；影子同拍 领土余额一致 ${stateSame}，nb 一致 ${nbSame}，neut 一致 ${neutSame}，cmds 计数一致 ${cmdSame}，三项全一致 ${same}`);
  for (const [b, pb] of perBot) {
    const last = pb.dCmds.length ? pb.dCmds[pb.dCmds.length - 1] : 0;
    chk.push(`#   ${b}: ${pb.n} 条，影子缺 ${pb.miss}，nb 一致 ${pb.nb}，neut 一致 ${pb.neut}，cmds 一致 ${pb.cmds}；最后一条 cmds 差（影子-真）${last}`);
    // cmds 差的变化点：影子在哪一段多发 / 少发了指令（真号的 cmds 只在 send 成功时加一）
    const order = (pb.dT || []).map((t, i) => [t, pb.dCmds[i]]).sort((a, b2) => a[0] - b2[0]);
    let prevD = 0, prevT = 0;
    const chg = [];
    for (const [t, dd] of order) {
      if (dd !== prevD) {
        const mine = shadowCmds.filter((c) => c.bot === b && c.t > prevT && c.t <= t).map((c) => `${c.t}:${c.kind} ${c.pct}→${c.targetName}`);
        chg.push(`(${prevT},${t}] 差 ${prevD}→${dd}；这一段影子指令：${mine.join('、') || '无'}`);
      }
      prevD = dd; prevT = t;
    }
    for (const c of chg.slice(0, 6)) chk.push(`#       变化点 ${c}`);
    if (chg.length > 6) chk.push(`#       …共 ${chg.length} 个变化点`);
  }
}
{
  let n = 0, hit = 0, sameKind = 0; const miss = [];
  for (const [k, r] of real.dis) {
    const b = k.split('@')[0];
    if (!pol.has(b) || +k.split('@')[1] > until) continue;
    n++;
    const s = sh.dis.get(k);
    if (s && s.pct === r.pct && s.to === r.to) { hit++; if (s.kind === r.kind) sameKind++; } else if (miss.length < 8) miss.push(`${k}:真 ${r.kind} pct=${r.pct}→${r.to} 影子 ${s ? `${s.kind} pct=${s.pct}→${s.to}` : '无'}`);
  }
  let extra = 0; const ex = [];
  for (const [k, s] of sh.dis) if (!real.dis.has(k)) { extra++; if (ex.length < 8) ex.push(`${k}:${s.kind} pct=${s.pct}→${s.to}`); }
  chk.push(`# HL-DISPATCH 比对：真日志 ${n} 条；影子在同一拍给出同对象同比例 ${hit} 条（其中种类也相同 ${sameKind}）；影子多出 ${extra} 条`);
  if (miss.length) chk.push('#   真有影子无/不同（前 8）：' + miss.join('；'));
  if (ex.length) chk.push('#   影子多出（前 8）：' + ex.join('；'));
}
{
  let n = 0, hit = 0;
  for (const [k, r] of real.open) { const b = k.split('@')[0]; if (!pol.has(b) || +k.split('@')[1] > until) continue; n++; const s = sh.open.get(k); if (s && s.spend === r.spend && s.bal === r.bal) hit++; }
  chk.push(`# HL-OPENING 比对：真日志 ${n} 条；影子同拍同金额 ${hit} 条；影子共 ${sh.open.size} 条`);
}
const errs = shadowLog.filter((l) => l.text.startsWith('[SHADOW-ERROR]'));
chk.push(`# 影子策略报错 ${errs.length} 条${errs.length ? '：' + errs.slice(0, 3).map((e) => `${e.bot}@${e.t} ${e.text}`).join(' | ') : ''}`);
const kinds = {};
for (const c of shadowCmds) { const k = `${c.bot}:${c.kind}`; kinds[k] = (kinds[k] || 0) + 1; }
chk.push('# 影子指令计数：' + Object.entries(kinds).sort().map(([k, n]) => `${k}×${n}`).join(' '));
{
  // 每条影子指令是从策略源码的哪一行发出来的（调用栈里属于策略文件的最里 4 层，行号已换回原文件行号）
  const bySite = new Map();
  for (const c of shadowCmds) {
    const tgt = c.kind !== 'attack' ? '' : c.target >= NEUTRAL ? '→无主地' : c.target >= H ? '→内置AI' : '→真人';
    const k = `${c.kind}${tgt} 〔${c.site || '?'}〕`;
    const e = bySite.get(k) || { n: 0, troops: 0, t0: c.t, t1: c.t };
    e.n++; e.troops += c.troops; e.t0 = Math.min(e.t0, c.t); e.t1 = Math.max(e.t1, c.t);
    bySite.set(k, e);
  }
  chk.push('# 影子指令的发令位置（策略源码行号）：');
  for (const [k, e] of [...bySite].sort((a, b) => b[1].n - a[1].n)) chk.push(`#   ${k}：${e.n} 条，约 ${e.troops.toLocaleString('en-US')} 兵，t=${e.t0}~${e.t1}`);
}
fs.writeFileSync(path.join(OUT, 'shadow_check.txt'), chk.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'shadow_log.txt'), shadowLog.map((l) => `${l.t}\t[${l.bot}] ${l.text}`).join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'shadow_cmds.tsv'), 't\tbot\tkind\tpct\ttarget\ttargetName\tbal\tterr\ttroops\tsite\n' + shadowCmds.map((c) => [c.t, c.bot, c.kind, c.pct, c.target, c.targetName, c.bal, c.terr, c.troops, c.site || ''].join('\t')).join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'shadow_nofull.tsv'), 't\tbot\tevent\tdetail_or_target\twantTroops\tshadowQuota\tbal\n' + nfEvents.join('\n') + '\n');
{
  const per = new Map();
  for (const r of nfEvents) { const [t, b, ev] = r.split('\t'); const o = per.get(b) || { lock: null, block: 0, poke: 0, firstBlock: null, lastBlock: null }; per.set(b, o); if (ev.startsWith('锁上')) { if (o.lock === null) o.lock = +t; } else { if (ev === '挡掉') o.block++; else o.poke++; if (o.firstBlock === null) o.firstBlock = +t; o.lastBlock = +t; } }
  const line = [...per].map(([b, o]) => `${b}: 锁上@${o.lock ?? '-'} 之后被挡 ${o.block} 次、改 1 兵试探 ${o.poke} 次${o.firstBlock !== null ? `（t=${o.firstBlock}~${o.lastBlock}）` : ''}`).join('；');
  console.log('# isNoFullSend（影子）：' + (line || '全程没有任何号被锁上'));
  fs.appendFileSync(path.join(OUT, 'shadow_check.txt'), '# isNoFullSend（影子）：' + (line || '全程没有任何号被锁上') + '\n');
}
{
  const E = [`# ${mid} t=300~1499 有内置 AI 邻居的决策拍：影子有没有出手，没出手时卡在哪条底线（策略 ${SRC}；Style.pickTarget → floorFor → floorFor0 → winFloor = max(价格项, dpKeep, safeFinite)）`];
  if (earlyDiag.err) E.push(`# 诊断出错：${earlyDiag.err}`);
  let T = { dec: 0, fired: 0, neutralOnly: 0, idle: 0, sbMate: 0 };
  for (const [b, st] of early) {
    E.push(`${b}: 有 AI 邻居的决策拍 ${st.dec}（t=${st.t0}~${st.t1}）；出手打 AI/人 ${st.fired}；只打无主地/其他指令 ${st.neutralOnly}；零指令 ${st.idle}` + (st.idle ? `（零指令时平均余额 ${Math.round(st.idleBal / st.idle)}）` : ''));
    for (const [k, n] of [...st.cls].sort((a, c) => c[1] - a[1])) E.push(`    ${k}: ${n} 拍`);
    T.dec += st.dec; T.fired += st.fired; T.neutralOnly += st.neutralOnly; T.idle += st.idle; T.sbMate += st.sbMate; T.cheap = (T.cheap || 0) + (st.sbMateCheap || 0); T.cheapTerr = (T.cheapTerr || 0) + (st.sbMateCheapTerr || 0);
    for (const [k, n] of st.cls) { const kk = k.startsWith('safeFinite') ? 'safeFinite（任何参照）' : k.startsWith('邻居 AI') ? '不让打' : k.startsWith('过了底线') ? '过了底线没发' : '其他底线'; T[kk] = (T[kk] || 0) + n; }
  }
  E.push(`# 合计：决策拍 ${T.dec}，出手 ${T.fired}，只打无主地/其他 ${T.neutralOnly}，零指令 ${T.idle}；其中 safeFinite 底线卡住且参照的是我方队友 ${T.sbMate} 拍（占零指令 ${T.idle ? (100 * T.sbMate / T.idle).toFixed(1) : '0'}%）`);
  E.push(`#       零指令拍按原因：safeFinite（任何参照）${T['safeFinite（任何参照）'] || 0}，邻居 AI 不让打（价格高于 winWorth / 当拍地价）${T['不让打'] || 0}，价格项或 dpKeep 等其他底线 ${T['其他底线'] || 0}，过了底线没发 ${T['过了底线没发'] || 0}`);
  E.push(`#       「参照我方队友」的 ${T.sbMate} 拍里，最好的目标每格成本 ≤3 兵（几乎是空地）的 ${T.cheap || 0} 拍，这些目标当时平均 ${T.cheap ? Math.round(T.cheapTerr / T.cheap) : 0} 格`);
  if (earlyEx.length) { E.push('# 例子（每 50 拍取一条）'); E.push(...earlyEx.slice(0, 60)); }
  fs.writeFileSync(path.join(OUT, 'shadow_early.txt'), E.join('\n') + '\n');
  {
    const EH = [`# ${mid} t=300~1499 身边既没有内置 AI、也没有无主地的决策拍：开局逻辑为什么不打贴着的敌方真人（策略 ${SRC}；Policy.act → super.act（V13 Style.act）→ pickTarget → allow / floorFor）`];
    if (earlyHumanDiag.err) EH.push(`# 诊断出错：${earlyHumanDiag.err}`);
    EH.push(`# floorAt 复刻核对：${earlyHumanDiag.fChk || 0} 次里不一致 ${earlyHumanDiag.fBad || 0} 次`);
    { const Pq = (earlyHumanDiag.P) || (pol.values().next().value || {}).p || {}; EH.push(`# 生效参数：preyKill=${Pq.preyKill} preyFloor=${Pq.preyFloor} personMax=${Pq.personMax} idleCap=${Pq.idleCap} minSend=${Pq.minSend} sendFrac=${Pq.sendFrac} feeK=${Pq.feeK} reserve=${Pq.reserve} cRef=${Pq.cRef} keepCap=${Pq.keepCap} kDef=${Pq.kDef} capMin=${Pq.capMin} denW=${Pq.denW} defCap=${Pq.defCap} ref=${Pq.ref} earlyEnd=${Pq.earlyEnd} coreFrom=${Pq.coreFrom} dpEnd=${Pq.dpEnd}`); }
    let tot = { dec: 0, cmd: 0 }; const totCls = new Map();
    for (const [b, st] of earlyH) {
      tot.dec += st.dec; tot.cmd += st.cmd;
      EH.push(`${b}: 这样的决策拍 ${st.dec}（t=${st.t0}~${st.t1}）；其中有指令 ${st.cmd}；余额 ${st.bal0}→${st.bal1}，领土 ${st.terr0}→${st.terr1}`);
      for (const [c, n] of [...st.cls.entries()].sort((x, y) => y[1] - x[1])) { EH.push(`    ${c}: ${n} 拍`); totCls.set(c, (totCls.get(c) || 0) + n); }
      for (const [q, ce] of [...st.cheapest.entries()].sort((x, y) => y[1].n - x[1].n).slice(0, 3)) EH.push(`    最便宜的敌方真人邻居 ${names[q]}#${q}：${ce.n} 拍，每格 ${ce.pxMin.toFixed(1)}~${ce.pxMax.toFixed(1)} 兵；它 ${ce.terr0} 格 / ${ce.bal0} 兵 → ${ce.terr1} 格 / ${ce.bal1} 兵`);
    }
    EH.push(`# 合计：决策拍 ${tot.dec}，有指令 ${tot.cmd}；零指令按原因：${[...totCls.entries()].sort((x, y) => y[1] - x[1]).map(([c, n]) => `${c} ${n}`).join('；')}`);
    if (earlyHEx.length) { EH.push('# 例子（每 100 拍取一条）'); EH.push(...earlyHEx.slice(0, 80)); }
    fs.writeFileSync(path.join(OUT, 'shadow_early_humans.txt'), EH.join('\n') + '\n');
  }
  console.log(E.filter((x) => x.startsWith('# 合计') || x.startsWith('#       ')).join('\n'));
}
{
  const E = [`# ${mid} t>=1500 吃内置 AI 的诊断（影子运行；只统计身边有内置 AI 的决策拍；归类按 buyLand 循环走到的第一个非真人报价）`];
  if (lateDiag.err) E.push(`# 诊断出错：${lateDiag.err}`);
  const tot = new Map(); let dec = 0;
  for (const [b, st] of late) { dec += st.dec; for (const [k, c] of st.cls) { const t = tot.get(k) || { n: 0, terr: 0, bal: 0, cSum: 0, wSum: 0, k: 0 }; t.n += c.n; t.terr += c.terr; t.bal += c.bal; t.cSum += c.cSum; t.wSum += c.wSum; t.k += c.k; tot.set(k, t); } }
  const fmtC = (c) => `${c.n} 拍${c.k ? `（目标平均 ${Math.round(c.terr / c.k)} 格，每格成本平均 ${(c.cSum / c.k).toFixed(1)}，出价平均 ${(c.wSum / c.k).toFixed(1)}；当拍自己余额平均 ${Math.round(c.bal / c.n).toLocaleString('en-US')}）` : `（当拍自己余额平均 ${Math.round(c.bal / Math.max(1, c.n)).toLocaleString('en-US')}）`}`;
  E.push(`全队：身边有内置 AI 的决策拍 ${dec} 个`);
  for (const [k, c] of [...tot].sort((a, c2) => c2[1].n - a[1].n)) E.push(`    ${k}: ${fmtC(c)}`);
  for (const [b, st] of late) {
    E.push(`${b}: 决策拍 ${st.dec}（t=${st.t0}~${st.t1}）`);
    for (const [k, c] of [...st.cls].sort((a, c2) => c2[1].n - a[1].n)) E.push(`    ${k}: ${fmtC(c)}`);
  }
  if (lateEx.length) { E.push('# 例子（每 100 拍取一条）'); E.push(...lateEx.slice(0, 80)); }
  fs.writeFileSync(path.join(OUT, 'shadow_late_ai.txt'), E.join('\n') + '\n');
}
if (DK) {
  fs.writeFileSync(path.join(OUT, 'shadow_donor_gate.tsv'), `# 复刻校验：${donChk.ok} 行一致 / ${donChk.bad} 行不一致${donDiag.err ? ' | 出错：' + donDiag.err.split('\n')[0] : ''}${donChk.ex.length ? ' | ' + donChk.ex.join(' ; ') : ''}\n` +
    't\tdonor\tbal\tterr\tdMe\tboxedIn\tcoast\treason\ttarget\tpct\tkind\tcands\n' + donRows.map((r) => [r.t, r.donor, r.B, r.L, r.dMe.toFixed(1), r.boxedIn, r.coast, r.reason, r.target, r.pct, r.kind, r.cands.join(';')].join('\t')).join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'shadow_underfire.tsv'), (fireScan.err ? `# 出错：${fireScan.err}\n` : '') + 't\tbot\tterr\tbal\tinHumanAtk\tratio\tunderFire\tdoomedA\tdoomedB\tmaxSquadTerr\n' + fireRows.join('\n') + '\n');
  console.log(`# 调度门槛复刻：${donRows.length} 行（相位拍），与影子实际捐款比对 ${donChk.ok} 一致 / ${donChk.bad} 不一致${donDiag.err ? '；出错 ' + donDiag.err.split('\n').slice(0, 2).join(' | ') : ''}`);
  for (const e of donChk.ex) console.log('#   ' + e);
}
{
  const cols = ['t', 'bot', 'bal', 'terr', 'dMe', 'coastPx', 'boats', 'reason', 'x', 'y', 'neutral', 'size', 'price', 'dist', 'floor', 'max', 'min', 'amount'];
  fs.writeFileSync(path.join(OUT, 'shadow_boat_gate.tsv'), (boatDiag.err ? `# 出错：${boatDiag.err.split('\n')[0]}\n` : '') + cols.join('\t') + '\n' + boatRows.map((r) => cols.map((c) => c === 'dMe' ? r.dMe.toFixed(1) : r[c]).join('\t')).join('\n') + '\n');
  const LBL = { 'no-coast': '没有海岸格（引擎不让出船）', 'no-boats-allowed': '有海岸格但引擎不让出船', 'nocall-donate': '本拍在捐兵（调度排在船前面）', 'nocall-attack': '本拍已出兵', 'nocall-early': '本拍没走到 idleBoats', 'frontBrother': '有队友还贴着敌人、自己密度 <115：不出船', 'count6': '在海上的船 ≥6', 'cooldown': '距上次找船不到 18 拍', 'nohit': '找不到目标（2500 格水路内没有无主地 / 非邻居的敌人）', 'max<min': '留底以上的 boatFrac 份额不到一条船的下限', 'SENT:neutral': '发船去无主地', 'SENT:enemy': '发船去敌人的岸', 'mopup-nocall': '收尾模式没发', 'idle-return-other': 'idleBoats 走了别的分支', 'boatTo-refused': 'boatTo 被拒', 'eff>maxEff': '目标折算价高于上限' };
  const lab = (k) => k.startsWith('maxBoats(') ? `在海上的船已到 maxBoats 上限 ${k.slice(9, -1)}` : (LBL[k.replace('+sentElsewhere', '')] || k) + (k.endsWith('+sentElsewhere') ? '（本拍别处发了船）' : '');
  const E = [`# ${mid} t>=1500 船的门槛（影子运行；只统计四周没有可打的邻居、也没有无主地的决策拍；归类按 Policy.idleBoats 第一段 → boatOut → searchWater 的先后）`];
  const tot = new Map();
  for (const r of boatRows) tot.set(r.reason, (tot.get(r.reason) || 0) + 1);
  E.push(`全队：${boatRows.length} 个决策拍：` + [...tot].sort((a, b2) => b2[1] - a[1]).map(([k, n]) => `${lab(k)} ${n}`).join('；'));
  for (const b of bots) {
    const rs = boatRows.filter((r) => r.bot === b);
    if (!rs.length) continue;
    const m = new Map();
    for (const r of rs) { const o = m.get(r.reason) || { n: 0, t0: r.t, t1: r.t }; o.n++; o.t1 = r.t; m.set(r.reason, o); }
    const cp = rs.map((r) => r.coastPx);
    E.push(`${b}: ${rs.length} 个决策拍（t=${rs[0].t}~${rs[rs.length - 1].t}；海岸格 ${Math.min(...cp)}~${Math.max(...cp)}）：` + [...m].sort((a, b2) => b2[1].n - a[1].n).map(([k, o]) => `${lab(k)} ${o.n}（t=${o.t0}~${o.t1}）`).join('；'));
    const hits = rs.filter((r) => r.x !== '');
    if (hits.length) {
      const byT = new Map();
      for (const r of hits) { const k = `(${r.x},${r.y}) ${r.neutral ? '无主地 ' + r.size + ' 格' : '敌人的岸'}`; const o = byT.get(k) || { n: 0, t0: r.t, t1: r.t, dMin: r.dist, dMax: r.dist, sent: 0 }; o.n++; o.t1 = r.t; o.dMin = Math.min(o.dMin, r.dist); o.dMax = Math.max(o.dMax, r.dist); if (r.reason.startsWith('SENT')) o.sent++; byT.set(k, o); }
      E.push('    找到的目标：' + [...byT].sort((a, b2) => b2[1].n - a[1].n).slice(0, 8).map(([k, o]) => `${k}，水路 ${o.dMin}${o.dMax !== o.dMin ? '~' + o.dMax : ''} 格，${o.n} 拍（t=${o.t0}~${o.t1}），发出 ${o.sent} 条`).join('；'));
    }
    for (const r of rs.filter((x) => x.reason.startsWith('SENT'))) E.push(`    t=${r.t} 发船 → (${r.x},${r.y}) ${r.neutral ? '无主地 ' + r.size + ' 格' : '敌人的岸'}，水路 ${r.dist} 格；余额 ${Math.round(r.bal)}，留底 ${r.floor}，上限 ${r.max} / 下限 ${r.min} → 带兵 ${r.amount}，船费 ${iV(32 * r.bal, 1024)}`);
    const lim = rs.filter((x) => x.reason === 'max<min').slice(0, 3);
    for (const r of lim) E.push(`    例 t=${r.t} 不到下限：目标 (${r.x},${r.y}) ${r.neutral ? '无主地 ' + r.size + ' 格' : '敌人的岸'}，余额 ${Math.round(r.bal)}，留底 ${r.floor}，上限 ${r.max} < 下限 ${r.min}`);
  }
  fs.writeFileSync(path.join(OUT, 'shadow_boat_gate.txt'), E.join('\n') + '\n');
}
fs.writeFileSync(path.join(OUT, 'shadow_coast.tsv'), 't\tbot\tterr\tcoastPx\tboatsAllowed\tleft\n' + coastRows.join('\n') + '\n');
for (const tr of traces) {
  const f = path.join(OUT, `shadow_trace_${tr.bot}_${tr.t0}_${tr.t1}.txt`);
  const sum = ['# 决策拍分类统计（区间内每个决策拍都计入，不受抽样间隔影响；可用兵 / 下限 取首选目标）：'];
  for (const [k, st] of tr.stats || []) sum.push(`#   ${k}: ${st.n} 拍（t=${st.t0}~${st.t1}）` + (Number.isFinite(st.availMin) ? `；可用兵 ${Math.round(st.availMin)}~${Math.round(st.availMax)}，一条指令下限(20%余额) ${Math.round(st.chunkMin)}~${Math.round(st.chunkMax)}，比值 ${(100 * st.ratioMin).toFixed(0)}%~${(100 * st.ratioMax).toFixed(0)}%` : ''));
  for (const [k, st] of tr.stats || []) if (st.fireN) sum.push(`#   └ 「${k}」里：${st.fireN} 条对人/bot 的出兵共约 ${Math.round(st.fireTroops)} 兵；其中超过软上限（over=1）时发的 ${st.overN || 0} 条；目标每格成本 ≥ 自己的出价（c>=worth，只因 over 才放行）的 ${st.hiN || 0} 条约 ${Math.round(st.hiTroops || 0)} 兵` + (st.hiN ? `，c/worth = ${st.hiMin.toFixed(2)}~${st.hiMax.toFixed(2)}` : ''));
  fs.writeFileSync(f, `# ${mid} ${tr.bot} 影子决策明细 t=${tr.t0}~${tr.t1}（策略 ${SRC}；worth/safe/keep/avail 按 buyLand 源码公式重算）\n` + sum.join('\n') + '\n' + tr.lines.join('\n') + '\n');
  console.log(`# 轨迹 ${tr.bot} ${tr.t0}~${tr.t1}：` + [...(tr.stats || [])].map(([k, st]) => `${k} ${st.n}`).join('；'));
}
console.log(chk.join('\n'));
