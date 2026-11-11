#!/usr/bin/env node
// shadow.mjs — 影子策略：在整局重演（resim_lib）的真实局面上，逐拍只读地运行部署版策略源码，
// 截获它在每个本地拍想下的每一条指令（陆攻 / 捐款 / 船）以及发出这条指令的代码行（调用栈）。
//
// 原理：联机是锁步的，客户端本地第 t 拍看到的局面 = 全局真值第 t 拍（日志 HL-TICK 与重演逐点相等已验证）。
//   自己发出的指令要等服务器回合包带回来才生效，所以本地局面里没有“已发未到”的指令。
//   因此把同一份策略代码放在真值局面上逐拍运行、指令只记录不执行，得到的就是客户端在本地各拍的真实决策序列。
// 校验（三重，全部机械对比）：
//   1) 影子在 t%90==0 的 nb / neut / cmds / boats 与日志 [HL-TICK] 相同；
//   2) 影子吐出的 [HL-OPENING] / [HL-DISPATCH] 行与日志逐行相同；
//   3) 录像里该号落地的指令（pct、目标）能在影子序列里按顺序找到 → 同时得到“决策拍 → 落地拍”的延迟。
//
// 用法：node shadow.mjs <matchId> [--replay other] [--log id1,id2] [--bots a,b|all] [--strategy va|vb|c110|c116|g09]
//                        [--to T] [--accept always|sim] [--per-tick 1] [--quit 1|0] [--probe bot:t0:t1] [--tag x] [--nocut] [--pin-no-full] [--quiet]
//   --pc-shift auto（默认）| 0 | 1：Policy.send 记下的 pendingQuotaCheck（isNoFullSend 的核对记录）从哪一拍开始核对。
//       0    = 代码原样：发令拍 +1 到 +7。
//       1    = 一律晚 1 拍：发令拍 +2 到 +7（--pc-end shift 则到 +8）。
//       auto = 代码原样，但“本拍受理了一条、同一拍策略又下了第二条被适配层拒掉”时，这条记录晚 1 拍才开始核对。
//       四局的对照（都是机械对比，命令见 notes/PROGRESS.md）：
//         A055：0 → 539/539 个 HL-TICK 点全同；1 → kaito9（900 拍起）、riku_x（1260 拍起）、alex_k（4140 拍起）的 cmds 各少 1；auto → 539/539。
//               例：kaito9 875 拍发令，876 拍余额因更早一条指令落地而下降 → 876 拍额度清零，到 880 拍回到 727，下一条（门槛 697）放行；
//               若 877 拍才清零，880 拍只有 547，下一条被拦，和日志（cmds=25）、录像（896 拍落地 pct=73）都对不上。
//         A057：0 → HL-TICK 全同，但 riku_x 最后 4 条对 [ua] 的指令影子是 pct=0、录像是 pct=122（11905、11910 拍发令后 +1 拍余额正被 [ua] 打掉，
//               原样会把 isNoFullSend 置真）；1 和 auto → 53/53 条全部配上。这两次发令都是“同拍第二条被拒”的情形。
//         A059、A094：三种口径的 HL-TICK 点全同（290/290、86/86）；置真拍号最多差 1 拍。
//       所以默认用 auto：它是唯一一种四局都对得上的口径。线上外壳为什么在这种情形下少核对 1 拍，镜像里没有外壳源码，查不到（记为 unknown）。
//   --pc-end keep（默认）：核对窗口的终点不后移，仍是“发令拍 + 7”（A094 noah88 560 拍发令、余额 568 拍才掉：窗口若延到 568 拍，570 拍的下一条被拦，对不上日志）。
//   --pc-trace：把每条待检记录的去向（pcEval 被核对 / pcDrop 超时作废 / pcOver 被下一条覆盖）记进 shadow_flags.csv
//   --act-every N：对照用，假设外壳每 N 拍才调一次 act（N=5 时 A057 有 4 个号的 cmds 对不上日志，已排除）
//   --per-tick N：每拍最多受理几条指令（默认 1；N=5 时 A057 有 4 个号的 cmds 对不上日志，已排除）
//   --quit 1（默认）：录像里出现离场指令的人类席位进 window.__quitPlayers（线上外壳也维护这张表；A057 关掉它就在 4005 拍起对不上日志）
//   默认每个号只跑到它日志最后一行的拍号 + 89（之后真实客户端没有再算过）；--nocut 取消这个截断。
//   --pin-no-full：反事实对照——每拍把 isNoFullSend 钉成假（局面仍是录像真值，只看同一局面下决策差多少），配 --tag 另存。
//   --accept always（默认）：实机适配层的受理口径 = 能行动就受理、每拍最多 1 条（A059 zexos1 的 cmds 计数 26/26 点相同；
//                    换成模拟器 Game.attack 的前置条件则少 1 条）。
// 输出（out/<matchId>/）：
//   shadow_cmds.csv   每条影子指令：t,bot,p,kind,pct,target,targetName,ok,bal,terr,dens,tBal,tTerr,troops,arg,landedAt,site,path,
//                     c,worth,over,need,onMe,person（进攻令在 buyLand 报价表里的单价、当拍愿付价、余额是否过 100 倍领土、need、对方是否正在打我、是否真人）
//   shadow_check.csv  与 HL-TICK 的逐点对比：t,bot,logNb,shNb,logNeut,shNeut,logCmds,shCmds,logBoats,shBoats,ok
//   shadow_log.txt    影子吐出的日志行（与 in_game.log 的同类行对比用）
//   shadow_match.csv  录像落地指令 ↔ 影子决策：tick,bot,p,kind,pct,target,targetName,n(同拍条数),uniq(0 未定位/1 唯一/2 同组连续/3 唯一窗口),
//                     tDecide,lag,balDecide,troopsDecide(决策时想出的兵),balExec(执行前余额),applied,spent(实际扣掉的兵+手续费),shTarget,path
//   shadow_chunks.csv 成块补帧：每个（号, 落地拍）一行：n 条、决策拍区间 t0–t1、延迟区间、是否是连续的决策
//   shadow_probe.txt  --probe 指定区间内 offers / safeAt / pickTarget 等中间量
//   shadow_idle.csv   闲置审计：每个号每 100 拍里各类决策拍的个数（cmd / boxed / dp / floor / floorN / other；other 再分 oPrice/oGate/oEmpty/oNoCall，
//                     priceC/priceWorth/priceDq = 卡在价格线的那些拍里 最便宜目标的单价 / 愿付价 / 该目标密度 的均值，priceOnMe = 其中正被人打的拍数）、顶在 150 倍上限的拍数、身边机器人地的面积与密度
//   shadow_flags.csv  策略内部闸门：isNoFullSend 何时被置真（连同当时那条待检记录）、Policy.send 没走到 g.attack 就返回 false 的每一次
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { openMatch, readLogSnaps, NEUTRAL, P_INNER, T_LAND } from './resim_lib.mjs';
import { P_BORDER } from '/agent/repos/c136-data/src/sim/sim/index.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT_ROOT = path.resolve(HERE, '../out');
const STRAT_DIR = '/agent/repos/c136-data/src/strategy';
const SIM_DIR = '/agent/repos/c136-data/src/sim/sim';
const BUNDLES = '/agent/repos/c136-data/bundles';

