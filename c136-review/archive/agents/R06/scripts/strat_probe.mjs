#!/usr/bin/env node
// strat_probe.mjs — 影子策略探针。
//
// 在干净模拟器按录像逐拍重演出来的真实局面上，逐拍运行策略源码（src/strategy/v27-team-<版本>.js 的 Policy）。
// 策略发出的指令只记录、不执行：局面始终只由录像推进。用来回答
//   「在这一拍的真实局面下，策略代码会怎么决定？每个邻居的报价 c、worth、保底线 safe/keep、可用兵 avail 是多少？卡在 buyLand 的哪一行？」
//
//   python3 c136-review/agents/R06/scripts/sim_prep.py <matchId>      # 先有 out/<matchId>/sim_in.json
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/strat_probe.mjs <matchId> --me 45,47 \
//        [--to T] [--dump 45:2070:2200:30,47:3400:3900:60] [--strategy c110] [--offline] [--nfs 0|1] [--win 90] [--json] [--tally] [--boatcheck] [--mtncheck]
//
//   --me      要挂影子策略的玩家号（逗号分隔；squad = 全部我方号）
//   --dump    玩家:起拍:止拍:步长，在这些拍打印 buyLand 的逐报价账（可多段，逗号分隔）
//   --boatcheck  配 --dump：每个 dump 拍多打一行「发船检查」（idleBoats/boatOut/searchWater 在这一拍的各项条件，只读）
//   --mtncheck   配 --dump：每个 dump 拍多打一行「翻山检查」（自己贴着的山体另一侧是谁的地；c110 没有翻山指令，只读）
//   --nfs     强制 isNoFullSend 的取值（缺省：让影子自己按代码演化）
//   --offline 让策略以为自己在离线模拟器里（g.online=false）；缺省按线上（g.online=true）
//   --win     汇总窗口（拍），打印每个窗口影子想发的指令数和录像里实际执行的指令数
//   --part i/n  长局分片跑：只给 --me 名单里第 i 片（按名单下标 % n）的号挂影子，结果写 probe.part<i>of<n>.json；
//             每个影子只读局面、指令不执行，所以分片与一次跑完逐字节相同（B021 前 3000 拍核对过）。全部片跑完后
//             strat_probe.mjs <matchId> --merge n 合成 probe.json（不重演，只拼文件）
//   --tally   每个决策拍（t%period==0）给每个影子号记一行「卡在哪道闸」，写进 probe.json 的 tally（配 --json）：
//             t<coreFrom 走 General.act → Style.pickTarget 的路径（打内置 AI 的底线 winFloor=max(winR 项, dpKeep, safeFinite)）；
//             t>=coreFrom 走 Policy.buyLand 的路径（真人报价的出口行号）。--dump 在 t<coreFrom 的拍也打印这条路径的逐邻居账
//
// 局限（读结果时要记住）：
//   1. 影子看到的是「没有延迟的真实局面」。真机在卡顿时看到的是落后几十到几百拍的局面。
//   2. 影子的指令不执行，所以同一个想法会每 5 拍（对同一目标每 15 拍）重复出现，条数不能直接和录像比，只比「有没有」和「打谁」。
//   3. 影子的内部记忆（hitTo、lastBoat、lastDonateTick、isNoFullSend…）是它自己演化出来的，和真机不保证一致。
//   4. 模拟器与实机逐兵一致的范围以 sim_state.json 的 check 为准（B039 全程一致）；本脚本另外打印影子局面与日志快照的核对数。
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { decodeReplay, mapOf } from '/agent/repos/c136-data/src/sim/tools/c102-replay-lib.mjs';
import { Game, MAX_PLAYERS, NEUTRAL, P_INNER, iV } from '/agent/repos/c136-data/src/sim/sim/game.js';
import { loadMap, T_LAND } from '/agent/repos/c136-data/src/sim/sim/map.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../out');
const SRC = '/agent/repos/c136-data/src';
const argv = process.argv.slice(2);
const mid = argv[0];
const has = (k) => argv.includes(`--${k}`);
const opt = (k, d) => (has(k) ? argv[argv.indexOf(`--${k}`) + 1] : d);
if (!mid) {
  console.error('用法：strat_probe.mjs <matchId> --me 45,47 [--to T] [--dump 玩家:起拍:止拍:步长,...] [--strategy c110] [--offline] [--nfs 0|1] [--win 90] [--json]');
  process.exit(2);
}
const TO = +opt('to', 1e9);
const VER = opt('strategy', 'c110');
const ONLINE = !has('offline');
const NFS = has('nfs') ? +opt('nfs', 0) : null;
const WIN = +opt('win', 0);
const TALLY = has('tally');
const DUMPS = (opt('dump', '') || '').split(',').filter(Boolean).map((s) => {
  const [p, a, b, st] = s.split(':').map(Number);
  return { p, a, b: b ?? a, st: st || 5 };
});

const PART = has('part') ? opt('part', '1/1').split('/').map(Number) : null;
if (has('merge')) {
  const n = +opt('merge', 0);
  const parts = [];
  for (let i = 1; i <= n; i++) parts.push(JSON.parse(fs.readFileSync(path.join(OUT, mid, `probe.part${i}of${n}.json`), 'utf8')));
  const base = parts[0];
  for (const q of parts) {
    if (q.to !== base.to || q.strategy !== base.strategy || q.online !== base.online || JSON.stringify(q.meAll) !== JSON.stringify(base.meAll)) {
      console.error(`分片不一致：to/strategy/online/名单 对不上（${q.part} vs ${base.part}）`);
      process.exit(3);
    }
    if (JSON.stringify(q.actual) !== JSON.stringify(base.actual) || JSON.stringify(q.check) !== JSON.stringify(base.check)) {
      console.error(`分片不一致：录像侧的 actual/check 对不上（${q.part} vs ${base.part}）`);
      process.exit(3);
    }
  }
  const order = new Map(base.meAll.map((p, i) => [p, i]));
  const shadowsAll = {};
  for (const p of base.meAll) for (const q of parts) if (q.shadows[p]) shadowsAll[p] = q.shadows[p];
  const miss = base.meAll.filter((p) => !shadowsAll[p]);
  if (miss.length) { console.error(`分片不全：缺 ${miss.join(',')}`); process.exit(3); }
  const tallyAll = parts.flatMap((q) => q.tally).sort((a, b) => a.t - b.t || order.get(a.p) - order.get(b.p));
  const out = { matchId: base.matchId, strategy: base.strategy, online: base.online, to: base.to, check: base.check, simVsEngine: base.simVsEngine, shadows: shadowsAll, actual: base.actual, tally: tallyAll };
  fs.writeFileSync(path.join(OUT, mid, 'probe.json'), JSON.stringify(out));
  console.log(`${mid}: 合并 ${n} 片 → probe.json（影子 ${Object.keys(shadowsAll).length} 个，tally ${tallyAll.length} 行，actual ${base.actual.length} 条，到 t=${base.to}，日志快照核对 ${base.check[0]}/${base.check[1]}）`);
  process.exit(0);
}

// ---- 策略源码：只改两行 import 的路径，其余原样 ----------------------------------------------
const stratSrc = fs.readFileSync(path.join(SRC, 'strategy', `v27-team-${VER}.js`), 'utf8')
  .replace('from "../../sim/index.js"', `from "${SRC}/sim/sim/index.js"`)
  .replace('from "../../sim/map.js"', `from "${SRC}/sim/sim/map.js"`);
const stratDir = path.join(OUT, '_strat');
fs.mkdirSync(stratDir, { recursive: true });
const stratFile = path.join(stratDir, `v27-team-${VER}.mjs`);
if (!fs.existsSync(stratFile) || fs.readFileSync(stratFile, 'utf8') !== stratSrc) fs.writeFileSync(stratFile, stratSrc);
const { Policy } = await import(pathToFileURL(stratFile).href);

