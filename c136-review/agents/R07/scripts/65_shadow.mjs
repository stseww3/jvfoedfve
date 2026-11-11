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
//        [--bots a,b|all] [--trace bot:t0:t1[:every]]… [--ver va|vb|vc]
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

const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
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
      if (guard && target !== NEUTRAL) nfEvents.push([g.t, b, ok ? '改成1兵试探' : '挡掉', pname(g, target), Math.round(troops), sq, B0].join('\t'));
      return ok;
    };
  }
  pol.set(b, p);
}
const shadowCmds = [];
const coastRows = [];
const nfEvents = [];
const pname = (g, q) => (q === NEUTRAL ? '无主地' : q < H ? `${names[q]}#${q}[T${g.teams[q]}${g.state[q] === 2 ? '离' : ''}]` : `AI#${q}`);

// 按 buyLand 的源码公式重算每个报价的 安全底 / 留底 / 可用兵（Vb：L5350-5446；Va/Vc 行号略有出入，公式相同）
function evalOffers(g, p) {
  const me = p.me, P = p.p;
  const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iV(12 * B, 1024), dMe = B / L;
  const dMedOther = typeof p.otherHumanMedDens === 'function' ? p.otherHumanMedDens(g) : null;
  const m = P.maxW * p.winRatio(g.t);
  const refDens = dMedOther !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMedOther) : dMe;
  const worth = m * refDens, over = P.surplus > 0 && B > 100 * L, cheap = P.growth > 0 ? 0.1 / p.baseRate(g) : 0;
  const rows = [];
  for (const o of (p.__offers || []).slice(0, 6)) {
    const q = o.q;
    let safe = p.safeAt(g, q);
    if (!o.person || o.nearCollapse || (P.bleedSafeCap > 0 && (o.bleeding || o.tD < 0.45))) safe = Math.min(safe, P.oppFloorCap * L);
    let keep = Infinity;
    if (o.c < cheap) keep = 0;
    if (o.c < worth) {
      const worthOwn = P.ownWorthMinKeep > 0 && g.t >= P.ownWorthFrom && !o.nearCollapse ? m * dMe : worth;
      const budget = Math.max(0, (worthOwn * L - fee * m - o.c * L) / (1 + m));
      const minKeep = o.person && (o.nearCollapse || (P.bleedDiscount < 1 && o.bleeding) || (P.thinDiscount < 1 && o.tD < P.thinMaxTD)) ? (0.70 * o.c * L) / m : (o.c * L) / m;
      keep = Math.min(keep, P.post > 0 ? Math.max(minKeep, B - fee - budget) : minKeep);
    }
    if (over) keep = Math.min(keep, (dMe >= 122 ? 0.82 : P.hold) * 100 * L);
    keep = Math.max(keep, safe);
    const avail = B - fee - keep;
    const verdict = o.c >= worth && o.c >= cheap && !over ? '价高' : avail <= 0 ? '无可用' : (!o.pulseMode && avail < P.chunk * B && avail < 1.25 * o.need) ? '不够一条' : '';
    rows.push({ o, q, safe, keep, avail, verdict });
  }
  return { B, L, fee, dMe, dMedOther, m, worth, over, cheap, rows };
}

function classify(ev, cmdsNow, hadOffers) {
  if (cmdsNow.some((c) => c.kind === 'attack' && c.target !== NEUTRAL)) return '出手打人/bot';
  if (cmdsNow.some((c) => c.kind === 'attack')) return '只打无主地';
  if (cmdsNow.some((c) => c.kind === 'donate')) return '捐兵';
  if (cmdsNow.length) return '其他指令';
  if (!hadOffers) return '没走到 buyLand';
  if (!ev.rows.length) return '没有可打的邻居';
  const v = ev.rows[0].verdict;
  return v === '价高' ? '首选目标价高（c>=worth）' : v === '无可用' ? '首选目标无可用兵（avail<=0）' : v === '不够一条' ? '首选目标可用兵不够一条指令（avail<chunk*B）' : '有可用兵但没发（脉冲下限/冷却/其他）';
}

