#!/usr/bin/env node
// sim_replay.mjs — 用干净模拟器（/agent/repos/c136-data/src/sim）按录像逐拍重演一局，产出全场真值。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/sim_replay.mjs <matchId> [--to T] [--every N]
//
// 输入：out/<matchId>/sim_in.json（sim_prep.py 生成：录像路径、每个真人的队号、日志快照核对点）
// 输出：out/<matchId>/sim_state.json
//   check     ：日志快照（HL-TICK 的 terr/bal）与重演同一拍状态的逐点对比 → 重演是否可信、从哪一拍开始偏
//   ticks/teamLand/teamBal/humans ：每 every 拍全体真人的领土与兵力、各队合计
//   deaths    ：每个真人的阵亡拍 + 死前 200 拍对它有在途进攻的玩家
//   donations ：每笔捐款指令在重演里的结果（到账、手续费、收款人是否已离开、收款人领土/兵力）
//   squadCmds ：我方号的陆攻/发船（实发兵、手续费、当时余额），以及别人对我方号的陆攻
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeReplay, mapOf } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';
import { Game, MAX_PLAYERS, iV } from '/agent/repos/c136-data/src/sim/sim/game.js';
import { loadMap } from '/agent/repos/c136-data/src/sim/sim/map.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../out');
const argv = process.argv.slice(2);
const mid = argv[0];
const opt = (k, d) => (argv.includes(`--${k}`) ? argv[argv.indexOf(`--${k}`) + 1] : d);
const TO = +opt('to', 1e9);
const EVERY = +opt('every', 30);
const TRACE = opt('trace', null) ? opt('trace', '').split(':').map(Number) : null; // 调试：--trace 玩家:起拍:止拍，逐拍打印该玩家状态
if (!mid) {
  console.error('用法：sim_replay.mjs <matchId> [--to T] [--every N]');
  process.exit(2);
}
const inp = JSON.parse(fs.readFileSync(path.join(OUT, mid, 'sim_in.json'), 'utf8'));
const d = decodeReplay(fs.readFileSync(inp.replayPath, 'utf8'));
const vu = d.vu;
const { mapIdx, mapSeed } = mapOf(vu);
const map = loadMap(mapIdx, mapSeed);
const H = vu.humanCount;

