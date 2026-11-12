// match.mjs — 把一个对局包变成可以重演的世界：录像解码、分队、我方席位、逐拍执行录像指令。
//
// 只读 /agent/repos/c136-data/bundles/<局>/ 下的 replay.txt、in_game.log、results.csv；我方席位先查 packs/index.json
//（R06 用日志快照指纹核过的名单），没有就按日志的 [HL-GAME-INIT] me= 取。
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { DATA, SIM, REPLAY_LIB, TGame, assignTeams, teamOpts, NEUTRAL, P_INNER, T_LAND, MAX_PLAYERS, iV } from './tgame.mjs';

const { decodeReplay, mapOf } = REPLAY_LIB;
const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SIMV2 = path.resolve(HERE, '..');
export const BUNDLES = path.join(DATA, 'bundles');

// 同一场对局、录像更长的包（R06 r06lib.py 的 PEER_REPLAY）
export const PEER_REPLAY = { B039: 'A058', B038: 'A057' };

// 地图：共享目录没有这局的种子地图时，读 sim-v2/maps/ 下从真引擎导出的同格式文件
export function loadMapAny(index, seed) {
  try { return SIM.loadMap(index, seed); } catch (e) {
    const file = path.join(SIMV2, 'maps', `${index}_${seed}.bin.gz`);
    if (!fs.existsSync(file)) throw new Error(`没有地图 ${index}_${seed}：共享目录和 sim-v2/maps 都没有`);
    const buf = zlib.gunzipSync(fs.readFileSync(file));
    if (buf.toString('latin1', 0, 4) !== 'TMAP') throw new Error(`bad map file ${file}`);
    const w = buf.readUInt16LE(4), h = buf.readUInt16LE(6), n = w * h;
    const type = new Uint8Array(buf.buffer, buf.byteOffset + 8, n).slice();
    const id = new Uint16Array(n);
    let land = 0;
    for (let p = 0; p < n; p++) { id[p] = buf.readUInt16LE(8 + n + 2 * p); if (type[p] === T_LAND) land++; }
    return { index, seed, w, h, type, id, land, mountains: [3, 7, 9, 21, 25].includes(index) };
  }
}

let PACKS = null;
function packs() {
  if (PACKS === null) {
    const f = path.join(SIMV2, 'packs', 'index.json');
    PACKS = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {};
  }
  return PACKS;
}

// 日志：号名 → 席位号（[HL-GAME-INIT] me=）、编队槽位（[HL-SPAWN] / [HL-SPAWN-BACKEND] 的 slot=）、快照（[HL-TICK]）
export function readLog(mid) {
  const file = path.join(BUNDLES, mid, 'in_game.log');
  const out = { seatOf: new Map(), slotOf: new Map(), snaps: [], cmdsAt: [], dispatch: [] };
  if (!fs.existsSync(file)) return out;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    let m = line.match(/\[([^\]]+)\] \[HL-GAME-INIT\].*\bme=(\d+)/);
    if (m) { if (!out.seatOf.has(m[1])) out.seatOf.set(m[1], +m[2]); continue; }
    // 捐款发出的日志（c116 系）：策略在本机第 t 拍调了 g.donate 并得到 true
    m = line.match(/\[([^\]]+)\] \[HL-DISPATCH\] t=(\d+) \S+ pct=(\d+)\/1024 -> ally=(\d+)/);
    if (m) { out.dispatch.push({ label: m[1], t: +m[2], pct: +m[3], to: +m[4] }); continue; }
    m = line.match(/\[([^\]]+)\] \[HL-SPAWN(?:-BACKEND)?\] me=(\d+) slot=(\d+)/);
    if (m) {
      if (!out.seatOf.has(m[1])) out.seatOf.set(m[1], +m[2]);
      if (!out.slotOf.has(+m[2])) out.slotOf.set(+m[2], +m[3]);
      continue;
    }
    m = line.match(/\[([^\]]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(\d+)/);
    if (m) {
      const c = line.match(/\bcmds=(\d+)/);
      out.snaps.push({ label: m[1], t: +m[2], terr: +m[3], bal: +m[4], cmds: c ? +c[1] : -1 });
    }
  }
  return out;
}

