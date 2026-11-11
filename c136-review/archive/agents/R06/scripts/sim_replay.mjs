#!/usr/bin/env node
// sim_replay.mjs — 用干净模拟器（/agent/repos/c136-data/src/sim）按录像逐拍重演一局，产出全场真值。
//
//   python3 c136-review/agents/R06/scripts/sim_prep.py <matchId>            # 先生成 out/<matchId>/sim_in.json
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/sim_replay.mjs <matchId> [--to T] [--every N] [--trace 玩家:起拍:止拍]
//
// 输出 out/<matchId>/sim_state.json：
//   check     ：日志每条 HL-TICK 快照 (拍, 领土, 兵力) 能否在重演同一拍的全体真人里找到完全相同的玩家 → 重演可信到哪一拍
//   lineId    ：日志行号 → 玩家号（指纹对上的行；r06lib 用它归并身份，不靠名字）
//   ticks / teamLand / teamBal / teamHumans / teamHusk / humans ：每 every 拍的全场状态
//   deaths / deathT / leaveT ：每个真人的阵亡拍、离开拍
//   donations ：录像里每笔捐款在重演中的结果（到账、手续费、收款人当时的领土/兵力/是否空壳）
//   squadCmds ：我方号的陆攻/发船指令是否生效、实发兵、手续费；别人对我方号的陆攻
//   ledger    ：我方每个号每 100 拍的兵力去向账（利息、因顶格/空壳少拿的利息、出兵、打谁花了多少、从谁手里拿了几格、被谁拿走几格、被谁打掉多少兵、捐出/收到）
//   neigh     ：我方每个号每 90 拍的真实邻居（按接壤格数）、身上的在途进攻、自己的在途进攻
//
// 与实机的差别只补了一处：组队局的颜色初始化（见 TeamGame.setupColors 的注释）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeReplay, mapOf } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';
import { Game, MAX_PLAYERS, NEUTRAL, iV } from '/agent/repos/c136-data/src/sim/sim/game.js';
import { loadMap } from '/agent/repos/c136-data/src/sim/sim/map.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../out');
const argv = process.argv.slice(2);
const mid = argv[0];
const opt = (k, d) => (argv.includes(`--${k}`) ? argv[argv.indexOf(`--${k}`) + 1] : d);
const TO = +opt('to', 1e9);
const EVERY = +opt('every', 30);
const TRACE = opt('trace', null) ? opt('trace', '').split(':').map(Number) : null;
if (!mid) {
  console.error('用法：sim_replay.mjs <matchId> [--to T] [--every N] [--trace 玩家:起拍:止拍]');
  process.exit(2);
}
const inp = JSON.parse(fs.readFileSync(path.join(OUT, mid, 'sim_in.json'), 'utf8'));
const d = decodeReplay(fs.readFileSync(inp.replayPath, 'utf8'));
const vu = d.vu;
const { mapIdx, mapSeed } = mapOf(vu);
const map = loadMap(mapIdx, mapSeed);
const H = vu.humanCount;
const squad = new Set(inp.squad);

// ---- 兵力去向账：按 (100 拍窗口, 我方号, 科目, 对方) 累加 ----------------------------------
const LW = 100;
const ledger = new Map();
let simRef = null;
const add = (me, kind, other, v) => {
  if (!v) return;
  const key = `${Math.floor(simRef.t / LW)}|${me}|${kind}|${other}`;
  ledger.set(key, (ledger.get(key) || 0) + v);
};

