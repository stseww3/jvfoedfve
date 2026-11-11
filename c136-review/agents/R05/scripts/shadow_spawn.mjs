#!/usr/bin/env node
// shadow_spawn.mjs — 影子选点：把线上同一份协调器源码（spawn-coordinator-c116-<ver>.mjs 的 TeamSpawnCoordinator）
//   放到录像里某个选点拍的真实局面上重新求解一次（只读，不落地），看它给出的锚点、半径和十个点。
//   局面 = 录像里到该拍为止每个真人最后一条出生指令的位置（我方号的当前位置作为 curX/curY 传入，和线上后端一致）。
//   每个采样拍都用一台全新的协调器（没有「角已锁定」「保留旧点」的记忆），所以结果是「此刻从零求解会给什么」；
//   --chain 时改为一台协调器按拍顺序连续求解（带记忆），用来看锁角/旧点的影响。
// 另外复算角落扇形阵的锚点打分（Vb L1079-1131）：每个角方框内每 16 px 一个候选，
//   landSamples = 以它为心、45 ≤ d ≤ min(280,r2) 的 28 px 网格采样点落在同一陆块上的个数（<14 丢弃），
//   metric = landSamples×18 − 到角距离×2.2；并给出「四周陆地 ≤ 一半」的候选里 metric 最好的一个作对照。
// 用法：
//   node scripts/shadow_spawn.mjs <局> [--ver vb] [--at -14,-6,-5,-1] [--chain] [--drop 66,7] [--anchors]
//     --drop  求解时把这些玩家编号从真人列表里拿掉（看某个敌人在不在对结果的影响）
//     --anchors 打印每个角 metric 前 5 的锚点候选
//     --rcell 55,52,51 锚点打分那一段改用这些 rCell 各算一遍（rCell 随已落点真人数变：L838）
//   拆盘局（我方号被大厅分进两个并行实例，协调器只有一台）专用：
//     --slots 18:0,19:7            录像这一盘里的我方号用日志里的真实槽位（玩家编号:槽位），不用默认的按编号排序
//     --phantom 8:0,1:1,…          另一盘里的我方号也登记进 squadBots（槽位:它在另一盘的玩家编号），位置未知（curX=-1）
//                                  → 协调器 L818 会把本盘里「编号与它相同」的真人当成我方号跳过
//     --points                      只打印每个采样拍解出的点集（按 x,y 排序），用来和日志里的 [HL-SPAWN-BACKEND] 对
//     --every a:b                   采样拍改为 a..b 每拍
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { loadReplay, timeline } from './replay_cmds.mjs';
import { simulate, assignTeams, DATA, bare } from './sim_replay.mjs';
import { squadIds } from './match_truth.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const val = (k, d) => (args.includes(k) ? args[args.indexOf(k) + 1] : d);
const verOf = (id) => { if (id[0] === 'B') return 'c110'; const n = +id.slice(1); return n <= 17 ? 'va' : n <= 95 ? 'vb' : 'vc'; };
const ver = val('--ver', verOf(mid));
let AT = String(val('--at', '-14,-6,-5,-1')).split(',').map(Number);
if (args.includes('--every')) { const [a, b] = String(val('--every', '')).split(':').map(Number); AT = []; for (let t = a; t <= b; t++) AT.push(t); }
const SLOTS = new Map(String(val('--slots', '')).split(',').filter(Boolean).map((s) => s.split(':').map(Number)));
const PHANTOM = String(val('--phantom', '')).split(',').filter(Boolean).map((s) => s.split(':').map(Number));
const POINTS = args.includes('--points');
const DROP = new Set(String(val('--drop', '')).split(',').filter(Boolean).map(Number));
const chain = args.includes('--chain');
const SRC = { va: 'spawn-coordinator-c116-va.mjs', vb: 'spawn-coordinator-c116-vb.mjs', vc: 'spawn-coordinator-c116-vc.mjs', c110: 'spawn-coordinator-c110.mjs' }[ver];
const mod = await import(pathToFileURL(path.join(DATA, 'src/strategy', SRC)).href);
const { TeamSpawnCoordinator } = mod;

// 地图与队伍：借重演器在第 0 拍停下
let G = null, INFO = null;
await simulate(mid, { maxTick: 0, onStart(g, info) { G = g; INFO = info; } });
const W = G.W, H = G.H, N = W * H;
const mapType = G.map.type;
const names = INFO.names, HN = INFO.H;
const teams = INFO.T ? INFO.T.teams : null;
const sq = squadIds(mid, names, HN).squad; // Map(pid → bot)
const myTeam = teams ? teams[[...sq.keys()][0]] : 0;

const d = loadReplay(mid);
const tl = timeline(d).cmds;
const spawns = [];
for (const c of tl) if (c.id === 0) spawns.push({ t: c.tick, p: c.player, x: c.dX % W, y: Math.floor(c.dX / W) });
spawns.sort((a, b) => a.t - b.t);

