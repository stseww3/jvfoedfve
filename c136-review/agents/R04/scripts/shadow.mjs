#!/usr/bin/env node
// shadow.mjs — 「影子策略」：在真引擎重放的每一拍，把全场真实状态抄进模拟器的 Game 对象，
// 再让本局实际部署的那份策略源码（Policy）对着它跑一遍，但它发出的指令只记录、不执行。
// 这样能看到某个号在某一拍「按代码会走哪条分支、报价单长什么样、底线是多少」，用来给决策审计找到代码行。
//
// 用法：
//   node scripts/shadow.mjs <局号> --bots ryan_m,zero_7 --from 600 --to 1700 [--ver vb|va|vc|c110]
//        [--trace] [--every 1|5] [--quiet] [--at t1,t2,...] [--out 目录] [--rows]
//     --out 目录    写出 intents.tsv（影子想发的每条指令）、logs.txt（影子打出的日志行）、check.json（自检与影子锁统计）
//     --rows        另写 rows.tsv：每个行动拍一行（邻居构成、最弱 AI 邻居、打 AI 要守的底线、是否出手）
//     --from/--to   影子策略运行的拍段（之前只快进引擎；策略内部记忆从 --from 开始积累）
//     --trace       每个行动拍都打印：报价单前几条、底线、想发的指令
//     --at          只在这些拍打印详细状态（报价单、底线、捐款判定）
//     --water       配合 --at：另外打印发船选落点（searchWater）的候选清单（每个可登陆对象的水程、单价、折算）
//     --every 5     像素层每 5 拍抄一次（默认；玩家/进攻/船每拍都抄）；--every 1 每拍都抄像素
//   输出末尾有保真度自检：影子策略自己算的 nb/neut 与该号真实日志 [HL-TICK] 同拍的 nb/neut 是否一致，
//   以及影子发出的调度（[HL-DISPATCH]）与真实日志同拍调度是否一致。
//
// 注意：影子看到的是「服务器真值」，而真实的号看到的是它自己客户端推进到的那一拍（同一拍号下状态相同，
// 但指令要晚若干拍才落地）；影子发出的指令不落地，所以它与真号的内部记忆会有小差异。结论以分支条件为主。
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const { createHost } = require('./engine_host.cjs');
const { patchTruth } = require('./engine_truth.cjs');
const { loadCsv, DATA } = require('./engine_replay.cjs');
const SRC = '/agent/repos/c136-data/src';
const SIM = await import(SRC + '/sim/sim/index.js');
const { Game, loadMap, NEUTRAL, P_INNER, P_BORDER, T_LAND, T_WATER } = SIM;

const DIAG = await import('./shadow_diag.mjs');
const VERS = { vb: 'v27-team-c116-vb.js', va: 'v27-team-c116-va.js', vc: 'v27-team-c116.js', c110: 'v27-team-c110.js' };

export async function loadPolicy(ver) {
  const file = VERS[ver];
  if (!file) throw new Error('未知策略版本 ' + ver);
  const dir = path.join(HERE, '..', 'tmp', 'strategy');
  fs.mkdirSync(dir, { recursive: true });
  let src = fs.readFileSync(path.join(SRC, 'strategy', file), 'utf8');
  src = src.replace(/from "\.\.\/\.\.\/sim\/index\.js"/g, `from "${SRC}/sim/sim/index.js"`).replace(/from "\.\.\/\.\.\/sim\/map\.js"/g, `from "${SRC}/sim/sim/map.js"`);
  const out = path.join(dir, file.replace(/\.js$/, '.mjs'));
  if (!fs.existsSync(out) || fs.readFileSync(out, 'utf8') !== src) fs.writeFileSync(out, src);
  return import(out);
}

export function versionOf(mid) {
  if (mid[0] === 'B') return 'c110';
  const n = +mid.slice(1);
  return n <= 17 ? 'va' : n <= 95 ? 'vb' : 'vc';
}