const STRAT_FILES = { va: 'v27-team-c116-va.js', vb: 'v27-team-c116-vb.js', c116: 'v27-team-c116.js', c110: 'v27-team-c110.js', g09: 'v27-team-g09.js' };
const VA = new Set(['A003', 'A005', 'A009']);
export function strategyKeyFor(mid) {
  if (mid.startsWith('B')) return 'c110';
  return VA.has(mid) ? 'va' : 'vb';
}

// 策略源码只改两行 import 的路径（行数不变，行号与原文件一致），写到 out/_shadow/ 后动态加载。
export async function loadStrategy(key) {
  const file = STRAT_FILES[key];
  if (!file) throw new Error(`未知策略版本 ${key}`);
  let src = fs.readFileSync(path.join(STRAT_DIR, file), 'utf8');
  const a = '"../../sim/index.js"', b = '"../../sim/map.js"';
  if (!src.includes(a) || !src.includes(b)) throw new Error('策略文件的 import 行变了');
  src = src.replace(a, JSON.stringify(pathToFileURL(path.join(SIM_DIR, 'index.js')).href)).replace(b, JSON.stringify(pathToFileURL(path.join(SIM_DIR, 'map.js')).href));
  const dir = path.join(OUT_ROOT, '_shadow');
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, file.replace(/\.js$/, '.mjs'));
  if (!fs.existsSync(out) || fs.readFileSync(out, 'utf8') !== src) fs.writeFileSync(out, src);
  const mod = await import(pathToFileURL(out).href);
  return { mod, file, out };
}

// 不改局面的陆攻受理判断（照抄 sim Game.attack 的前置条件）。
export function wouldAttack(g, p, target) {
  if (!g.canAct(p) || p === target) return false;
  target = Math.min(target, NEUTRAL);
  if (target < NEUTRAL && g.alive[target] === 0) target = NEUTRAL;
  if (target < NEUTRAL && !g.isEnemy(p, target)) return false;
  const already = g.hasAttack(p, target);
  if (!already && !g.hasFreeSlot(p)) return false;
  const before = g.front[p].length;
  let add = 0;
  const B = g.border[p], d = g.dir4, px = g.px, own = g.own;
  for (let i = B.length - 1; i >= 0 && add === 0; i--) {
    const c0 = B[i];
    if (px[c0] !== P_BORDER) continue;
    for (let k = 3; k >= 0; k--) {
      const c = c0 + d[k];
      if (target === NEUTRAL ? px[c] === T_LAND : (px[c] >= P_INNER && own[c] === target)) { add = 1; break; }
    }
  }
  if (before === 0 && add === 0) return false;
  if (!already && add === 0) return false;
  return true;
}

function stackOf(fileTag) {
  const st = new Error().stack.split('\n').slice(2);
  const fr = [];
  for (const l of st) {
    const m = l.match(/at (?:async )?(?:new )?([\w.$<>]+)?.*?([\w.-]+\.mjs):(\d+):\d+/);
    if (!m || !m[2].startsWith(fileTag)) continue;
    fr.push(`${(m[1] || '?').replace(/^Object\./, '')}:${m[3]}`);
  }
  return fr;
}