// 组队局的颜色初始化：实机（引擎 2.17.1 的 ad.dk → aKa）每个玩家只取 1 个随机数（按队色取深浅），
// 模拟器的 setupColors 是单挑局写法（每个内置 AI 取 3 个）。不补这一处，随机数序列错位，
// 内置 AI 的出生点和出兵节奏全都对不上实况。队色表 aKK / aKL 抄自引擎；队号 → 队色序号用 lH（引擎 aDn = lH[fX]）。
const TEAM = inp.nTeams > 0 ? { teams: inp.teams, nTeams: inp.nTeams, botTeams: inp.botTeams } : null;
const LH = inp.lH || [0, 1, 2, 3, 4, 5, 6, 7, 8];
const KK = [[100, 100, 100], [144, 0, 0], [0, 128, 0], [0, 0, 144], [128, 128, 0], [128, 0, 128], [0, 128, 128], [196, 196, 196], [0, 0, 0]];
const KL = [[4, 4, 4, 20], [4, 0, 0, 27], [0, 4, 0, 31], [0, 0, 4, 27], [4, 4, 0, 31], [4, 0, 4, 31], [0, 4, 4, 31], [4, 4, 4, 14], [4, 4, 4, 13]];
const DIAG = !!process.env.R06_DIAG;
const RING = (() => {
  const i = process.argv.indexOf('--ring');
  return i > 0 ? process.argv[i + 1].split(':').map(Number) : null;
})();
const diagSeen = new Map();
const diag = (s) => {
  const k = s.replace(/t=\d+ /, '').replace(/\d+/g, '#');
  const n = (diagSeen.get(k) || 0) + 1;
  diagSeen.set(k, n);
  if (n <= 6) console.log('DIAG ' + s);
};
class TeamGame extends Game {
  setupColors() {
    if (!TEAM || process.env.R06_NO_TEAM_COLORS) return super.setupColors();
    const P = MAX_PLAYERS, rng = this.rng;
    const cols = new Array(P);
    for (let i = P - 1; i >= 0; i--) {
      const tm = i < this.humans ? TEAM.teams[i] : TEAM.botTeams ? 1 + (i % TEAM.nTeams) : 0;
      const ej = LH[tm];
      const lp = iV((KL[ej][3] + 1) * rng.next(), 32768);
      const r = KK[ej][0] + lp * KL[ej][0], gg = KK[ej][1] + lp * KL[ej][1], b = KK[ej][2] + lp * KL[ej][2];
      cols[i] = ((r >> 2) << 12) | ((gg >> 2) << 6) | (b >> 2);
    }
    const h = this.humans, hc = this.humanColors;
    this.humans = P;
    this.humanColors = cols;
    super.setupColors();
    this.humans = h;
    this.humanColors = hc;
  }

  // 以下三个覆盖只做记账，不改任何状态。
  // 诊断用（R06_DIAG=1）：记录走到引擎少见分支的时刻，用来查重演和真实对局从哪开始有出入
  expand(p) {
    if (DIAG) {
      const n = this.front[p].length;
      if (n > 2048) diag(`t=${this.t} 前沿超 2048：玩家 ${p} 前沿 ${n} 格 领土 ${this.terr[p]}`);
    }
    return super.expand(p);
  }

  expandAttack(p, a) {
    const k = this.slotBase(p) + a;
    const tg = this.atkTarget[k];
    const ps = squad.has(p), ts = tg < NEUTRAL && squad.has(tg);
    const rg = RING && this.t >= RING[1] && this.t <= RING[2] && (RING[0] === p || RING[0] === tg);
    if (!ps && !ts && !rg) return super.expandAttack(p, a);
    const tr0 = this.atkTroops[k], b0 = this.bal[p], t0 = this.terr[p], fr0 = this.atkFresh[k];
    const vb0 = tg < NEUTRAL ? this.bal[tg] : 0, vc0 = tg < NEUTRAL ? this.attackTroopsOn(tg, p) : 0, vt0 = tg < NEUTRAL ? this.terr[tg] : 0;
    super.expandAttack(p, a);
    const tr1 = this.hasAttack(p, tg) ? this.attackTroopsOn(p, tg) : 0;
    const spent = tr0 + b0 - (tr1 + this.bal[p]);
    const gained = this.terr[p] - t0;
    if (rg) console.log(`RING t=${this.t} ${p}→${tg} fresh=${fr0} 兵 ${tr0}→${tr1}${this.hasAttack(p, tg) ? '' : '(结束)'} 余额 ${b0}→${this.bal[p]} 得 ${gained} 格（领土 ${this.terr[p]}）｜对方 领土 ${vt0} 兵 ${vb0}→${tg < NEUTRAL ? this.bal[tg] : 0} 反击兵 ${vc0}→${tg < NEUTRAL ? this.attackTroopsOn(tg, p) : 0}`);
    if (ps) {
      add(p, 'spent', tg, spent);
      add(p, 'gain', tg, gained);
    }
    if (ts) {
      add(tg, 'lost', p, gained);
      add(tg, 'dmg', p, vb0 - this.bal[tg] + (vc0 - this.attackTroopsOn(tg, p)));
    }
  }