// ---- 对局重演（与 sim_replay.mjs 相同的驱动；这里不记账） ------------------------------------
const inp = JSON.parse(fs.readFileSync(path.join(OUT, mid, 'sim_in.json'), 'utf8'));
const d = decodeReplay(fs.readFileSync(inp.replayPath, 'utf8'));
const vu = d.vu;
const { mapIdx, mapSeed } = mapOf(vu);
// 共享目录 src/sim/maps 里没有这局的种子地图时，读 map_export.mjs 从真引擎导出的同格式文件（out/_maps/）
function loadMapAny(index, seed) {
  try { return loadMap(index, seed); } catch (e) {
    const file = path.join(OUT, '_maps', `${index}_${seed}.bin.gz`);
    if (!fs.existsSync(file)) throw new Error(`没有地图 ${index}_${seed}：共享目录和 out/_maps 都没有（先跑 map_export.mjs ${mid}）`);
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
const map = loadMapAny(mapIdx, mapSeed);
const H = vu.humanCount;
const squad = new Set(inp.squad);
const TEAM = inp.nTeams > 0 ? { teams: inp.teams, nTeams: inp.nTeams, botTeams: inp.botTeams } : null;
const LH = inp.lH || [0, 1, 2, 3, 4, 5, 6, 7, 8];
const KK = [[100, 100, 100], [144, 0, 0], [0, 128, 0], [0, 0, 144], [128, 128, 0], [128, 0, 128], [0, 128, 128], [196, 196, 196], [0, 0, 0]];
const KL = [[4, 4, 4, 20], [4, 0, 0, 27], [0, 4, 0, 31], [0, 0, 4, 27], [4, 4, 0, 31], [4, 0, 4, 31], [0, 4, 4, 31], [4, 4, 4, 14], [4, 4, 4, 13]];
class TeamGame extends Game {
  setupColors() {
    if (!TEAM) return super.setupColors();
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

  // 船落在「不是空地、也没人占」的格子（水 / 边界 / 山）：真引擎 acN 用像素的归属位 (地形码 & 3) << 3 当目标席位
  // （水 16、边界 24、山 8），对那个席位开一条攻击线，没有接壤时下一次结算原数退回余额；干净模拟器的 landAt 在这种落点
  // 直接返回（船上的兵凭空消失）。这段改法取自统筹入库的 R01 工具 /agent/repos/c136-data/src/tools/resim_lib_r01.mjs。
  landAt(p, troops, c, at) {
    const v = this.px[c];
    if (v !== T_LAND && v < P_INNER) {
      const target = (v & 3) << 3;
      oddLandings.push({ t: this.t, p, troops, target });
      if (target === p) { this.addBalance(p, troops); return; }
      if (!this.isEnemy(p, target)) {
        const room = this.receiverRoom(target, troops);
        if (room >= 1 && this.bookDonation(target, room)) this.addBalance(target, room);
        return;
      }
      if (this.hasAttack(p, target) || this.hasFreeSlot(p)) {
        this.front[p].push(at);
        this.addAttack(p, troops, target);
        this.schedule(p, true);
      }
      return;
    }
    return super.landAt(p, troops, c, at);
  }
}
const oddLandings = [];
const g = new TeamGame({
  map, humans: H, players: vu.playerCount, difficulty: H > 1 ? 0 : vu.botDifficultyValue, spawnSeed: vu.spawningSeed,
  selectableSpawn: !!vu.selectableSpawn, battleRoyaleMode: vu.battleRoyaleMode,
  humanColors: vu.colorsData ? Array.from(vu.colorsData.subarray(0, H)) : [0],
  teams: inp.teams, nTeams: inp.nTeams, botTeams: inp.botTeams,
});
g.me = vu.selectedPlayer;

// 名字表：策略按名字认编队号（isOurSquadBot）。真人名字取录像头；内置 AI 的名字取真引擎重放写下的 allNames。
let names = null;
try {
  const st = JSON.parse(fs.readFileSync(path.join(OUT, mid, 'sim_state.json'), 'utf8'));
  if (Array.isArray(st.allNames) && st.allNames.length >= H) names = st.allNames.slice();
} catch {}
if (!names) {
  names = new Array(MAX_PLAYERS).fill('');
  for (let p = 0; p < H; p++) names[p] = inp.names?.[p] ?? '';
  console.log('注意：没有 sim_state.json 的 allNames，内置 AI 的名字为空（撞名 AI 不会被影子策略当成编队号）');
}
g.names = names;
const nm = (p) => (p === NEUTRAL || p >= 512 ? '无主地' : `${names[p] || 'bot' + p}(${p}${p < H ? (g.state[p] === 2 ? '·空壳' : `·队${g.teams[p]}`) : '·AI'})`);
const k = (v) => (Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(2) + 'M' : Math.abs(v) >= 1e4 ? Math.round(v / 1e3) + 'k' : String(Math.round(v)));

// 真人的「翻山」指令（录像指令号 10；只有山地图有）。干净模拟器只给内置 AI 写了翻山（bots.js mountainAttack），
// 这里按线上引擎原文 bB.qi.i2(player, pct, 格子, 目标) 补上真人的入口：
//   目标规范化（rk）→ 点的那一格必须是无主陆地或目标的地（fT；点在无主陆地上时目标改成无主地）→ 那一格四邻里的山体
//   （按 fb 的 3..0 顺序、同一山体只算一次）里第一个「自己的贴山边界格也挨着」的山体（fI/fK）→ 已有对该目标的进攻线或还有空线（kF/kY）
//   → 出兵量 m6 = 模拟器的 sendAll（另扣 max(余额/10, 1000)）→ 把那格山推进自己的前线表 → addAttack → schedule(…, true)。
const T_MOUNTAIN = 5;
function humanMountain(p, pct, tile, target) {
  if (!g.canAct(p) || p === target) return false;
  target = Math.min(target, NEUTRAL);
  if (target < NEUTRAL && g.alive[target] === 0) target = NEUTRAL;
  if (target < NEUTRAL && !g.isEnemy(p, target)) return false;
  const x = tile % g.W, y = Math.floor(tile / g.W);
  if (!(x > 0 && x < g.W - 1 && y > 0 && y < g.H - 1)) return false;
  const v = g.px[tile];
  if (v === T_LAND) target = NEUTRAL;
  else if (v >= P_INNER) { if (g.own[tile] !== target) return false; } else return false;
  const ids = [], cells = [];
  for (let k = 3; k >= 0; k--) {
    const c = tile + g.dir4[k];
    if (g.px[c] === T_MOUNTAIN && !ids.includes(g.wid[c])) { ids.push(g.wid[c]); cells.push(c); }
  }
  const C = g.cliff[p] || [];
  const touches = (id) => {
    for (let i = 0; i < C.length; i++) for (let k = 3; k >= 0; k--) { const c = C[i] + g.dir4[k]; if (g.px[c] === T_MOUNTAIN && g.wid[c] === id) return true; }
    return false;
  };
  let hit = -1;
  for (let i = 0; i < ids.length; i++) if (touches(ids[i])) { hit = cells[i]; break; }
  if (hit < 0) return false;
  if (!g.hasAttack(p, target) && !g.hasFreeSlot(p)) return false;
  const troops = g.sendAll(p, pct);
  g.front[p].push(hit);
  g.addAttack(p, troops, target);
  g.schedule(p, true);
  return true;
}

const actual = []; // 录像里我方影子号实际执行的指令
const execCmd = (c) => {
  const { id, player, dX, dZ } = c;
  if (id === 0) g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false);
  else if (id === 1) {
    const B0 = g.bal[player];
    const ok = g.attack(dX, dZ, player);
    if (actualFor.has(player)) actual.push({ t: g.t, p: player, k: 'atk', to: Math.min(dZ, NEUTRAL), pct: dX, ok, B0 });
  } else if (id === 2) {
    const B0 = g.bal[player];
    const ok = g.donate(dX, dZ, player);
    if (actualFor.has(player)) actual.push({ t: g.t, p: player, k: 'don', to: dZ, pct: dX, ok, B0 });
  } else if (id === 3) {
    const B0 = g.bal[player];
    const ok = g.boat(dX, dZ >> 3, dZ & 7, player);
    if (actualFor.has(player)) actual.push({ t: g.t, p: player, k: 'boat', to: -1, pct: dX, ok, B0 });
  } else if (id === 4) {
    if (dX === 849) g.recall(dZ, player);
    else g.chase(dX, dZ, player);
  } else if (id === 5) {
    if (dX !== 513) g.retreat(dX, player);
  } else if (id === 10) {
    humanMountain(player, dX >> 10, dZ, dX % 1024);
  } else if (id === 8 || id === 9) {
    if (g.spawnPhase) {
      g.eliminate(player);
      let n = g.aliveCount;
      for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
      g.aliveCount = n;
    } else g.leave(player);
  }
};

// ---- 影子：策略实例 + 只读视图 ---------------------------------------------------------------
const meAll = opt('me', 'squad') === 'squad' ? [...squad] : opt('me', '').split(',').map(Number);
const meList = PART ? meAll.filter((_, i) => i % PART[1] === PART[0] - 1) : meAll;
const actualFor = new Set(meAll); // 录像侧的 actual 按完整名单记，各片相同
const shadows = new Map();
class Probe extends Policy {
  send(gv, target, troops, hint) {
    const ok = super.send(gv, target, troops, hint);
    this._sends.push({ t: gv.t, to: target, troops: Math.round(troops), ok });
    return ok;
  }
}
const makeView = (me, sh) => {
  const cache = new Map();
  const rec = (o) => sh.cmds.push({ t: g.t, ...o });
  const over = {
    online: ONLINE,
    attack: (pct, target, p = me) => {
      if (!g.canAct(p) || p === target) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      if (!(g.quote(p, pct, 12) >= 0)) return false;
      target = Math.min(target, NEUTRAL);
      if (target < NEUTRAL && g.alive[target] === 0) target = NEUTRAL;
      if (target < NEUTRAL && !g.isEnemy(p, target)) return false;
      if (!g.hasAttack(p, target) && !g.hasFreeSlot(p)) return false;
      rec({ k: 'atk', to: target, pct, amt: iV(g.bal[p] * (pct + 1), 1024) });
      return true;
    },
    boat: (pct, water, dir, p = me) => {
      if (!g.canAct(p) || !g.boatsAllowed(p)) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      if (!(g.quote(p, pct, 32) >= 0)) return false;
      rec({ k: 'boat', to: -1, pct, amt: iV(g.bal[p] * (pct + 1), 1024) });
      return true;
    },
    boatTo: (pct, target, p = me, radius = 32) => {
      if (!g.canAct(p) || !g.boatsAllowed(p)) return false;
      const s = g.boatSpot(target, p, radius);
      if (s === null) return false;
      pct = Math.max(0, Math.min(1023, pct | 0));
      if (!(g.quote(p, pct, 32) >= 0)) return false;
      rec({ k: 'boat', to: g.px[target] >= 16 ? g.own[target] : NEUTRAL, pct, amt: iV(g.bal[p] * (pct + 1), 1024) });
      return true;
    },
    donate: (pct, q, p = me) => {
      const v = g.donateQuote(pct, q, p);
      if (!(v > 0)) return false;
      rec({ k: 'don', to: q, pct, amt: v });
      return true;
    },
    retreat: () => false,
    chase: () => false,
    recall: () => false,
  };
  return new Proxy(g, {
    get(t, key) {
      if (key in over) return over[key];
      const v = t[key];
      if (typeof v !== 'function') return v;
      let b = cache.get(key);
      if (!b) cache.set(key, (b = v.bind(t)));
      return b;
    },
  });
};
for (const me of meList) {
  const sh = { me, cmds: [], pol: new Probe({}, me), err: 0, firstErr: '' };
  sh.pol._sends = [];
  if (NFS !== null) sh.pol.isNoFullSend = !!NFS;
  sh.view = makeView(me, sh);
  shadows.set(me, sh);
}

// ---- safeFinite 的拆解（公式抄自 V13.safeFinite L2532-2542、Strategy.threatOf L464-492） -------------------------
// 内置 AI q 的「它更想打谁」：q 的其余邻居里 兵+压在 q 身上的兵 最少的那个（threatOf 的 minOther），连同是谁
const threatWho = (q, me) => {
  const Bq = g.border[q], px = g.px, own = g.own, d4 = g.dir4;
  const busyNeutral = g.hasAttack(q, NEUTRAL);
  let minOther = Infinity, who = -1;
  const n = Bq.length, stp = n > 1024 ? Math.ceil(n / 1024) : 1;
  const seen = new Set();
  for (let i = n - 1; i >= 0; i -= stp) {
    const b = Bq[i];
    for (let kk = 0; kk < 4; kk++) {
      const c = b + d4[kk], v = px[c];
      if (v === T_LAND) {
        if (!busyNeutral) return { neutral: true, minOther: 0, who: -1 };
        continue;
      }
      if (v < 16) continue;
      const o = own[c];
      if (o === q || o === me || seen.has(o)) continue;
      seen.add(o);
      if (g.hasAttack(q, o)) continue;
      const sv = g.bal[o] + g.attackTroopsOn(o, q);
      if (sv < minOther) { minOther = sv; who = o; }
    }
  }
  return { neutral: false, minOther, who };
};
// who 是谁：我方在场号（同队/异队）、我方空壳、其他真人（同队/异队）、内置 AI
const whoKind = (me, o) => {
  if (o < 0) return '-';
  if (o >= H) return '内置AI';
  const left = g.state[o] === 2, same = g.teams[o] === g.teams[me];
  if (squad.has(o)) return left ? '我方空壳' : same ? '我方号·同队' : '我方号·异队';
  return left ? '外人空壳' : same ? '外人队友' : '敌方真人';
};
// safeFinite = 对每个内置 AI 邻居 q（活着、有空槽、没在打我）：取「q 的其余邻居里 兵+压在 q 身上的兵 最少的那个」，再对 q 取最大。
// 返回数值、取到的是谁（who）、经由哪个内置 AI 邻居（via）。
const sbInfo = (pol, me) => {
  let sb = 0, who = -1, via = -1;
  for (const q of pol.nb) {
    if (!g.alive[q] || !g.isBot(q) || !g.hasFreeSlot(q) || g.hasAttack(q, me)) continue;
    const th = threatWho(q, me);
    if (th.neutral || !Number.isFinite(th.minOther)) continue;
    const v = th.minOther - g.attackTroopsOn(me, q);
    if (v > sb) { sb = v; who = th.who; via = q; }
  }
  return { sb, who, via };
};

// ---- buyLand 的逐报价账（公式逐行抄自 Policy.buyLand；只算不发） ------------------------------
const explain = (sh) => {
  const pol = sh.pol, gv = sh.view, P = pol.p, me = sh.me;
  pol.analyze(gv);
  const B = g.bal[me], L = Math.max(1, g.terr[me]), fee = iV(12 * B, 1024), dMe = B / L;
  const dMedOther = pol.otherHumanMedDens(gv);
  const nHumans = pol.livingHumanCount(gv);
  const humanNbCount = pol.nb.filter((p) => g.alive[p] && pol.person(gv, p)).length;
  const m = P.maxW * pol.winRatio(g.t);
  const refDens = dMedOther !== null && g.t >= P.marketFrom ? Math.max(dMe, P.marketFloor * dMedOther) : dMe;
  const worth = m * refDens, over = P.surplus > 0 && B > 100 * L, cheap = P.growth > 0 ? 0.1 / pol.baseRate(gv) : 0;
  const minCmd = pol.minCmd(gv);
  const sbi = sbInfo(pol, me);
  const dpk = pol.dpKeep(gv);
  const rows = [];
  let done = null;
  for (const o of pol.offers(gv)) {
    const { q, c, need, person } = o;
    const row = { q, c, need, person, tD: o.tD, cnt: pol.cnt[q], flags: [o.nearCollapse && '将崩', o.bleeding && '被别人打', o.onMe && '在打我', o.pulseMode && 'pulse', o.isCrowdedHard && 'crowdedHard', o.isAgg && 'agg'].filter(Boolean) };
    rows.push(row);
    if (done) { row.gate = `（排在后面：${done}）`; continue; }
    if (c >= worth && c >= cheap && !over) { row.gate = 'L5267 报价 c >= worth 且没超软上限 → break'; done = '前一个报价已 break'; continue; }
    const isSole = person && !o.isDoorSea && nHumans >= 3 && !o.nearCollapse && !o.bleeding && !o.onMe && o.newNbs > 0 && humanNbCount === 1;
    if (isSole && c >= worth && c >= cheap && B < P.overHumanCap * 100 * L) { row.gate = 'L5271 唯一的真人缓冲邻居且 c>=worth、兵 < overHumanCap×100×地 → 跳过'; continue; }
    if (person && !o.isDoorSea && g.terr[q] < 250 && fee > 2 * need && c > 8 * worth && nHumans >= 3) { row.gate = 'L5275 目标 <250 格且手续费 > 2×need → 跳过'; continue; }
    const hardCapMult = o.isCrowdedHard && c >= 2.15 * worth && g.bal[q] >= 0.55 * B ? 1.5 : P.crowdedHardCap;
    if (person && !o.isDoorSea && o.isCrowdedHard && c >= worth && c >= cheap && B < hardCapMult * 100 * L) { row.gate = `L5280 crowdedHard 且 c>=worth、兵 < ${hardCapMult}×100×地 → 跳过`; continue; }
    if (P.absorbMode >= 1 && person && !o.isDoorSea && !o.nearCollapse && (o.inAtk ?? 0) >= P.absorbWaveMin * B) { row.gate = 'L5284 absorb → 跳过'; continue; }
    if (o.isDoorSea) { row.gate = 'L5288 doorSea 分支（不在本探针范围）'; continue; }
    let safe = pol.safeAt(gv, q);
    row.safeRaw = safe;
    if (!person || o.nearCollapse || (P.bleedSafeCap > 0 && (o.bleeding || o.tD < 0.45))) {
      const capPerPx = person && o.nearCollapse && (o.inAtk ?? 0) < 0.02 * B && ((c < 0.25 * worth && need <= 0.10 * B) || (g.bal[q] <= 0.05 * B && c < 25)) ? Math.min(P.oppFloorCap, P.collapseFloorCap ?? 85) : P.oppFloorCap;
      safe = Math.min(safe, capPerPx * L);
      row.safeCap = capPerPx;
    }
    let keep = Infinity;
    if (c < cheap) keep = 0;
    if (c < worth) {
      const worthOwn = P.ownWorthMinKeep > 0 && g.t >= P.ownWorthFrom && !o.nearCollapse ? m * dMe : worth;
      const budget = Math.max(0, (worthOwn * L - fee * m - c * L) / (1 + m));
      const minKeep = person && (o.nearCollapse || (P.bleedDiscount < 1 && o.bleeding) || (P.thinDiscount < 1 && o.tD < P.thinMaxTD)) ? (0.70 * c * L) / m : (c * L) / m;
      keep = Math.min(keep, P.post > 0 ? Math.max(minKeep, B - fee - budget) : minKeep);
      row.budget = budget;
    }
    const isSiegeShrink = P.siegeShrinkRatio > 0 && !pol.isNoFullSend && g.t >= P.leaderHardFrom && L < P.siegeShrinkRatio * (g.peak?.[me] ?? L) && nHumans >= 4 && person && !o.nearCollapse && !o.bleeding;
    if (isSiegeShrink && c >= worth && c >= cheap && B < P.crowdedHardCap * 100 * L) { row.gate = 'L5345 siegeShrink → 跳过'; continue; }
    if (over) {
      const overKeepMult = isSole ? P.overHumanKeep : isSiegeShrink ? P.siegeOverKeep : o.isCrowdedHard ? 1.08 : P.hold;
      keep = Math.min(keep, overKeepMult * 100 * L);
      row.overKeep = overKeepMult;
    }
    // safe 的两个来源：safeFinite（内置 AI 邻居的另一个邻居的兵）与 dpKeep（最强真人邻居打穿我要的兵）；谁大谁说了算
    const keepPre = keep;
    row.safeBy = sbi.sb > dpk && safe > Math.min(dpk, row.safeCap ? row.safeCap * L : Infinity) ? 'sb' : 'dpKeep';
    keep = Math.max(keep, safe);
    const avail = B - fee - keep;
    row.safe = safe; row.keep = keep; row.avail = avail;
    if (avail <= 0) {
      const safeNoSb = Math.min(dpk, !person || row.safeCap ? (row.safeCap ?? P.oppFloorCap) * L : Infinity);
      const availNoSb = B - fee - Math.max(keepPre, safeNoSb);
      const cnt0 = pol.cnt[q], want0 = 1.25 * need + 3 * cnt0, x0 = Math.min(availNoSb, want0);
      row.passNoSb = row.safeBy === 'sb' && x0 >= minCmd && (x0 >= want0 || x0 >= P.chunk * B);
      row.sbWho = sbi.who; row.sbVia = sbi.via;
      row.gate = `L5361 avail<=0：保底线 keep=${k(keep)}（safe=${k(safe)}，来自 ${row.safeBy === 'sb' ? `safeFinite=${k(sbi.sb)}〔经由 ${nm(sbi.via)} 的另一个邻居 ${nm(sbi.who)}·${whoKind(me, sbi.who)}〕${row.passNoSb ? '；去掉这一项就能出兵' : ''}` : `dpKeep=${k(dpk)}`}）不低于余额`;
      continue;
    }
    const cnt = pol.cnt[q];
    if (!person) {
      if (g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) { row.gate = 'L5364 已在打这个非真人目标 → 跳过'; continue; }
      const want = 1.25 * need + 3 * cnt, x = Math.min(avail, want);
      if (x < minCmd) { row.gate = `L5367a 这笔单太小：x=min(avail, want=1.25×need+3×接壤)=${k(x)} < minCmd=feeK×手续费=${k(minCmd)}（余额的 4.7%）→ 跳过`; continue; }
      if (x < want && x < P.chunk * B) { row.gate = `L5367b 能出的兵 x=${k(x)} 小于 want=${k(want)} 且不足 chunk×兵=${k(P.chunk * B)} → 跳过`; continue; }
      row.send = x; row.gate = 'L5368 出兵（非真人，整笔）'; done = '已出兵';
      continue;
    }
    const usePulseBlock = P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));
    const curAtk = g.attackTroopsOn(me, q);
    const floorCmd = Math.max(minCmd, P.pulseMinShare * B);
    if (usePulseBlock) {
      if (g.t >= 3800 && (o.nearCollapse || o.bleeding || (P.aggMemMode === 2 && o.isAgg))) {
        if (curAtk >= 0.08 * B || curAtk >= 0.65 * need) { row.gate = 'L5490 对它的在途兵已够（>=8% 兵或 >=65% need）→ 跳过'; continue; }
        const targetSlot = Math.min(0.85 * need + 3 * cnt, Math.floor(P.pulseFrac * B));
        const pulse = Math.min(avail, Math.max(targetSlot - curAtk, Math.floor(0.08 * B)));
        if (pulse < floorCmd) { row.gate = `L5497 pulse=${k(pulse)} 小于 max(minCmd, 4% 兵)=${k(floorCmd)} → 跳过`; continue; }
        row.send = pulse; row.gate = 'L5500 出兵（t>=3800 对将崩/被别人打的真人：pulse，上限 12% 兵）'; done = '已出兵';
        continue;
      }
      if (o.nearCollapse) {
        if (curAtk >= 0.04 * B || curAtk >= 0.30 * need) { row.gate = 'L5504 在途兵已够 → 跳过'; continue; }
        const pulse = Math.min(avail, Math.max(Math.floor(P.pulseFrac * B), Math.min(avail, Math.floor(0.30 * need))));
        if (pulse < floorCmd) { row.gate = 'L5506 pulse 太小 → 跳过'; continue; }
        row.send = pulse; row.gate = 'L5507 出兵（将崩目标：pulse）'; done = '已出兵';
        continue;
      }
      if (o.pulseMode) {
        if (curAtk >= 0.04 * B) { row.gate = 'L5511 对它的在途兵 >= 4% 兵 → 跳过'; continue; }
        const want = Math.min(1.20 * need + 3 * cnt, Math.floor(P.pulseFrac * B));
        const x = Math.min(avail, want);
        if (x < floorCmd) { row.gate = `L5520 x=${k(x)} 小于 max(minCmd, 4% 兵)=${k(floorCmd)} → 跳过`; continue; }
        row.send = x; row.gate = 'L5522 出兵（pulse：上限 12% 兵）'; done = '已出兵';
        continue;
      }
    }
    const want = 1.25 * need + 3 * cnt, x = Math.min(avail, want);
    if (x <= 0 || (x < want && (x < P.chunk * B || (P.pplKill > 0 && person)))) { row.gate = `L5528 买不起整笔（want=${k(want)}）且 avail=${k(avail)} 不足 chunk×兵=${k(P.chunk * B)} → 跳过`; continue; }
    row.send = x; row.gate = 'L5531 出兵（真人，非 pulse：min(avail, 1.25×need)）'; done = '已出兵';
  }
  return { B, L, dMe, m, worth, cheap, over, dMedOther, nHumans, rows, sbi, dpk };
};

