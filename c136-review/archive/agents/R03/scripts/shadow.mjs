#!/usr/bin/env node
// shadow.mjs — 「影子策略」：在精确重放（resim.mjs）的每一拍真实状态上，旁路运行当局实际使用的策略源码
// （Va/Vb/Vc/c110 的 class Policy），记录它在每个本地拍会发出什么指令、走的是源码哪一行。
//
//   bash c136-review/tools/run-heavy.sh node shadow.mjs <matchId> [--maps t1,t2] [--until T] [--multi] [--strict-donate] [--minlat N] [--quiet]
//   （同一趟也写出 out/cache/<mid>-resim.json，等于顺带跑了 resim.mjs）
//
// 为什么可行：页面本地拍号 T 时策略读到的状态 = 服务器第 T 拍的状态（traj.csv 逐行核对 100% 一致），
// 策略本身是确定性的（除选点外不含随机数/墙钟），它的记忆只依赖「每拍看到的状态 + 自己发令的返回值」。
// 所以把同一份源码放在重放状态上逐拍调用 act()，就能还原它当时每一拍的决定。
// 影子发出的指令不落地（真实状态只由录像里的指令推进），与线上一致：线上发的指令也要等服务器回放才生效。
//
// 校验（输出里逐项给出一致率）：
//   · [HL-TICK] 的 nb / neut / cmds / boats（traj.csv，每 90 拍一行）
//   · [HL-DISPATCH] 捐款调度（events.csv：拍号、种类、pct、对象、myBal）
//   · [HL-OPENING] 开局 DP 扩张（opening.csv：拍号、cyc、rings、spend、bal、terr）
// 产出 out/cache/<mid>-shadow.json：
//   bots[bot] = { me, slot, stopT, error, acts[], cmds[], logs[], check{...}, match{...} }
//   cmds 行：[t, kind(1攻 2捐 3船), pct, target, ok, B, L, path("buyLand:5616>send:3865>send:485")]
//   acts 行：[t, B, L, nb, neut, cmds, isNoFullSend(0/1), shadowQuota, nOffers, top[[q,c,need,person,nearCollapse,bleeding,onMe,pulseMode,crowdedHard,inAtk,tD]…], 本拍发令数, worth, over(0/1), safeAt(-1)]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', 'cache');
const SIM = await import(path.join(DATA, 'src/sim/sim/index.js'));
const MAP = await import(path.join(DATA, 'src/sim/sim/map.js'));
const { NEUTRAL, P_INNER, P_BORDER, T_LAND, iV } = SIM;

export function strategyFileOf(mid) {
  const n = +mid.slice(1);
  if (mid[0] === 'A') return n <= 17 ? 'v27-team-c116-va.js' : n <= 96 ? 'v27-team-c116-vb.js' : 'v27-team-c116.js';
  if (mid[0] === 'B') return 'v27-team-c110.js';
  return 'v27-team-g09.js';
}

// 与页面 compileStrategy 相同的做法（见 c136-data/src/sim/tools/c117/teamgate.mjs）：把两行 import 换成参数，
// 去掉 export，其余一字不动——所以调用栈里的行号 − 2 就是源文件行号。
const compiled = new Map();
export function compileStrategy(file) {
  if (compiled.has(file)) return compiled.get(file);
  const body = fs.readFileSync(file, 'utf8')
    .replace(/^import\s*\{([^}]*)\}\s*from\s*['"]\.\.\/\.\.\/sim\/(index|map)\.js['"];?/gm,
      (_, names, which) => `const {${names}} = ${which === 'index' ? '__tsbSim' : '__tsbMap'};`)
    .replace(/^export\s+(?=(const|let|class|function)\s)/gm, '');
  if (typeof globalThis.window === 'undefined') globalThis.window = {};
  // eslint-disable-next-line no-new-func
  const r = new Function('__tsbSim', '__tsbMap', `${body}\nreturn { Policy, PARAMS };`)({ ...SIM }, { ...MAP });
  compiled.set(file, r);
  return r;
}

function readCsv(file) {
  if (!fs.existsSync(file)) return [];
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(Boolean);
  const head = lines[0].split(',');
  return lines.slice(1).map((l) => {
    const c = l.split(',');
    const o = {};
    head.forEach((h, i) => { o[h] = c[i]; });
    return o;
  });
}

