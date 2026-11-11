// 调试：收官阶段「还不是本队的陆地」在给定拍上分成多少块、每块多大、归谁、陆上挨着谁、离本队哪个号的海岸最近（真值重演）。
// 用法：node dbg/leftover.mjs <mid> <t1,t2,...> [--top 12] [--json 输出文件]
// 引擎口径：game.js victoryTick L1398~1412——领先队的地 ≥ 全图陆地（一格不剩）、没有任何前线、领先者没有敌船在海上，才结束。
// 块 = 同一归属（中立 / 同一个 AI / 同一个真人）的四连通陆地。
//   陆邻 = 与这块四邻相接的别家地（按归属计相接的格数）；本队号（在线）陆邻 > 0 说明走陆路就能打；
//   只有水/山相邻的块只能走船（或等别人先上岸）。「最近岸」= 这块到本队在线各号海岸格的最近直线距离（像素）。
import fs from 'node:fs';
import { resim } from '../resim.mjs';

const args = process.argv.slice(2);
const mid = args[0];
const ticks = new Set(String(args[1] || '').split(',').map(Number));
const topIdx = args.indexOf('--top');
const TOP = topIdx > 0 ? +args[topIdx + 1] : 12;
const jsonIdx = args.indexOf('--json');
const until = Math.max(...ticks) + 1;
const T_LAND = 1, T_WATER = 2, P_INNER = 16, NEUTRAL = 512;
const out = {};
let R = null;

