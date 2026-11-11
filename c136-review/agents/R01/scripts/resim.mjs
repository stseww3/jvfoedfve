// resim.mjs — 逐拍重演整局（512 席位）并与局内日志逐快照核对，同时导出全局事实表。公共部分在 resim_lib.mjs。
//   node resim.mjs <matchId> [--replay <otherMatchId>] [--log id1,id2] [--bots a,b] [--ticks N] [--no-dump] [--every 90] [--sq-every 30]
//                  [--trace t0,t1,p1,p2,...]
// --replay：B 系列包的 replay.txt 是截断的，用同局 A 包的录像。--log：拿哪些包的日志当观测点（默认本包；可加同局对面那支队）。
// 输出 out/<matchId>/：
//   resim_check.csv      每条 [HL-TICK] 的 terr/bal 与重演值逐号比对（ok=1 表示两个数都完全相等）
//   resim_players.csv    每 --every 拍：全部人类号的 队伍/存活/状态(2=离场)/领土/兵力
//   resim_teams.csv      每 --every 拍：各队领土、兵力、存活人数、占全图陆地比例（队 0 = 内置 AI）
//   resim_squad.csv      每 --sq-every 拍：日志里出现的号的详细状态（进攻、被攻、邻居、中立/水接触、船）
//   resim_pairs.csv      每 --every 拍窗口：涉及这些号的丢地/夺地（victim, attacker, px）
//   resim_transfers.csv  全部转账：指令捐款(cmd)、离场号/AI 自动捐款(auto)、运兵船靠队友岸(boat)
//   resim_events.csv     人类号的阵亡(died)/离场(left)/失地未死(landless)，带当时进攻者和累计夺地最多的对手
//   resim_meta.json      地图、队伍、核对统计
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps, NEUTRAL } from './resim_lib.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const rmid = opt('replay', mid);
const maxTicks = +opt('ticks', 1e9);
const every = +opt('every', 90);
const sqEvery = +opt('sq-every', 30);
const noDump = args.includes('--no-dump');
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '..', 'out', mid);
fs.mkdirSync(OUT, { recursive: true });

const m = openMatch(mid, { replay: rmid, rngFix: !args.includes('--no-rngfix') });
const { g, H, tm, names } = m;

// 观测点
const onlyBots = opt('bots', '') ? new Set(opt('bots', '').split(',')) : null; // --bots a,b：只认这些号（见 readLogSnaps）
const squad = {}; // label -> p
const snaps = new Map();
for (const lb of opt('log', mid).split(',')) {
  const { me, rows } = readLogSnaps(lb, lb === mid ? '' : lb + ':', onlyBots);
  for (const [b, p] of Object.entries(me)) squad[(lb === mid ? '' : lb + ':') + b] = p;
  for (const r of rows) { if (!snaps.has(r.t)) snaps.set(r.t, []); snaps.get(r.t).push(r); }
}
const sqIds = new Set(Object.values(squad));
const sqLabel = Object.fromEntries(Object.entries(squad).map(([b, p]) => [p, b]));

// --trace
const tr = opt('trace', '') ? opt('trace', '').split(',').map(Number) : null;
const trSet = tr ? new Set(tr.slice(2)) : null;
const atkStr = (p) => m.atkOut(p).map(([t, v]) => `${t}:${v}`).join('|');
if (tr) m.onCmd = (c, r) => {
  if (g.t >= tr[0] && g.t <= tr[1] && (trSet.has(c.player) || ((c.id === 1 || c.id === 2) && trSet.has(c.dZ)))) console.log(`  cmd t=${g.t} id=${c.id} p=${c.player} dX=${c.dX} dZ=${c.dZ} -> ${r} bal=${g.bal[c.player]} atk=[${atkStr(c.player)}]`);
};

const check = ['t,bot,p,logTerr,simTerr,logBal,simBal,ok'];
const players = ['t,p,team,alive,state,terr,bal'];
const teamsCsv = ['t,team,terr,bal,alive,sharePct'];
const sq = ['t,bot,p,alive,state,terr,bal,dens,room150,atkOut,atkIn,enemyNb,allyNb,huskNb,aiNb,neutralC,waterC,boats,boatTroops'];
const pairs = ['t0,t1,victim,attacker,px'];
const firstBad = {}; let okN = 0, badN = 0;