// 启动真引擎重放，并在引擎作用域里放一组只读取数函数
export function startEngine(mid) {
  const h = createHost({ patch: patchTruth });
  h.run('bx(true)');
  h.flushTimers();
  h.ctx.__rep = fs.readFileSync(path.join(DATA, mid, 'replay.txt'), 'utf8').trim();
  if (!h.run('bC.aMU.zS(window.__rep)')) throw new Error('录像解不开');
  h.run('bC.aVq()');
  h.flushTimers();
  const info = JSON.parse(h.run('JSON.stringify({ku:aE.ku, players:aE.a0E, ke:aE.ke, w:bV.fk, h:bV.fl, map:bV.fF, slots:(aE.ku<16?12:8)})'));
  const api = h.run(`(function () {
    var W = bV.fk, H = bV.fl, NP = W * H, N = aE.a0E, ku = aE.ku;
    return {
      advance: function (n) { var st = bi.a3I; for (var k = 0; k < n; k++) { if (aE.a38 === 2) break; st.__step(); } return [bi.kr(), aE.hx ? 1 : 0, aE.a38]; },
      names: function () { var r = []; for (var p = 0; p < N; p++) r.push(ah.a3o[p]); return r; },
      owners: function (out) { for (var i = 0, fD = 0; i < NP; i++, fD += 4) out[i] = ad.h9(fD) ? ad.fR(fD) : 65535; },
      players: function (terr, bal, peak, alive, state, debt, x0, y0, x1, y1) {
        for (var p = 0; p < N; p++) { terr[p] = ah.hN[p]; bal[p] = ah.hb[p]; peak[p] = ah.a0i[p]; alive[p] = ah.nU[p]; state[p] = ah.a6S[p]; debt[p] = ah.a6b[p]; x0[p] = ah.jS[p]; y0[p] = ah.jU[p]; x1[p] = ah.jT[p]; y1[p] = ah.jV[p]; }
      },
      attacks: function (cnt, tgt, trp, slotsHuman) {
        for (var p = 0; p < N; p++) {
          var n = ah.nU[p] ? ae.gg(p) : 0; cnt[p] = n;
          var base = p < ku ? slotsHuman * p : slotsHuman * ku + 4 * (p - ku);
          for (var i = 0; i < n; i++) { tgt[base + i] = ae.gl(p, i); trp[base + i] = ae.gm(p, i); }
        }
      },
      boats: function (bSlot, bPos, bTroops, bId, bType, boatCount) {
        var z = bQ.z, n = z.mk;
        for (var i = 0; i < n; i++) { bSlot[i] = z.mo[i]; bPos[i] = z.mz[i]; bTroops[i] = z.a9g[i]; bId[i] = z.mn[i]; bType[i] = z.ml[i]; }
        for (var p = 0; p < N; p++) boatCount[p] = z.ky[p];
        return n;
      },
      teams: function (out) { var any = 0; for (var p = 0; p < N; p++) { out[p] = (bj.fX && bj.fX[p]) | 0; if (out[p]) any = 1; } return any; },
      quota: function (out) { var q = ao.__q(); out.set(q[0].subarray(0, out.length)); return q[1]; },
      tick: function () { return bi.kr(); }
    };
  })()`);
  return { h, info, api };
}

