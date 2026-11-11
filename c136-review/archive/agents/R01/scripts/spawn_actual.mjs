#!/usr/bin/env node
// spawn_actual.mjs — 每个本队号实际从哪里出生（开局第 1 拍领土包围盒的中心），和日志里拿到的出生位置对不对得上。
// 用途：出生指令没有落地的号由引擎在出生阶段结束时随机放（game.js endSpawnPhase L657–666），resim_report 的 spawn 一节对这些号只写“没有出生指令”，这里补上实际位置。
// 用法：node spawn_actual.mjs <matchId> [--replay other] [--log id1,id2] [--bots a,b]
// 输出：号 | 席位 | 实际出生点 | 录像里落地的出生指令条数（最后一条在出生阶段第几步） | 日志里协调器给的位置（各版，[HL-SPAWN-BACKEND]）| 本地兜底位置（[HL-SPAWN]）
//       | 实际点离最后一版协调器位置多远 | 最近的本队号及距离；末尾：出生阶段共几步、全场有出生指令的人类席位数、本队两两距离的最小/中位/最大。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openMatch, readLogSnaps } from './resim_lib.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUNDLES = '/agent/repos/c136-data/bundles';
const argv = process.argv.slice(2);
const mid = argv[0];
const opt = (k, d) => (argv.includes('--' + k) ? argv[argv.indexOf('--' + k) + 1] : d);
const rp = opt('replay', mid);
const logs = opt('log', mid).split(',');

const me = {}; const backend = {}; const local = {};
for (const id of logs) {
  const r = readLogSnaps(id, '', opt('bots', null) ? new Set(opt('bots', '').split(',')) : null);
  Object.assign(me, r.me);
  const f = `${BUNDLES}/${id}/in_game.log`;
  if (!fs.existsSync(f)) continue;
  for (const line of fs.readFileSync(f, 'utf8').split('\n')) {
    let m = line.match(/\[([^\]]+)\] \[HL-SPAWN-BACKEND\] me=(\d+).*-> \((\d+),(\d+)\)/);
    if (m) { (backend[m[1]] ??= []).push([+m[3], +m[4]]); continue; }
    m = line.match(/\[([^\]]+)\] \[HL-SPAWN\] me=(\d+).*-> \((\d+),(\d+)\)/);
    if (m) (local[m[1]] ??= []).push([+m[3], +m[4]]);
  }
}
const m = openMatch(rp);
const g = m.g;
// 录像里的出生指令（replay_cmds.csv 由 replay_cmds.mjs 写）：player -> [步号…]
const spawnSteps = {}, spawnPix = {}; let spawnPlayers = new Set(), nSpawn = 0;
const rc = path.resolve(HERE, '../out', mid, 'replay_cmds.csv');
if (fs.existsSync(rc)) {
  const L = fs.readFileSync(rc, 'utf8').trim().split('\n'); const h = L[0].split(',');
  const iK = h.indexOf('kind'), iP = h.indexOf('player'), iS = h.indexOf('step');
  const iD = h.indexOf('dX');
  for (const ln of L.slice(1)) { const c = ln.split(','); if (c[iK] !== 'spawn') continue; nSpawn++; spawnPlayers.add(+c[iP]); (spawnSteps[+c[iP]] ??= []).push(+c[iS]); (spawnPix[+c[iP]] ??= []).push(+c[iD]); }
}
while (g.t < 1 && m.tick());
const pos = {};
for (const [bot, p] of Object.entries(me)) pos[bot] = [(g.x0[p] + g.x1[p]) >> 1, (g.y0[p] + g.y1[p]) >> 1];
const bots = Object.keys(me).sort((a, b) => me[a] - me[b]);
const dist = (a, b) => Math.round(Math.hypot(a[0] - b[0], a[1] - b[1]));
const out = ['bot,p,x,y,spawnCmds,lastStep,backendLast,distToBackend,localLast,nearestMate,nearestDist'];
console.log(`== ${mid} 实际出生点（第 ${g.t} 拍领土包围盒中心）；地图 ${g.W}x${g.H}`);
for (const b of bots) {
  const p = me[b], P = pos[b];
  const st = spawnSteps[p] || [];
  const be = backend[b] || [], lo = local[b] || [];
  const beL = be[be.length - 1], loL = lo[lo.length - 1];
  let nm = null, nd = 1e9;
  for (const o of bots) if (o !== b) { const d = dist(P, pos[o]); if (d < nd) { nd = d; nm = o; } }
  console.log(`  ${b.padEnd(8)} #${String(p).padStart(2)} 实际 (${P[0]},${P[1]}) | 落地出生指令 ${st.length} 条${st.length ? `（最后一条第 ${st[st.length - 1]} 步）` : ''} | 协调器 ${be.length} 版：${be.map((q) => `(${q[0]},${q[1]})`).join('→') || '无'}`
    + ` | 本地兜底 ${lo.map((q) => `(${q[0]},${q[1]})`).join('→') || '无'} | 离最后一版协调器位置 ${beL ? dist(P, beL) : '-'} | 最近本队号 ${nm} ${nd}`);
  out.push([b, p, P[0], P[1], st.length, st.length ? st[st.length - 1] : '', beL ? beL.join(':') : '', beL ? dist(P, beL) : '', loL ? loL.join(':') : '', nm, nd].join(','));
}
// 协调器各版位置里哪几版在录像里有落地的出生指令（像素完全相同才算）
let v1 = 0, v1Hit = 0, vN = 0, vNHit = 0;
for (const b of bots) {
  const be = backend[b] || [], pix = new Set(spawnPix[me[b]] || []);
  be.forEach((q, i) => { const hit = pix.has(q[1] * g.W + q[0]); if (i === 0) { v1++; if (hit) v1Hit++; } else { vN++; if (hit) vNHit++; } });
}
console.log(`  协调器给的位置：第 1 版 ${v1} 个，其中录像里有同像素出生指令落地的 ${v1Hit} 个；第 2 版及以后 ${vN} 个，落地 ${vNHit} 个（同一个号前后给过同一个位置的按版各算一次）`);
const ds = [];
for (let i = 0; i < bots.length; i++) for (let j = i + 1; j < bots.length; j++) ds.push(dist(pos[bots[i]], pos[bots[j]]));
ds.sort((a, b) => a - b);
const meta = JSON.parse(fs.readFileSync(path.resolve(HERE, '../out', mid, 'replay_meta.json'), 'utf8'));
console.log(`  出生阶段 ${meta.spawnSteps} 步；全场 ${meta.humans} 个人类席位里 ${spawnPlayers.size} 个有出生指令落地（共 ${nSpawn} 条）；本队 ${bots.filter((b) => (spawnSteps[me[b]] || []).length).length}/${bots.length} 个号有`);
console.log(`  本队两两距离 最小/中位/最大 = ${ds[0]}/${ds[ds.length >> 1]}/${ds[ds.length - 1]} 像素`);
const outDir = path.resolve(HERE, '../out', mid);
fs.writeFileSync(path.join(outDir, 'spawn_actual.csv'), out.join('\n') + '\n');