const posAt = (t) => { const m = new Map(); for (const s of spawns) { if (s.t > t) break; m.set(s.p, { x: s.x, y: s.y }); } return m; };
const mk = () => { const c = new TeamSpawnCoordinator(); c.setMap({ matchKey: mid, W, H, mapType }); return c; };
const slotOf = SLOTS.size ? SLOTS : new Map([...sq.keys()].sort((a, b) => a - b).map((p, i) => [p, i]));

function solveAt(co, t) {
  const pos = posAt(t);
  const squadBots = [...sq.entries()].map(([p, bot]) => ({ slot: slotOf.get(p), port: 0, name: names[p], meId: p, curX: pos.get(p)?.x ?? -1, curY: pos.get(p)?.y ?? -1 }));
  for (const [slot, meId] of PHANTOM) squadBots.push({ slot, port: 0, name: `[APEX] phantom${slot}`, meId, curX: -1, curY: -1 });
  const humans = [];
  for (let p = 0; p < HN; p++) {
    if (DROP.has(p)) continue;
    const q = pos.get(p);
    humans.push({ id: p, name: names[p], team: teams ? teams[p] : 0, x: q ? q.x : -1, y: q ? q.y : -1, terr: q ? 12 : 0 });
  }
  const plan = co.solve({ squadBots, humans, myTeam });
  return { plan, pos };
}

const land = mk().land;
console.log(`# ${mid} 协调器 ${SRC}｜地图 ${W}x${H} 陆地 ${land}｜真人 ${HN}，我方 ${sq.size}（队 ${myTeam}）｜全场出生指令 ${spawns.length} 条（拍 ${spawns[0]?.t}…${spawns[spawns.length - 1]?.t}）${DROP.size ? `｜求解时拿掉玩家 ${[...DROP].join(',')}` : ''}${chain ? '｜连续求解（带记忆）' : '｜每拍全新求解'}`);