// 把真引擎此刻的状态抄进模拟器 Game（只读镜像）
export class Mirror {
  constructor(info, api) {
    this.info = info; this.api = api;
    const map = loadMap(info.map, 0);
    if (map.w !== info.w || map.h !== info.h || map.land !== info.ke) throw new Error('模拟器地图与引擎地图对不上');
    const g = new Game({ map, humans: info.ku, players: info.players, difficulty: 0, spawnSeed: 0, selectableSpawn: false, humanColors: new Array(info.ku).fill(0) });
    this.g = g; this.map = map;
    g.online = true;
    g.spawnPhase = 0;
    g.land = info.ke;
    g.names = api.names();
    g.teamGame = api.teams(g.teams);
    let nT = 0; for (let p = 0; p < 512; p++) nT = Math.max(nT, g.teams[p]);
    g.nTeams = nT;
    this.ownRaw = new Uint16Array(g.N);
    for (let p = 0; p < 512; p++) { g.border[p] = []; g.coast[p] = []; g.cliff[p] = []; g.front[p] = []; }
    g.aliveList = new Uint16Array(512);
    this.intents = [];
    const self = this;
    // 指令只记录、不执行。返回值尽量贴近线上：进攻要有接触且有空槽，捐款要对方是在场队友，船要有海岸和落点。
    g.attack = function (pct, target, p = this.me) {
      if (!this.canAct(p) || p === target) return false;
      target = Math.min(target, NEUTRAL);
      if (target < NEUTRAL && !this.isEnemy(p, target)) return false;
      const already = this.hasAttack(p, target);
      if (!already && !this.hasFreeSlot(p)) return false;
      if (!self.touches(p, target)) return false;
      const troops = Math.floor(((pct + 1) * this.bal[p]) / 1024);
      self.intents.push({ t: this.t, p, kind: 'attack', pct, target, troops });
      return true;
    };
    g.donate = function (pct, q, p = this.me) {
      if (!this.canAct(p) || !this.isTeammate(p, q) || !this.alive[q]) return false;
      self.intents.push({ t: this.t, p, kind: 'donate', pct, target: q, troops: Math.floor(((pct + 1) * this.bal[p]) / 1024) });
      return true;
    };
    g.boatTo = function (pct, target, p = this.me, radius = 32) {
      let s = null;
      try { s = this.boatSpot(target, p, radius); } catch (e) { s = null; }
      if (s === null) return false;
      self.intents.push({ t: this.t, p, kind: 'boat', pct, target, troops: Math.floor(((pct + 1) * this.bal[p]) / 1024) });
      return true;
    };
    g.boat = function (pct, water, dir, p = this.me) {
      if (!this.boatsAllowed(p)) return false;
      self.intents.push({ t: this.t, p, kind: 'boat', pct, target: water, troops: Math.floor(((pct + 1) * this.bal[p]) / 1024) });
      return true;
    };
    g.chase = function (pct, id, p = this.me) { self.intents.push({ t: this.t, p, kind: 'chase', pct, target: id, troops: 0 }); return true; };
    g.recall = function (id, p = this.me) { self.intents.push({ t: this.t, p, kind: 'recall', pct: 0, target: id, troops: 0 }); return true; };
    g.retreat = function (target, p = this.me) { if (!this.hasAttack(p, Math.min(target, NEUTRAL))) return false; self.intents.push({ t: this.t, p, kind: 'retreat', pct: 0, target, troops: 0 }); return true; };
  }

  touches(p, target) {
    const g = this.g, B = g.border[p], d = g.dir4, px = g.px, own = g.own;
    for (let i = B.length - 1; i >= 0; i--) {
      for (let k = 0; k < 4; k++) {
        const c = B[i] + d[k];
        if (target === NEUTRAL ? px[c] === T_LAND : (px[c] >= P_INNER && own[c] === target)) return true;
      }
    }
    return false;
  }

  // 每拍都抄的轻量部分：玩家数组、进攻槽、船、配额、存活表
  light() {
    const g = this.g, api = this.api;
    g.t = api.tick();
    api.players(g.terr, g.bal, g.peak, g.alive, g.state, g.debt, g.x0, g.y0, g.x1, g.y1);
    api.attacks(g.atkCount, g.atkTarget, g.atkTroops, g.slotsHuman);
    g.boatN = api.boats(g.bSlot, g.bPos, g.bTroops, g.bId, g.bType, g.boatCount);
    const used = new Uint8Array(512);
    for (let b = 0; b < g.boatN; b++) { const p = g.bSlot[b] >> 3; g.boatOf[(p << 3) + used[p]++] = b; g.bRoute[b] = null; }
    g.donCap = api.quota(g.donQuota);
    let n = 0, top = -1;
    for (let p = 0; p < 512; p++) if (g.alive[p]) { g.aliveList[n++] = p; if (top < 0 || g.terr[p] > g.terr[top]) top = p; }
    g.aliveCount = n;
    if (top >= 0) g.rank[0] = top;
  }