const scan = (g, ctx) => {
  const { H, squad, leftT } = ctx;
  const W = g.W, N = g.N, px = g.px, own = g.own, d4 = g.dir4;
  const sqIds = Object.values(squad).map((s) => s.id).filter((x) => x >= 0);
  const myTeam = g.teams[sqIds[0]];
  const online = (p) => p < H && g.alive[p] && (leftT[p] < 0 || leftT[p] > g.t);
  const mine = (o) => o < H && g.teams[o] === myTeam;
  const cls = (c) => {
    const v = px[c];
    if (v === T_LAND) return NEUTRAL;
    if (v >= P_INNER) return mine(own[c]) ? -1 : own[c];
    return -2;
  };
  const coastOf = new Map();
  for (const p of sqIds) {
    if (!online(p)) continue;
    const C = g.coast[p];
    if (C && C.length) coastOf.set(p, C);
  }
  const mark = new Uint8Array(N);
  const comps = [];
  const stack = [];
  for (let c0 = 0; c0 < N; c0++) {
    if (mark[c0]) continue;
    const k0 = cls(c0);
    if (k0 < 0) continue;
    let n = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1, water = 0, wall = 0, sx = 0, sy = 0;
    const adj = new Map();
    const cells = [];
    mark[c0] = 1;
    stack.push(c0);
    while (stack.length) {
      const c = stack.pop();
      n++;
      const x = c % W, y = (c - x) / W;
      sx += x; sy += y;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      if (cells.length < 4000) cells.push(c);
      for (let k = 0; k < 4; k++) {
        const e = c + d4[k];
        if (e < 0 || e >= N) continue;
        const v = px[e];
        if (v === T_WATER) { water++; continue; }
        if (v !== T_LAND && v < P_INNER) { wall++; continue; }
        const ke = cls(e);
        if (ke === k0) {
          if (!mark[e]) { mark[e] = 1; stack.push(e); }
        } else {
          const o = v >= P_INNER ? own[e] : NEUTRAL;
          adj.set(o, (adj.get(o) || 0) + 1);
        }
      }
    }
    let best = null;
    const step = Math.max(1, Math.floor(cells.length / 60));
    for (const [p, C] of coastOf) {
      let dm = 1e18;
      for (let i = 0; i < cells.length; i += step) {
        const c = cells[i], x = c % W, y = (c - x) / W;
        for (let j = 0; j < C.length; j += 1) {
          const q = C[j], qx = q % W, qy = (q - qx) / W;
          const dd = (qx - x) * (qx - x) + (qy - y) * (qy - y);
          if (dd < dm) dm = dd;
        }
      }
      const d = Math.round(Math.sqrt(dm));
      if (!best || d < best[1]) best = [p, d];
    }
    comps.push({ k: k0, n, box: [x0, y0, x1, y1], at: [Math.round(sx / n), Math.round(sy / n)], water, wall, adj: [...adj.entries()], near: best });
  }
  comps.sort((a, b) => b.n - a.n);
  const nm = (q) => (q === NEUTRAL ? '中立' : q >= H ? `AI${q}` : `${(R ? R.names[q] : ctx.names[q] || '?').replace('[APEX] ', '').slice(0, 12)}#${q}${online(q) ? '' : '*'}`);
  const tot = { n: 0, comps: comps.length, neutral: 0, ai: 0, human: 0, landAdjOnline: 0, landAdjHuskOnly: 0, waterOnly: 0, nLandAdjOnline: 0, nLandAdjHuskOnly: 0, nWaterOnly: 0 };
  for (const c of comps) {
    tot.n += c.n;
    if (c.k === NEUTRAL) tot.neutral += c.n; else if (c.k >= H) tot.ai += c.n; else tot.human += c.n;
    const adjOn = c.adj.some(([o]) => o < H && mine(o) && online(o));
    const adjHusk = c.adj.some(([o]) => o < H && mine(o) && !online(o));
    c.reach = adjOn ? '陆邻在线号' : adjHusk ? '只陆邻空壳' : c.adj.length ? '陆邻别家' : '只隔水/山';
    if (adjOn) { tot.landAdjOnline += c.n; tot.nLandAdjOnline++; } else if (adjHusk) { tot.landAdjHuskOnly += c.n; tot.nLandAdjHuskOnly++; } else { tot.waterOnly += c.n; tot.nWaterOnly++; }
  }
  const sizes = { '1': 0, '2-5': 0, '6-20': 0, '21-100': 0, '101-1000': 0, '>1000': 0 };
  const sizeTiles = { ...sizes };
  for (const c of comps) {
    const b = c.n === 1 ? '1' : c.n <= 5 ? '2-5' : c.n <= 20 ? '6-20' : c.n <= 100 ? '21-100' : c.n <= 1000 ? '101-1000' : '>1000';
    sizes[b]++; sizeTiles[b] += c.n;
  }
  const boatsOut = {};
  for (let b = 0; b < g.boatN; b++) {
    const p = g.bSlot[b] >> 3;
    if (p < H && mine(p)) { const o = (boatsOut[nm(p)] ||= [0, 0]); o[0]++; o[1] += g.bTroops[b]; }
  }
  out[g.t] = { tot, sizes, sizeTiles, boatsOut, top: comps.slice(0, TOP).map((c) => ({ who: nm(c.k), n: c.n, box: c.box, at: c.at, water: c.water, wall: c.wall, reach: c.reach, adj: c.adj.map(([o, v]) => [nm(o), v]), near: c.near ? [nm(c.near[0]), c.near[1]] : null })) };
  const land = g.land;
  console.log(`t=${g.t} 非本队陆地 ${tot.n} 格（占全图 ${(100 * tot.n / land).toFixed(3)}%）共 ${tot.comps} 块：中立 ${tot.neutral} AI ${tot.ai} 敌方真人 ${tot.human} | 陆邻在线号 ${tot.nLandAdjOnline} 块 ${tot.landAdjOnline} 格，只陆邻空壳 ${tot.nLandAdjHuskOnly} 块 ${tot.landAdjHuskOnly} 格，只隔水/山 ${tot.nWaterOnly} 块 ${tot.waterOnly} 格`);
  console.log(`    块大小分布（块数/格数）：${Object.keys(sizes).map((k) => `${k}格:${sizes[k]}/${sizeTiles[k]}`).join('  ')} | 本队在海上的船：${Object.entries(boatsOut).map(([k, v]) => `${k} ${v[0]}条 ${v[1]}兵`).join('，') || '无'}`);
  for (const c of out[g.t].top) {
    console.log(`    ${c.who.padEnd(14)} ${String(c.n).padStart(6)} 格 框(${c.box.join(',')}) 心(${c.at}) 邻水边 ${c.water} 邻山 ${c.wall} | ${c.reach}：${c.adj.map(([o, v]) => `${o}×${v}`).join(' ') || '-'} | 最近岸 ${c.near ? `${c.near[0]} ${c.near[1]}px` : '-'}`);
  }
};

R = resim(mid, { until, quiet: true, onState: (g, ctx) => { if (ticks.has(g.t)) scan(g, ctx); } });
if (jsonIdx > 0) fs.writeFileSync(args[jsonIdx + 1], JSON.stringify(out));