export function loadMatch(mid, opts = {}) {
  const pk = packs()[mid] || {};
  const replayMid = opts.replayFrom || pk.replay || PEER_REPLAY[mid] || mid;
  const replayPath = path.join(BUNDLES, replayMid, 'replay.txt');
  if (!fs.existsSync(replayPath)) throw new Error(`没有录像 ${replayPath}`);
  const d = decodeReplay(fs.readFileSync(replayPath, 'utf8'));
  const vu = d.vu;
  const H = vu.humanCount;
  const names = new Array(MAX_PLAYERS).fill('');
  if (vu.playerNamesData) for (let p = 0; p < H; p++) names[p] = String(vu.playerNamesData[p] ?? '');
  if (pk.aiNames) for (const [p, nm] of Object.entries(pk.aiNames)) names[+p] = nm;
  const colors = vu.colorsData ? Array.from(vu.colorsData).slice(0, H) : new Array(H).fill(0);
  const teamGame = vu.gameMode !== 0 && vu.numberTeams >= 2;
  const ta = teamGame ? assignTeams(names, colors, H, vu.numberTeams) : null;
  const { mapIdx, mapSeed } = mapOf(vu);
  const map = loadMapAny(mapIdx, mapSeed);
  const log = readLog(mid);
  let squad;
  if (opts.squad) squad = opts.squad.slice();
  else if (pk.squad) squad = pk.squad.slice();
  else squad = [...new Set(log.seatOf.values())].filter((p) => p < H).sort((a, b) => a - b);
  // 槽位：日志里有就用，没有的按席位号顺序补到没被占的号上
  const slotOf = new Map();
  const used = new Set();
  for (const p of squad) {
    const s = pk.slots && pk.slots[p] !== undefined ? pk.slots[p] : log.slotOf.get(p);
    if (s !== undefined && !used.has(s)) { slotOf.set(p, s); used.add(s); }
  }
  let next = 0;
  for (const p of squad) {
    if (slotOf.has(p)) continue;
    while (used.has(next)) next++;
    slotOf.set(p, next); used.add(next);
  }
  // 录像一共多少拍（出生阶段的步不算）；每个真人最后一条指令（离场除外）的执行拍、离场拍
  const spawnSteps = vu.selectableSpawn ? (H <= 2 ? 30 : H <= 50 ? 40 : 50) + 1 : 0;
  let units = 0, iw = 0;
  const lastCmd = new Map(), leaveT = new Map();
  for (let i = 0; i < d.ja.length; i++) {
    if (d.jY[i]) {
      const tick = units - spawnSteps;
      for (let a = iw; a < iw + d.ja[i]; a++) {
        const c = d.cmds[a];
        if (c.player >= H || tick < 0) continue;
        if (c.id === 8 || c.id === 9) { if (!leaveT.has(c.player)) leaveT.set(c.player, tick); } else if (c.id !== 6 && c.id !== 7) lastCmd.set(c.player, tick);
      }
      iw += d.ja[i];
      units += 1;
    } else units += d.ja[i];
  }
  // 页面寿命：这个席位的页面最后一次有动静的本机拍 = max(日志最后一条快照 + 89, 录像里最后一条指令)。之后页面没再算过。
  const lastSnap = new Map();
  for (const s of log.snaps) {
    const p = log.seatOf.get(s.label);
    if (p !== undefined && (lastSnap.get(p) ?? -1) < s.t) lastSnap.set(p, s.t);
  }
  const pageEnd = new Map();
  for (const p of squad) pageEnd.set(p, Math.max(lastSnap.has(p) ? lastSnap.get(p) + 89 : -1, lastCmd.get(p) ?? -1));
  // 页面在席位还活着的时候就停摆了（doomed）：页面寿命早于席位在真局里出局的拍（没有出局记录的按录像末拍）
  const doomed = new Set();
  if (pk.deathT) {
    const endT = Math.max(0, units - spawnSteps);
    for (const p of squad) {
      const dt = pk.deathT[p] ?? -1;
      if (pageEnd.get(p) + 1 < (dt >= 0 ? dt : endT - 90)) doomed.add(p);
    }
  }
  return {
    mid, replayMid, d, vu, H, names, colors, ta, teamGame, map, mapKey: `${mapIdx}_${mapSeed}`, squad, slotOf, log,
    replayTicks: Math.max(0, units - spawnSteps), spawnSteps, pageEnd, leaveT, lastCmd, doomed, deathT: pk.deathT || null,
  };
}