const explainEarly = (sh) => {
  const pol = sh.pol, gv = sh.view, P = pol.p, me = sh.me;
  pol.analyze(gv);
  const B = g.bal[me], L = Math.max(1, g.terr[me]);
  const { floorAt } = pol.floors(gv);
  const min = pol.minCmd(gv);
  const dpk = pol.dpKeep(gv);
  const pf = pol.peopleFloor(gv);
  const { sb, who: sbWho, via: sbVia } = sbInfo(pol, me);
  let active = 0;
  const base = g.slotBase(me);
  for (let i = g.atkCount[me] - 1; i >= 0; i--) if (g.atkTarget[base + i] !== NEUTRAL) active++;
  const rows = [];
  for (const q of pol.nb) {
    if (!g.alive[q] || !g.terr[q]) continue;
    const person = pol.person(gv, q);
    const perPx = pol.price(gv, q);
    const row = { q, person, perPx, cnt: pol.cnt[q] };
    rows.push(row);
    if (!g.hasAttack(me, q) && (active >= P.maxTargets || !g.hasFreeSlot(me))) { row.gate = 'slots'; row.txt = 'L1192 进攻槽位已满'; continue; }
    if (!pol.allow(gv, q)) {
      if (person) { row.gate = 'allow'; row.txt = 'L1193 allow=false（真人：没有动机/在等）'; }
      else if (!pol.botOk(gv, q)) { row.gate = 'botOk'; row.txt = `L2147 botOk=false：botPx=${pol.botPx(gv, q).toFixed(1)} > winWorth=${pol.winWorth(gv).toFixed(1)}（=winR×t×自己密度）`; }
      else { row.gate = 'botMax'; row.txt = `L2147 price=${perPx.toFixed(1)} > botMax=${P.botMax}`; }
      continue;
    }
    if (perPx > P.maxCost) { row.gate = 'maxCost'; row.txt = 'L1195 price > maxCost'; continue; }
    const fl = pol.floorFor(gv, q, floorAt(perPx));
    const avail = B - fl;
    row.floor = fl; row.avail = avail;
    if (avail <= pol.minShare(gv, q) * B || avail < min) {
      if (!person && P.winR > 0 && g.t < P.dpEnd) {
        const mult = pol.contested(gv, q) ? P.sharedBotMult : 1;
        const t1 = (mult * pol.botPx(gv, q) * L) / (P.winR * Math.max(1, g.t));
        const terms = [['winR', t1], ['dpKeep', dpk], ['sb', sb], ['ppl', pf]].sort((a, b) => b[1] - a[1]);
        row.gate = 'floor:' + terms[0][0];
        const flNoSb = Math.max(t1, dpk, pf);
        row.passNoSb = B - flNoSb > pol.minShare(gv, q) * B && B - flNoSb >= min;
        row.txt = `L1197 可用兵 ${k(avail)} <= minSend(${P.minSend})×兵=${k(pol.minShare(gv, q) * B)}：底线 ${k(fl)} = max(winR 项 ${k(t1)}, dpKeep ${k(dpk)}, safeFinite ${k(sb)}${sb > 0 ? `〔经由 ${nm(sbVia)} 的另一个邻居 ${nm(sbWho)}·${whoKind(me, sbWho)}〕` : ''})${terms[0][0] === 'sb' ? (row.passNoSb ? '；去掉 safeFinite 项就能出兵' : '；去掉 safeFinite 项仍不够') : ''}`;
      } else { row.gate = 'floor'; row.txt = `L1197 可用兵 ${k(avail)} 不足（底线 ${k(fl)}）`; }
      continue;
    }
    const need = pol.elimCost(gv, q) + g.attackTroopsOn(q, me) - g.attackTroopsOn(me, q);
    if (need <= 0) { row.gate = 'need0'; row.txt = 'L1199 need<=0'; continue; }
    if (!person && g.hasAttack(me, q) && (!g.hasAttack(q, me) || g.attackTroopsOn(me, q) >= 0.35 * need)) { row.gate = 'already'; row.txt = 'L1200 已在打它'; continue; }
    const send = pol.amount(gv, q, avail, need, min);
    if (!(send >= min)) { row.gate = 'amount'; row.txt = 'L1202 amount < minCmd'; continue; }
    row.gate = 'ok'; row.send = send; row.txt = `L1208 可出兵 ${k(send)}`;
  }
  return { B, L, dpk, sb, sbWho, sbVia, rows };
};