  endAttack(p, a, troops) {
    if (squad.has(p)) {
      const room = Math.max(0, Math.min(this.terr[p] * 150 - this.bal[p], 1.5e9 - this.bal[p]));
      if (troops > room) add(p, 'capRet', -1, troops - room);
    }
    return super.endAttack(p, a, troops);
  }

  economyTick() {
    if (this.t % 10 !== 9) return super.economyTick();
    const pre = [];
    for (const p of squad) {
      if (!this.alive[p]) continue;
      const b = this.bal[p];
      // 不顶格、不是空壳时本来能拿的利息
      const st = this.state[p];
      this.state[p] = 0;
      this.bal[p] = Math.min(b, this.softCap(p));
      const r0 = this.interestRate(p);
      this.bal[p] = b;
      this.state[p] = st;
      let pot = Math.max(iV(r0 * b, 1e4), 1);
      if (this.t % 100 === 99) pot += this.terr[p];
      pre.push([p, b, pot, st]);
    }
    super.economyTick();
    for (const [p, b, pot, st] of pre) {
      const got = this.bal[p] - b;
      add(p, 'inc', -1, got);
      if (pot > got) add(p, st === 2 ? 'huskLoss' : 'capLoss', -1, pot - got);
    }
  }
}

const g = new TeamGame({
  map, humans: H, players: vu.playerCount, difficulty: H > 1 ? 0 : vu.botDifficultyValue, spawnSeed: vu.spawningSeed,
  selectableSpawn: !!vu.selectableSpawn, battleRoyaleMode: vu.battleRoyaleMode,
  humanColors: vu.colorsData ? Array.from(vu.colorsData.subarray(0, H)) : [0],
  teams: inp.teams, nTeams: inp.nTeams, botTeams: inp.botTeams,
});
simRef = g;
g.me = vu.selectedPlayer;
const donations = [];
const squadCmds = [];
const leaveT = {};
let rejected = 0;