const dumpPlayers = () => {
  if (noDump) return;
  const tt = new Map();
  for (let p = 0; p < m.vu.playerCount; p++) {
    const team = g.teams[p];
    if (!tt.has(team)) tt.set(team, [0, 0, 0]);
    const a = tt.get(team);
    if (g.alive[p]) { a[0] += g.terr[p]; a[1] += g.bal[p]; a[2]++; }
    if (p < H) players.push([g.t, p, team, g.alive[p], g.state[p], g.terr[p], g.bal[p]].join(','));
  }
  for (const [team, a] of [...tt.entries()].sort((x, y) => x[0] - y[0])) teamsCsv.push([g.t, team, a[0], a[1], a[2], (100 * a[0] / g.land).toFixed(2)].join(','));
};
const nbStr = (list) => list.sort((a, b) => b[1] - a[1]).slice(0, 5).map(([o, c]) => `${o}:${c}:${g.terr[o]}:${g.bal[o]}`).join('|');
const dumpSquad = () => {
  if (noDump) return;
  for (const p of sqIds) {
    if (!g.alive[p]) { sq.push([g.t, sqLabel[p], p, 0, g.state[p], 0, 0, 0, 0, '', '', '', '', '', '', 0, 0, 0, 0].join(',')); continue; }
    const nb = m.neighbours(p);
    const en = [], al = [], hu = [], ai = [];
    for (const [o, c] of nb.players) {
      if (o >= H) ai.push([o, c]);
      else if (g.isEnemy(p, o)) en.push([o, c]);
      else if (g.state[o] === 2) hu.push([o, c]);
      else al.push([o, c]);
    }
    const aiC = ai.reduce((s, x) => s + x[1], 0);
    sq.push([g.t, sqLabel[p], p, 1, g.state[p], g.terr[p], g.bal[p], g.terr[p] ? (g.bal[p] / g.terr[p]).toFixed(1) : 0, 150 * g.terr[p] - g.bal[p],
      atkStr(p), m.atkIn(p).map(([a, v]) => `${a}:${v}`).join('|'), nbStr(en), nbStr(al), nbStr(hu), `${ai.length}:${aiC}`, nb.neutral, nb.water,
      g.boatCount[p], g.boatCount[p] ? g.boatTroops(p) : 0].join(','));
  }
};
let winT0 = g.t;
const dumpPairs = () => {
  if (!noDump) for (const [k, px] of m.lossWin) {
    const [v, a] = k.split('|').map(Number);
    if (sqIds.has(v) || sqIds.has(a)) pairs.push([winT0, g.t, v, a, px].join(','));
  }
  m.lossWin.clear();
  winT0 = g.t;
};

const t0 = Date.now();
dumpPlayers(); dumpSquad();
while (g.t < maxTicks && m.tick()) {
  if (tr && g.t >= tr[0] && g.t <= tr[1]) console.log(`  t=${g.t} ` + tr.slice(2).map((p) => `p${p} terr=${g.terr[p]} bal=${g.bal[p]} atk=[${atkStr(p)}]`).join(' ; '));
  const s = snaps.get(g.t);
  if (s) for (const r of s) {
    const ok = g.terr[r.p] === r.terr && g.bal[r.p] === r.bal;
    check.push([g.t, r.bot, r.p, r.terr, g.terr[r.p], r.bal, g.bal[r.p], ok ? 1 : 0].join(','));
    if (ok) okN++; else { badN++; if (firstBad[r.bot] === undefined) firstBad[r.bot] = g.t; }
  }
  if (g.t % every === 0) { dumpPlayers(); dumpPairs(); }
  if (g.t % sqEvery === 0) dumpSquad();
}
dumpPlayers(); dumpPairs(); dumpSquad();
const ms = Date.now() - t0;

fs.writeFileSync(path.join(OUT, 'resim_check.csv'), check.join('\n') + '\n');
if (!noDump) {
  fs.writeFileSync(path.join(OUT, 'resim_players.csv'), players.join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'resim_teams.csv'), teamsCsv.join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'resim_squad.csv'), sq.join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'resim_pairs.csv'), pairs.join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'resim_transfers.csv'), ['t,from,to,pct,kind,fromBal,toBal,toTerr,paid,received,ok',
    ...m.transfers.map((x) => [x.t, x.from, x.to, x.pct, x.kind, x.fromBal, x.toBal, x.toTerr, x.paid, x.received, x.ok].join(','))].join('\n') + '\n');
  fs.writeFileSync(path.join(OUT, 'resim_events.csv'), ['t,ev,p,team,terr,bal,detail',
    ...m.events.map((x) => [x.t, x.ev, x.p, g.teams[x.p], x.terr, x.bal, x.detail].join(','))].join('\n') + '\n');
}
const firstBadAll = Object.values(firstBad).length ? Math.min(...Object.values(firstBad)) : null;
const meta = { matchId: mid, replayOf: rmid, map: m.map, W: g.W, Hh: g.H, land: g.land, humans: H, players: m.vu.playerCount,
  nTeams: tm ? tm.nTeams : 0, teamCounts: tm ? tm.counts : null, botTeams: tm ? tm.botTeams : null, lastTick: g.t, over: g.over, winnerTeam: g.winnerTeam,
  checkOk: okN, checkBad: badN, firstBad, firstBadTick: firstBadAll, applied: m.applied, rejected: m.rejected, ms,
  teams: tm ? Object.fromEntries(Array.from({ length: H }, (_, p) => [p, tm.fX[p]])) : null,
  names: names.slice(0, H), squad, spawn: m.spawn };
fs.writeFileSync(path.join(OUT, 'resim_meta.json'), JSON.stringify(meta));
console.log(`${mid}: map ${m.map} ${g.W}x${g.H} land=${g.land} humans=${H} nTeams=${meta.nTeams} counts=${JSON.stringify(meta.teamCounts)} lastTick=${g.t} over=${g.over} winner=${g.winnerTeam} ${ms}ms`);
console.log(`  log check: ok=${okN} bad=${badN} firstBad=${JSON.stringify(firstBad)}`);
console.log(`  cmds applied=${JSON.stringify(m.applied)} rejected=${JSON.stringify(m.rejected)}  transfers=${m.transfers.length} events=${m.events.length}`);
if (tm) console.log('  teams: ' + Object.entries(squad).map(([b, p]) => `${b}=T${tm.fX[p]}`).join(' '));
