#!/usr/bin/env node
// resim.mjs — 用仓库自带的模拟器（/agent/repos/c136-data/src/sim/sim，只读）按录像把一局重放一遍，
// 并与我方日志里的 [HL-TICK] 快照（traj.csv：每 90 拍一次的领土/余额）逐点比对，量出“模拟器重放”与线上的偏差。
//
// 为什么要比：模拟器是线上客户端的移植版，重放是否逐拍一致没有人验证过。只有比对通过的拍段，才能把重放得到的
// 全场状态（对手余额、谁在打谁）当证据用；比对不过的拍段只能当线索。
//
// 用法：
//   cd c136-review/agents/R04
//   timeout 60 python3 scripts/replay_lib.py --teams-json /agent/repos/c136-data/bundles/A013/replay.txt > tmp/A013.teams.json
//   HEAVY_QUEUE=90 timeout 115 bash ../../tools/run-heavy.sh node scripts/resim.mjs A013 tmp/A013.teams.json [--until T] [--dump out.tsv]
// 输出：逐个 90 拍快照的比对汇总（完全一致的点数、首次不一致的拍号、领土/余额相对偏差的分位数）。
import fs from 'node:fs';
import path from 'node:path';

const DATA = '/agent/repos/c136-data';
const { Game, loadMap, NEUTRAL } = await import(`${DATA}/src/sim/sim/index.js`);
const { decodeReplay, mapOf } = await import(`${DATA}/src/sim/tools/c102-replay-lib.mjs`);

const args = process.argv.slice(2);
const mid = args[0];
const teamsFile = args[1];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const until = +opt('until', 1e9);
const dump = opt('dump', null);

const dir = path.join(DATA, 'bundles', mid);
const d = decodeReplay(fs.readFileSync(path.join(dir, 'replay.txt'), 'utf8'));
const vu = d.vu;
const H = vu.humanCount;
const tj = JSON.parse(fs.readFileSync(teamsFile, 'utf8'));
const { mapIdx, mapSeed } = mapOf(vu);
const map = loadMap(mapIdx, mapSeed);
const gopts = {
  map,
  humans: H,
  players: vu.playerCount,
  difficulty: H > 1 ? 0 : vu.botDifficultyValue,
  spawnSeed: vu.spawningSeed,
  selectableSpawn: !!vu.selectableSpawn,
  battleRoyaleMode: vu.battleRoyaleMode,
  humanColors: vu.colorsData ? Array.from(vu.colorsData.subarray(0, H)) : [0],
  passableWater: vu.passableWater,
  passableMountains: vu.passableMountains,
};
if (tj.teams) {
  gopts.teams = tj.fX;
  gopts.nTeams = tj.teams;
  if (tj.botsTeamless) gopts.botTeams = false;
}
const g = new Game(gopts);
g.me = vu.selectedPlayer;

// 日志快照
const snaps = new Map(); // t -> [{bot, me, terr, bal}]
const results = fs.readFileSync(path.join(dir, 'results.csv'), 'utf8').trim().split('\n').slice(1).map((l) => l.split(','));
const idOf = new Map();
for (let p = 0; p < H; p++) {
  const nm = tj.names[p] || '';
  const m = nm.match(/\[APEX\]\s*([a-z0-9_]+)/i);
  if (m) idOf.set(m[1], p);
}
for (const r of results) if (!idOf.has(r[0])) idOf.set(r[0], +r[1]);
const trajLines = fs.readFileSync(path.join(dir, 'traj.csv'), 'utf8').trim().split('\n');
const th = trajLines[0].split(',');
const ci = (n) => th.indexOf(n);
for (const l of trajLines.slice(1)) {
  const c = l.split(',');
  const bot = c[ci('bot')];
  const t = +c[ci('t')];
  if (!idOf.has(bot) || !Number.isFinite(t)) continue;
  if (!snaps.has(t)) snaps.set(t, []);
  snaps.get(t).push({ bot, me: idOf.get(bot), terr: +c[ci('terr')], bal: +c[ci('bal')] });
}