  // 像素层：归属 + 边界/海岸/内陆分类（定义与模拟器 refreshBorder 相同）
  pixels() {
    const g = this.g, raw = this.ownRaw, type = this.map.type, W = g.W, H = g.H, px = g.px, own = g.own;
    this.api.owners(raw);
    for (let p = 0; p < 512; p++) { g.border[p].length = 0; g.coast[p].length = 0; g.cliff[p].length = 0; }
    const N = g.N;
    for (let i = 0; i < N; i++) {
      const o = raw[i];
      if (o === 65535) { const v = type[i]; px[i] = v; own[i] = (v & 3) << 3; } else { px[i] = P_INNER; own[i] = o; }
    }
    for (let y = 1; y < H - 1; y++) {
      for (let i = y * W + 1, e = y * W + W - 1; i < e; i++) {
        const o = raw[i];
        if (o === 65535) continue;
        let hostile = false, water = false, wall = false;
        for (let k = 0; k < 4; k++) {
          const c = i + (k === 0 ? -W : k === 1 ? 1 : k === 2 ? W : -1);
          const ro = raw[c];
          if (ro === 65535) {
            const v = type[c];
            if (v === T_LAND) { hostile = true; break; }
            if (v === T_WATER) water = true; else if (v >= 3) wall = true;
          } else if (ro !== o) { hostile = true; break; }
        }
        if (hostile) { g.border[o].push(i); px[i] = P_BORDER; } else if (water) { g.coast[o].push(i); px[i] = P_BORDER; } else if (wall) { g.cliff[o].push(i); px[i] = P_BORDER; }
      }
    }
  }
}

function fmt(n) { n = Math.round(n); const a = Math.abs(n); return a >= 1e7 ? (n / 1e6).toFixed(1) + 'M' : a >= 1e6 ? (n / 1e6).toFixed(2) + 'M' : a >= 1e4 ? (n / 1e3).toFixed(1) + 'k' : String(n); }

