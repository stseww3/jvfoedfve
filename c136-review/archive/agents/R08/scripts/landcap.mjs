#!/usr/bin/env node
// landcap.mjs — 「好地实际抢到多少」的底账：真引擎重演（resim_r08.mjs 的钩子，只读）+ 逐格跟踪。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/landcap.mjs <局>
//        [--replay-from <局2>] [--peer <局2> | --peer-tag <标签>] [--t0 600] [--t1 1800] [--tag <标签>] [--quiet]
// 输出：out/<局>/landcap.json（带 --tag 时是 landcap_<标签>.json；landcap.py 把它和 shadow.json / resim.json 合起来出表）
//
// 记下的东西：
//   1. 出生份额：开局拍每个真人的出生点（初始地块的质心）；把全图每一格陆地分给
//      (a) 直线距离最近的真人出生点（vorE，和 R05 的 spawn_voronoi.mjs 同口径，不看地形），
//      (b) 走陆路最先到的真人（vorB：从各人初始地块同时向外一圈一圈走，只走陆地；走不到的格记在 unreach）。
//   2. 采样拍（默认 300,630,900,1260,1500,1800）每个真人的地、兵，以及「名下的地（vorE）此刻在谁手里」：
//      自己 / 同队编队号 / 异队编队号 / 同队野人 / 敌队真人 / 内置 AI / 无主。
//   3. 内置 AI 的地的去向：t0（默认 600）那一拍属于内置 AI 的每一格，逐拍看它第一次落到哪个真人手里（到 t1 为止）；
//      按（名下是谁、t0 时属于哪个 AI、第一个拿到它的真人、哪个 30 拍窗）汇总。到 t1 还没被真人拿走的记成：仍在原 AI / 别的 AI / 无主。
//   4. 接壤采样：t0~t1 每 10 拍，每个编队号贴着哪些内置 AI（接触格数）、贴不贴无主地。
//   5. t0 时每个内置 AI 的地、兵、队；之后哪一拍出局。
//   6. t0 之后才被内置 AI 占的格（AI 在 t0 之后还在往无主地里长）：每 10 拍全图扫一遍，新出现的 AI 格也跟到 t1，
//      去向单独记在 fateLate（口径同 fate；q = 第一次看到它时的那个 AI）。
//   7. 反事实出生份额：有 out/<局>/spawnlast.json（spawncheck.py 写的「各号日志里最后一条出生指派」）时，
//      把编队号挪到各自最后一条指派的坐标上、别的真人不动，重算直线最近的份额（cf）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out');
const NEUTRAL = 512, T_LAND = 1, P_INNER = 16;
const args = process.argv.slice(2);
const mid = args[0];
if (!mid) { console.error('用法见文件头'); process.exit(2); }
const opt = (k, d) => (args.includes(`--${k}`) ? args[args.indexOf(`--${k}`) + 1] : d);
const T0 = +opt('t0', 600), T1 = +opt('t1', 1800);
const TS = String(opt('at', '300,630,900,1260,1500,1800')).split(',').map(Number);
const TAG = opt('tag', null);
const { resim } = await import(path.join(HERE, 'resim_r08.mjs'));

let S = null;
const ownIds = new Set(), peerIds = new Set();