// ---- t<coreFrom 的逐邻居账见上（公式抄自 L1180-1213、L2265-2276、L4542-4550）
// ---- 每个决策拍记一行「卡在哪」 -----------------------------------------------------------------
const tally = [];
const tallyTick = (sh) => {
  const pol = sh.pol, me = sh.me, P = pol.p;
  const mine = sh.cmds.filter((c) => c.t === g.t);
  const out = mine.map((c) => (c.k === 'atk' ? (c.to === NEUTRAL ? 'N' : (c.to < H && g.state[c.to] !== 2 ? 'H' : 'A')) : c.k === 'boat' ? 'B' : 'D')).join('');
  const B = g.bal[me], L = Math.max(1, g.terr[me]);
  const rec = { t: g.t, p: me, B, L, nb: pol.nb.length, neut: pol.neutral, out };
  let onMe = 0;
  for (const q of g.attackersOf(me)) if (q < H && g.state[q] !== 2) onMe += g.attackTroopsOn(q, me);
  rec.onMe = onMe;
  if (g.t < P.coreFrom) {
    const e = explainEarly(sh);
    const ai = e.rows.filter((r) => !r.person);
    rec.ai = ai.length;
    rec.hum = e.rows.length - ai.length;
    if (ai.length) {
      // 最便宜的那个内置 AI 邻居卡在哪
      const best = ai.slice().sort((a, b) => a.perPx - b.perPx)[0];
      rec.gate = ai.some((r) => r.gate === 'ok') ? 'ok' : best.gate;
      rec.px = +best.perPx.toFixed(1);
      if (rec.gate === 'floor:sb') { rec.sbKind = whoKind(me, e.sbWho); rec.passNoSb = best.passNoSb ? 1 : 0; rec.sb = e.sb; }
    }
  } else {
    const e = explain(sh);
    const per = e.rows.filter((r) => r.person), non = e.rows.filter((r) => !r.person);
    rec.ai = non.length;
    rec.hum = per.length;
    rec.over = e.over ? 1 : 0;
    rec.worth = +e.worth.toFixed(1);
    const code = (r) => (r.send ? 'send' : (r.gate.match(/^L\d+[ab]?/) || ['later'])[0]);
    if (per.length) {
      rec.hg = per.map(code).join(',');
      rec.hc = +Math.min(...per.map((r) => r.c)).toFixed(1);
      const sf = per.filter((r) => r.safe !== undefined).map((r) => r.safeRaw);
      if (sf.length) rec.safe = Math.round(Math.max(...sf));
    }
    if (non.length) rec.ag = non.map(code).join(',');
    // L5361 卡住的报价里，保底线取的是 safeFinite 还是 dpKeep；safeFinite 取到的是谁的兵；去掉后能不能出兵
    const sbRows = e.rows.filter((r) => r.gate && r.gate.startsWith('L5361') && r.safeBy === 'sb');
    if (sbRows.length) {
      rec.sbKind = whoKind(me, e.sbi.who);
      rec.sb = Math.round(e.sbi.sb);
      rec.sbA = sbRows.filter((r) => !r.person).length;
      rec.sbH = sbRows.filter((r) => r.person).length;
      rec.sbPassA = sbRows.filter((r) => !r.person && r.passNoSb).length;
      rec.sbPassH = sbRows.filter((r) => r.person && r.passNoSb).length;
    }
    const first = per[0];
    if (first && first.gate && first.gate.startsWith('L5361')) rec.h5361 = first.safeBy;
  }
  tally.push(rec);
};