export async function runShadow(mid, o = {}) {
  const replay = o.replay || mid;
  const logIds = o.log || [mid];
  const key = o.strategy || strategyKeyFor(mid);
  const { mod, file } = await loadStrategy(key);
  const fileTag = file.replace(/\.js$/, '');
  const m = openMatch(mid, { replay });
  const g = m.g, H = m.H, names = m.names;

  // 日志里的号：席位号、槽位、HL-TICK 行
  const bots = new Map(); // label -> {p, slot, ticks: Map(t -> {nb, neut, cmds, boats})}
  for (const id of logIds) {
    const pre = logIds.length > 1 ? id + ':' : '';
    const lp = `${BUNDLES}/${id}/in_game.log`;
    if (!fs.existsSync(lp)) continue;
    for (const line of fs.readFileSync(lp, 'utf8').split('\n')) {
      let x = line.match(/\[([^\]]+)\] \[HL-GAME-INIT\].*me=(\d+)/);
      if (x) { bots.set(pre + x[1], { p: +x[2], name: x[1], slot: null, ticks: new Map(), logLines: [] }); continue; }
      // 没有 [HL-GAME-INIT] 行的号（A094 的 ryan_m/zexos1/noah88）：席位号取自 [HL-SPAWN-BACKEND] me=
      x = line.match(/\[([^\]]+)\] \[HL-SPAWN-BACKEND\] me=(\d+)/);
      if (x && !bots.has(pre + x[1])) bots.set(pre + x[1], { p: +x[2], name: x[1], slot: null, ticks: new Map(), logLines: [] });
      x = line.match(/\[([^\]]+)\] \[(HL-[A-Z-]+)\] (.*)$/);
      if (!x) continue;
      const b = bots.get(pre + x[1]);
      if (!b) continue;
      { const tt = x[3].match(/^t=(\d+)/); if (tt) b.lastLogT = Math.max(b.lastLogT ?? 0, +tt[1]); }
      if (x[2] === 'HL-SPAWN-BACKEND') { const s = x[3].match(/slot=(\d+)/); if (s) b.slot = +s[1]; }
      else if (x[2] === 'HL-TICK') {
        const s = x[3].match(/t=(\d+) .*nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)/);
        if (s) b.ticks.set(+s[1], { nb: +s[2], neut: +s[3], cmds: +s[4], boats: +s[5] });
      } else if (x[2] === 'HL-OPENING' || x[2] === 'HL-DISPATCH') b.logLines.push(`[${x[2]}] ${x[3].trim()}`);
    }
  }
  let want = o.bots && o.bots !== 'all' ? new Set(o.bots.split(',')) : null;
  const sh = [];
  const quit = new Set();
  const cmds = [], slog = [], probeOut = [];
  const probe = o.probe ? (() => { const [b, t0, t1] = o.probe.split(':'); return { bot: b, t0: +t0, t1: +t1 }; })() : null;
  for (const [label, b] of bots) {
    if (want && !want.has(label) && !want.has(b.name)) continue;
    const p = b.p;
    const pol = new mod.Policy({}, p);
    const win = { __hlLog: (s) => slog.push({ t: g.t, bot: label, s }), __quitPlayers: o.quit ? quit : undefined };
    if (b.slot !== null) win.__tsbSquadSlot = b.slot;
    const gv = Object.create(g);
    gv.online = true;
    gv.me = p;
    gv.names = names;
    const st = { label, p, pol, win, gv, lastCmdTick: -1, nThisTick: 0, b, nCalls: 0, flags: [] };
    // Policy.send 返回 false 且没有走到 g.attack：被策略自己的闸门（isNoFullSend 配额守卫等）拦下。
    if (typeof pol.send === 'function') {
      const origSend = pol.send.bind(pol);
      pol.send = (gg, target, troops, hint) => {
        const n0 = st.nCalls;
        const r = hint === undefined ? origSend(gg, target, troops) : origSend(gg, target, troops, hint);
        if (!r && st.nCalls === n0) st.flags.push({ t: g.t, bot: label, ev: 'sendHeld', target, troops: Math.round(troops), bal: g.bal[p], noFull: pol.isNoFullSend ? 1 : 0, shadowQuota: Math.round(pol.shadowQuota ?? -1), note: '' });
        return r;
      };
    }
    // 记下本拍 offers() 的结果，供闲置审计判断 buyLand 停在哪一道闸门。
    if (typeof pol.offers === 'function') {
      const origOffers = pol.offers.bind(pol);
      pol.offers = (gg) => { const r = origOffers(gg); st.lastOffers = { t: g.t, list: r }; return r; };
    }
    const perTick = o.perTick ?? 1;
    const rec = (kind, pct, target, ok, extra = {}) => {
      const fr = o.noStack ? [] : stackOf(fileTag);
      const bal = g.bal[p];
      // 这条进攻令在 buyLand 报价表里的单价 c、当拍的愿付价 worth、是否 over（余额 > 100 倍领土，buyLand 因此不做 c>=worth 的熔断）
      let offer = {};
      if (kind === 'attack' && target >= 0 && target < NEUTRAL && st.lastOffers && st.lastOffers.t === g.t && typeof pol.winRatio === 'function' && pol.p && pol.p.maxW !== undefined) {
        const of = st.lastOffers.list.find((x) => x.q === target);
        if (of && typeof of.c === 'number') {
          const P = pol.p, L = Math.max(1, g.terr[p]), dMe = bal / L;
          const dMed = typeof pol.otherHumanMedDens === 'function' ? pol.otherHumanMedDens(gv) : null;
          const refDens = dMed !== null && dMed !== undefined && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe;
          offer = { oc: of.c.toFixed(2), oworth: (P.maxW * pol.winRatio(g.t) * refDens).toFixed(2), oover: P.surplus > 0 && bal > 100 * L ? 1 : 0, oneed: Math.round(of.need), oOnMe: of.onMe ? 1 : 0, operson: of.person ? 1 : 0 };
        }
      }
      cmds.push({
        t: g.t, bot: label, p, kind, pct, target, ok: ok ? 1 : 0, bal, terr: g.terr[p],
        tBal: target >= 0 && target < NEUTRAL ? g.bal[target] : 0, tTerr: target >= 0 && target < NEUTRAL ? g.terr[target] : 0,
        troops: kind === 'attack' || kind === 'donate' ? Math.floor((bal * (pct + 1)) / 1024) : 0,
        site: fr[0] || '', path: fr.slice(0, 6).join('<'), ...offer, ...extra,
      });
    };
    const gate = () => {
      if (st.lastCmdTick !== g.t) { st.lastCmdTick = g.t; st.nThisTick = 0; }
      if (st.nThisTick >= perTick) return false;
      return true;
    };
    gv.attack = function (pct, target, pl = p) {
      st.nCalls++;
      let ok = gate();
      if (ok && (o.accept || 'always') === 'sim') ok = wouldAttack(g, pl, target);
      else if (ok) ok = g.canAct(pl);
      if (ok) st.nThisTick++;
      rec('attack', pct, target, ok);
      return ok;
    };
    gv.donate = function (pct, q, pl = p) {
      let ok = gate() && g.canAct(pl) && q !== pl && q < NEUTRAL && g.alive[q] !== 0 && g.isTeammate(pl, q);
      if (ok) st.nThisTick++;
      rec('donate', pct, q, ok);
      return ok;
    };
    gv.boat = function (pct, water, dir, pl = p) {
      const ok = gate() && g.canAct(pl) && g.boatsAllowed(pl);
      if (ok) st.nThisTick++;
      rec('boat', pct, -1, ok, { arg: `${water}:${dir}` });
      return ok;
    };
    gv.boatTo = function (pct, target, pl = p, radius = 32) {
      const ok = gate() && g.canAct(pl) && g.boatsAllowed(pl);
      if (ok) st.nThisTick++;
      rec('boatTo', pct, -1, ok, { arg: `${target}:${radius}` });
      return ok;
    };
    gv.retreat = function (target, pl = p) { const ok = g.canAct(pl) && g.hasAttack(pl, Math.min(target, NEUTRAL)); rec('retreat', 0, target, ok); return ok; };
    gv.recall = function (id, pl = p) { rec('recall', 0, -1, true, { arg: String(id) }); return true; };
    gv.chase = function (pct, id, pl = p) { rec('chase', pct, -1, true, { arg: String(id) }); return true; };
    if (probe && (probe.bot === label || probe.bot === b.name)) {
      const wrap = (name, fmt) => {
        if (typeof pol[name] !== 'function') return;
        const orig = pol[name].bind(pol);
        pol[name] = (...a) => {
          const r = orig(...a);
          if (g.t >= probe.t0 && g.t <= probe.t1) probeOut.push(`t=${g.t} ${name}(${a.slice(1).map((v) => (typeof v === 'function' ? 'fn' : JSON.stringify(v))).join(',')}) -> ${fmt ? fmt(r) : JSON.stringify(r)}`);
          return r;
        };
      };
      const num = (v) => (typeof v === 'number' ? (Number.isInteger(v) ? v : +v.toFixed(2)) : v);
      wrap('offers', (r) => JSON.stringify((r || []).map((x) => Object.fromEntries(Object.entries(x).filter(([, v]) => typeof v !== 'object' || v === null).map(([k, v]) => [k, num(v)])))));
      wrap('safeAt', (r) => String(num(r)));
      wrap('winRatio', (r) => String(num(r)));
      wrap('otherHumanMedDens', (r) => String(num(r)));
      wrap('pickTarget', (r) => JSON.stringify(r && { q: r.q, amount: num(r.amount) }));
      wrap('peopleSafe', (r) => String(num(r)));
      wrap('baseRate', (r) => String(num(r)));
      for (const nm of ['allow', 'expandNeutral', 'dpNeutral', 'tryDonateToTeammate', 'idleBoats', 'boatOut', 'boatFood', 'frontBoat', 'buyLand', 'counterAttack', 'searchWater', 'searchFood', 'isMopUp', 'winFloor', 'peopleFloor', 'botMax']) wrap(nm, (r) => JSON.stringify(typeof r === 'number' ? num(r) : r));
      st.probeState = () => {
        if (!(g.t >= probe.t0 && g.t <= probe.t1)) return;
        const d = (q) => (g.terr[q] > 0 ? (g.bal[q] / g.terr[q]).toFixed(1) : '0');
        const nm = (q) => (q >= NEUTRAL ? 'NEUTRAL' : q < m.H ? `${m.names[q]}#${q}` : `AI#${q}`);
        const nb = (pol.nb || []).map((q) => `${nm(q)}[T${g.teams ? g.teams[q] : '-'} 地${g.terr[q]} 密${d(q)} ${g.isBot(q) ? '机' : '人'}]`).join(' ');
        // safeFinite 的来源：每个机器人邻居 q 的“其他邻居”里余额最小的是谁（threatOf L417 的 minOther）
        if (g.t < 1500 && g.t % 5 === 0) {
          for (const q of pol.nb || []) {
            if (!g.alive[q] || !g.isBot(q) || !g.terr[q]) continue;
            const others = [...m.neighbours(q).players.keys()].filter((o2) => o2 !== p && o2 !== q && g.alive[o2]);
            const lst = others.map((o2) => [g.bal[o2] + g.attackTroopsOn(o2, q), o2]).sort((x, y) => x[0] - y[0]).slice(0, 3);
            probeOut.push(`t=${g.t}   机器人邻居 ${nm(q)}（地${g.terr[q]} 兵${g.bal[q]} 空槽${g.hasFreeSlot(q) ? 1 : 0} 正打我${g.hasAttack(q, p) ? 1 : 0}）的其他邻居按余额从小到大：${lst.map(([v, o2]) => `${nm(o2)}[T${g.teams ? g.teams[o2] : '-'}${g.state[o2] === 2 ? ' 壳' : ''}${g.hasAttack(q, o2) ? ' 正被它打' : ''}]=${v}`).join(' , ') || '（无）'}`);
          }
        }
        probeOut.push(`t=${g.t} 状态 bal=${g.bal[p]} terr=${g.terr[p]} dens=${d(p)} neutral=${pol.neutral} coast=${g.coast?.[p]?.length ?? 0} noFull=${pol.isNoFullSend ? 1 : 0} atkOut=${g.atkCount[p]} 船=${g.boatCount[p]}/${pol.p.maxBoats}（可出海 ${g.boatsAllowed(p) ? 1 : 0}，上次出海 ${pol.lastBoat ?? '-'}） 邻居: ${nb || '（无）'}`);
      };
    }
    sh.push(st);
  }
  if (!sh.length) throw new Error('没有可跑影子的号（日志里没有 HL-GAME-INIT）');

  const check = [];
  // 录像里每条陆攻 / 捐款执行前的余额与是否生效（按执行顺序记，matchReplay 用同样的顺序取）
  const exec = [];
  let pre = null;
  m.preCmd = (c) => { pre = (c.id === 1 || c.id === 2) ? { bal: g.bal[c.player], t: g.t } : null; };
  m.onCmd = (c, res) => {
    if ((c.id === 8 || c.id === 9) && c.player < H) quit.add(c.player);
    if (pre && !g.spawnPhase) exec.push({ player: c.player, id: c.id, dX: c.dX, dZ: c.dZ, t: pre.t, bal: pre.bal, ok: res ? 1 : 0, spent: pre.bal - g.bal[c.player] });
  };
  const TO = o.to ?? 1e9;
  const saveWin = globalThis.window;
  let errN = 0;
  // 闲置审计：每个决策拍（t % period == 0）记一次这个号的处境，按 100 拍汇总。
  //   cmd   这一拍发了指令（受理与否都算）
  //   boxed 没有可打的邻居也没有中立地（nb=0 且 neutral=0）
  //   dp    1500 拍前身边还有中立地、这一拍没发令，且不属于 floor/floorN（开局按租期出手，间隔是设计内的）
  //   floorN 同 floor，但身边还剩中立地（开局期的 floorN 多半是 dpKeep 在按计划留兵；中立吃完之后剩 1–4 格的 floorN 与 floor 是一回事）
  //   floor 1500 拍前、中立地已经没有：身边有机器人/离场壳的地，但 pickTarget 的保底线 winFloor（L4562，取 safeFinite=邻居机器人的其他邻居里最小的余额）不低于自己的余额
  //   other 其余（有人类邻居但没出手等）。other 再按 buyLand 的走向细分（只对有 offers() 的版本）：
  //     oPrice  offers() 排第一的目标单价 c >= 愿付价 worth 且 c >= cheap 且余额没过 100 倍领土 → buyLand L5358 的 break（一个都不买）
  //             worth = maxW * winRatio(t) * max(自己密度, marketFloor * 其他人类密度中位数)；c = (打死对方要的兵 + 手续费) / 能拿到的地
  //     oGate   排第一的目标过了价格线，但被后面的闸门拦下（sole buffer / crowded hard / 保底 keep 等）
  //     oEmpty  offers() 是空的（没有可打的邻居或没有空攻击槽）
  //     oNoCall 这一拍没走到 offers()
  //   cap   余额顶在 150 倍领土（利息为 0）
  const idleAgg = new Map();
  const idleAudit = (s, nCmd) => {
    const pol = s.pol, p = s.p, per = pol.p?.period || 5;
    if (g.t % per !== 0) return;
    const B = g.bal[p], L = g.terr[p];
    if (!L) return;
    const nbs = pol.nb || [];
    let ai = 0, aiLand = 0, aiBal = 0, foe = 0, wf = Infinity;
    for (const q of nbs) {
      if (!g.alive[q] || !g.terr[q]) continue;
      if (g.isBot(q)) { ai++; aiLand += g.terr[q]; aiBal += g.bal[q]; if (g.t < 1500 && typeof pol.winFloor === 'function') wf = Math.min(wf, pol.winFloor(s.gv, q)); }
      else foe++;
    }
    // winFloor = max(机器人地的回本线, dpKeep, safeFinite)：记下卡住时是哪一项最大
    let by = '';
    if (wf !== Infinity && wf >= B && nCmd === 0) {
      const keep = typeof pol.dpKeep === 'function' ? pol.dpKeep(s.gv) : 0, safe = pol.sb ?? 0;
      by = safe >= wf - 0.5 ? 'safe' : keep >= wf - 0.5 ? 'keep' : 'px';
    }
    let cls;
    if (nCmd > 0) cls = 'cmd';
    else if (!nbs.length && !pol.neutral) cls = 'boxed';
    else if (wf !== Infinity && wf >= B) cls = pol.neutral > 0 ? 'floorN' : 'floor';
    else if (g.t < 1500 && pol.neutral > 0) cls = 'dp';
    else cls = 'other';
    const k = `${s.label}|${Math.floor(g.t / 100) * 100}`;
    let a = idleAgg.get(k);
    if (!a) idleAgg.set(k, (a = { bot: s.label, t0: Math.floor(g.t / 100) * 100, acts: 0, cmd: 0, boxed: 0, dp: 0, floor: 0, floorN: 0, other: 0, cap: 0, bal: 0, terr: 0, wf: 0, nwf: 0, ai: 0, aiLand: 0, aiBal: 0, foe: 0, by_safe: 0, by_keep: 0, by_px: 0,
      oPrice: 0, oGate: 0, oEmpty: 0, oNoCall: 0, pC: 0, pWorth: 0, pOnMe: 0, pInAtk: 0, pDq: 0 }));
    a.acts++; a[cls]++; a.bal += B; a.terr += L; a.ai += ai; a.aiLand += aiLand; a.aiBal += aiBal; a.foe += foe;
    if (cls === 'other') {
      const lo = s.lastOffers && s.lastOffers.t === g.t ? s.lastOffers.list : null;
      const P = pol.p || {};
      if (!lo) a.oNoCall++;
      else if (!lo.length) a.oEmpty++;
      else if (typeof pol.winRatio === 'function' && P.maxW !== undefined) {
        const dMe = B / Math.max(1, L);
        const dMed = typeof pol.otherHumanMedDens === 'function' ? pol.otherHumanMedDens(s.gv) : null;
        const refDens = dMed !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe;
        const worth = P.maxW * pol.winRatio(g.t) * refDens, over = P.surplus > 0 && B > 100 * L, cheap = P.growth > 0 ? 0.1 / pol.baseRate(s.gv) : 0;
        const o0 = lo[0];
        if (o0.c >= worth && o0.c >= cheap && !over) {
          a.oPrice++; a.pC += o0.c; a.pWorth += worth;
          const inAtk = lo.reduce((x, y) => x + (y.inAtk || 0), 0);
          if (inAtk > 0) { a.pOnMe++; a.pInAtk += inAtk; }
          a.pDq += g.bal[o0.q] / Math.max(1, g.terr[o0.q]);
        } else a.oGate++;
      } else a.oGate++;
    }
    if (B >= 150 * L - 150) a.cap++;
    if (wf !== Infinity) { a.wf += wf; a.nwf++; }
    if (by) a['by_' + by]++;
  };
  while (g.t < TO && m.tick()) {
    for (const s of sh) {
      const p = s.p;
      if (!g.alive[p] || g.state[p] === 2) continue;
      // 日志每 90 拍必有一行 HL-TICK：最后一行之后超过 89 拍，说明真实客户端没有算到这一拍（卡死或已断开），影子也停。
      if (!o.nocut && g.t > (s.b.lastLogT ?? 0) + 89) continue;
      if (o.actEvery > 1 && g.t % o.actEvery !== 0) continue; // 对照用：假设外壳不是每拍都调 act
      globalThis.window = s.win;
      if (o.pinNoFull) { s.pol.isNoFullSend = false; s.pol.pendingQuotaCheck = null; }
      // --pc-end keep：核对窗口的起点按 --pc-shift 后移，终点仍是“发令拍 + 7”（原代码的终点），即窗口 = [发令拍+1+shift, 发令拍+7]。
      if (o.pcEnd === 'keep' && s.pol.pendingQuotaCheck?._sh && g.t > s.pol.pendingQuotaCheck.t + 6 - s.pol.pendingQuotaCheck._sh) s.pol.pendingQuotaCheck = null;
      const nf0 = !!s.pol.isNoFullSend, pc0 = s.pol.pendingQuotaCheck ? { ...s.pol.pendingQuotaCheck } : null, bal0 = g.bal[p];
      const nCmd0 = cmds.length;
      try { s.pol.act(s.gv);
        // --pc-shift auto：只有“本拍受理了一条、同拍又有一条被适配层拒掉”时才把核对起点后移 1 拍（见文件头）。
        let shiftBy = o.pcShift;
        if (o.pcAuto) { let nOk = 0, nNo = 0; for (let k = nCmd0; k < cmds.length; k++) { if (cmds[k].ok) nOk++; else nNo++; } shiftBy = nOk > 0 && nNo > 0 ? 1 : 0; }
        if (shiftBy && s.pol.pendingQuotaCheck && s.pol.pendingQuotaCheck.t === g.t + 1 && !s.pol.pendingQuotaCheck._sh && !s.pol.pendingQuotaCheck._seen) { s.pol.pendingQuotaCheck.t += shiftBy; s.pol.pendingQuotaCheck._sh = shiftBy; }
        if (s.pol.pendingQuotaCheck) s.pol.pendingQuotaCheck._seen = 1;
        if (s.probeState) s.probeState(); idleAudit(s, cmds.length - nCmd0); } catch (e) { if (errN++ < 5) console.error(`影子出错 t=${g.t} ${s.label}: ${e.stack.split('\n').slice(0, 3).join(' | ')}`); }
      // 待检记录的去向（--pc-trace 才记，量大）：pcEval = 本拍被核对（置真或扣额度）；pcDrop = 超过 6 拍作废；pcOver = 没等到核对就被下一条指令的记录覆盖。
      if (o.pcTrace && pc0) {
        const pc1 = s.pol.pendingQuotaCheck;
        const due = g.t >= pc0.t, late = g.t > pc0.t + 6, low = bal0 < pc0.bal0 - pc0.fee;
        const sent = Math.max(0, pc0.bal0 - bal0 - pc0.fee);
        const ev = due && late ? 'pcDrop' : due && low ? 'pcEval' : (pc1 && pc1 !== pc0 && (pc1.bal0 !== pc0.bal0 || pc1.want !== pc0.want || pc1.t !== pc0.t)) ? 'pcOver' : null;
        if (ev) s.flags.push({ t: g.t, bot: s.label, ev, target: -1, troops: Math.round(pc0.want), bal: bal0, noFull: s.pol.isNoFullSend ? 1 : 0, shadowQuota: Math.round(s.pol.shadowQuota ?? -1),
          note: `发令拍=${pc0.t - 1 - (pc0._sh || 0)} 发令时余额=${pc0.bal0} 手续费=${pc0.fee} 想发=${Math.round(pc0.want)} 本拍余额=${bal0}` + (ev === 'pcEval' ? ` 算出实发=${sent} ${pc0.want >= 1.12 * sent && sent < pc0.bal0 - pc0.fee - 50 ? '判为被限额' : '判为正常'}` : '') });
      }
      if (!nf0 && s.pol.isNoFullSend) {
        s.flags.push({ t: g.t, bot: s.label, ev: 'isNoFullSend', target: -1, troops: pc0 ? Math.round(pc0.want) : 0, bal: bal0, noFull: 1, shadowQuota: Math.round(s.pol.shadowQuota ?? -1),
          note: pc0 ? `发令拍=${pc0.t - 1 - (pc0._sh || 0)} 发令时余额=${pc0.bal0} 手续费=${pc0.fee} 想发=${Math.round(pc0.want)} 检查时余额=${bal0} 算出实发=${Math.max(0, pc0.bal0 - bal0 - pc0.fee)}` : '无待检记录' });
      }
    }
  }
  globalThis.window = saveWin;
  // 校验 1：影子自己吐出的 [HL-TICK] 行（与实机同一行代码、同一时刻取值）对日志的 [HL-TICK] 行。
  const shTick = new Map();
  for (const l of slog) {
    const x = l.s.match(/\[HL-TICK\] t=(\d+) .*nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)/);
    if (x) shTick.set(l.bot + '|' + x[1], { nb: +x[2], neut: +x[3], cmds: +x[4], boats: +x[5] });
  }
  for (const s of sh) {
    for (const [t, lt] of s.b.ticks) {
      if (t > g.t) continue;
      const v = shTick.get(s.label + '|' + t);
      const r = { t, bot: s.label, logNb: lt.nb, shNb: v ? v.nb : '', logNeut: lt.neut, shNeut: v ? v.neut : '', logCmds: lt.cmds, shCmds: v ? v.cmds : '', logBoats: lt.boats, shBoats: v ? v.boats : '' };
      r.ok = v && r.logNb === r.shNb && r.logNeut === r.shNeut && r.logCmds === r.shCmds && r.logBoats === r.shBoats ? 1 : 0;
      check.push(r);
    }
  }
  check.sort((a, b) => a.t - b.t || (a.bot < b.bot ? -1 : 1));
  return { m, sh, cmds, slog, check, probeOut, bots, key, file, errN, exec, idleAgg };
}