function init(g, ctx) {
  const N = g.N, W = g.W, H = ctx.H, px = g.px, own = g.own;
  for (const [name, s] of Object.entries(ctx.squad)) if (s.id >= 0) (name.includes(':') ? peerIds : ownIds).add(s.id);
  const land = new Uint8Array(N);
  let nLand = 0;
  const sx = new Float64Array(H), sy = new Float64Array(H), sn = new Int32Array(H);
  for (let c = 0; c < N; c++) {
    const v = px[c];
    if (v === T_LAND || v >= P_INNER) { land[c] = 1; nLand++; }
    if (v >= P_INNER && own[c] < H) { const o = own[c]; sx[o] += c % W; sy[o] += Math.floor(c / W); sn[o]++; }
  }
  const pts = [];
  for (let p = 0; p < H; p++) if (sn[p] > 0) pts.push({ id: p, x: Math.round(sx[p] / sn[p]), y: Math.round(sy[p] / sn[p]) });
  // (a) 直线最近
  const regE = new Int16Array(N).fill(-1);
  const vorE = new Int32Array(H);
  for (let c = 0; c < N; c++) {
    if (!land[c]) continue;
    const x = c % W, y = Math.floor(c / W);
    let best = -1, bd = Infinity;
    for (let i = 0; i < pts.length; i++) {
      const dx = pts[i].x - x, dy = pts[i].y - y, d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = pts[i].id; }
    }
    regE[c] = best;
    vorE[best]++;
  }
  // 反事实：编队号都站到日志里最后一条出生指派上
  let cf = null;
  const slp = path.join(OUT, mid, 'spawnlast.json');
  if (fs.existsSync(slp)) {
    const SL = JSON.parse(fs.readFileSync(slp, 'utf8'));
    const pts2 = pts.map((p) => ({ ...p }));
    let moved = 0;
    for (const p of pts2) {
      const r = SL[p.id];
      if (r && r.last && (Math.abs(r.last[0] - p.x) > 4 || Math.abs(r.last[1] - p.y) > 4)) { p.x = r.last[0]; p.y = r.last[1]; moved++; }
    }
    const v2 = new Int32Array(H);
    for (let c = 0; c < N; c++) {
      if (!land[c]) continue;
      const x = c % W, y = Math.floor(c / W);
      let best = -1, bd = Infinity;
      for (let i = 0; i < pts2.length; i++) {
        const dx = pts2[i].x - x, dy = pts2[i].y - y, d = dx * dx + dy * dy;
        if (d < bd) { bd = d; best = pts2[i].id; }
      }
      v2[best]++;
    }
    cf = { moved, humans: pts2.map((p) => ({ id: p.id, x: p.x, y: p.y, vorE: v2[p.id] })) };
  }
  // (b) 陆路最先到：多源广度优先，源 = 各真人的初始地块
  const regB = new Int16Array(N).fill(-1);
  const vorB = new Int32Array(H);
  const queue = new Int32Array(N);
  let qh = 0, qt = 0;
  for (let c = 0; c < N; c++) if (px[c] >= P_INNER && own[c] < H) { regB[c] = own[c]; queue[qt++] = c; }
  const d4 = g.dir4;
  while (qh < qt) {
    const c = queue[qh++], r = regB[c];
    vorB[r]++;
    for (let k = 0; k < 4; k++) {
      const n = c + d4[k];
      if (n < 0 || n >= N || !land[n] || regB[n] >= 0) continue;
      regB[n] = r;
      queue[qt++] = n;
    }
  }
  let unreach = 0;
  for (let c = 0; c < N; c++) if (land[c] && regB[c] < 0) unreach++;
  S = { N, W, H, land, nLand, pts, regE, regB, vorE, vorB, unreach, cf, at: {}, occ: {}, trk: null, trkQ: null, pend: null, nPend: 0,
    fate: new Map(), fateLate: new Map(), seen: null, lateQ: null, pendL: null, nPendL: 0, nLate: 0,
    contact: new Map(), neutContact: new Map(), ai0: [], aiDeath: {}, aiAlive: [] };
}

function occAt(g) {
  const { N, H, land, regE } = S, px = g.px, own = g.own, teams = g.teams;
  const tab = new Map();   // r -> [self, sqSame, sqOther, mate, enemy, ai, neutral, peerSame, peerOther]
  for (let c = 0; c < N; c++) {
    if (!land[c]) continue;
    const r = regE[c];
    let row = tab.get(r);
    if (!row) { row = new Int32Array(9); tab.set(r, row); }
    if (px[c] < P_INNER) { row[6]++; continue; }
    const o = own[c];
    if (o === r) row[0]++;
    else if (o >= H) row[5]++;
    else {
      const same = g.teamGame && teams[o] === teams[r];
      if (ownIds.has(o)) row[same ? 1 : 2]++;
      else if (peerIds.has(o)) row[same ? 7 : 8]++;
      else row[same ? 3 : 4]++;
    }
  }
  const o = {};
  for (const [r, row] of tab) o[r] = Array.from(row);
  return o;
}