// 发船检查（只读）：idleBoats（c110 L4979-5006）→ boatOut（L1035-1050）→ searchWater（L1056-1113）在这一拍的各项条件。
// searchWater 只写它自己的草稿数组；这里不调 boatOut / boatFood（它们会改 lastBoat 并发令）。
const explainBoat = (sh) => {
  const pol = sh.pol, me = sh.me, P = pol.p;
  const o = { allowed: !!g.boatsAllowed(me), boatCount: g.boatCount[me], maxBoats: P.maxBoats, sinceLast: g.t - (pol.lastBoat ?? -1e9), boatEvery: P.boatEvery,
    coast: g.coast?.[me]?.length ?? 0, idleNeed: P.idleCap * 100 * g.terr[me], range: P.boatRange };
  try { o.mop = !!pol.isMopUp(g); } catch { o.mop = null; }
  let hit = null;
  try { hit = pol.searchWater(g); } catch (e) { o.err = String(e).slice(0, 80); }
  if (hit) {
    const bal = g.bal[me];
    o.hit = { owner: hit.neutral ? NEUTRAL : g.own[hit.land], neutral: !!hit.neutral, price: hit.price, eff: hit.eff, size: hit.size };
    try {
      const { floorAt, cap, avgNb } = pol.floors(g);
      o.floor = floorAt(hit.price);
      o.max = P.boatFrac * (bal - o.floor);
      const early = g.t < P.earlyEnd;
      const reserveK = early ? P.reserveEarly : P.reserve;
      o.parts = { cap, keepCap: P.keepCap, floorK: pol.floorK, reserveK, cRef: P.cRef,
        reserveTerm: reserveK * cap * Math.min(1, hit.price / P.cRef), refFloor: Math.max((early ? P.refEarly : P.ref) * avgNb, pol.defenseNeed(g)),
        seaSafe: P.seaSafe > 0 && g.t >= P.coreFrom ? pol.safeAt(g, -1) : 0,
        idleKeep: P.idleSafe > 0 && pol.idle(g) ? P.idleSafe * 100 * g.terr[me] + iV(32 * bal, 1024) : 0 };
    } catch (e) { o.err = String(e).slice(0, 80); }
    o.min = P.boatFee > 0 && hit.neutral ? 60 : Math.max(60, P.feeK * iV(32 * bal, 1024));
  }
  return o;
};
const boatLine = (sh) => {
  const o = explainBoat(sh), pol = sh.pol;
  const pre = [];
  if (!o.allowed) pre.push('引擎不许发船');
  if (o.boatCount >= o.maxBoats) pre.push(`在海上的船 ${o.boatCount} >= maxBoats ${o.maxBoats}`);
  if (pol.neutral > 0) pre.push('有无主邻格（L4995 return）');
  if (o.sinceLast < o.boatEvery) pre.push(`距上次发船检查 ${o.sinceLast} 拍 < boatEvery ${o.boatEvery}`);
  if (pol.nb.length && g.bal[sh.me] < o.idleNeed) pre.push(`有可打的邻居且兵 < idleCap×100×地 = ${k(o.idleNeed)}（L4996 return）`);
  let res;
  if (!o.hit) res = `searchWater 在 ${o.range} 格水程内找不到可登陆的地（无主地，或不在保护名单里、也不是陆上邻居的玩家的地）${o.err ? '；' + o.err : ''}`;
  else res = `searchWater 命中 ${o.hit.neutral ? '无主地' : nm(o.hit.owner)}（price=${o.hit.price.toFixed(1)} eff=${o.hit.eff.toFixed(1)}）；可发 max=boatFrac×(兵−floor ${k(o.floor ?? 0)})=${k(o.max ?? 0)}，下限 min=${k(o.min)} → ${(o.max ?? 0) < o.min ? 'max < min，不发（L1044）' : '够发'}${o.parts ? `；floor 的来历（L865/L2869）：floorK ${o.parts.floorK} × min(keepCap ${o.parts.keepCap} × 100×地 ${k(o.parts.cap)}, max(reserve ${o.parts.reserveK} × 100×地 × min(1, price/cRef ${o.parts.cRef}) = ${k(o.parts.reserveTerm)}, refFloor ${k(o.parts.refFloor)}))，再与 safeAt(-1)=${k(o.parts.seaSafe)}、idleKeep=${k(o.parts.idleKeep)} 取大` : ''}`;
  return `        发船检查：岸格 ${o.coast}，mopUp=${o.mop ? '是' : '否'}；${pre.length ? '前置条件挡住：' + pre.join('；') + '；' : '前置条件都过；'}${res}`;
};