function traceLine(g, b, p, tr, cmdsNow, ev) {
  const me = p.me, P = p.p;
  const { B, L, dMe, dMedOther, m, worth, over, cheap } = ev;
  const out = [];
  out.push(`t=${g.t} ${b} B=${B} L=${L} d=${dMe.toFixed(1)} nb=${p.nb.length} neut=${p.neutral} cmds=${p.cmds} noFull=${p.isNoFullSend ? 1 : 0} shQ=${Math.round(p.shadowQuota ?? 0)} | m=${m.toFixed(3)} worth=${worth.toFixed(1)} cheap=${cheap.toFixed(1)} over=${over ? 1 : 0} dMedOther=${dMedOther === null ? '-' : dMedOther.toFixed(1)} safe(-1)=${Math.round(p.safeAt(g, -1))}`);
  for (const r of ev.rows) {
    const o = r.o, q = r.q;
    out.push(`    → ${pname(g, q)} terr=${g.terr[q]} bal=${g.bal[q]} dq=${(g.bal[q] / Math.max(1, g.terr[q])).toFixed(1)} cnt=${p.cnt[q]} | c=${o.c.toFixed(1)} rankC=${(o.rankC ?? o.c).toFixed(1)} need=${Math.round(o.need)} tD=${(o.tD ?? 0).toFixed(2)} ${o.person ? '人' : '机'}${o.pulseMode ? ' pulse' : ''}${o.nearCollapse ? ' nearCollapse' : ''}${o.bleeding ? ' bleeding' : ''}${o.onMe ? ' onMe' : ''}${o.isCrowdedHard ? ' crowdedHard' : ''}${o.isAgg ? ' agg' : ''} | safe=${Math.round(r.safe)} keep=${Number.isFinite(r.keep) ? Math.round(r.keep) : 'Inf'} avail=${Number.isFinite(r.avail) ? Math.round(r.avail) : '-Inf'} chunkB=${Math.round(P.chunk * B)} pulseB=${Math.round(P.pulseFrac * B)} ${r.verdict === '价高' ? '价高(c>=worth)→break' : r.verdict === '无可用' ? '无可用(avail<=0)' : r.verdict}`);
  }
  if (!ev.rows.length) out.push('    （offers 为空：没有可打的邻居）');
  for (const c of cmdsNow) out.push(`    ⇒ 影子指令 ${c.kind} pct=${c.pct} → ${c.targetName}（约 ${c.troops} 兵）`);
  if (!cmdsNow.length) out.push('    ⇒ 本拍没有指令');
  tr.lines.push(...out);
}

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
    const nf0 = p.isNoFullSend, pc0 = p.pendingQuotaCheck ? { ...p.pendingQuotaCheck } : null;
    try { p.act(g); } catch (e) { shadowLog.push({ bot: b, t: g.t, text: `[SHADOW-ERROR] ${e && e.message}` }); }
    if (nf0 === false && p.isNoFullSend) {
      const B = g.bal[me];
      nfEvents.push([g.t, b, '锁上isNoFullSend', pc0 ? `待核对出兵:发令拍=${pc0.t - 1} 想发=${Math.round(pc0.want)} 发令时余额=${pc0.bal0} 手续费=${pc0.fee} 本拍余额=${B} 推算实发=${Math.max(0, pc0.bal0 - B - pc0.fee)}` : '无待核对记录', '', '', B].join('\t'));
    }
    delete g.attack; delete g.donate; delete g.boat; delete g.boatTo; delete g.chase; delete g.recall; delete g.retreat;
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
      tr.stats.set(cls, st);
      if (tr.every && g.t % tr.every !== 0 && !cmdsNow.length) continue;
      if (p.__offers === null && !cmdsNow.length && g.t >= P.coreFrom) { tr.lines.push(`t=${g.t} ${b}（本拍没走到 buyLand）B=${g.bal[me]} L=${g.terr[me]} cmds=${p.cmds}`); continue; }
      traceLine(g, b, p, tr, cmdsNow, ev);
    }
  }
  if (onlineHad) g.online = online0; else delete g.online;
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
    if (s.nb === r.nb && s.neut === r.neut && s.cmds === r.cmds) same++;
  }
  chk.push(`# HL-TICK 比对：真日志 ${n} 条；影子同拍 领土余额一致 ${stateSame}，nb 一致 ${nbSame}，neut 一致 ${neutSame}，cmds 计数一致 ${cmdSame}，三项全一致 ${same}`);
  for (const [b, pb] of perBot) {
    const last = pb.dCmds.length ? pb.dCmds[pb.dCmds.length - 1] : 0;
    chk.push(`#   ${b}: ${pb.n} 条，影子缺 ${pb.miss}，nb 一致 ${pb.nb}，neut 一致 ${pb.neut}，cmds 一致 ${pb.cmds}；最后一条 cmds 差（影子-真）${last}`);
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
fs.writeFileSync(path.join(OUT, 'shadow_check.txt'), chk.join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'shadow_log.txt'), shadowLog.map((l) => `${l.t}\t[${l.bot}] ${l.text}`).join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'shadow_cmds.tsv'), 't\tbot\tkind\tpct\ttarget\ttargetName\tbal\tterr\ttroops\n' + shadowCmds.map((c) => [c.t, c.bot, c.kind, c.pct, c.target, c.targetName, c.bal, c.terr, c.troops].join('\t')).join('\n') + '\n');
fs.writeFileSync(path.join(OUT, 'shadow_nofull.tsv'), 't\tbot\tevent\tdetail_or_target\twantTroops\tshadowQuota\tbal\n' + nfEvents.join('\n') + '\n');
{
  const per = new Map();
  for (const r of nfEvents) { const [t, b, ev] = r.split('\t'); const o = per.get(b) || { lock: null, block: 0, poke: 0, firstBlock: null, lastBlock: null }; per.set(b, o); if (ev.startsWith('锁上')) { if (o.lock === null) o.lock = +t; } else { if (ev === '挡掉') o.block++; else o.poke++; if (o.firstBlock === null) o.firstBlock = +t; o.lastBlock = +t; } }
  const line = [...per].map(([b, o]) => `${b}: 锁上@${o.lock ?? '-'} 之后被挡 ${o.block} 次、改 1 兵试探 ${o.poke} 次${o.firstBlock !== null ? `（t=${o.firstBlock}~${o.lastBlock}）` : ''}`).join('；');
  console.log('# isNoFullSend（影子）：' + (line || '全程没有任何号被锁上'));
  fs.appendFileSync(path.join(OUT, 'shadow_check.txt'), '# isNoFullSend（影子）：' + (line || '全程没有任何号被锁上') + '\n');
}
fs.writeFileSync(path.join(OUT, 'shadow_coast.tsv'), 't\tbot\tterr\tcoastPx\tboatsAllowed\tleft\n' + coastRows.join('\n') + '\n');
for (const tr of traces) {
  const f = path.join(OUT, `shadow_trace_${tr.bot}_${tr.t0}_${tr.t1}.txt`);
  const sum = ['# 决策拍分类统计（区间内每个决策拍都计入，不受抽样间隔影响；可用兵 / 下限 取首选目标）：'];
  for (const [k, st] of tr.stats || []) sum.push(`#   ${k}: ${st.n} 拍（t=${st.t0}~${st.t1}）` + (Number.isFinite(st.availMin) ? `；可用兵 ${Math.round(st.availMin)}~${Math.round(st.availMax)}，一条指令下限(20%余额) ${Math.round(st.chunkMin)}~${Math.round(st.chunkMax)}，比值 ${(100 * st.ratioMin).toFixed(0)}%~${(100 * st.ratioMax).toFixed(0)}%` : ''));
  fs.writeFileSync(f, `# ${mid} ${tr.bot} 影子决策明细 t=${tr.t0}~${tr.t1}（策略 ${SRC}；worth/safe/keep/avail 按 buyLand 源码公式重算）\n` + sum.join('\n') + '\n' + tr.lines.join('\n') + '\n');
  console.log(`# 轨迹 ${tr.bot} ${tr.t0}~${tr.t1}：` + [...(tr.stats || [])].map(([k, st]) => `${k} ${st.n}`).join('；'));
}
console.log(chk.join('\n'));