let coChain = chain ? mk() : null;
for (const t of AT) {
  const co = chain ? coChain : mk();
  const { plan, pos } = solveAt(co, t);
  if (!plan.ok) { console.log(`t=${t} 求解失败 ${plan.error}`); continue; }
  const placed = [...pos.keys()].filter((p) => !sq.has(p) && !DROP.has(p)).length;
  const L = plan.list.slice().sort((a, b) => a.slot - b.slot);
  if (POINTS) {
    const key = L.map((e) => `${e.x},${e.y}`).sort().join(' ');
    const mine = L.filter((e) => sq.has(e.meId) && !PHANTOM.some(([s]) => s === e.slot)).map((e) => `${bare(e.name)}=s${e.slot}:${e.role}(${e.x},${e.y})`).join(' ');
    console.log(`t=${t} 已落点 ${placed}（敌 ${plan.enemyCount} 友 ${plan.randomAllyCount}）rCell ${plan.scales.rCell}｜${mine}｜点集 ${key}`);
    continue;
  }
  const cx = L.reduce((s, e) => s + e.x, 0) / L.length, cy = L.reduce((s, e) => s + e.y, 0) / L.length;
  const apex = L.find((e) => e.role === 'CORNER_APEX_BANK');
  const far = Math.max(...L.map((e) => Math.hypot(e.x - cx, e.y - cy)));
  console.log(`t=${t} 已落点的其他真人 ${placed}（敌 ${plan.enemyCount} 友 ${plan.randomAllyCount}）｜scales ${JSON.stringify(plan.scales)}｜质心 (${Math.round(cx)},${Math.round(cy)}) 最远 ${Math.round(far)} 最小间距 ${plan.minPairwiseDist}｜锁角 ${co.lockedCornerName ?? '-'}｜角尖 ${apex ? `(${apex.x},${apex.y})` : '-'}`);
  for (const e of L) {
    const real = pos.get(e.meId);
    let nearest = null;
    for (const [p, q] of pos) { if (sq.has(p) || DROP.has(p)) continue; const dd = Math.hypot(q.x - e.x, q.y - e.y); if (!nearest || dd < nearest.d) nearest = { d: dd, p }; }
    console.log(`    ${bare(e.name).padEnd(8)} ${e.role.padEnd(18)} → (${e.x},${e.y}) 最近队友 ${e.minAllyDist} 最近敌人(协调器口径) ${e.minEnemyDist}｜最近非我方 ${nearest ? `${Math.round(nearest.d)}px ${names[nearest.p]}#${nearest.p}T${teams ? teams[nearest.p] : 0}` : '-'}｜录像里此刻该号在 ${real ? `(${real.x},${real.y}) 差 ${Math.round(Math.hypot(real.x - e.x, real.y - e.y))}px` : '未落点'}`);
  }
}

// ---- 锚点打分复算（Vb/Va/Vc 的角落扇形阵共用同一段逻辑；r2 取全场真人都已落点时的值）----
const RC = args.includes('--rcell') ? String(val('--rcell', '')).split(',').map(Number) : [null];
for (const rcArg of RC) {
  const co = mk();
  const { plan } = solveAt(co, AT[AT.length - 1]);
  const rCell = rcArg ?? plan.scales.rCell;
  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
  const K = sq.size + PHANTOM.length;
  const coef = { va: [1.38, 78, 132, 2.35, 142, 225], vb: [1.12, 66, 108, 1.88, 122, 182], vc: [1.32, 76, 126, 2.28, 145, 220] }[ver];
  if (coef && K >= 6) {
    const minReqSep = clamp(Math.round(0.95 * rCell), 42, 68);
    const r0 = clamp(Math.round(0.48 * rCell), 28, 46);
    const r1 = clamp(Math.round(coef[0] * rCell), Math.max(coef[1], r0 + minReqSep), coef[2]);
    const r2 = clamp(Math.round(coef[3] * rCell), Math.max(coef[4], r1 + minReqSep), coef[5]);
    const sampleR = Math.min(280, r2);
    let full = 0;
    for (let sy = -sampleR; sy <= sampleR; sy += 28) for (let sx = -sampleR; sx <= sampleR; sx += 28) { const dd = Math.hypot(sx, sy); if (dd >= 45 && dd <= sampleR) full++; }
    const minViable = Math.min(Math.max(1, Math.round(0.55 * co.maxCompSize)), Math.max(22000, Math.round(0.065 * co.land)));
    const okComp = (c) => (co.largestCompId >= 0 ? co.compId[c] === co.largestCompId : co.compSize[c] >= Math.max(minViable, Math.round(0.85 * co.maxCompSize)));
    console.log(`[锚点打分] rCell=${rCell} minReqSep=${minReqSep} r0=${r0} r1=${r1} r2=${r2}｜采样半径 ${sampleR}，一个四周全是陆地的锚点满额 ${full} 个采样点（<14 的候选被丢弃＝四周陆地不到 ${Math.round(1400 / full)}%）`);
    const corners = [['TOP_LEFT', 24, 24], ['TOP_RIGHT', W - 25, 24], ['BOTTOM_RIGHT', W - 25, H - 25], ['BOTTOM_LEFT', 24, H - 25]];
    const maxSearch = Math.round(0.42 * Math.min(W, H));
    for (const [name, ccx, ccy] of corners) {
      const cands = [];
      for (let dy = 0; dy <= maxSearch; dy += 16) for (let dx = 0; dx <= maxSearch; dx += 16) {
        const tx = ccx < W / 2 ? 20 + dx : W - 21 - dx, ty = ccy < H / 2 ? 20 + dy : H - 21 - dy;
        if (tx < 16 || ty < 16 || tx >= W - 16 || ty >= H - 16) continue;
        const tc = ty * W + tx;
        if (!co.landMask[tc] || !okComp(tc)) continue;
        const cid = co.compId[tc];
        let sumVx = 0, sumVy = 0, n = 0;
        for (let sy = -sampleR; sy <= sampleR; sy += 28) {
          const ny = ty + sy; if (ny < 12 || ny >= H - 12) continue;
          for (let sx = -sampleR; sx <= sampleR; sx += 28) {
            const nx = tx + sx; if (nx < 12 || nx >= W - 12) continue;
            const dd = Math.hypot(sx, sy); if (dd < 45 || dd > sampleR) continue;
            const nc = ny * W + nx;
            if (co.landMask[nc] && co.compId[nc] === cid) { sumVx += sx / dd; sumVy += sy / dd; n++; }
          }
        }
        const dCorner = Math.hypot(tx - ccx, ty - ccy);
        cands.push({ tx, ty, n, dCorner, metric: n * 18 - dCorner * 2.2, ang: Math.atan2(sumVy, sumVx) * 180 / Math.PI, bias: Math.hypot(sumVx, sumVy) / Math.max(1, n) });
      }
      const ok = cands.filter((c) => c.n >= 14).sort((a, b) => b.metric - a.metric);
      if (!ok.length) { console.log(`  ${name}: 没有合格锚点`); continue; }
      const f = (c) => `(${c.tx},${c.ty}) 采样 ${c.n}/${full}（${Math.round(100 * c.n / full)}%）到角 ${Math.round(c.dCorner)} metric ${Math.round(c.metric)} 中轴 ${Math.round(c.ang)}° 陆地偏向度 ${c.bias.toFixed(2)}`;
      const half = ok.filter((c) => c.n <= 0.5 * full)[0];
      console.log(`  ${name}: 合格候选 ${ok.length}（被 <14 丢弃 ${cands.length - ok.length}）｜最佳 ${f(ok[0])}`);
      console.log(`      四周陆地 ≤ 一半的候选里最好的：${half ? f(half) : '无'}${half ? `（比最佳低 ${Math.round(ok[0].metric - half.metric)} 分）` : ''}`);
      if (args.includes('--anchors')) for (const c of ok.slice(1, 5)) console.log(`      其次 ${f(c)}`);
    }
  }
}