let iv = 0, iw = 0, ix = 0, iy = 0;
const stat = { donOk: 0, donRej: 0, atkOk: 0, atkRej: 0, boatOk: 0, boatRej: 0 };
const execCmd = (c) => {
  const { id, player, dX, dZ } = c;
  if (id === 0) g.chooseSpawn(dX % g.W, Math.floor(dX / g.W), player, false);
  else if (id === 1) { if (g.attack(dX, dZ, player)) stat.atkOk++; else stat.atkRej++; }
  else if (id === 2) { if (g.donate(dX, dZ, player)) stat.donOk++; else stat.donRej++; }
  else if (id === 3) { if (g.boat(dX, dZ >> 3, dZ & 7, player)) stat.boatOk++; else stat.boatRej++; }
  else if (id === 4) { if (dX === 849) g.recall(dZ, player); else g.chase(dX, dZ, player); }
  else if (id === 5) { if (dX !== 513) g.retreat(dX, player); }
  else if (id === 8 || id === 9) {
    if (g.spawnPhase) {
      g.eliminate(player);
      let n = g.aliveCount;
      for (let i = n - 1; i >= 0; i--) if (g.alive[g.aliveList[i]] === 0) g.aliveList[i] = g.aliveList[--n];
      g.aliveCount = n;
    } else g.leave(player);
  }
};
const step = () => {
  if (iv >= d.ja.length) return false;
  const jZ = d.ja[iv];
  if (d.jY[iv]) {
    for (let a1 = iw; a1 < iw + jZ; a1++) execCmd(d.cmds[a1]);
    iw += jZ;
    iv++;
  } else if (++ix >= jZ) { iv++; ix = 0; }
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

const rows = [];
const cmp = (phase) => {
  const list = snaps.get(g.t);
  if (!list) return;
  for (const s of list) rows.push({ t: g.t, phase, bot: s.bot, me: s.me, lt: s.terr, lb: s.bal, st: g.terr[s.me], sb: g.bal[s.me], alive: g.alive[s.me] });
};
const t0 = Date.now();
// 日志是策略在“第 t 拍的指令执行之前还是之后”打的并不确定：两种相位都比（pre = 当拍指令执行前，post = 执行后、结算前）
while (!g.over && g.t <= until) {
  cmp('pre');
  if (!step()) break;
  cmp('post');
  g.tick();
}
const ms = Date.now() - t0;

const summarize = (phase) => {
  const R = rows.filter((r) => r.phase === phase);
  let exact = 0, firstBad = -1;
  const byT = new Map();
  for (const r of R) {
    const ok = r.lt === r.st && r.lb === r.sb;
    if (ok) exact++;
    if (!byT.has(r.t)) byT.set(r.t, [0, 0]);
    byT.get(r.t)[ok ? 0 : 1]++;
  }
  const ts = [...byT.keys()].sort((a, b) => a - b);
  for (const t of ts) if (byT.get(t)[1] > 0) { firstBad = t; break; }
  let lastAllOk = -1;
  for (const t of ts) { if (byT.get(t)[1] === 0) lastAllOk = t; else break; }
  const terrOk = R.filter((r) => r.lt === r.st).length;
  console.log(`[${phase}] 快照点 ${R.length}：领土与余额都完全一致 ${exact}，仅领土一致 ${terrOk}；从头起连续全对到 t=${lastAllOk}，首次出现不一致 t=${firstBad}`);
  // 分段偏差
  const bands = [[0, 630], [630, 1530], [1530, 3060], [3060, 4500], [4500, 1e9]];
  for (const [a, b] of bands) {
    const S = R.filter((r) => r.t >= a && r.t < b && r.lt > 0);
    if (!S.length) continue;
    const dt = S.map((r) => Math.abs(r.st - r.lt) / Math.max(1, r.lt)).sort((x, y) => x - y);
    const db = S.map((r) => Math.abs(r.sb - r.lb) / Math.max(1, r.lb)).sort((x, y) => x - y);
    const q = (arr, f) => arr[Math.min(arr.length - 1, Math.floor(f * arr.length))];
    const ex = S.filter((r) => r.lt === r.st && r.lb === r.sb).length;
    console.log(`   t∈[${a},${b === 1e9 ? '∞' : b})：点数 ${S.length}，完全一致 ${ex}；领土相对偏差 中位 ${(100 * q(dt, 0.5)).toFixed(2)}% / 90 分位 ${(100 * q(dt, 0.9)).toFixed(2)}%；余额相对偏差 中位 ${(100 * q(db, 0.5)).toFixed(2)}% / 90 分位 ${(100 * q(db, 0.9)).toFixed(2)}%`);
  }
};
console.log(`== ${mid} 重放到 t=${g.t}（录像步 ${iv}/${d.ja.length}，用时 ${ms}ms，over=${g.over}）；地图 ${mapIdx}_${mapSeed} 陆地 ${g.land}；真人 ${H}，队数 ${tj.teams}，内置 AI 无队=${!!tj.botsTeamless}`);
console.log(`   模拟器对录像指令的受理：陆攻 接受 ${stat.atkOk}/拒 ${stat.atkRej}；捐款 接受 ${stat.donOk}/拒 ${stat.donRej}；发船 接受 ${stat.boatOk}/拒 ${stat.boatRej}（录像只含线上已接受的指令，所以“拒”= 重放状态已偏离线上）`);
summarize('pre');
summarize('post');
if (dump) {
  const out = ['t\tphase\tbot\tme\tlogTerr\tsimTerr\tlogBal\tsimBal\talive'];
  for (const r of rows) out.push([r.t, r.phase, r.bot, r.me, r.lt, r.st, r.lb, r.sb, r.alive].join('\t'));
  fs.writeFileSync(dump, out.join('\n') + '\n');
}