// 录像里每条指令的拍号（与 resim_lib 的步进规则一致）。
export function replayCmds(m) {
  const d = m.d, H = m.H, jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  const rc = [];
  let iv = 0, iw = 0, ix = 0, stepN = 0;
  while (iv < d.ja.length) {
    const jZ = d.ja[iv];
    if (d.jY[iv]) { for (let a1 = iw; a1 < iw + jZ; a1++) rc.push({ tick: stepN - (jJ + 1), ...d.cmds[a1] }); iw += jZ; iv++; }
    else if (++ix >= jZ) { iv++; ix = 0; }
    stepN++;
  }
  return rc;
}

// 录像落地指令 ↔ 影子决策的对齐。
// 事实 1（由 A059 zexos1 的 574 / 623 / 861 拍验证）：同一拍里同一个号的多条指令，录像里是按“后发的在前”排的，这里先倒回发令顺序。
// 事实 2：目标在落地时已死，引擎把目标改记为无主地（512）；所以录像的 512 可以对上影子里任何一个玩家目标。
// 对齐：整条序列保持先后顺序，分别做“最早可行”和“最晚可行”两次贪心；两次给出同一个决策拍 → 唯一（uniq=1）。
export function matchReplay(m, sh, cmds, exec = null, maxLag = 1500) {
  const rc = replayCmds(m);
  if (exec) {
    // exec 与 rc 里 id=1/2 且 tick>=0 的指令同序；逐条挂上执行前余额、是否生效、实际扣兵
    const q = new Map();
    for (const e of exec) { const k = `${e.player}|${e.id}|${e.dX}|${e.dZ}|${e.t}`; if (!q.has(k)) q.set(k, []); q.get(k).push(e); }
    for (const c of rc) { if (c.id !== 1 && c.id !== 2) continue; const a = q.get(`${c.player}|${c.id}|${c.dX}|${c.dZ}|${c.tick}`); if (a && a.length) c.exec = a.shift(); }
  }
  const out = [];
  for (const s of sh) {
    const S = cmds.filter((c) => c.bot === s.label && c.ok && (c.kind === 'attack' || c.kind === 'donate'));
    S.forEach((c, i) => { c.seq = i; });
    const raw = rc.filter((c) => c.player === s.p && (c.id === 1 || c.id === 2) && c.tick >= 0);
    const R = [];
    for (let i = 0; i < raw.length;) { let j = i; while (j < raw.length && raw[j].tick === raw[i].tick) j++; for (let k = j - 1; k >= i; k--) R.push({ ...raw[k], n: j - i }); i = j; }
    const same = (r, c) => (r.id === 1 ? c.kind === 'attack' : c.kind === 'donate') && c.pct === r.dX && (c.target === r.dZ || (r.id === 1 && r.dZ === NEUTRAL && c.target < NEUTRAL)) && c.t <= r.tick && r.tick - c.t <= maxLag;
    let j = 0;
    const first = R.map((r) => { for (let k = j; k < S.length; k++) if (same(r, S[k])) { j = k + 1; return S[k]; } return null; });
    j = S.length - 1;
    const last = new Array(R.length).fill(null);
    for (let i = R.length - 1; i >= 0; i--) { for (let k = j; k >= 0; k--) if (same(R[i], S[k])) { j = k - 1; last[i] = S[k]; break; } }
    // 第三步：同一拍落地的一组里，只要有一条唯一，就试“整组是影子序列里连续的一段”：全部对得上 → 整组定位（uniq=2）。
    //         一条唯一都没有的组：在前后已定位的范围内找连续窗口，恰好只有一个窗口对得上 → 定位（uniq=3）。
    const fix = new Array(R.length).fill(null);
    for (let i = 0; i < R.length; i++) if (first[i] && last[i] && first[i].seq === last[i].seq) fix[i] = first[i];
    for (let i = 0; i < R.length;) {
      let j = i; while (j < R.length && R[j].tick === R[i].tick) j++;
      const n = j - i;
      if (n > 1) {
        let anchor = -1;
        for (let k = i; k < j; k++) if (fix[k]) { anchor = k; break; }
        const tryBase = (base) => { if (base < 0 || base + n > S.length) return false; for (let k = 0; k < n; k++) if (!same(R[i + k], S[base + k])) return false; return true; };
        if (anchor >= 0) {
          const base = fix[anchor].seq - (anchor - i);
          if (tryBase(base)) for (let k = 0; k < n; k++) if (!fix[i + k]) { fix[i + k] = S[base + k]; R[i + k].how = 2; }
        } else {
          let lo = 0, hi = S.length - n;
          for (let k = i - 1; k >= 0; k--) if (fix[k]) { lo = fix[k].seq + 1; break; }
          for (let k = j; k < R.length; k++) if (fix[k]) { hi = fix[k].seq - n; break; }
          const cands = [];
          for (let base = lo; base <= hi && cands.length < 2; base++) if (tryBase(base)) cands.push(base);
          if (cands.length === 1) for (let k = 0; k < n; k++) { fix[i + k] = S[cands[0] + k]; R[i + k].how = 3; }
        }
      }
      i = j;
    }
    R.forEach((r, i) => {
      const a = first[i], b = last[i], f = fix[i];
      out.push({
        tick: r.tick, bot: s.label, p: s.p, kind: r.id === 1 ? 'attack' : 'donate', pct: r.dX, target: r.dZ, n: r.n,
        tFirst: a ? a.t : '', tLast: f ? f.t : b ? b.t : '', uniq: f ? (r.how || 1) : 0, seq: f ? f.seq : '',
        lag: f ? r.tick - f.t : '', lagMin: b ? r.tick - b.t : '', lagMax: a ? r.tick - a.t : '',
        shTarget: f ? f.target : a ? a.target : '', path: (f || a || b || {}).path || '',
        balDecide: f ? f.bal : '', troopsDecide: f ? f.troops : '',
        balExec: r.exec ? r.exec.bal : '', applied: r.exec ? r.exec.ok : '', spent: r.exec ? r.exec.spent : '',
      });
    });
  }
  return out;
}

