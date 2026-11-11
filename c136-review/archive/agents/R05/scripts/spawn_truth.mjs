// spawn_truth.mjs — 选点「真账」：日志里的选点指派（[HL-SPAWN-BACKEND]/[HL-SPAWN]）对照录像里真正执行的出生指令。
// 背景：协调器在选点阶段会反复重算、换位（一局 20~30 次），日志最后一条指派不一定来得及执行；
//   真正的出生点 = 录像里该号最后一条 spawn 指令（id=0，dX=像素下标=y*W+x）。
// 做法：
//   1) 号名校验把日志里的号对到录像玩家；
//   2) 地图宽 W 未知 → 枚举 W，使「我方号所有 spawn 像素解出的 (x,y)」落在「日志出现过的指派点集合」里的条数最多；
//   3) 用 W 解出全场所有真人的最终出生点；
//   4) 输出每局一行汇总 + （--detail）逐号明细。
// 汇总列：matchId cohort W ourInReplay spawnCmdsOurs finalEqLastLog(最终执行点=日志最后指派 的号数) lateLogs(日志最后指派晚于最终执行、未被执行的号数)
//         minPair(我方最终点两两最小距离) medNearestAlly maxFromCentroid(我方点到质心最大距离) othersWithin(质心 maxFromCentroid 半径内的非我方真人数)
//         medNearestOther(我方各号到最近非我方真人出生点距离的中位) minNearestOther rolesExecuted(按最终执行点对应的日志角色计数)
// 用法：node spawn_truth.mjs [matchId ...] [--detail]
import fs from 'node:fs';
import path from 'node:path';
import { loadReplay, timeline } from './replay_cmds.mjs';

const DATA = process.env.C136_DATA || '/agent/repos/c136-data';
const args = process.argv.slice(2);
const detail = args.includes('--detail');
const idsArg = args.filter((a) => !a.startsWith('--'));
const ids = idsArg.length ? idsArg : fs.readdirSync(path.join(DATA, 'bundles')).sort();
const bare = (n) => String(n ?? '').replace(/\[[^\]]*\]/g, '').trim().toLowerCase();
const med = (a) => { if (!a.length) return ''; const s = [...a].sort((x, y) => x - y); return s[s.length >> 1]; };