function tick(g, ctx) {
  const t = g.t, { H } = S, px = g.px, own = g.own;
  if (TS.includes(t)) {
    S.at[t] = { terr: Array.from(g.terr.subarray(0, H)), bal: Array.from(g.bal.subarray(0, H)), alive: Array.from(g.alive.subarray(0, H)) };
    S.occ[t] = occAt(g);
  }
  if (t === T0) {
    const cells = [];
    for (let c = 0; c < S.N; c++) if (px[c] >= P_INNER && own[c] >= H && own[c] < NEUTRAL) cells.push(c);
    S.trk = Int32Array.from(cells);
    S.trkQ = new Int16Array(cells.length);
    S.pend = new Int32Array(cells.length);
    for (let i = 0; i < cells.length; i++) { S.trkQ[i] = own[cells[i]]; S.pend[i] = i; }
    S.nPend = cells.length;
    S.seen = new Uint8Array(S.N);
    for (let i = 0; i < cells.length; i++) S.seen[cells[i]] = 1;
    S.lateQ = new Int16Array(S.N).fill(-1);
    S.pendL = new Int32Array(S.N);
    for (let q = H; q < NEUTRAL; q++) if (g.alive[q] && g.terr[q] > 0) { S.ai0.push([q, g.terr[q], g.bal[q], g.teams ? g.teams[q] : 0]); S.aiAlive.push(q); }
  }
  if (t > T0 && t <= T1 && S.trk) {
    const { trk, trkQ, pend, regE, fate } = S;
    const bucket = Math.ceil(t / 30) * 30;
    let n = S.nPend;
    for (let j = n - 1; j >= 0; j--) {
      const i = pend[j], c = trk[i];
      if (px[c] < P_INNER) continue;
      const o = own[c];
      if (o >= H) continue;
      const key = `${regE[c]}|${trkQ[i]}|${o}|${bucket}`;
      fate.set(key, (fate.get(key) || 0) + 1);
      pend[j] = pend[--n];
    }
    S.nPend = n;
    // t0 之后才被 AI 占的格：先看已在跟的有没有落到真人手里，再（每 10 拍）把新出现的 AI 格收进来
    {
      const { pendL, lateQ, fateLate, seen } = S;
      let m = S.nPendL;
      for (let j = m - 1; j >= 0; j--) {
        const c = pendL[j];
        if (px[c] < P_INNER) continue;
        const o = own[c];
        if (o >= H) continue;
        const key = `${regE[c]}|${lateQ[c]}|${o}|${bucket}`;
        fateLate.set(key, (fateLate.get(key) || 0) + 1);
        pendL[j] = pendL[--m];
      }
      if (t % 10 === 0 && t < T1) {
        for (let c = 0; c < S.N; c++) {
          if (seen[c] || px[c] < P_INNER) continue;
          const o = own[c];
          if (o < H || o >= NEUTRAL) continue;
          seen[c] = 1; lateQ[c] = o; pendL[m++] = c; S.nLate++;
        }
      }
      S.nPendL = m;
    }
    for (let k = S.aiAlive.length - 1; k >= 0; k--) {
      const q = S.aiAlive[k];
      if (g.alive[q] === 0 || g.terr[q] === 0) { S.aiDeath[q] = t; S.aiAlive[k] = S.aiAlive[S.aiAlive.length - 1]; S.aiAlive.pop(); }
    }
  }
  if (t >= T0 && t <= T1 && t % 10 === 0) {
    for (const p of ownIds) {
      if (!g.alive[p]) continue;
      const m = ctx.contact(p);
      for (const [o, n] of m) {
        if (o === NEUTRAL) { if (!S.neutContact.has(p)) S.neutContact.set(p, []); S.neutContact.get(p).push(t); continue; }
        if (o < H) continue;
        const key = `${p}:${o}`;
        if (!S.contact.has(key)) S.contact.set(key, []);
        S.contact.get(key).push(t, n);
      }
    }
  }
  if (t === T1 && S.trk) {
    const { trk, trkQ, pend, regE, fate } = S;
    for (let j = S.nPend - 1; j >= 0; j--) {
      const i = pend[j], c = trk[i];
      const code = px[c] < P_INNER ? -1 : own[c] === trkQ[i] ? -2 : -3;   // -1 无主、-2 仍在原 AI、-3 别的 AI
      const key = `${regE[c]}|${trkQ[i]}|${code}|0`;
      fate.set(key, (fate.get(key) || 0) + 1);
    }
    for (let j = S.nPendL - 1; j >= 0; j--) {
      const c = S.pendL[j];
      const code = px[c] < P_INNER ? -1 : own[c] === S.lateQ[c] ? -2 : -3;
      const key = `${regE[c]}|${S.lateQ[c]}|${code}|0`;
      S.fateLate.set(key, (S.fateLate.get(key) || 0) + 1);
    }
  }
}