// 成块补帧：把唯一对上的落地指令按落地拍分组，每组给出 落地拍、决策拍区间、条数、是否为影子序列里连续的决策。
export function chunksOf(mt) {
  const by = new Map();
  for (const x of mt) {
    if (!x.uniq) continue;
    const k = x.bot + '|' + x.tick;
    if (!by.has(k)) by.set(k, []);
    by.get(k).push(x);
  }
  const out = [];
  for (const [k, a] of by) {
    const [bot, tick] = k.split('|');
    const ts = a.map((x) => x.tLast), seqs = a.map((x) => x.seq).sort((p, q) => p - q);
    out.push({ bot, tick: +tick, n: a.length, t0: Math.min(...ts), t1: Math.max(...ts), lag0: +tick - Math.max(...ts), lag1: +tick - Math.min(...ts), consec: seqs[seqs.length - 1] - seqs[0] === seqs.length - 1 ? 1 : 0, seq0: seqs[0], seq1: seqs[seqs.length - 1] });
  }
  return out.sort((a, b) => (a.bot < b.bot ? -1 : a.bot > b.bot ? 1 : a.tick - b.tick));
}

const IS_MAIN = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (IS_MAIN) {
  const argv = process.argv.slice(2);
  const mid = argv[0];
  const opt = (k, dflt) => (argv.includes(`--${k}`) ? argv[argv.indexOf(`--${k}`) + 1] : dflt);
  if (!mid) { console.error('用法：shadow.mjs <matchId> [--replay other] [--log ids] [--bots a,b] [--strategy va|vb|c110] [--to T] [--accept sim|always] [--per-tick N] [--quit 1] [--probe bot:t0:t1]'); process.exit(2); }
  const t0 = Date.now();
  const r = await runShadow(mid, {
    replay: opt('replay', mid), log: opt('log', mid).split(','), bots: opt('bots', 'all'), strategy: opt('strategy', null),
    nocut: argv.includes('--nocut'), pinNoFull: argv.includes('--pin-no-full'), to: opt('to', null) ? +opt('to') : undefined, accept: opt('accept', 'always'), perTick: +opt('per-tick', 1), actEvery: +opt('act-every', 1), pcShift: opt('pc-shift', 'auto') === 'auto' ? 0 : +opt('pc-shift', 0), pcAuto: opt('pc-shift', 'auto') === 'auto', pcTrace: argv.includes('--pc-trace'), pcEnd: opt('pc-end', 'keep'), quit: +opt('quit', 1), probe: opt('probe', null),
  });
  const { m, sh, cmds, slog, check, probeOut, idleAgg } = r;
  const dir = path.join(OUT_ROOT, mid);
  fs.mkdirSync(dir, { recursive: true });
  const q = (s) => `"${String(s).replace(/"/g, "'")}"`;
  const suffix = opt('tag', '') ? '_' + opt('tag', '') : '';
  const mt = matchReplay(m, sh, cmds, r.exec);
  const landedAt = new Map();
  for (const x of mt) if (x.uniq) landedAt.set(x.bot + '|' + x.seq, x.tick);
  fs.writeFileSync(path.join(dir, `shadow_cmds${suffix}.csv`), 't,bot,p,kind,pct,target,targetName,ok,bal,terr,dens,tBal,tTerr,troops,arg,landedAt,site,path,c,worth,over,need,onMe,person\n' +
    cmds.map((c) => [c.t, c.bot, c.p, c.kind, c.pct, c.target, q(c.target >= 0 ? m.label(c.target) : ''), c.ok, c.bal, c.terr, (c.bal / Math.max(1, c.terr)).toFixed(1), c.tBal, c.tTerr, c.troops, c.arg || '', c.seq !== undefined ? (landedAt.get(c.bot + '|' + c.seq) ?? '') : '', c.site, q(c.path), c.oc ?? '', c.oworth ?? '', c.oover ?? '', c.oneed ?? '', c.oOnMe ?? '', c.operson ?? ''].join(',')).join('\n') + '\n');
  fs.writeFileSync(path.join(dir, `shadow_check${suffix}.csv`), 't,bot,logNb,shNb,logNeut,shNeut,logCmds,shCmds,logBoats,shBoats,ok\n' +
    check.map((c) => [c.t, c.bot, c.logNb, c.shNb, c.logNeut, c.shNeut, c.logCmds, c.shCmds, c.logBoats, c.shBoats, c.ok].join(',')).join('\n') + '\n');
  fs.writeFileSync(path.join(dir, `shadow_log${suffix}.txt`), slog.map((l) => `[${l.bot}] ${l.s}`).join('\n') + '\n');
  fs.writeFileSync(path.join(dir, `shadow_match${suffix}.csv`), 'tick,bot,p,kind,pct,target,targetName,n,uniq,tDecide,lag,balDecide,troopsDecide,balExec,applied,spent,shTarget,path\n' +
    mt.map((x) => [x.tick, x.bot, x.p, x.kind, x.pct, x.target, q(m.label(x.target)), x.n, x.uniq, x.uniq ? x.tLast : '', x.lag, x.balDecide, x.troopsDecide, x.balExec, x.applied, x.spent, x.shTarget, q(x.path)].join(',')).join('\n') + '\n');
  const ch = chunksOf(mt);
  fs.writeFileSync(path.join(dir, `shadow_chunks${suffix}.csv`), 'bot,tick,n,t0,t1,lagMin,lagMax,consec,seq0,seq1\n' + ch.map((c) => [c.bot, c.tick, c.n, c.t0, c.t1, c.lag0, c.lag1, c.consec, c.seq0, c.seq1].join(',')).join('\n') + '\n');
  if (probeOut.length) fs.writeFileSync(path.join(dir, `shadow_probe${suffix}.txt`), probeOut.join('\n') + '\n');
  {
    const rows = ['bot,t0,acts,cmd,boxed,dp,floor,floorN,other,cap,bal,terr,dens,floorAvg,aiNb,aiLand,aiDens,foeNb,bySafe,byKeep,byPx,oPrice,oGate,oEmpty,oNoCall,priceC,priceWorth,priceDq,priceOnMe,priceInAtk'];
    for (const a of [...idleAgg.values()].sort((x, y) => (x.bot < y.bot ? -1 : x.bot > y.bot ? 1 : x.t0 - y.t0))) {
      const n = a.acts;
      rows.push([a.bot, a.t0, n, a.cmd, a.boxed, a.dp, a.floor, a.floorN, a.other, a.cap, Math.round(a.bal / n), Math.round(a.terr / n), (a.bal / Math.max(1, a.terr)).toFixed(1), a.nwf ? Math.round(a.wf / a.nwf) : '', (a.ai / n).toFixed(1), Math.round(a.aiLand / n), a.aiLand ? (a.aiBal / a.aiLand).toFixed(1) : '', (a.foe / n).toFixed(1), a.by_safe, a.by_keep, a.by_px,
        a.oPrice, a.oGate, a.oEmpty, a.oNoCall, a.oPrice ? (a.pC / a.oPrice).toFixed(1) : '', a.oPrice ? (a.pWorth / a.oPrice).toFixed(1) : '', a.oPrice ? (a.pDq / a.oPrice).toFixed(1) : '', a.pOnMe, a.pOnMe ? Math.round(a.pInAtk / a.pOnMe) : ''].join(','));
    }
    fs.writeFileSync(path.join(dir, `shadow_idle${suffix}.csv`), rows.join('\n') + '\n');
  }
  const flags = sh.flatMap((x) => x.flags).sort((a, b) => a.t - b.t);
  fs.writeFileSync(path.join(dir, `shadow_flags${suffix}.csv`), 't,bot,ev,target,targetName,troops,bal,noFull,shadowQuota,note\n' +
    flags.map((f) => [f.t, f.bot, f.ev, f.target, f.target >= 0 ? JSON.stringify(m.names[f.target] ?? (f.target === 512 ? 'NEUTRAL' : '')) : '', f.troops, f.bal, f.noFull, f.shadowQuota, JSON.stringify(f.note)].join(',')).join('\n') + '\n');
  for (const x of sh) {
    const nf = x.flags.find((f) => f.ev === 'isNoFullSend');
    const held = x.flags.filter((f) => f.ev === 'sendHeld');
    if (nf || held.length) console.log(`  [闸门] ${x.label}: isNoFullSend ${nf ? '在 t=' + nf.t + ' 置真（' + nf.note + '）' : '全程为假'}；Policy.send 被自己的闸门拦下 ${held.length} 次${held.length ? '（t=' + held[0].t + '–' + held[held.length - 1].t + '，其中 isNoFullSend 为真 ' + held.filter((f) => f.noFull).length + ' 次）' : ''}`);
  }

  // 摘要
  console.log(`# ${mid} 影子策略 ${r.file}：${sh.length} 个号，到第 ${m.g.t} 拍，用时 ${((Date.now() - t0) / 1000).toFixed(1)} 秒，出错 ${r.errN} 次`);
  for (const s of sh) {
    const ck = check.filter((c) => c.bot === s.label);
    const okAll = ck.filter((c) => c.ok).length;
    const f = (k1, k2) => ck.filter((c) => c[k1] === c[k2]).length;
    const firstBad = ck.find((c) => !c.ok);
    const mine = cmds.filter((c) => c.bot === s.label);
    const mm = mt.filter((x) => x.bot === s.label);
    const lags = mm.filter((x) => x.uniq).map((x) => x.lag).sort((a, b) => a - b);
    const qq = (p) => (lags.length ? lags[Math.min(lags.length - 1, Math.floor(p * lags.length))] : '-');
    console.log(`${s.label.padEnd(12)} #${String(s.p).padStart(3)} HL-TICK ${ck.length} 点：全同 ${okAll}（nb ${f('logNb', 'shNb')} neut ${f('logNeut', 'shNeut')} cmds ${f('logCmds', 'shCmds')} boats ${f('logBoats', 'shBoats')}）首个不同 ${firstBad ? `t=${firstBad.t} cmds 日志 ${firstBad.logCmds} 影子 ${firstBad.shCmds}` : '无'} | 影子受理 ${mine.filter((c) => c.ok).length} 条 | 录像落地 ${mm.length} 条，唯一配上 ${lags.length}，延迟 中位/p90/最大 ${qq(0.5)}/${qq(0.9)}/${lags.length ? lags[lags.length - 1] : '-'}`);
  }
  // 日志行对比
  for (const s of sh) {
    const mineLog = slog.filter((l) => l.bot === s.label && /HL-OPENING|HL-DISPATCH/.test(l.s)).map((l) => l.s.trim());
    const real = s.b.logLines;
    const setS = new Map(); for (const l of mineLog) setS.set(l, (setS.get(l) || 0) + 1);
    let both = 0; const onlyReal = [];
    for (const l of real) { if (setS.get(l) > 0) { both++; setS.set(l, setS.get(l) - 1); } else onlyReal.push(l); }
    const onlySh = [...setS.entries()].filter(([, n]) => n > 0).map(([l]) => l);
    console.log(`${s.label.padEnd(12)} OPENING/DISPATCH 行：日志 ${real.length}，影子 ${mineLog.length}，逐字相同 ${both}，只在日志 ${onlyReal.length}，只在影子 ${onlySh.length}`);
    if (!argv.includes('--quiet')) {
      for (const l of onlyReal.slice(0, 3)) console.log(`      只在日志: ${l.slice(0, 150)}`);
      for (const l of onlySh.slice(0, 3)) console.log(`      只在影子: ${l.slice(0, 150)}`);
    }
  }
}