const SLOT_BY_NAME = { ryan_m: 0, noah88: 1, leo_tx: 2, alex_k: 3, zero_7: 4, kaito9: 5, riku_x: 6, sora_w: 7, zexos1: 8, talon5: 9 };
const STACK_RE = /at (?:new )?([\w.$<>]+)[^\n]*<anonymous>:(\d+):\d+\)/g;
function codePath() {
  const st = new Error().stack || '';
  const out = [];
  let m;
  STACK_RE.lastIndex = 0;
  while ((m = STACK_RE.exec(st)) !== null) {
    const fn = m[1].replace(/^Policy\.|^V17\.|^V13\.|^Style\.|^General\.|^Strategy\./, '');
    out.push(`${fn}:${+m[2] - 2}`);
  }
  return out.reverse().join('>');
}

export function shadow(mid, opts = {}) {
  const bdir = path.join(DATA, 'bundles', mid);
  const file = path.join(DATA, 'src/strategy', opts.strategy || strategyFileOf(mid));
  const { Policy } = compileStrategy(file);
  const results = readCsv(path.join(bdir, 'results.csv'));
  const spawnRows = readCsv(path.join(bdir, 'spawn.csv'));
  const traj = readCsv(path.join(bdir, 'traj.csv'));
  const events = readCsv(path.join(bdir, 'events.csv'));
  const opening = readCsv(path.join(bdir, 'opening.csv'));

  const bots = {};
  let inited = false;
  let cur = null; // 当前正在 act 的号
  const multi = !!opts.multi; // 允许同一拍多条指令（线上 LiveGame 每拍只收 1 条，默认按 1 条）
  const strictDonate = !!opts.strictDonate;
  const adapter = opts.adapter || 'adjacent';
  const boatAdapter = opts.boatAdapter || 'sim';
  const quitMode = opts.quitMode || 'none';
  const actEvery = opts.actEvery || 1; // 页面每隔几拍调用一次 act（1 = 每拍）
  const skipAfterCmd = !!opts.skipAfterCmd; // 实验：本地接受一条指令后的下一拍不调用 act
  const personsAt = opts.persons ? new Map(String(opts.persons).split(',').map((x) => { const [a, b] = x.split('@'); return [+a, +(b || 0)]; })) : null;
  const boatMate = opts.boatMate || 'reject';
  const isBotMode = opts.isBotMode || 'clan';
  const minLat = Number.isFinite(opts.minLat) && opts.minLat > 0 ? opts.minLat : 6;
  const clanTag = (name) => { const m = /^\s*\[([^\]]*)\]/.exec(String(name || '')); return m ? m[1].trim().toUpperCase() : ''; };
  const mateAfter = /^mate-after:/.test(opts.isBotMode || '') ? +opts.isBotMode.split(':')[1] : -1;
  const quitSeen = new Set();
  const squadIds = new Set(); // 本地「指令是否被接受」的判定：sim=与模拟器 attack() 相同；adjacent=只看相邻；loose=不看前线

  const wouldAttack = (g, pct, target, p) => {
    if (!g.canAct(p) || p === target) return false;
    pct = Math.max(0, Math.min(1023, pct | 0));
    const t0 = g.attackTroopsTmp, f0 = g.attackFeeTmp;
    const q = g.quote(p, pct, 12);
    g.attackTroopsTmp = t0; g.attackFeeTmp = f0;
    if (!(q >= 0)) return false;
    target = Math.min(target, NEUTRAL);
    if (target < NEUTRAL && g.alive[target] === 0) target = NEUTRAL;
    if (target < NEUTRAL && !g.isEnemy(p, target)) return false;
    const already = g.hasAttack(p, target);
    if (!already && !g.hasFreeSlot(p)) return false;
    if (adapter === 'loose') return true;
    if (adapter === 'adjacent') {
      // 只要求有边界格与目标相邻（不管该格是否已是别的进攻的前线）
      const B2 = g.border[p], d2 = g.dir4, px2 = g.px, own2 = g.own;
      for (let i = B2.length - 1; i >= 0; i--) {
        const b = B2[i];
        for (let k2 = 3; k2 >= 0; k2--) {
          const c = b + d2[k2];
          if (target === NEUTRAL ? px2[c] === T_LAND : (px2[c] >= P_INNER && own2[c] === target)) return true;
        }
      }
      return false;
    }
    const before = g.front[p].length;
    const B = g.border[p], d = g.dir4, px = g.px, own = g.own;
    let add = false;
    outer: for (let i = B.length - 1; i >= 0; i--) {
      const b = B[i];
      if (px[b] !== P_BORDER) continue;
      for (let k = 3; k >= 0; k--) {
        const c = b + d[k];
        if (target === NEUTRAL ? px[c] === T_LAND : (px[c] >= P_INNER && own[c] === target)) { add = true; break outer; }
      }
    }
    if (before === 0 && !add) return false;
    if (!already && !add) return false;
    return true;
  };
  const wouldDonate = (g, pct, q, p) => {
    if (!g.teamGame || !g.canAct(p) || p === q) return false;
    if (q >= NEUTRAL || g.alive[q] === 0 || !g.isTeammate(p, q)) return false;
    if (strictDonate) return g.donateQuote(pct, q, p) > 0;
    pct = Math.max(0, Math.min(1023, pct | 0));
    const B = g.bal[p];
    const v = g.receiverRoom(q, Math.min(iV(B * (pct + 1), 1024), B - iV(64 * B, 1024)));
    return v >= 1;
  };

  // 船：与模拟器 boat()/boatTo() 相同的前置条件，但不付费、不下水；寻路时新加进航线表的航线事后撤销（真实状态只由回放指令推进）
  const wouldBoat = (g, pct, water, dir, p) => {
    if (!g.canAct(p)) return false;
    const W = g.W;
    const x = water % W, y = iV(water, W);
    if (!(0 < x && x < W - 1 && 0 < y && y < g.H - 1)) return false;
    if (!g.boatsAllowed(p)) return false;
    dir &= 7;
    if (!(dir < 4 && g.isShoreWater(water) && g.passable(water + g.dir4[dir]))) return false;
    pct = Math.max(0, Math.min(1023, pct | 0));
    const t0 = g.attackTroopsTmp, f0 = g.attackFeeTmp;
    const q = g.quote(p, pct, 32);
    g.attackTroopsTmp = t0; g.attackFeeTmp = f0;
    if (!(q >= 0)) return false;
    const n0 = g.routes.length, rt0 = g.routeTmp, bt0 = g.boatType;
    const ok = !!g.findBoatRoute(p, water, 1);
    while (g.routes.length > n0) {
      const r = g.routes.pop();
      const key = r[0] * g.N + r[r.length - 1];
      if (g.routeIndex.get(key) === g.routes.length) g.routeIndex.delete(key);
    }
    g.routeTmp = rt0; g.boatType = bt0;
    return ok;
  };
  const boatDbg = [];
  const wouldBoatTo = (g, pct, target, p) => {
    if (boatMate === 'reject' && g.px[target] >= P_INNER && g.isTeammate(p, g.own[target])) return false;
    const sp = g.boatSpot(target, p, 32);
    if (opts.boatDebug) {
      const W = g.W;
      const d = { t: g.t, p, target, x: target % W, y: iV(target, W), pxT: g.px[target], ownT: g.px[target] >= P_INNER ? g.own[target] : -1, sp, routes: g.routes.length, boatN: g.boatN, boatCount: g.boatCount[p] };
      if (sp) {
        const land = sp.water + g.dir4[sp.dir];
        d.landPx = g.px[land]; d.landOwn = g.px[land] >= P_INNER ? g.own[land] : -1;
        d.sx = sp.water % W; d.sy = iV(sp.water, W);
        let start = g.nearestCoast(p, sp.water);
        d.coast = start;
        if (start !== -1) { start = g.waterNextTo(start, sp.water); d.start = start; d.cached = start !== -1 ? g.findRoute(start, sp.water) : -2; d.cachedRev = start !== -1 ? g.findRoute(sp.water, start) : -2; }
      }
      boatDbg.push(d);
    }
    return sp !== null && wouldBoat(g, pct, sp.water, sp.dir, p);
  };

  const install = (g, ctx) => {
    g.names = ctx.names;
    const rec = (kind, pct, target, ok) => {
      const b = cur;
      b.cmds.push([g.t, kind, pct, target, ok ? 1 : 0, g.bal[b.me], g.terr[b.me], codePath()]);
      if (ok) b.lastCmdT = g.t;
      return ok;
    };
    const free = () => multi || cur.lastCmdT !== g.t;
    const simIsBot = Object.getPrototypeOf(g).isBot || g.isBot;
    const ov = {
      online: opts.online !== false,
      ...(isBotMode === 'mate-person' ? { isBot: (p) => p >= g.humans || (g.state[p] === 2 && !(cur && g.isTeammate(cur.me, p))) } : {}),
      ...(isBotMode === 'human-person' ? { isBot: (p) => p >= g.humans } : {}),
      ...(personsAt ? { isBot: (p) => p >= g.humans || (g.state[p] === 2 && !(personsAt.has(p) && g.t >= personsAt.get(p))) } : {}),
      // 线上适配层的 isBot（由 A025/A051/A066/A071 四局反推，适配层源码不在数据仓库里）：
      //   已离线的对手 = 机器人；已离线的同战队标签（[APEX]…）队友 = 机器人；已离线的其他随机队友 ≠ 机器人（仍算「真人」）
      ...(isBotMode === 'clan' ? { isBot: (p) => p >= g.humans || (g.state[p] === 2 && !(cur && g.isTeammate(cur.me, p) && clanTag(ctx.names[p]) !== clanTag(ctx.names[cur.me]))) } : {}),
      ...(isBotMode === 'random-mate-person' ? { isBot: (p) => p >= g.humans || (g.state[p] === 2 && !(cur && g.isTeammate(cur.me, p) && !squadIds.has(p))) } : {}),
      ...(mateAfter >= 0 ? { isBot: (p) => p >= g.humans || (g.state[p] === 2 && !(g.t >= mateAfter && cur && g.isTeammate(cur.me, p))) } : {}),
      attack: (pct, target, p = cur.me) => rec(1, pct, Math.min(target, NEUTRAL), free() && wouldAttack(g, pct, target, p)),
      donate: (pct, q, p = cur.me) => rec(2, pct, q, free() && wouldDonate(g, pct, q, p)),
      boat: (pct, water, dir, p = cur.me) => rec(3, pct, water * 8 + dir, free() && (boatAdapter === 'loose' ? g.canAct(p) && g.boatCount[p] < 5 && g.bal[p] > 0 : wouldBoat(g, pct, water, dir, p))),
      boatTo: (pct, landPix, p = cur.me) => rec(3, pct, -landPix, free() && (boatAdapter === 'loose' ? g.canAct(p) && g.boatCount[p] < 5 && g.bal[p] > 0 : wouldBoatTo(g, pct, landPix, p))),
      chase: () => false,
      recall: () => false,
      retreat: (target) => { cur.cmds.push([g.t, 5, 0, target, 1, g.bal[cur.me], g.terr[cur.me], codePath()]); return true; },
      leave: () => { cur.cmds.push([g.t, 8, 0, 0, 1, g.bal[cur.me], g.terr[cur.me], codePath()]); return true; },
    };
    return {
      on() { for (const k of Object.keys(ov)) g[k] = ov[k]; },
      off() { for (const k of Object.keys(ov)) delete g[k]; },
    };
  };

  let hooks = null;
  const init = (g, ctx) => {
    inited = true;
    hooks = install(g, ctx);
    for (const [bot, s] of Object.entries(ctx.squad)) {
      if (s.id < 0) continue;
      squadIds.add(s.id);
      const r = results.find((x) => x.bot === bot);
      const sp = spawnRows.filter((x) => x.bot === bot);
      // 小队槽位按机器人名固定（A051/A087/A066… 的 spawn.csv 全部一致）；日志缺出生行时（如 A071）用这张表
      const slot = sp.length ? +sp[sp.length - 1].slot : (bot in SLOT_BY_NAME ? SLOT_BY_NAME[bot] : s.id % 10);
      // event=left 的号：results.csv 的 tick 是外层最后一次采到的状态拍，不一定是页面真正停止的拍——
      // 页面日志（traj = HL-TICK，每 90 拍一行）可能还在往后打（A051 zero_7：results 994，日志到 1260）。
      // 影子至少跑到最后一行日志那一拍（含），之后页面是否还在运行不可知。
      const lastLogT = traj.filter((x) => x.bot === bot).reduce((m, x) => Math.max(m, +x.t), -1);
      const stopT = r && r.event === 'left' ? Math.max(+r.tick, lastLogT + 1) : Infinity;
      const b = {
        bot, me: s.id, slot, stopT, stopResultsT: r && r.event === 'left' ? +r.tick : null, lastLogT, error: null, pol: null, cmds: [], acts: [], logs: [], lastCmdT: -1, blocked: [], nfsFlip: null,
        win: { __tsbSquadSlot: slot, __quitPlayers: new Set(), __hlPerf: null },
        tick: [],
      };
      b.win.__hlLog = (line) => b.logs.push(line);
      globalThis.window = b.win;
      b.pol = new Policy(opts.params || {}, s.id);
      // Policy.send 里的「发兵限额」守卫（isNoFullSend 且影子额度不足时对真人/AI 目标直接 return false）：记下被它挡掉的出手
      const protoSend = Policy.prototype.send;
      b.pol.send = function (gg, target, troops, hint) {
        const n0 = b.cmds.length;
        const r = protoSend.call(this, gg, target, troops, hint);
        if (!r && b.cmds.length === n0 && this.isNoFullSend && troops > 2) {
          b.blocked.push([gg.t, Math.min(target, NEUTRAL), Math.round(troops), Math.round(this.shadowQuota), gg.bal[b.me]]);
        }
        return r;
      };
      const origOffers = b.pol.offers;
      if (typeof origOffers === 'function') {
        b.pol.offers = function (gg, ...rest) {
          const r2 = origOffers.call(this, gg, ...rest);
          b.lastOffers = r2;
          return r2;
        };
      }
      bots[bot] = b;
    }
  };

  const onState = (g, ctx) => {
    if (g.spawnPhase) return;
    if (!inited) init(g, ctx);
    const t = g.t;
    // 页面上的 __quitPlayers：已离线（被内置 AI 接管）的真人
    if (quitMode !== 'none') {
      for (let p = 0; p < g.humans; p++) {
        if (g.state[p] !== 2 || quitSeen.has(p)) continue;
        const isSquad = squadIds.has(p);
        if (quitMode === 'all-left' || (quitMode === 'squad-left' && isSquad) || quitMode === 'mates-left') {
          quitSeen.add(p);
          for (const b of Object.values(bots)) if (quitMode !== 'mates-left' || g.isTeammate(b.me, p)) b.win.__quitPlayers.add(p);
        }
      }
    }
    for (const b of Object.values(bots)) {
      if (b.error || t >= b.stopT || !g.canAct(b.me)) continue;
      if (actEvery > 1 && t % actEvery !== 0) continue;
      if (skipAfterCmd && b.lastCmdT === t - 1) continue;
      cur = b;
      globalThis.window = b.win;
      b.lastOffers = null;
      const nCmd0 = b.cmds.length;
      const nfs0 = b.pol.isNoFullSend;
      const pc0 = b.pol.pendingQuotaCheck ? { ...b.pol.pendingQuotaCheck } : null;
      hooks.on();
      try {
        if (opts.trace) opts.trace(g, b, b.pol, ctx);
        b.pol.act(g);
      } catch (e) {
        b.error = { t, message: String(e && e.stack ? e.stack : e).split('\n').slice(0, 4).join(' | ').slice(0, 600) };
      }
      hooks.off();
      if (!nfs0 && b.pol.isNoFullSend && !b.nfsFlip) b.nfsFlip = { t, pending: pc0, B: g.bal[b.me], L: g.terr[b.me] };
      const P = b.pol.p;
      if (t % (P.period || 5) === 0) {
        const me = b.me, B = g.bal[me], L = g.terr[me];
        const row = [t, B, L, b.pol.nb.length, b.pol.neutral, b.pol.cmds, b.pol.isNoFullSend ? 1 : 0, Math.round(b.pol.shadowQuota || 0)];
        const of = b.lastOffers;
        if (of && of.length !== undefined) {
          row.push(of.length);
          const top = [];
          for (let i = 0; i < Math.min(of.length, 4); i++) {
            const o = of[i];
            top.push([o.q, +(+o.c).toFixed(2), Math.round(o.need), o.person ? 1 : 0, o.nearCollapse ? 1 : 0, o.bleeding ? 1 : 0, o.onMe ? 1 : 0, o.pulseMode ? 1 : 0, o.isCrowdedHard ? 1 : 0, Math.round(o.inAtk || 0), o.tD === undefined ? -1 : +(+o.tD).toFixed(2)]);
          }
          row.push(top);
        } else row.push(-1, []);
        row.push(b.cmds.length - nCmd0);
        // buyLand 的门槛：worth = maxW × winRatio(t) × max(自己密度, marketFloor × 其他真人密度中位)；over = 余额 > 100×地
        let worth = -1, over = 0, safe = -1;
        try {
          const pol = b.pol;
          if (typeof pol.winRatio === 'function' && L > 0) {
            const dMe = B / Math.max(1, L);
            const dMed = typeof pol.otherHumanMedDens === 'function' ? pol.otherHumanMedDens(g) : null;
            const m = P.maxW * pol.winRatio(t);
            const refDens = dMed !== null && t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMed) : dMe;
            worth = +(m * refDens).toFixed(2);
            over = P.surplus > 0 && B > 100 * L ? 1 : 0;
            if (t >= P.coreFrom && typeof pol.safeAt === 'function') { hooks.on(); safe = Math.round(pol.safeAt(g, -1)); hooks.off(); }
          }
        } catch (e) { worth = -2; }
        row.push(worth, over, safe);
        b.acts.push(row);
      }
      if (t % 90 === 0) b.tick.push([t, b.pol.nb.length, b.pol.neutral, b.pol.cmds, b.pol.boats || 0]);
    }
  };

  let deathAll = null;
  const R = resim(mid, { until: opts.until, maps: opts.maps || [], onState: (g, ctx) => { deathAll = ctx.deathT; onState(g, ctx); } });
  globalThis.window = {};

  // ---- 校验 ----
  const report = { matchId: mid, strategy: path.basename(file), multi, strictDonate, adapter, boatMate, isBotMode, quitMode, actEvery, skipAfterCmd, minLat, validate: R.validate, bots: {} };
  if (opts.boatDebug) report.boatDbg = boatDbg;
  for (const b of Object.values(bots)) {
    const chk = { tick: { rows: 0, nb: 0, neut: 0, cmds: 0, boats: 0, firstCmdsDiff: null }, dispatch: { log: 0, shadow: 0, same: 0, firstDiff: null }, opening: { log: 0, shadow: 0, same: 0, firstDiff: null } };
    const tr = new Map(traj.filter((r) => r.bot === b.bot).map((r) => [+r.t, r]));
    const mine = new Map();
    for (const l of b.logs) {
      const m = /^\[HL-TICK\] t=(\d+) .* nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)/.exec(l);
      if (m) mine.set(+m[1], [+m[2], +m[3], +m[4], +m[5]]);
    }
    for (const [t, r] of tr) {
      const s = mine.get(t);
      if (!s) continue;
      chk.tick.rows++;
      if (s[0] === +r.nb) chk.tick.nb++;
      if (s[1] === +r.neut) chk.tick.neut++;
      if (s[2] === +r.cmds) chk.tick.cmds++; else if (!chk.tick.firstCmdsDiff) chk.tick.firstCmdsDiff = [t, +r.cmds, s[2]];
      if (s[3] === +r.boats) chk.tick.boats++;
    }
    const inRun = (e) => !opts.until || +e.t < opts.until; // --until 时只核对跑到的那一段日志
    const logD = events.filter((e) => e.type === 'DISPATCH' && e.bot === b.bot && inRun(e)).map((e) => `${e.t}|${e.kind}|${e.pct}|${e.target}|${e.myBal}`);
    const shD = [];
    for (const l of b.logs) {
      const m = /^\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)\/1024 -> ally=(\d+)\(.*\) boxedIn=(\w+) myBal=(\d+)/.exec(l);
      if (m) shD.push(`${m[1]}|${m[2]}|${m[3]}|${m[4]}|${m[6]}`);
    }
    chk.dispatch.log = logD.length; chk.dispatch.shadow = shD.length;
    const setS = new Set(shD);
    for (const x of logD) if (setS.has(x)) chk.dispatch.same++; else if (!chk.dispatch.firstDiff) chk.dispatch.firstDiff = x;
    const setL = new Set(logD);
    chk.dispatch.shadowOnly = shD.filter((x) => !setL.has(x)).slice(0, 3);
    const logO = opening.filter((e) => e.bot === b.bot && inRun(e)).map((e) => `${e.t}|${e.cyc}|${e.rings}|${e.spend}|${e.bal}|${e.terr}`);
    const shO = [];
    for (const l of b.logs) {
      const m = /^\[HL-OPENING\] t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)\/(\d+) terr=(\d+)/.exec(l);
      if (m) shO.push(`${m[1]}|${m[2]}|${m[3]}|${m[4]}|${m[5]}|${m[6]}`);
    }
    chk.opening.log = logO.length; chk.opening.shadow = shO.length;
    const setO = new Set(shO);
    for (const x of logO) if (setO.has(x)) chk.opening.same++; else if (!chk.opening.firstDiff) chk.opening.firstDiff = x;

    // ---- 影子发令 ↔ 录像成交 对齐（同种类、同 pct、同对象；录像同一拍内按后进先出还原发令顺序）----
    const exec = R.cmdLog.filter((c) => c[1] === b.me && (c[2] === 1 || c[2] === 2 || c[2] === 3));
    const groups = [];
    for (const c of exec) {
      if (groups.length && groups[groups.length - 1][0][0] === c[0]) groups[groups.length - 1].push(c);
      else groups.push([c]);
    }
    const issued = b.cmds.filter((c) => c[4] === 1 && c[1] <= 3);
    // 保序对齐：成交序列（按服务器拍升序、同拍内倒序 = 发令顺序）必须对应影子发令序列的一个递增子序列。
    // 从最后一批往前排，每批优先放在「连续 n 条」的最晚位置（客户端追帧时连发的 n 条在同一个服务器拍落地），
    // 放不下再逐条取最晚可行的——所以对重复签名（同 pct 同目标）给出的是延迟的下界。
    let pairs = []; // [serverT, localT, kind, pct, execTarget, effective, issuedIdx, issuedTarget]
    let unmatchedExec = 0;
    // 最小延迟下界：默认 6 拍（前九局全部成交都对得上）。个别局有 5 拍落地的指令，下界卡住会让保序对齐整段串位，
    // 这时用 --minlat 5 重跑（A046 的 zero_7：3635 拍发、3640 拍落地）。
    const MINLAT = minLat;
    const sigOk = (s, kind, pct, target, S) => {
      if (s[1] !== kind || s[2] !== pct) return false;
      if (s[0] > S - MINLAT) return false;
      if (kind === 1 && s[3] !== target) {
        // 引擎 bD.gv.rk：指令落地时目标已死 → 目标改成中立（录像里记的是改写后的 512）
        const dt = s[3] < NEUTRAL ? deathAll[s[3]] : -1;
        return target === NEUTRAL && dt >= 0 && dt <= S;
      }
      if (kind === 2 && s[3] !== target) return false;
      return true;
    };
    let bound = issued.length;
    for (let gi = groups.length - 1; gi >= 0; gi--) {
      const ordered = groups[gi].slice().reverse();
      const S = ordered[0][0];
      const n = ordered.length;
      const tgt = (c) => (c[2] === 1 ? Math.min(c[4], NEUTRAL) : c[4]);
      let hi = bound - 1;
      while (hi >= 0 && issued[hi][0] > S - MINLAT) hi--;
      let placed = -1;
      for (let end = hi; end >= n - 1; end--) {
        const st = end - n + 1;
        let ok = true;
        for (let k = n - 1; k >= 0; k--) {
          const c = ordered[k];
          if (!sigOk(issued[st + k], c[2], c[3], tgt(c), S)) { ok = false; break; }
        }
        if (ok) { placed = st; break; }
      }
      const rows = new Array(n);
      if (placed >= 0) {
        for (let k = 0; k < n; k++) {
          const c = ordered[k], is = issued[placed + k];
          rows[k] = [c[0], is[0], c[2], c[3], tgt(c), c[5], placed + k, is[3]];
        }
        bound = placed;
      } else {
        for (let k = n - 1; k >= 0; k--) {
          const c = ordered[k];
          let found = -1;
          for (let i = Math.min(hi, bound - 1); i >= 0; i--) {
            if (sigOk(issued[i], c[2], c[3], tgt(c), S)) { found = i; break; }
          }
          if (found >= 0) {
            rows[k] = [c[0], issued[found][0], c[2], c[3], tgt(c), c[5], found, issued[found][3]];
            bound = found;
          } else {
            unmatchedExec++;
            rows[k] = [c[0], -1, c[2], c[3], tgt(c), c[5], -1, -1];
          }
        }
      }
      pairs = rows.concat(pairs);
    }
    const lags = pairs.filter((p) => p[1] >= 0).map((p) => p[0] - p[1]).sort((a, c) => a - c);
    const issuedIdx = [];
    b.cmds.forEach((c, i) => { if (c[4] === 1 && c[1] <= 3) issuedIdx.push(i); });
    const execOf = new Array(b.cmds.length).fill(-1); // b.cmds 下标 → 成交的服务器拍（-1 = 没成交）
    for (const p of pairs) if (p[6] >= 0) execOf[issuedIdx[p[6]]] = p[0];
    const match = {
      execOf,
      exec: exec.length, issued: issued.length, matched: lags.length, unmatchedExec,
      lagMedian: lags.length ? lags[lags.length >> 1] : null, lagMax: lags.length ? lags[lags.length - 1] : null, lagMin: lags.length ? lags[0] : null,
      pairs,
    };
    report.bots[b.bot] = { me: b.me, slot: b.slot, stopT: b.stopT === Infinity ? null : b.stopT, stopResultsT: b.stopResultsT, lastLogT: b.lastLogT, error: b.error, check: chk, match, cmds: b.cmds, acts: b.acts, logs: b.logs.filter((l) => !l.startsWith('[HL-TICK]')), tick: b.tick, blocked: b.blocked, nfsFlip: b.nfsFlip, final: { cmds: b.pol.cmds, boats: b.pol.boats || 0, isNoFullSend: !!b.pol.isNoFullSend } };
  }
  report.resim = R;
  return report;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const mid = args[0];
  if (!mid) { console.error('用法：node shadow.mjs <matchId> [--until T] [--multi] [--strict-donate] [--strategy file.js]'); process.exit(2); }
  const opt = (k, dflt) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : dflt);
  const until = opt('until', null);
  const t0 = Date.now();
  const mapsArg = opt('maps', '');
  const rep = shadow(mid, { until: until ? +until : undefined, multi: args.includes('--multi'), strictDonate: args.includes('--strict-donate'), strategy: opt('strategy', null), adapter: opt('adapter', null), boatAdapter: opt('boat-adapter', null), boatDebug: args.includes('--boat-debug'), isBotMode: opt('isbot', null), quitMode: opt('quit', null), persons: opt('persons', null), actEvery: +(opt('act-every', 0) || 0), skipAfterCmd: args.includes('--skip-after-cmd'), minLat: +(opt('minlat', 6)), boatMate: opt('boat-mate', null), maps: mapsArg ? mapsArg.split(',').map(Number) : [] });
  fs.mkdirSync(OUT, { recursive: true });
  const R = rep.resim;
  delete rep.resim;
  if (!until) fs.writeFileSync(path.join(OUT, `${mid}-resim.json`), JSON.stringify(R));
  fs.writeFileSync(path.join(OUT, `${mid}-shadow.json`), JSON.stringify(rep));
  const v = rep.validate;
  console.log(`${mid} 影子策略（${rep.strategy}${rep.multi ? '，同拍多令' : ''}）用时 ${((Date.now() - t0) / 1000).toFixed(1)}s；重放 traj 核对 ${v.bothExact}/${v.rows}`);
  {
    let rows = 0, cm = 0, bo = 0, ex = 0, mt = 0;
    for (const b of Object.values(rep.bots)) { rows += b.check.tick.rows; cm += b.check.tick.cmds; bo += b.check.tick.boats; ex += b.match.exec; mt += b.match.matched; }
    console.log(`  合计（adapter=${rep.adapter} boatMate=${rep.boatMate} isBot=${rep.isBotMode} actEvery=${rep.actEvery}${rep.skipAfterCmd ? ' skipAfterCmd' : ''}）：HL-TICK ${rows} 行，cmds 一致 ${cm}，boats 一致 ${bo}；成交对上 ${mt}/${ex}`);
  }
  for (const [bot, b] of Object.entries(rep.bots)) {
    const c = b.check;
    if (args.includes('--summary')) break;
    console.log(`  ${bot.padEnd(7)} me=${String(b.me).padStart(3)} slot=${b.slot} ` +
      `HL-TICK ${c.tick.rows}行 nb ${c.tick.nb} neut ${c.tick.neut} cmds ${c.tick.cmds} boats ${c.tick.boats}` +
      `${c.tick.firstCmdsDiff ? ` 首差@${c.tick.firstCmdsDiff[0]}(日志${c.tick.firstCmdsDiff[1]} 影子${c.tick.firstCmdsDiff[2]})` : ''}` +
      ` | 调度 日志${c.dispatch.log} 影子${c.dispatch.shadow} 同${c.dispatch.same}` +
      ` | 开局 日志${c.opening.log} 影子${c.opening.shadow} 同${c.opening.same}` +
      ` | 成交${b.match.exec} 影子令${b.match.issued} 对上${b.match.matched} 延迟中位${b.match.lagMedian} 最大${b.match.lagMax}` +
      `${b.error ? ` | 报错@${b.error.t}: ${b.error.message.slice(0, 160)}` : ''}`);
    if (!args.includes('--quiet')) {
      if (c.dispatch.firstDiff) console.log(`      调度首差（日志有影子无）：${c.dispatch.firstDiff}；影子独有：${(c.dispatch.shadowOnly || []).join(' ; ')}`);
      if (c.opening.firstDiff) console.log(`      开局首差（日志有影子无）：${c.opening.firstDiff}`);
    }
  }
}