// 翻山检查（只读；只有山地图有意义）：自己的贴山边界格（g.cliff[me]）挨着哪些山体；这些山体四邻的陆地格是谁的。
// 引擎 bB.qi.i2（录像指令号 10）的前置条件：点的格子是目标的地或无主陆地，且它四邻的某个山体也被自己的贴山边界格挨着。
// c110 源码里没有任何翻山指令（全文没有 mountain / cliff），这一行只说明「规则上够得着谁」。
const mtnLine = (sh) => {
  const me = sh.me, pol = sh.pol, C = g.cliff?.[me] || [], d4 = g.dir4;
  const ids = new Set();
  for (let i = 0; i < C.length; i++) for (let q = 3; q >= 0; q--) { const c = C[i] + d4[q]; if (g.px[c] === T_MOUNTAIN) ids.add(g.wid[c]); }
  if (!ids.size) return `        翻山检查：贴山边界格 ${C.length}，没有挨着山体`;
  const cnt = new Map();
  let neutral = 0;
  const N = g.W * g.H;
  for (let c = 0; c < N; c++) {
    if (g.px[c] !== T_MOUNTAIN || !ids.has(g.wid[c])) continue;
    for (let q = 0; q < 4; q++) {
      const n = c + d4[q], v = g.px[n];
      if (v === T_LAND) neutral++;
      else if (v >= P_INNER && g.own[n] !== me) cnt.set(g.own[n], (cnt.get(g.own[n]) || 0) + 1);
    }
  }
  const tag = (q) => {
    let prot = false, mate = false;
    try { prot = !!pol.isProtectedSquadMate(g, q); } catch {}
    try { mate = !!pol.isTeammate(g, q); } catch {}
    const land = pol.cnt?.[q] > 0 ? '·陆上已接壤' : '';
    if (mate) return '队友' + land;
    if (prot) return '保护名单' + land;
    return (q < g.humans ? (g.state[q] === 2 ? '敌方空壳' : '敌方真人') : '内置AI') + land;
  };
  const rows = [...cnt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([q, n]) => `${nm(q)}[${tag(q)}] ${n} 条边 地${g.terr[q]} 兵${k(g.bal[q])}`);
  const foes = [...cnt.keys()].filter((q) => { const t = tag(q); return t.startsWith('敌方真人') && !t.includes('陆上已接壤'); });
  return `        翻山检查：贴山边界格 ${C.length}，挨着 ${ids.size} 个山体；山体另一侧：${rows.join('；') || '没有别人的地'}${neutral ? `；无主陆地 ${neutral} 条边` : ''}`
    + `｜陆上不接壤、翻山够得着的敌方真人 ${foes.length} 个${foes.length ? '（' + foes.map((q) => `${nm(q)} ${cnt.get(q)} 条边 地${g.terr[q]} 兵${k(g.bal[q])}`).join('、') + '）' : ''}`;
};