const execCmd = (c) => {
  const { id, player, dX, dZ } = c;
  if (id === 0) {
    g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false);
  } else if (id === 1) {
    const B0 = g.bal[player];
    const ok = g.attack(dX, dZ, player);
    if (!ok) rejected++;
    const tg = Math.min(dZ, NEUTRAL);
    if (squad.has(player) || squad.has(dZ)) {
      squadCmds.push({ t: g.t, k: 'atk', p: player, to: dZ, pct: dX, ok: ok ? 1 : 0, B0, sent: ok ? g.attackTroopsTmp : 0, fee: ok ? g.attackFeeTmp : 0,
        toTerr: dZ < NEUTRAL ? g.terr[dZ] : 0, toBal: dZ < NEUTRAL ? g.bal[dZ] : 0, myTerr: g.terr[player] });
    }
    if (ok && squad.has(player)) {
      add(player, 'atkOut', tg < NEUTRAL && !g.alive[tg] ? NEUTRAL : tg, g.attackTroopsTmp);
      add(player, 'fee', -1, g.attackFeeTmp);
    }
  } else if (id === 2) {
    const B0 = g.bal[player], R0 = g.bal[dZ], RT = g.terr[dZ];
    const st = g.state[dZ];
    const onRecv = g.alive[dZ] ? g.attackersOf(dZ).map((a) => [a, g.attackTroopsOn(a, dZ)]) : [];
    const ok = g.donate(dX, dZ, player);
    if (!ok) rejected++;
    const fee = ok ? Math.floor((64 * B0) / 1024) : 0;
    const delivered = ok ? B0 - fee - g.bal[player] : 0;
    donations.push({ t: g.t, from: player, to: dZ, pct: dX, ok: ok ? 1 : 0, B0, fee, delivered, toLeft: st === 2 ? 1 : 0, toTerr: RT, toBal: R0, fromTerr: g.terr[player], onRecv });
    if (ok) {
      if (squad.has(player)) {
        add(player, 'donOut', dZ, delivered);
        add(player, 'donFee', -1, fee);
      }
      if (squad.has(dZ)) add(dZ, 'donIn', player, delivered);
    }
  } else if (id === 3) {
    const B0 = g.bal[player];
    const ok = g.boat(dX, dZ >> 3, dZ & 7, player);
    if (!ok) rejected++;
    if (squad.has(player)) {
      squadCmds.push({ t: g.t, k: 'boat', p: player, pct: dX, ok: ok ? 1 : 0, B0, sent: ok ? g.attackTroopsTmp : 0, fee: ok ? g.attackFeeTmp : 0, cell: dZ >> 3, myTerr: g.terr[player] });
      if (ok) {
        add(player, 'boatOut', -1, g.attackTroopsTmp);
        add(player, 'fee', -1, g.attackFeeTmp);
      }
    }
  } else if (id === 4) {
    if (dX === 849) g.recall(dZ, player);
    else g.chase(dX, dZ, player);
  } else if (id === 5) {
    if (dX !== 513) {
      const b0 = g.bal[player];
      g.retreat(dX, player);
      if (squad.has(player)) squadCmds.push({ t: g.t, k: 'retreat', p: player, to: dX, ok: 1, B0: b0, sent: g.bal[player] - b0, fee: 0 });
    }
  } else if (id === 8 || id === 9) {
    if (!(player in leaveT)) leaveT[player] = { t: g.spawnPhase ? 0 : g.t, id, terr: g.terr[player], bal: g.bal[player], alive: g.alive[player] };
    if (g.spawnPhase) {
      g.eliminate(player);
      let n = g.aliveCount;
      for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
      g.aliveCount = n;
    } else g.leave(player);
  }
};

let iv = 0, iw = 0, ix = 0, iy = 0;
const step = () => {
  if (iv >= d.ja.length) return false;
  const jZ = d.ja[iv];
  if (d.jY[iv]) {
    for (let a1 = iw; a1 < iw + jZ; a1++) execCmd(d.cmds[a1]);
    iw += jZ;
    iv++;
  } else if (++ix >= jZ) {
    iv++;
    ix = 0;
  }
  return true;
};
if (vu.selectableSpawn) {
  const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
  while (iy <= jJ) {
    if (!step()) break;
    if (iy === jJ) g.endSpawnPhase();
    iy++;
  }
}
const spawnBox = {};
for (const p of squad) spawnBox[p] = [g.x0[p], g.y0[p], g.x1[p], g.y1[p], g.terr[p]];

// 日志快照按拍分组
const checksAt = new Map();
for (const c of inp.checks) {
  if (!checksAt.has(c.t)) checksAt.set(c.t, []);
  checksAt.get(c.t).push(c);
}
const checkRows = [];
const lineId = {};
const lineAmb = {};
const deathT = new Int32Array(H).fill(-1);
const lastAtk = Array.from({ length: H }, () => new Map());
const ticks = [];
const teamLand = [], teamBal = [], teamHumans = [], teamHusk = [];
const hum = Array.from({ length: H }, () => ({ terr: [], bal: [] }));
const nT = g.nTeams || inp.nTeams;
const t0 = Date.now();