export function spawnTruth(id) {
  const dir = path.join(DATA, 'bundles', id);
  const logp = path.join(dir, 'in_game.log');
  if (!fs.existsSync(logp) || !fs.existsSync(path.join(dir, 'replay.txt'))) return null;
  const card = JSON.parse(fs.readFileSync(path.join(dir, 'card.json'), 'utf8'));
  const d = loadReplay(id); const tl = timeline(d);
  const H = d.vu.humanCount; const names = d.vu.playerNamesData ? d.vu.playerNamesData.data : [];
  // 日志指派
  const assigns = new Map(); // bot -> [{x,y,role,slot,line,me}]
  const re = /^(\d+)\s+\[([^\]]+)\] \[HL-SPAWN(-BACKEND)?\] me=(\d+) slot=(\d+)(?: role=(\w+))?.*?-> \((\d+),(\d+)\)/;
  const meOf = new Map();
  for (const line of fs.readFileSync(logp, 'utf8').split('\n')) {
    const m = re.exec(line);
    if (!m) { const g = /\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)/.exec(line); if (g && !meOf.has(g[1])) meOf.set(g[1], +g[2]); continue; }
    const bot = m[2];
    if (!assigns.has(bot)) assigns.set(bot, []);
    assigns.get(bot).push({ line: +m[1], backend: !!m[3], me: +m[4], slot: +m[5], role: m[6] || (m[3] ? 'SQUAD' : 'AUTONOMOUS'), x: +m[7], y: +m[8] });
    if (!meOf.has(bot)) meOf.set(bot, +m[4]);
  }
  // 号名校验
  const pid = new Map();
  for (const [bot, me] of meOf) {
    if (me < H && bare(names[me]) === bot.toLowerCase()) pid.set(bot, me);
    else { for (let p = 0; p < H; p++) if (bare(names[p]) === bot.toLowerCase()) { pid.set(bot, p); break; } }
  }
  const ourIds = new Set(pid.values());
  // spawn 指令
  const spawns = new Map(); // player -> [{tick,pix}]
  for (const c of tl.cmds) if (c.id === 0) { if (!spawns.has(c.player)) spawns.set(c.player, []); spawns.get(c.player).push({ tick: c.tick, pix: c.dX }); }
  const logPts = new Set(); for (const arr of assigns.values()) for (const a of arr) logPts.add(a.x + ',' + a.y);
  const ourPix = []; for (const p of ourIds) for (const s of spawns.get(p) || []) ourPix.push(s.pix);
  let bestW = 0, bestHit = 0;
  if (ourPix.length && logPts.size) {
    for (let W = 100; W < 12000; W++) {
      let hit = 0;
      for (const px of ourPix) if (logPts.has((px % W) + ',' + Math.floor(px / W))) hit++;
      if (hit > bestHit) { bestHit = hit; bestW = W; }
    }
  }
  const okW = bestW > 0 && bestHit >= Math.max(3, 0.6 * ourPix.length);
  const W = okW ? bestW : 0;
  const xy = (px) => (W ? { x: px % W, y: Math.floor(px / W) } : null);
  const bots = [];
  for (const [bot, p] of pid) {
    const sp = spawns.get(p) || [];
    const fin = sp.length ? sp[sp.length - 1] : null;
    const A = assigns.get(bot) || [];
    const lastLog = A.length ? A[A.length - 1] : null;
    const f = fin && W ? xy(fin.pix) : null;
    let roleExec = '';
    if (f) { for (let i = A.length - 1; i >= 0; i--) if (A[i].x === f.x && A[i].y === f.y) { roleExec = A[i].role; break; } }
    bots.push({ bot, player: p, nSpawnCmds: sp.length, finalTick: fin ? fin.tick : null, final: f, lastLog: lastLog ? { x: lastLog.x, y: lastLog.y, role: lastLog.role } : null,
      nAssignLogs: A.length, eqLast: !!(f && lastLog && f.x === lastLog.x && f.y === lastLog.y), roleExec });
  }
  const others = [];
  if (W) for (let p = 0; p < H; p++) { if (ourIds.has(p)) continue; const sp = spawns.get(p); if (!sp || !sp.length) continue; const q = xy(sp[sp.length - 1].pix); others.push({ player: p, name: names[p], ...q, tick: sp[sp.length - 1].tick }); }
  const pts = bots.filter((b) => b.final).map((b) => b.final);
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  let minPair = Infinity; const nearestAlly = [];
  for (let i = 0; i < pts.length; i++) { let m = Infinity; for (let j = 0; j < pts.length; j++) if (i !== j) m = Math.min(m, dist(pts[i], pts[j])); if (pts.length > 1) { nearestAlly.push(Math.round(m)); minPair = Math.min(minPair, m); } }
  const cx = pts.reduce((s, p) => s + p.x, 0) / Math.max(1, pts.length), cy = pts.reduce((s, p) => s + p.y, 0) / Math.max(1, pts.length);
  const maxFromC = pts.length ? Math.max(...pts.map((p) => dist(p, { x: cx, y: cy }))) : 0;
  const within = others.filter((o) => dist(o, { x: cx, y: cy }) <= maxFromC).length;
  const nearestOther = pts.map((p) => (others.length ? Math.round(Math.min(...others.map((o) => dist(p, o)))) : null)).filter((x) => x !== null);
  for (const b of bots) if (b.final && others.length) { let m = Infinity, who = null; for (const o of others) { const dd = dist(b.final, o); if (dd < m) { m = dd; who = o; } } b.nearestOther = { d: Math.round(m), player: who.player, name: who.name }; }
  const roles = {}; for (const b of bots) if (b.final) roles[b.roleExec || '?'] = (roles[b.roleExec || '?'] || 0) + 1;
  // 叠点：两个我方号最终出生点相距 < 12 像素（同一像素或紧挨）
  const dupPairs = [];
  const fb = bots.filter((b) => b.final);
  for (let i = 0; i < fb.length; i++) for (let j = i + 1; j < fb.length; j++) { const dd = dist(fb[i].final, fb[j].final); if (dd < 12) dupPairs.push(`${fb[i].bot}+${fb[j].bot}@(${fb[i].final.x},${fb[i].final.y})`); }
  const nNoSpawnCmd = bots.filter((b) => b.nSpawnCmds === 0).length;
  return { id, cohort: card.cohort, W, wHit: bestHit, wTotal: ourPix.length, H, bots, others, centroid: { x: Math.round(cx), y: Math.round(cy) }, maxFromCentroid: Math.round(maxFromC), othersWithin: within,
    minPair: Number.isFinite(minPair) ? Math.round(minPair) : '', medNearestAlly: med(nearestAlly), medNearestOther: med(nearestOther), minNearestOther: nearestOther.length ? Math.min(...nearestOther) : '', roles, dupPairs, nNoSpawnCmd };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  if (!detail) console.log(['matchId', 'cohort', 'W', 'ourInReplay', 'spawnCmdsOurs', 'finalEqLastLog', 'notExecutedLast', 'minPair', 'medNearestAlly', 'maxFromCentroid', 'othersWithin', 'medNearestOther', 'minNearestOther', 'rolesExecuted', 'noSpawnCmdBots', 'dupPairs'].join('\t'));
  for (const id of ids) {
    let r; try { r = spawnTruth(id); } catch (e) { r = null; }
    if (!r) continue;
    if (detail) {
      console.log(`# ${id} cohort=${r.cohort} W=${r.W} (解出 ${r.wHit}/${r.wTotal}) 真人=${r.H} 我方在录像=${r.bots.length} 质心=(${r.centroid.x},${r.centroid.y}) 最大半径=${r.maxFromCentroid} 半径内非我方真人=${r.othersWithin} 没有出生指令的号=${r.nNoSpawnCmd} 叠点=${r.dupPairs.join(' ') || '无'}`);
      for (const b of r.bots.sort((a, b2) => a.player - b2.player)) {
        console.log(`  ${b.bot.padEnd(12)} #${String(b.player).padEnd(3)} 出生指令=${String(b.nSpawnCmds).padEnd(3)} 最终拍=${b.finalTick} 最终点=${b.final ? `(${b.final.x},${b.final.y})` : '-'} 角色=${b.roleExec || '?'} 日志最后指派=${b.lastLog ? `(${b.lastLog.x},${b.lastLog.y}) ${b.lastLog.role}` : '-'} ${b.eqLast ? '一致' : '不一致'} 最近非我方=${b.nearestOther ? `${b.nearestOther.d}px #${b.nearestOther.player} ${b.nearestOther.name}` : '-'}`);
      }
    } else {
      const eq = r.bots.filter((b) => b.eqLast).length, withFinal = r.bots.filter((b) => b.final).length;
      console.log([id, r.cohort, r.W, r.bots.length, r.wTotal, eq, withFinal - eq, r.minPair, r.medNearestAlly, r.maxFromCentroid, r.othersWithin, r.medNearestOther, r.minNearestOther,
        Object.entries(r.roles).sort().map(([k, v]) => `${k}:${v}`).join(' '), r.nNoSpawnCmd, r.dupPairs.join(' ')].join('\t'));
    }
  }
}