const printDump = (sh, acted) => {
  const pol = sh.pol, me = sh.me;
  if (g.t < pol.p.coreFrom) {
    const ee = explainEarly(sh);
    console.log(`[探针·开局段] t=${g.t} ${nm(me)} 地 ${ee.L} 兵 ${k(ee.B)} 密 ${(ee.B / ee.L).toFixed(1)} ｜策略眼里 nb=${pol.nb.length} neut=${pol.neutral} ｜dpKeep=${k(ee.dpk)} safeFinite=${k(ee.sb)}${ee.sb > 0 ? `（经由 ${nm(ee.sbVia)}；它的另一个邻居 ${nm(ee.sbWho)}·${whoKind(me, ee.sbWho)}）` : ''}`);
    for (const r of ee.rows) console.log(`        邻居 ${nm(r.q)} ${r.person ? '真人' : '非真人'} 接${r.cnt} 地${g.terr[r.q]} 兵${k(g.bal[r.q])} price=${r.perPx.toFixed(1)} → ${r.txt}`);
    const mine0 = sh.cmds.filter((c) => c.t === g.t);
    console.log(`        影子 act() 这一拍发出：${mine0.length ? mine0.map((c) => `${{ atk: '攻', boat: '船', don: '捐' }[c.k]}→${c.to < 0 ? '?' : nm(c.to)} ${c.pct}‰ ${k(c.amt)}`).join('；') : '无'}`);
    return;
  }
  const e = explain(sh);
  const prot = [];
  // 被保护名单挡在 nb 之外的真实邻居（按接壤格数）
  const cntAll = new Map();
  const B = g.border[me], d4 = g.dir4;
  for (let i = 0; i < B.length; i++) {
    for (let q = 0; q < 4; q++) {
      const c = B[i] + d4[q];
      if (g.px[c] >= 16 && g.own[c] !== me) cntAll.set(g.own[c], (cntAll.get(g.own[c]) || 0) + 1);
    }
  }
  for (const [q, n] of [...cntAll.entries()].sort((a, b) => b[1] - a[1])) if (!pol.nb.includes(q)) prot.push(`${nm(q)} 接${n} 地${g.terr[q]} 密${(g.bal[q] / Math.max(1, g.terr[q])).toFixed(0)}`);
  console.log(`[探针] t=${g.t} ${nm(me)} 地 ${e.L} 兵 ${k(e.B)} 密 ${e.dMe.toFixed(1)} ｜策略眼里 nb=${pol.nb.length} neut=${pol.neutral} ｜worth=${e.worth.toFixed(1)}（m=${e.m.toFixed(3)}）cheap=${e.cheap.toFixed(1)} 超软上限=${e.over ? '是' : '否'} 其余真人密度中位=${e.dMedOther === null ? '-' : e.dMedOther.toFixed(0)} ｜NFS 锁=${pol.isNoFullSend ? '是' : '否'} 影子配额=${k(pol.shadowQuota)}`);
  if (prot.length) console.log(`        不在 nb 里的真实邻居（保护名单）：${prot.join('；')}`);
  for (const r of e.rows) {
    const s = r.safe === undefined ? '' : ` safe=${k(r.safe)}${r.safeCap ? `(封顶 ${r.safeCap}×地；原 ${k(r.safeRaw)})` : ''} keep=${k(r.keep)} avail=${k(r.avail)}`;
    console.log(`        报价 ${nm(r.q)} ${r.person ? '真人' : '非真人'} 接${r.cnt} 地${g.terr[r.q]} 兵${k(g.bal[r.q])} 密${(g.bal[r.q] / Math.max(1, g.terr[r.q])).toFixed(0)} tD=${r.tD.toFixed(2)} c=${r.c.toFixed(1)} need=${k(r.need)}${r.flags.length ? ' [' + r.flags.join(',') + ']' : ''}${s} → ${r.gate}${r.send ? `：${k(r.send)}（${(100 * r.send / e.B).toFixed(1)}% 兵）` : ''}`);
  }
  if (!e.rows.length) console.log('        offers 为空（nb 里没有可报价的邻居）');
  if (has('boatcheck')) console.log(boatLine(sh));
  if (has('mtncheck')) console.log(mtnLine(sh));
  if (acted !== null) {
    const mine = sh.cmds.filter((c) => c.t === g.t);
    console.log(`        影子 act() 这一拍发出：${mine.length ? mine.map((c) => `${{ atk: '攻', boat: '船', don: '捐' }[c.k]}→${c.to < 0 ? '?' : nm(c.to)} ${c.pct}‰ ${k(c.amt)}`).join('；') : '无'}`);
  }
};