const sample = () => {
  ticks.push(g.t);
  const tl = new Array(nT + 1).fill(0), tb = new Array(nT + 1).fill(0), th = new Array(nT + 1).fill(0), tk = new Array(nT + 1).fill(0);
  for (let i = g.aliveCount - 1; i >= 0; i--) {
    const p = g.aliveList[i];
    const tm = g.teams[p];
    tl[tm] += g.terr[p];
    tb[tm] += g.bal[p];
    if (p < H) {
      if (g.state[p] === 2) tk[tm] += g.terr[p];
      else th[tm]++;
    }
  }
  teamLand.push(tl);
  teamBal.push(tb);
  teamHumans.push(th);
  teamHusk.push(tk);
  for (let p = 0; p < H; p++) {
    hum[p].terr.push(g.alive[p] ? g.terr[p] : 0);
    hum[p].bal.push(g.alive[p] ? g.bal[p] : 0);
  }
};

const trackAttackers = () => {
  for (let i = g.aliveCount - 1; i >= 0; i--) {
    const a = g.aliveList[i];
    const b = g.slotBase(a);
    for (let k = g.atkCount[a] - 1; k >= 0; k--) {
      const tg = g.atkTarget[b + k];
      if (tg < H) {
        const m = lastAtk[tg];
        const e = m.get(a);
        if (e) {
          e.t = g.t;
          e.n++;
          e.sum += g.atkTroops[b + k];
        } else m.set(a, { t0: g.t, t: g.t, n: 1, sum: g.atkTroops[b + k] });
      }
    }
  }
};

// 我方每个号的真实邻居（按接壤格数）
const neigh = [];
const NE = 90;
const sampleNeigh = () => {
  const d4 = g.dir4, px = g.px, own = g.own;
  for (const p of squad) {
    if (!g.alive[p]) continue;
    const cnt = new Map();
    let neut = 0, cells = 0;
    const B = g.border[p];
    for (let i = 0; i < B.length; i++) {
      const b = B[i];
      if (px[b] < 17 || own[b] !== p) continue;
      cells++;
      for (let q = 0; q < 4; q++) {
        const c = b + d4[q];
        const v = px[c];
        if (v === 1) neut++;
        else if (v >= 16 && own[c] !== p) cnt.set(own[c], (cnt.get(own[c]) || 0) + 1);
      }
    }
    const nb = [...cnt.entries()].sort((x, y) => y[1] - x[1]).slice(0, 8).map(([q, n]) => [q, n, g.terr[q], g.bal[q], g.teams[q], q < H ? (g.state[q] === 2 ? 2 : 1) : 0]);
    const sb = g.slotBase(p);
    const mine = [];
    for (let k = 0; k < g.atkCount[p]; k++) mine.push([g.atkTarget[sb + k], g.atkTroops[sb + k]]);
    const on = g.attackersOf(p).map((a) => [a, g.attackTroopsOn(a, p), g.teams[a]]);
    neigh.push({ t: g.t, p, terr: g.terr[p], bal: g.bal[p], st: g.state[p], border: cells, coast: g.coast[p] ? g.coast[p].length : 0, neut, nb, mine, on, boats: g.boatCount[p], nbAll: cnt.size });
  }
};