async function main() {
  const args = process.argv.slice(2);
  const mid = args[0];
  const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
  const has = (k) => args.includes(k);
  const ver = opt('--ver', versionOf(mid));
  DIAG.setDiagVersion(ver);
  const from = +opt('--from', 0), to = +opt('--to', 1e9);
  const every = +opt('--every', 5);
  const nOffers = +opt('--offers', 4);
  const trace = has('--trace'), quiet = has('--quiet');
  const at = new Set((opt('--at', '') || '').split(',').filter(Boolean).map(Number));
  const logs = [];
  globalThis.window = { __hlLog: (s) => logs.push(s) };
  const { Policy } = await loadPolicy(ver);
  const { info, api } = startEngine(mid);
  const names = api.names();
  const want = (opt('--bots', '') || '').split(',').filter(Boolean);
  const ids = [];
  for (const b of want) {
    let p = /^\d+$/.test(b) ? +b : -1;
    if (p < 0) for (let q = 0; q < info.ku; q++) if (names[q] === b || names[q] === '[APEX] ' + b || (names[q] || '').endsWith(' ' + b)) { p = q; break; }
    if (p < 0) throw new Error('找不到号 ' + b);
    ids.push([b, p]);
  }
  const nm = (q) => (q === NEUTRAL ? '无主地' : q >= info.ku ? 'AI#' + q : (names[q] || '').replace('[APEX] ', '') + '#' + q);
  console.log(`# ${mid} 影子策略（${VERS[ver]}），号：${ids.map(([b, p]) => b + '=' + p).join(' ')}，拍段 ${from}~${to}`);
  // 快进到 from
  let st = api.advance(1);
  while (st[1] === 1 && st[2] !== 2) st = api.advance(1); // 出生阶段
  while (st[0] < from - 1 && st[2] !== 2) st = api.advance(Math.min(200, from - 1 - st[0]));
  const M = new Mirror(info, api);
  const g = M.g;
  // 每个号的编队槽位（策略用 window.__tsbSquadSlot 决定调度相位）：取自本局日志的 [HL-SPAWN*] me=.. slot=..
  const slotOf = new Map();
  try {
    const re = /\[HL-SPAWN[A-Z-]*\] me=(\d+) slot=(\d+)/g;
    const txt = fs.readFileSync(path.join(DATA, mid, 'in_game.log'), 'utf8');
    let mm;
    while ((mm = re.exec(txt))) slotOf.set(+mm[1], +mm[2]);
  } catch (e) { /* 没有日志就用 me%10 */ }
  const pols = ids.map(([b, p]) => ({ b, p, pol: new Policy({}, p), errs: 0, lastErr: '', snap: [], slot: slotOf.has(p) ? slotOf.get(p) : null }));
  // 真实日志（用于保真度自检）
  const traj = loadCsv(path.join(DATA, mid, 'traj.csv'));
  const realTick = new Map();
  for (const r of traj) realTick.set(r.bot + '@' + r.t, r);
  const ev = loadCsv(path.join(DATA, mid, 'events.csv'));
  const realDis = new Map();
  for (const r of ev) if (r.type === 'DISPATCH' || r.type === 'DONATE') realDis.set(r.bot + '@' + r.t, r);
  // 记录「禁止全额出兵」影子锁（isNoFullSend）何时锁上、此后拦掉了多少次出兵（Policy.send L3844~3862）
  for (const S of pols) {
    S.lockAt = null; S.blocked = []; S.probes = []; S.sends = 0;
    const pol = S.pol, origSend = pol.send;
    pol.send = function (gg, target, troops, budgetHint) {
      const guard = this.p.quotaGuardMode > 0 && this.isNoFullSend && troops > 2 && this.shadowQuota < Math.min(0.55 * troops, 0.06 * gg.bal[this.me]);
      const r = budgetHint === undefined ? origSend.call(this, gg, target, troops) : origSend.call(this, gg, target, troops, budgetHint);
      S.sends++;
      if (guard && target !== NEUTRAL) { if (!r) S.blocked.push([gg.t, target, Math.round(troops)]); else S.probes.push([gg.t, target, Math.round(troops)]); }
      return r;
    };
  }
  const rowsOn = has('--rows');
  const rowsOut = [];
  const ourSet = new Set(pols.map((S) => S.p));
  let lastPix = -1;
  const outLines = [];
  const cmp = { nbOk: 0, nbBad: 0, disBoth: 0, disOnlyShadow: 0, disOnlyReal: 0, disSame: 0 };
  const shadowDis = new Map();
  while (st[2] !== 2 && st[0] < to) {
    st = api.advance(1);
    const t = st[0];
    M.light();
    if (every <= 1 || t % every === 0 || lastPix < 0) { M.pixels(); lastPix = t; }
    for (const S of pols) {
      const { pol, p, b } = S;
      if (!g.alive[p]) continue;
      const i0 = M.intents.length, l0 = logs.length;
      let offers = null, safeNone = null;
      const detail = trace || at.has(t);
      const origOffers = pol.offers;
      const capture = detail || (rowsOn && t % 5 === 0);
      if (capture) {
        pol.offers = function (gg) { const r = origOffers.call(this, gg); offers = r; return r; };
      }
      g.me = p;
      if (S.slot !== null) globalThis.window.__tsbSquadSlot = S.slot; else delete globalThis.window.__tsbSquadSlot;
      try { pol.act(g); } catch (e) { S.errs++; S.lastErr = `t=${t} ${String(e && e.stack || e).split('\n').slice(0, 3).join(' | ')}`; }
      if (capture) pol.offers = origOffers;
      if (S.lockAt === null && pol.isNoFullSend) S.lockAt = t;
      if (rowsOn && t % 5 === 0) {
        // 每个行动拍一行：邻居构成、最弱的 AI 邻居、打 AI 时要守的底线、有没有出手
        let nAI = 0, nAIweak = 0, nHum = 0, minFloor = -1, weakLand = 0;
        const coreFrom = pol.p.coreFrom ?? 1500;
        let fl = null;
        try { if (t < coreFrom) fl = pol.floors(g); } catch (e) { fl = null; }
        for (const q of pol.nb) {
          if (!g.alive[q] || !g.terr[q]) continue;
          if (pol.person(g, q)) { nHum++; continue; }
          nAI++;
          if (g.bal[q] < g.terr[q]) { nAIweak++; weakLand += g.terr[q]; }
          let f0 = -1;
          try { f0 = t < coreFrom ? (fl ? pol.floorFor(g, q, fl.floorAt(pol.price(g, q))) : -1) : Math.min(pol.safeAt(g, q), pol.p.oppFloorCap * Math.max(1, g.terr[p])); } catch (e) { f0 = -1; }
          if (f0 >= 0 && (minFloor < 0 || f0 < minFloor)) minFloor = f0;
        }
        const ints2 = M.intents.length - i0;
        // 核心期前、贴着内置 AI、这一拍没出手：底线是被哪一项顶住的（shadow_diag.floorBind）
        let fb = null;
        if (t < coreFrom && nAI > 0 && ints2 === 0) { try { fb = DIAG.floorBind(pol, g, ourSet); } catch (e) { fb = null; } }
        // 核心期、这一拍没有陆攻意图：buyLand 在第一条真人报价上被哪道门拦下（shadow_diag.coreGate）
        let gate = '', gateAI = '';
        if (t >= coreFrom) {
          const kinds = M.intents.slice(i0).map((x) => x.kind);
          if (kinds.includes('attack')) gate = '';
          else if (kinds.includes('donate')) gate = 'donate';
          else if (kinds.includes('boat')) gate = 'boat';
          else if (offers === null) gate = 'nobuy';
          else if (!offers.length) gate = 'nooffer';
          else {
            try {
              const res = DIAG.coreGate(pol, g, offers, ourSet);
              const hit = res.find((r) => pol.person(g, r[0])) || res[0];
              gate = hit ? hit[1] + ':' + hit[0] + (hit[2] ? ':' + hit[2] : '') : 'unreached';
            } catch (e) { gate = 'err'; }
          }
          // 第一条非真人（内置 AI）报价的去向，不管这一拍有没有别的意图；floor 带上是哪一项顶住的
          if (offers && offers.length) {
            try {
              const resA = DIAG.coreGate(pol, g, offers, ourSet);
              const hitA = resA.find((r) => !pol.person(g, r[0]));
              if (hitA) gateAI = hitA[1] + ':' + hitA[0] + (hitA[2] ? ':' + hitA[2] : '');
              else if (offers.some((o) => !pol.person(g, o.q))) gateAI = 'behind:' + offers.find((o) => !pol.person(g, o.q)).q;
            } catch (e) { gateAI = 'err'; }
          }
          // 贴着内置 AI 但报价单里没有它：covered = 在途的兵已经够吃掉它（offers L5096 rawNeed ≤ 0）；
          // slots = 目标数已满 / 没有空槽（L5089）；nobuy = 这一拍 buyLand 没走到报价单（调度、救急等先返回）
          if (gateAI === '' && nAI > 0) {
            try {
              const P = pol.p, base = g.slotBase(p);
              let active = 0;
              for (let i = g.atkCount[p] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== 512) active++;
              let nOffer = 0, nCov = 0, nSlot = 0, qq = -1;
              for (const q of pol.nb) {
                if (!g.alive[q] || !g.terr[q] || pol.person(g, q)) continue;
                const already = g.hasAttack(p, q);
                if (!already && (active >= P.maxTargets || !g.hasFreeSlot(p))) { nSlot++; if (qq < 0) qq = q; continue; }
                const rawNeed = pol.elimCost(g, q) + g.attackTroopsOn(q, p) - g.attackTroopsOn(p, q);
                if (rawNeed <= 0) { nCov++; qq = q; continue; }
                nOffer++; qq = q;
              }
              gateAI = (nOffer ? 'nobuy' : nCov ? 'covered' : nSlot ? 'slots' : 'none') + ':' + qq;
            } catch (e) { gateAI = 'err2'; }
          }
        }
        rowsOut.push([t, b, g.terr[p], g.bal[p], pol.nb.length, nAI, nAIweak, weakLand, nHum, pol.neutral, g.coast[p].length, ints2, Math.round(minFloor), pol.isNoFullSend ? 1 : 0, g.totalAttackTroops(p),
          fb ? fb.bind : '', fb ? fb.ref : '', fb ? Math.round(fb.avail) : '', fb ? Math.round(fb.need) : '', gate, gateAI].join('\t'));
      }
      const ints = M.intents.slice(i0);
      const newLogs = logs.slice(l0);
      for (const L of newLogs) {
        const m = /\[HL-TICK\] t=(\d+) .* nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)/.exec(L);
        if (m) {
          S.snap.push([+m[1], +m[4], +m[5]]);
          const r = realTick.get(b + '@' + m[1]);
          if (r) { if (+r.nb === +m[2] && +r.neut === +m[3]) cmp.nbOk++; else { cmp.nbBad++; if (cmp.nbBad <= 6) outLines.push(`  [自检不一致] ${b} 拍 ${m[1]}：影子 nb=${m[2]} neut=${m[3]}；真实日志 nb=${r.nb} neut=${r.neut}`); } }
        }
        const d = /\[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)\/1024 -> ally=(\d+)/.exec(L);
        if (d) shadowDis.set(b + '@' + d[1], { kind: d[2], pct: +d[3], target: +d[4] });
      }
      if (!quiet && (detail || ints.length)) {
        const B = g.bal[p], L = Math.max(1, g.terr[p]);
        let line = `拍 ${t} ${b}：领土 ${g.terr[p]} 余额 ${fmt(B)} 密度 ${(B / L).toFixed(1)} nb=${pol.nb ? pol.nb.length : '?'} neut=${pol.neutral ?? '?'}`;
        if (ints.length) line += ' ⇒ ' + ints.map((x) => `${x.kind === 'attack' ? '陆攻' : x.kind === 'donate' ? '捐款' : x.kind === 'boat' ? '发船' : x.kind} ${x.kind === 'boat' ? '' : nm(x.target)} ${fmt(x.troops)}（${x.pct}/1024）`).join('；');
        else line += ' ⇒ 不出手';
        outLines.push(line);
        if (detail) {
          try {
            const safe = pol.safeAt ? pol.safeAt(g, -1) : NaN;
            let s = `    底线 safeAt(-1)=${fmt(safe)}（${(safe / L).toFixed(1)}×地）`;
            if (pol.isNoFullSend !== undefined) s += ` isNoFullSend=${pol.isNoFullSend} shadowQuota=${fmt(pol.shadowQuota || 0)}`;
            outLines.push(s);
          } catch (e) { outLines.push('    safeAt 出错：' + String(e).slice(0, 80)); }
          if (t % 5 === 0) {
            const coreFrom = pol.p.coreFrom ?? 1500;
            if (t < coreFrom) outLines.push(...DIAG.diagPre(pol, g, nm));
            else { outLines.push(...DIAG.diagCore(pol, g, nm, offers)); outLines.push(...DIAG.diagDonate(pol, g, nm)); outLines.push(...DIAG.diagBoats(pol, g, nm)); if (has('--water')) outLines.push(...DIAG.diagWater(pol, g, nm)); }
          }
          for (const L2 of newLogs) if (!/HL-TICK/.test(L2)) outLines.push('    日志：' + L2.slice(0, 260));
        }
      }
    }
  }
  // 保真度：调度逐拍对比
  for (const S of pols) {
    for (const [k, v] of shadowDis) {
      if (!k.startsWith(S.b + '@')) continue;
      const r = realDis.get(k);
      if (r) { cmp.disBoth++; if (+r.pct === v.pct && +r.target === v.target) cmp.disSame++; } else cmp.disOnlyShadow++;
    }
    for (const [k] of realDis) {
      if (!k.startsWith(S.b + '@')) continue;
      const t = +k.split('@')[1];
      if (t < from || t > to) continue;
      if (!shadowDis.has(k)) cmp.disOnlyReal++;
    }
  }
  // 保真度：相邻日志快照之间「发令数」的增量，影子 vs 真实日志
  for (const S of pols) {
    for (let i = 1; i < S.snap.length; i++) {
      const [t1, c1, b1] = S.snap[i], [t0, c0, b0] = S.snap[i - 1];
      const r1 = realTick.get(S.b + '@' + t1), r0 = realTick.get(S.b + '@' + t0);
      if (!r1 || !r0) continue;
      const dReal = +r1.cmds - +r0.cmds, dSh = c1 - c0;
      cmp.dc = (cmp.dc || 0) + 1;
      if (dReal === dSh) cmp.dcSame = (cmp.dcSame || 0) + 1;
      else if (Math.abs(dReal - dSh) <= 1) cmp.dcNear = (cmp.dcNear || 0) + 1;
      else if ((cmp.dcBad = (cmp.dcBad || 0) + 1) <= 5) outLines.push(`  [发令数不一致] ${S.b} (${t0},${t1}]：影子 +${dSh}，真实日志 +${dReal}`);
    }
  }
  const outDir = opt('--out', null);
  if (outDir) {
    fs.mkdirSync(outDir, { recursive: true });
    const nameOf = new Map(pols.map((S) => [S.p, S.b]));
    fs.writeFileSync(path.join(outDir, 'intents.tsv'), 't\tp\tbot\tkind\tpct\ttarget\ttroops\n' + M.intents.map((x) => [x.t, x.p, nameOf.get(x.p), x.kind, x.pct, x.target, x.troops].join('\t')).join('\n') + '\n');
    fs.writeFileSync(path.join(outDir, 'logs.txt'), logs.join('\n') + '\n');
    if (rowsOn) fs.writeFileSync(path.join(outDir, 'rows.tsv'), 't\tbot\tterr\tbal\tnb\tnAI\tnAIweak\tweakLand\tnHum\tneut\tcoast\tintents\tfloorAI\tnfs\tatkOut\tbind\tsbRef\tavail\tneed\tgate\tgateAI\n' + rowsOut.join('\n') + '\n');
    fs.writeFileSync(path.join(outDir, 'check.json'), JSON.stringify({ match: mid, ver: VERS[ver], from, to: st[0], ku: info.ku, bots: pols.map((S) => ({ bot: S.b, p: S.p, slot: S.slot, cmds: S.pol.cmds, boats: S.pol.boats, errs: S.errs, lockAt: S.lockAt, blocked: S.blocked, probes: S.probes })), cmp }, null, 1) + '\n');
  }
  for (const l of outLines) console.log(l);
  console.log(`# 自检：相邻快照之间的发令数增量 一致 ${cmp.dcSame || 0} / 差 1 以内 ${cmp.dcNear || 0} / 不一致 ${cmp.dcBad || 0}（共 ${cmp.dc || 0} 段）`);
  console.log(`# 自检：nb/neut 与真实日志一致 ${cmp.nbOk} 点，不一致 ${cmp.nbBad} 点；调度同拍都有 ${cmp.disBoth}（其中对象和比例完全相同 ${cmp.disSame}），只有影子有 ${cmp.disOnlyShadow}，只有真实日志有 ${cmp.disOnlyReal}`);
  for (const S of pols) if (S.errs) console.log(`# ${S.b} 策略运行报错 ${S.errs} 次，最后一次：${S.lastErr.slice(0, 400)}`);
  for (const S of pols) console.log(`# ${S.b} 影子指令计数 cmds=${S.pol.cmds} boats=${S.pol.boats}；isNoFullSend ${S.lockAt === null ? '全程未锁' : '在第 ' + S.lockAt + ' 拍锁上'}，此后被它拦掉的出兵 ${S.blocked.length} 次${S.blocked.length ? '（首次拍 ' + S.blocked[0][0] + '，末次拍 ' + S.blocked[S.blocked.length - 1][0] + '，合计想出 ' + fmt(S.blocked.reduce((a, b) => a + b[2], 0)) + ' 兵）' : ''}，改成 1 兵试探 ${S.probes.length} 次`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