// ---- 主循环 -----------------------------------------------------------------------------------
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
const checksAt = new Map();
for (const c of inp.checks) {
  if (!checksAt.has(c.t)) checksAt.set(c.t, []);
  checksAt.get(c.t).push(c);
}
let chkN = 0, chkOk = 0;
// 与真引擎重放（eng_replay.cjs 写的 sim_state.json）逐采样拍核对全体真人的 (领土, 兵力)；我方号另有逐拍核对
let truth = null;
try { truth = JSON.parse(fs.readFileSync(path.join(OUT, mid, 'sim_state.json'), 'utf8')); } catch (err) { truth = null; }
const truthIdx = new Map();
if (truth) truth.ticks.forEach((t, i) => truthIdx.set(t, i));
const div = { firstT: -1, firstWho: [], squadFirst: {}, lastOkT: -1, drift: {} };
const cmpTruth = () => {
  if (!truth) return;
  const pt = truth.perTick;
  if (pt && pt.bal) {
    const i = g.t - pt.t0;
    for (const p of squad) {
      if (div.squadFirst[p] !== undefined) continue;
      const tb = pt.bal[p] ? pt.bal[p][i] : undefined, tt = pt.terr[p] ? pt.terr[p][i] : undefined;
      if (tb === undefined || tb === null || tt === undefined) continue;
      const sb = g.alive[p] ? g.bal[p] : -1, stt = g.alive[p] ? g.terr[p] : 0;
      if (sb !== tb || stt !== tt) div.squadFirst[p] = { t: g.t, sim: [stt, sb], eng: [tt, tb] };
    }
    // 分叉之后偏了多少：每个我方号记兵力相对偏差和领土偏差的最大值（两边都活着的拍）
    for (const p of squad) {
      const tb = pt.bal[p] ? pt.bal[p][i] : undefined, tt = pt.terr[p] ? pt.terr[p][i] : undefined;
      if (tb === undefined || tb === null || tb < 0 || !g.alive[p]) continue;
      const m = (div.drift[p] = div.drift[p] || { balRel: 0, balT: -1, terrAbs: 0, terrT: -1 });
      const r = Math.abs(g.bal[p] - tb) / Math.max(1000, tb), dt = Math.abs(g.terr[p] - tt);
      if (m.offT === undefined && (r > 0.02 || dt > Math.max(10, 0.02 * tt))) m.offT = g.t;
      if (r > m.balRel) { m.balRel = r; m.balT = g.t; }
      if (dt > m.terrAbs) { m.terrAbs = dt; m.terrT = g.t; }
    }
  }
  const i = truthIdx.get(g.t);
  if (i === undefined || div.firstT >= 0) return;
  const bad = [];
  for (let p = 0; p < H; p++) {
    const tt = truth.hum[p].terr[i], tb = truth.hum[p].bal[i];
    const stt = g.alive[p] ? g.terr[p] : 0;
    if (stt !== tt || (g.alive[p] && tt > 0 && g.bal[p] !== tb)) bad.push({ p, sim: [stt, g.alive[p] ? g.bal[p] : -1], eng: [tt, tb] });
  }
  if (bad.length) { div.firstT = g.t; div.firstWho = bad.slice(0, 8); } else div.lastOkT = g.t;
};
const t0 = Date.now();
while (!g.over && g.t < TO) {
  cmpTruth();
  const cs = checksAt.get(g.t);
  if (cs) {
    for (const c of cs) {
      chkN++;
      let hit = false;
      for (const p of squad) if (g.alive[p] && g.terr[p] === c.terr && g.bal[p] === c.bal) { chkOk++; hit = true; break; }
      if (!hit && process.env.PROBE_CHECK_DEBUG && chkN - chkOk <= 12) console.log(`[核对不上] t=${c.t} ${c.name} 日志 地${c.terr} 兵${c.bal}`);
    }
  }
  if (!step()) break;
  // 影子在「这一拍的指令已执行、引擎还没走这一拍」的局面上决策（与真机 afterTick 的时点相当）
  for (const sh of shadows.values()) {
    const me = sh.me;
    if (!g.alive[me] || g.state[me] === 2) continue;
    if (NFS !== null) sh.pol.isNoFullSend = !!NFS;
    const dump = DUMPS.find((x) => x.p === me && g.t >= x.a && g.t <= x.b && (g.t - x.a) % x.st === 0);
    const nfs0 = sh.pol.isNoFullSend;
    try {
      sh.pol.act(sh.view);
    } catch (err) {
      if (!sh.err++) sh.firstErr = `t=${g.t} ${err && err.stack ? err.stack.split('\n').slice(0, 3).join(' | ') : err}`;
    }
    if (!nfs0 && sh.pol.isNoFullSend && sh.nfsT === undefined) sh.nfsT = g.t;
    if (TALLY && g.t % sh.pol.p.period === 0 && g.t >= 100) {
      try { tallyTick(sh); } catch (err) { if (!sh.terr) sh.terr = `t=${g.t} ${err && err.stack ? err.stack.split('\n').slice(0, 3).join(' | ') : err}`; }
    }
    if (dump) printDump(sh, true);
  }
  g.tick();
}
if (truth) {
  const sq = Object.entries(div.squadFirst).sort((a, b) => a[1].t - b[1].t);
  console.log(`${mid}: 干净模拟器 vs 真引擎重放：全体真人在采样拍一致到 t=${div.lastOkT}` + (div.firstT >= 0 ? `，第一处不同 t=${div.firstT}：${div.firstWho.map((b) => `${nm(b.p)}#${b.p} 模拟器 地${b.sim[0]}/兵${b.sim[1]} 真引擎 地${b.eng[0]}/兵${b.eng[1]}`).join('；')}` : '，没有不同'));
  const dr = Object.entries(div.drift).filter(([, v]) => v.balRel > 0 || v.terrAbs > 0).sort((a, b) => b[1].balRel - a[1].balRel);
  console.log(`        我方号分叉后的最大偏差（兵力相对值@拍，领土格数@拍）：${dr.length ? dr.map(([p, v]) => `${nm(+p)} ${(100 * v.balRel).toFixed(2)}%@${v.balT} ${v.terrAbs}格@${v.terrT}${v.offT !== undefined ? ` 偏差首次超过2%的拍=${v.offT}` : ' 全程偏差≤2%'}`).join('；') : '没有'}`);
  console.log(`        我方号逐拍第一处不同：${sq.length ? sq.slice(0, 20).map(([p, v]) => `${nm(+p)}@${v.t}(模拟器 ${v.sim[0]}/${v.sim[1]} 真 ${v.eng[0]}/${v.eng[1]})`).join('；') : '没有'}`);
}
if (oddLandings.length) console.log(`        船落在水/边界/山格（按真引擎 acN 处理：对归属位席位开攻击线或原数退回）${oddLandings.length} 次，共 ${k(oddLandings.reduce((a, b) => a + b.troops, 0))} 兵；第一次 t=${oddLandings[0].t} #${oddLandings[0].p}`);
console.log(`${mid}: 影子重演到 t=${g.t}，耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s；日志快照核对 ${chkOk}/${chkN}；策略 ${VER}，g.online=${ONLINE}${NFS !== null ? `，强制 NFS=${NFS}` : ''}`);
for (const sh of shadows.values()) {
  if (sh.err) console.log(`  me=${sh.me} 影子策略抛错 ${sh.err} 次，第一次：${sh.firstErr}`);
  if (sh.terr) console.log(`  me=${sh.me} tally 抛错，第一次：${sh.terr}`);
}
if (NFS === null) {
  const on = [...shadows.values()].filter((sh) => sh.nfsT !== undefined).map((sh) => `${names[sh.me]}@${sh.nfsT}`);
  const off = [...shadows.values()].filter((sh) => sh.nfsT === undefined).map((sh) => names[sh.me]);
  console.log(`影子的 isNoFullSend 置真拍（按代码 L3831-3843 的条件在真实余额轨迹上演化；影子的指令不执行，余额下跌只来自录像里真实执行的指令和挨打）：${on.join('，') || '无'}｜始终为假：${off.join('，') || '无'}`);
}
if (WIN > 0) {
  for (const sh of shadows.values()) {
    const me = sh.me;
    console.log(`== me=${me} ${names[me]} 每 ${WIN} 拍：影子想发 / 录像里实际执行（攻=对玩家陆攻，无=打无主地，船，捐）；NFS 锁=${sh.pol.isNoFullSend ? '是' : '否'}`);
    const rows = new Map();
    const bump = (t, key, to) => {
      const w = Math.floor(t / WIN) * WIN;
      if (!rows.has(w)) rows.set(w, { sAtk: 0, sNeu: 0, sBoat: 0, sDon: 0, aAtk: 0, aNeu: 0, aBoat: 0, aDon: 0, sTo: new Map(), aTo: new Map() });
      const r = rows.get(w);
      r[key]++;
      if (to !== undefined && to !== NEUTRAL && to >= 0) {
        const mm = key[0] === 's' ? r.sTo : r.aTo;
        mm.set(to, (mm.get(to) || 0) + 1);
      }
    };
    for (const c of sh.cmds) bump(c.t, c.k === 'atk' ? (c.to === NEUTRAL ? 'sNeu' : 'sAtk') : c.k === 'boat' ? 'sBoat' : 'sDon', c.to);
    for (const c of actual) if (c.p === me && c.ok) bump(c.t, c.k === 'atk' ? (c.to === NEUTRAL ? 'aNeu' : 'aAtk') : c.k === 'boat' ? 'aBoat' : 'aDon', c.to);
    for (const w of [...rows.keys()].sort((a, b) => a - b)) {
      const r = rows.get(w);
      const f = (mm) => [...mm.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([q, n]) => `${names[q] || 'bot' + q}×${n}`).join(' ');
      console.log(`   t=${String(w).padStart(5)} 影子 攻${r.sAtk} 无${r.sNeu} 船${r.sBoat} 捐${r.sDon} ｜实际 攻${r.aAtk} 无${r.aNeu} 船${r.aBoat} 捐${r.aDon} ｜影子目标 ${f(r.sTo) || '-'} ｜实际目标 ${f(r.aTo) || '-'}`);
    }
  }
}
if (has('json')) {
  const o = {};
  for (const sh of shadows.values()) o[sh.me] = { cmds: sh.cmds, sends: sh.pol._sends, nfs: sh.pol.isNoFullSend ? 1 : 0, nfsT: sh.nfsT ?? -1, err: sh.err };
  fs.writeFileSync(path.join(OUT, mid, PART ? `probe.part${PART[0]}of${PART[1]}.json` : 'probe.json'), JSON.stringify({ matchId: mid, strategy: VER, online: ONLINE, to: g.t, ...(PART ? { part: `${PART[0]}/${PART[1]}`, meAll } : {}), check: [chkOk, chkN], simVsEngine: truth ? { lastOkT: div.lastOkT, firstT: div.firstT, firstWho: div.firstWho, squadFirst: div.squadFirst, drift: div.drift } : null, shadows: o, actual, tally }));
}