const t0 = Date.now();
const R = resim(mid, { until: T1 + 1, quiet: true, replayFrom: opt('replay-from', null), peer: opt('peer', null), peerTag: opt('peer-tag', null),
  onStart: init, onTick: tick });
const humans = [];
for (const p of S.pts) {
  humans.push({ id: p.id, name: R.names[p.id], team: R.teams[p.id], squad: ownIds.has(p.id) ? 1 : peerIds.has(p.id) ? 2 : 0,
    x: p.x, y: p.y, vorE: S.vorE[p.id], vorB: S.vorB[p.id], leftT: R.leftT[p.id], deathT: R.deathT[p.id] });
}
const out = {
  matchId: mid, replayFrom: opt('replay-from', null) || mid, endTick: R.endTick, t0: T0, t1: T1, H: S.H, W: S.W, land: S.nLand, engineLand: R.land,
  teamGame: R.nTeams >= 2, nTeams: R.nTeams, botsTeamed: R.botsTeamed, unreach: S.unreach, humans, at: S.at, occ: S.occ,
  ai0: S.ai0, aiDeath: S.aiDeath, nTracked: S.trk ? S.trk.length : 0,
  fate: [...S.fate.entries()].map(([k, n]) => [...k.split('|').map(Number), n]),
  nTrackedLate: S.nLate, fateLate: [...S.fateLate.entries()].map(([k, n]) => [...k.split('|').map(Number), n]),
  cf: S.cf,
  contact: Object.fromEntries(S.contact), neutContact: Object.fromEntries(S.neutContact),
};
fs.mkdirSync(path.join(OUT, mid), { recursive: true });
const outName = TAG ? `landcap_${TAG}.json` : 'landcap.json';
fs.writeFileSync(path.join(OUT, mid, outName), JSON.stringify(out));
if (!args.includes('--quiet') || true) {
  console.log(`${mid}: ${outName} 写出｜陆地 ${S.nLand}（引擎 ${R.land}）｜出生的真人 ${humans.length}/${S.H}（编队 ${[...ownIds].length}，同房另一支 ${[...peerIds].length}）｜走陆路到不了的格 ${S.unreach}`
    + `｜t=${T0} 属于内置 AI 的格 ${out.nTracked}，到 t=${T1} 被真人拿走 ${out.fate.filter((r) => r[2] >= 0).reduce((s, r) => s + r[4], 0)}｜之后才被 AI 占的格 ${out.nTrackedLate}，被真人拿走 ${out.fateLate.filter((r) => r[2] >= 0).reduce((s, r) => s + r[4], 0)}`
    + `｜反事实出生份额 ${S.cf ? `有（挪了 ${S.cf.moved} 个号）` : '无（没有 spawnlast.json）'}｜重演到 t=${R.endTick}｜${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