// 组队局的颜色初始化：实机（引擎 ad.dk → aKa）每个玩家只取 1 个随机数（按队色取深浅），
// 模拟器的 setupColors 是单挑局写法（每个内置 AI 取 3 个）。不改这一处，随机数序列错位，
// 内置 AI 的出生点和出兵节奏全都对不上实况。这里按引擎 2.17.1 的 aKK / aKL 表补上。
const TEAM = inp.nTeams > 0 ? { teams: inp.teams, nTeams: inp.nTeams, botTeams: inp.botTeams } : null;
const LH = inp.lH || [0, 1, 2, 3, 4, 5, 6, 7, 8];
const KK = [[100, 100, 100], [144, 0, 0], [0, 128, 0], [0, 0, 144], [128, 128, 0], [128, 0, 128], [0, 128, 128], [196, 196, 196], [0, 0, 0]];
const KL = [[4, 4, 4, 20], [4, 0, 0, 27], [0, 4, 0, 31], [0, 0, 4, 27], [4, 4, 0, 31], [4, 0, 4, 31], [0, 4, 4, 31], [4, 4, 4, 14], [4, 4, 4, 13]];
class TeamGame extends Game {
  setupColors() {
    if (!TEAM || process.env.R06_NO_TEAM_COLORS) return super.setupColors();
    const P = MAX_PLAYERS, rng = this.rng;
    const cols = new Array(P);
    for (let i = P - 1; i >= 0; i--) {
      const tm = i < this.humans ? TEAM.teams[i] : TEAM.botTeams ? 1 + (i % TEAM.nTeams) : 0;
      const ej = LH[tm]; // 队号 → 队色序号（引擎 aDn = lH[fX]）
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
}
const g = new TeamGame({
  map, humans: H, players: vu.playerCount, difficulty: H > 1 ? 0 : vu.botDifficultyValue, spawnSeed: vu.spawningSeed,
  selectableSpawn: !!vu.selectableSpawn, battleRoyaleMode: vu.battleRoyaleMode,
  humanColors: vu.colorsData ? Array.from(vu.colorsData.subarray(0, H)) : [0],
  teams: inp.teams, nTeams: inp.nTeams, botTeams: inp.botTeams,
});
g.me = vu.selectedPlayer;
const squad = new Set(inp.squad);
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
    if (squad.has(player) || squad.has(dZ)) {
      squadCmds.push({ t: g.t, k: 'atk', p: player, to: dZ, pct: dX, ok: ok ? 1 : 0, B0, sent: ok ? g.attackTroopsTmp : 0, fee: ok ? g.attackFeeTmp : 0,
        toTerr: dZ < 512 ? g.terr[dZ] : 0, toBal: dZ < 512 ? g.bal[dZ] : 0 });
    }
  } else if (id === 2) {
    const B0 = g.bal[player], R0 = g.bal[dZ], RT = g.terr[dZ];
    const st = g.state[dZ];
    const ok = g.donate(dX, dZ, player);
    if (!ok) rejected++;
    donations.push({ t: g.t, from: player, to: dZ, pct: dX, ok: ok ? 1 : 0, B0, fee: ok ? Math.floor((64 * B0) / 1024) : 0, delivered: ok ? g.bal[dZ] - R0 : 0,
      toLeft: st === 2 ? 1 : 0, toTerr: RT, toBal: R0, fromTerr: g.terr[player] });
  } else if (id === 3) {
    const B0 = g.bal[player];
    const ok = g.boat(dX, dZ >> 3, dZ & 7, player);
    if (!ok) rejected++;
    if (squad.has(player)) squadCmds.push({ t: g.t, k: 'boat', p: player, pct: dX, ok: ok ? 1 : 0, B0, sent: ok ? g.attackTroopsTmp : 0, fee: ok ? g.attackFeeTmp : 0 });
  } else if (id === 4) {
    if (dX === 849) g.recall(dZ, player);
    else g.chase(dX, dZ, player);
  } else if (id === 5) {
    if (dX !== 513) g.retreat(dX, player);
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

// 核对点按拍分组
const checksAt = new Map();
for (const c of inp.checks) {
  if (!checksAt.has(c.t)) checksAt.set(c.t, []);
  checksAt.get(c.t).push(c);
}
const checkRows = [];
const lineId = {};
const deathT = new Int32Array(H).fill(-1);
const lastAtk = Array.from({ length: H }, () => new Map()); // 对每个真人：最近看到的进攻者 → {t, troops 累计采样}
const ticks = [];
const teamLand = [], teamBal = [];
const hum = Array.from({ length: H }, () => ({ terr: [], bal: [] }));
const nT = g.nTeams || inp.nTeams;
const t0 = Date.now();

const sample = () => {
  ticks.push(g.t);
  const tl = new Array(nT + 1).fill(0), tb = new Array(nT + 1).fill(0);
  for (let i = g.aliveCount - 1; i >= 0; i--) {
    const p = g.aliveList[i];
    tl[g.teams[p]] += g.terr[p];
    tb[g.teams[p]] += g.bal[p];
  }
  teamLand.push(tl);
  teamBal.push(tb);
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

const deaths = [];
sample();
while (!g.over && g.t < TO) {
  const cs = checksAt.get(g.t);
  if (cs) {
    for (const c of cs) {
      let hit = -1, near = -1, nearD = Infinity;
      for (let p = 0; p < H; p++) {
        if (!g.alive[p]) continue;
        if (g.terr[p] === c.terr && g.bal[p] === c.bal) { hit = p; break; }
        if (squad.has(p)) {
          const dd = Math.abs(g.terr[p] - c.terr) / Math.max(1, c.terr) + Math.abs(g.bal[p] - c.bal) / Math.max(1, c.bal);
          if (dd < nearD) { nearD = dd; near = p; }
        }
      }
      if (hit >= 0) lineId[c.line] = hit;
      checkRows.push({ line: c.line, name: c.name, t: c.t, terr: c.terr, bal: c.bal, p: hit, near, nearTerr: near >= 0 ? g.terr[near] : 0, nearBal: near >= 0 ? g.bal[near] : 0, nearD: near >= 0 ? +nearD.toFixed(4) : -1 });
    }
  }
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

// 核对汇总：日志每条快照能不能在重演的同一拍找到 (领土, 兵力) 完全相同的真人
const allN = checkRows.length;
const exact = checkRows.filter((r) => r.p >= 0).length;
const badRows = checkRows.filter((r) => r.p < 0).sort((a, b) => a.t - b.t);
const firstBadAll = badRows.length ? badRows[0].t : -1;
const out = {
  matchId: mid, replayPath: inp.replayPath, map: `${mapIdx}_${mapSeed}`, W: g.W, Hmap: g.H, land: g.land, humans: H, nTeams: nT, endT: g.t, over: g.over ? 1 : 0,
  wallMs: Date.now() - t0, rejectedCmds: rejected,
  check: { points: allN, exact, firstBad: firstBadAll, bad: badRows.slice(0, 400) },
  lineId,
  every: EVERY, ticks, teamLand, teamBal, humans: hum,
  deathT: Array.from(deathT), deaths, leaveT, donations, squadCmds,
  final: { teamLand: teamLand[teamLand.length - 1], winner: g.winner ?? null },
};
fs.writeFileSync(path.join(OUT, mid, 'sim_state.json'), JSON.stringify(out));
console.log(`${mid}: 重演到 t=${g.t}（over=${g.over ? 1 : 0}），耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s，录像指令在重演里被拒 ${rejected} 条`);
console.log(`日志快照 ${allN} 条，在重演同一拍找到 (领土, 兵力) 完全相同的真人 ${exact} 条（${allN ? (100 * exact / allN).toFixed(1) : 0}%），第一条对不上的拍 ${firstBadAll}`);
for (const r of badRows.slice(0, 12)) console.log(`  对不上：t=${r.t} [${r.name}] 日志 领土 ${r.terr} 兵 ${r.bal} ｜ 最接近的我方号 me=${r.near} 重演 领土 ${r.nearTerr} 兵 ${r.nearBal}`);