export function buildWorld(M, extra = {}) {
  const { vu, H } = M;
  const g = new TGame({
    map: M.map,
    humans: H,
    players: vu.playerCount,
    difficulty: H > 1 ? 0 : vu.botDifficultyValue,
    spawnSeed: vu.spawningSeed,
    selectableSpawn: !!vu.selectableSpawn,
    battleRoyaleMode: vu.battleRoyaleMode,
    humanColors: vu.colorsData ? Array.from(vu.colorsData.subarray(0, H)) : [0],
    passableWater: vu.passableWater,
    passableMountains: vu.passableMountains,
    names: M.names,
    ...teamOpts(M.ta, H),
    ...extra,
  });
  g.me = vu.selectedPlayer;
  return g;
}

// 执行一条录像指令。返回 { ok, rec }：ok = 生效；rec = 引擎会不会把它记进录像（陆攻：过了报价 / 目标 / 槽位检查）。
export function execRecorded(g, c) {
  const { id, player, dX, dZ } = c;
  if (id === 0) return { ok: g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false), rec: true };
  if (id === 1) {
    const n0 = g.landAttacks[player];
    const ok = g.attack(dX, dZ, player);
    return { ok, rec: g.landAttacks[player] !== n0 };
  }
  if (id === 2) { const ok = g.donate(dX, dZ, player); return { ok, rec: ok }; }
  if (id === 3) { const ok = g.boat(dX, dZ >> 3, dZ & 7, player); return { ok, rec: ok }; }
  if (id === 4) { const ok = dX === 849 ? g.recall(dZ, player) : g.chase(dX, dZ, player); return { ok, rec: ok }; }
  if (id === 5) { const ok = dX !== 513 ? g.retreat(dX, player) : false; return { ok, rec: ok }; }
  if (id === 10) { const ok = g.mountainCmd(player, dX >> 10, dZ, dX % 1024); return { ok, rec: ok }; }
  if (id === 8 || id === 9) {
    if (g.spawnPhase) {
      g.eliminate(player);
      let n = g.aliveCount;
      for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
      g.aliveCount = n;
    } else g.leave(player);
    return { ok: true, rec: true };
  }
  return { ok: false, rec: false };
}

// 逐拍放录像。step() 执行当前拍的录像指令（exec 回调决定怎么执行），录像放完返回 false。
export class ReplayStepper {
  constructor(M, g, exec) {
    this.d = M.d;
    this.H = M.H;
    this.g = g;
    this.exec = exec || ((c) => execRecorded(g, c));
    this.iv = 0; this.iw = 0; this.ix = 0; this.iy = 0;
  }

  step() {
    const d = this.d;
    if (this.iv >= d.ja.length) return false;
    const jZ = d.ja[this.iv];
    if (d.jY[this.iv]) {
      for (let a1 = this.iw; a1 < this.iw + jZ; a1++) this.exec(d.cmds[a1]);
      this.iw += jZ;
      this.iv++;
    } else if (++this.ix >= jZ) {
      this.iv++;
      this.ix = 0;
    }
    return true;
  }

  // 出生阶段：前 jJ+1 步；最后一步之后引擎给没选点的人随机落子。onStep(步号) 在每一步的录像指令执行之后调用。
  runSpawnPhase(onStep) {
    if (!this.d.vu.selectableSpawn) return;
    const H = this.H;
    const jJ = H <= 2 ? 30 : H <= 50 ? 40 : 50;
    while (this.iy <= jJ) {
      if (!this.step()) break;
      if (onStep) onStep(this.iy, jJ);
      if (this.iy === jJ) this.g.endSpawnPhase();
      this.iy++;
    }
  }

  state() { return { iv: this.iv, iw: this.iw, ix: this.ix, iy: this.iy }; }
  restore(s) { this.iv = s.iv; this.iw = s.iw; this.ix = s.ix; this.iy = s.iy; }
  fork(g, exec) { const s = new ReplayStepper({ d: this.d, H: this.H }, g, exec); s.restore(this.state()); return s; }
}

// 邻接：p 的边界格四邻里别人的格子数（按席位），以及无主陆地的条数
export function contacts(g, p) {
  const m = new Map();
  const B = g.border[p];
  if (!B || !g.alive[p]) return m;
  const d4 = g.dir4, px = g.px, own = g.own;
  for (let i = B.length - 1; i >= 0; i--) {
    const b = B[i];
    for (let k = 0; k < 4; k++) {
      const c = b + d4[k], v = px[c];
      if (v >= P_INNER) { const o = own[c]; if (o !== p) m.set(o, (m.get(o) || 0) + 1); }
      else if (v === T_LAND) m.set(NEUTRAL, (m.get(NEUTRAL) || 0) + 1);
    }
  }
  return m;
}

export { NEUTRAL, P_INNER, T_LAND, MAX_PLAYERS, iV };