const deaths = [];
sample();
while (!g.over && g.t < TO) {
  const cs = checksAt.get(g.t);
  if (cs) {
    for (const c of cs) {
      // 日志只会是我方号写的：只在我方号里找指纹；同一拍有多个我方号状态完全相同（开局头几十拍）时记为歧义，交给名字去定
      let hit = -1, near = -1, nearD = Infinity;
      const hits = [];
      for (const p of squad) {
        if (!g.alive[p]) continue;
        if (g.terr[p] === c.terr && g.bal[p] === c.bal) hits.push(p);
        const dd = Math.abs(g.terr[p] - c.terr) / Math.max(1, c.terr) + Math.abs(g.bal[p] - c.bal) / Math.max(1, c.bal);
        if (dd < nearD) { nearD = dd; near = p; }
      }
      if (hits.length === 1) { hit = hits[0]; lineId[c.line] = hit; } else if (hits.length > 1) { hit = hits[0]; lineAmb[c.line] = hits; }
      checkRows.push({ line: c.line, name: c.name, t: c.t, terr: c.terr, bal: c.bal, p: hit, near, nearTerr: near >= 0 ? g.terr[near] : 0, nearBal: near >= 0 ? g.bal[near] : 0, nearD: near >= 0 ? +nearD.toFixed(4) : -1 });
    }
  }
  if (g.t % NE === 0) sampleNeigh();
  if (!step()) break;
  if (g.t % 5 === 0) trackAttackers();
  g.tick();
  if (TRACE && g.t >= TRACE[1] && g.t <= TRACE[2]) {
    const p = TRACE[0], b = g.slotBase(p);
    const mine = [];
    for (let k = 0; k < g.atkCount[p]; k++) mine.push(`${g.atkTarget[b + k]}:${g.atkTroops[b + k]}`);
    const on = g.attackersOf(p).map((a) => `${a}:${g.attackTroopsOn(a, p)}`);
    console.log(`TR t=${g.t} terr=${g.terr[p]} bal=${g.bal[p]} peak=${g.peak[p]} myAtk=[${mine.join(',')}] onMe=[${on.join(',')}] boats=${g.boatCount[p]}`);
  }
  for (let p = 0; p < H; p++) {
    if (deathT[p] < 0 && g.alive[p] === 0) {
      deathT[p] = g.t;
      const at = [...lastAtk[p].entries()].filter(([, e]) => e.t >= g.t - 200).map(([a, e]) => ({ a, team: g.teams[a], isHuman: a < H ? 1 : 0, left: g.state[a] === 2 ? 1 : 0, from: e.t0, last: e.t, avgTroops: Math.round(e.sum / e.n) }))
        .sort((x, y) => y.avgTroops * (y.last - y.from + 5) - x.avgTroops * (x.last - x.from + 5)).slice(0, 5);
      deaths.push({ p, t: g.t, attackers: at });
    }
  }
  if (g.t % EVERY === 0) sample();
}
sample();

// 核对汇总
const allN = checkRows.length;
const exact = checkRows.filter((r) => r.p >= 0).length;
const badRows = checkRows.filter((r) => r.p < 0).sort((a, b) => a.t - b.t);
const firstBadAll = badRows.length ? badRows[0].t : -1;
const led = [];
for (const [k, v] of ledger) {
  const [w, me, kind, other] = k.split('|');
  led.push([+w * LW, +me, kind, +other, v]);
}
const finalBots = {};
for (const p of squad) finalBots[p] = { alive: g.alive[p], st: g.state[p], terr: g.terr[p], bal: g.bal[p], team: g.teams[p] };
const out = {
  matchId: mid, replayPath: inp.replayPath, map: `${mapIdx}_${mapSeed}`, W: g.W, Hmap: g.H, land: g.land, humans: H, nTeams: nT, endT: g.t, over: g.over ? 1 : 0,
  wallMs: Date.now() - t0, rejectedCmds: rejected,
  check: { points: allN, exact, firstBad: firstBadAll, bad: badRows.slice(0, 400) },
  lineId, lineAmb,
  every: EVERY, ticks, teamLand, teamBal, teamHumans, teamHusk, hum,
  teams: Array.from(g.teams.subarray(0, MAX_PLAYERS)),
  deathT: Array.from(deathT), deaths, leaveT, donations, squadCmds, spawnBox,
  ledgerWindow: LW, ledger: led, neighEvery: NE, neigh, finalBots,
};
fs.writeFileSync(path.join(OUT, mid, 'sim_state.json'), JSON.stringify(out));
console.log(`${mid}: 重演到 t=${g.t}（over=${g.over ? 1 : 0}），耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s，录像里的陆攻/发船/捐款指令在重演中没生效 ${rejected} 条`);
console.log(`日志快照 ${allN} 条，在重演同一拍找到 (领土, 兵力) 完全相同的真人 ${exact} 条（${allN ? (100 * exact / allN).toFixed(1) : 0}%），第一条对不上的拍 ${firstBadAll}`);
for (const r of badRows.slice(0, 8)) console.log(`  对不上：t=${r.t} [${r.name}] 日志 领土 ${r.terr} 兵 ${r.bal} ｜ 最接近的我方号 me=${r.near} 重演 领土 ${r.nearTerr} 兵 ${r.nearBal}`);
