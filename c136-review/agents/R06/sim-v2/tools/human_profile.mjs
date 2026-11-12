#!/usr/bin/env node
// human_profile.mjs — 量「其余真人」（不是我方席位的真人）在真局里怎么下指令，给 arena 的对手模型定参数、做验收对照。
//
// 用法（在 c136-review/agents/R06 下，套 run-heavy.sh）：
//   node sim-v2/tools/human_profile.mjs [--matches A018,B021,…|packs] [--to 9000] [--out sim-v2/calib/human-profile.json]
// 做法：录像原样重放；每条其余真人的指令在执行前记下：阶段、种类、对象类别（无主地 / 内置 AI 与空壳 / 真人）、千分比、
// 自己的兵和地、对象的兵和地、对象当时有没有在打自己、离自己上一条指令隔了多少拍。
// 输出：各阶段的分布摘要（终端）和明细汇总（JSON）。
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, buildWorld, ReplayStepper, execRecorded, contacts, SIMV2, NEUTRAL } from '../lib/match.mjs';
import { parseArgs, list, num } from '../lib/util.mjs';

const o = parseArgs(process.argv.slice(2));
const packs = JSON.parse(fs.readFileSync(path.join(SIMV2, 'packs', 'index.json'), 'utf8'));
const mids = !o.matches || o.matches === 'packs' ? Object.keys(packs).sort() : list(o.matches);
const TO = num(o.to, 9000);
const budget = num(o['budget-ms'], 80000);
const wall0 = Date.now();

// 阶段划分：fine（默认，给对手模型用：开局利息每 10 拍 5~7%，同一个 357 拍里前后的打法差很多，必须切细）；
// coarse（7 段，对着捐款配额的时间带，报告里的总表用）
const PH_COARSE = [[0, 357], [357, 630], [630, 1071], [1071, 1530], [1530, 3210], [3210, 4284], [4284, 1e9]];
const PH_FINE = [[0, 105], [105, 231], [231, 357], [357, 490], [490, 630], [630, 850], [850, 1071], [1071, 1300], [1300, 1530], [1530, 2142], [2142, 3210], [3210, 4284], [4284, 6000], [6000, 1e9]];
const PH = o.phases === 'coarse' ? PH_COARSE : PH_FINE;
const phOf = (t) => PH.findIndex(([a, b]) => t >= a && t < b);
// 分位点表：0%、5%、…、100% 共 21 点（对手模型按它抽样，保住两头的全压和小额）
const Q21 = (a) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return Array.from({ length: 21 }, (_, i) => s[Math.min(s.length - 1, Math.round(i * (s.length - 1) / 20))]); };
// 标准正态分位（Acklam 近似）
function invNorm(p) {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const pl = 0.02425;
  if (p < pl) { const x = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * x + c[1]) * x + c[2]) * x + c[3]) * x + c[4]) * x + c[5]) / ((((d[0] * x + d[1]) * x + d[2]) * x + d[3]) * x + 1); }
  if (p > 1 - pl) { const x = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * x + c[1]) * x + c[2]) * x + c[3]) * x + c[4]) * x + c[5]) / ((((d[0] * x + d[1]) * x + d[2]) * x + d[3]) * x + 1); }
  const x = p - 0.5, r = x * x;
  return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * x / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}
// 给一组指令的千分比打「正态分」（同阶段同类别内的名次 → 正态分位；并列取平均名次）
function scoreRows(rows) {
  const idx = rows.map((_, i) => i).sort((x, y) => rows[x].pct - rows[y].pct);
  const n = rows.length;
  for (let i = 0; i < n;) {
    let j = i;
    while (j + 1 < n && rows[idx[j + 1]].pct === rows[idx[i]].pct) j++;
    const z = invNorm(((i + j) / 2 + 0.5) / n);
    for (let k = i; k <= j; k++) rows[idx[k]].z = z;
    i = j + 1;
  }
}
// 同一个人的指令之间有多像：单因素方差分量的组内相关（只算下过 ≥2 条的人）
function icc(rows) {
  const g = new Map();
  for (const r of rows) { if (r.z === undefined) continue; let a = g.get(r.seat); if (!a) g.set(r.seat, (a = [])); a.push(r.z); }
  let N = 0, k = 0, sumSq = 0, grand = 0;
  const groups = [...g.values()].filter((a) => a.length >= 2);
  for (const a of groups) { N += a.length; k++; sumSq += a.length * a.length; for (const z of a) grand += z; }
  if (k < 3) return null;
  grand /= N;
  let ssb = 0, ssw = 0;
  for (const a of groups) { const m = a.reduce((s, x) => s + x, 0) / a.length; ssb += a.length * (m - grand) ** 2; for (const z of a) ssw += (z - m) ** 2; }
  const msb = ssb / (k - 1), msw = ssw / Math.max(1, N - k), n0 = (N - sumSq / N) / (k - 1);
  return { icc: +((msb - msw) / (msb + (n0 - 1) * msw)).toFixed(3), seats: k, cmds: N };
}
const corr = (xs, ys) => {
  const n = xs.length; if (n < 3) return null;
  const mx = xs.reduce((s, x) => s + x, 0) / n, my = ys.reduce((s, x) => s + x, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2; }
  return sxx > 0 && syy > 0 ? +(sxy / Math.sqrt(sxx * syy)).toFixed(3) : null;
};
const phName = (i) => `${PH[i][0]}~${PH[i][1] > 1e8 ? '' : PH[i][1]}`;
const q = (a, f) => { if (!a.length) return null; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(f * s.length))]; };
const q3 = (a, d = 0) => (a.length ? [q(a, 0.25), q(a, 0.5), q(a, 0.75)].map((v) => +v.toFixed(d)).join('/') : '-');

// 明细：rows[phase] = { atk: [...], boat: n, don: n, ... }
// 某类对象占自己全部接壤的几成（接壤 = 边界格的四邻里不是自己的陆地格，按格数计；含队友）
function fracs(w, p, H, adj) {
  let tot = 0, n = 0, b = 0, h = 0;
  for (const [q2, c2] of adj) {
    tot += c2;
    if (q2 === NEUTRAL) n += c2;
    else if (w.alive[q2] && w.isEnemy(p, q2)) { if (q2 >= H || w.state[q2] === 2) b += c2; else h += c2; }
  }
  return tot > 0 ? { fN: n / tot, fB: b / tot, fH: h / tot } : { fN: 0, fB: 0, fH: 0 };
}
const bucket = (f) => (f <= 0 ? -1 : f <= 0.1 ? 0 : f <= 0.3 ? 1 : f <= 0.6 ? 2 : 3);
// 自己的兵密度（兵 ÷ 地）分八档：<2 / 2~5 / 5~10 / 10~20 / 20~40 / 40~70 / 70~100 / ≥100
const D_EDGES = [2, 5, 10, 20, 40, 70, 100];
const dBucket = (d) => { let b = 0; while (b < D_EDGES.length && d >= D_EDGES[b]) b++; return b; };
const z8 = () => [0, 0, 0, 0, 0, 0, 0, 0];

const newAcc = () => PH.map(() => ({ cmds: 0, okCmds: 0, sent: 0, balTicks: 0, terrTicks: 0, aliveTicks: 0, expo: { neutral: 0, ai: 0, hum: 0, all: 0, aiN: 0, aiNoN: 0, humFarm: 0, humNoFarm: 0 }, ok2: { aiN: 0, aiNoN: 0, humFarm: 0, humNoFarm: 0 }, expoB: { neutral: [0, 0, 0, 0], ai: [0, 0, 0, 0], hum: [0, 0, 0, 0] }, okB: { neutral: [0, 0, 0, 0], ai: [0, 0, 0, 0], hum: [0, 0, 0, 0] }, sentBy: { neutral: 0, ai: 0, hum: 0, boat: 0 }, okBy: { neutral: 0, ai: 0, hum: 0, boat: 0 }, empty: { neutral: 0, ai: 0, hum: 0, boat: 0, don: 0 }, expoD: z8(), balD: z8(), okD: z8(), sentD: z8(), okDby: { neutral: z8(), ai: z8(), hum: z8(), boat: z8() }, seats: [], neutral: [], ai: [], hum: [], boats: [], dons: [], gaps: [], perHuman: [] }));
const SNAP_T = [357, 630, 1071, 1530, 2142, 3210, 4284, 6000];

// 一局的明细（按局缓存到 sim-v2/_cache/hp/：机器忙的时候 20 局一次跑不完，再跑一次同样的命令接着算，已算过的局直接读缓存）
function collect(mid) {
  const acc = newAcc(), leaves = [], snapsAll = {};
  let humansTotal = 0;
  let M;
  try { M = loadMatch(mid); } catch (e) { console.error(`${mid}: ${e.message}`); return null; }
  const H = M.H, squad = new Set(M.squad);
  const w = buildWorld(M);
  const st = new ReplayStepper(M, w);
  st.runSpawnPhase();
  const lastCmdT = new Int32Array(H).fill(-1);
  const cnt = PH.map(() => new Uint16Array(H));
  // 每人每阶段的账：在场拍数、余额·拍、出手的兵、生效指令数
  const seatAcc = PH.map(() => ({ alive: new Float64Array(H), bal: new Float64Array(H), sent: new Float64Array(H), ok: new Uint16Array(H) }));
  const atkOn = (a, b) => w.alive[a] && w.hasAttack(a, b);
  st.exec = (c) => {
    const p = c.player;
    let tally = null, cls = null, cls2 = null, clsB = -1, emptyA = null, emptyK = null;
    const dB = c.player < H && w.terr[c.player] > 0 ? dBucket(w.bal[c.player] / w.terr[c.player]) : 0;
    const mine = p < H && !squad.has(p) && w.alive[p] && w.state[p] !== 2 && (c.id === 1 || c.id === 2 || c.id === 3);
    if (mine && w.bal[p] < 2) {
      // 空单：余额见底时点的指令（全压以后接着连点）。引擎照收（0 兵的陆攻只要有接壤就算生效），但不花兵、不改局面。
      // 单独记数，不进下面任何一项统计 —— 画像里的指令密度、千分比、连点、间隔都只算手里有兵时点的。
      emptyA = acc[phOf(w.t)];
      emptyK = c.id === 3 ? 'boat' : c.id === 2 ? 'don' : 'neutral';
      if (c.id === 1) {
        let tg = Math.min(c.dZ, NEUTRAL);
        if (tg < NEUTRAL && !w.alive[tg]) tg = NEUTRAL;
        if (tg !== NEUTRAL) emptyK = tg >= H || w.state[tg] === 2 ? 'ai' : 'hum';
      }
    } else if (mine) {
      const t = w.t, ph = phOf(t), A = acc[ph];
      const B = w.bal[p], T = w.terr[p];
      tally = A;
      A.cmds++;
      cnt[ph][p]++;
      if (lastCmdT[p] >= 0) A.gaps.push(t - lastCmdT[p]);
      lastCmdT[p] = t;
      if (c.id === 1) {
        let tg = Math.min(c.dZ, NEUTRAL);
        if (tg < NEUTRAL && !w.alive[tg]) tg = NEUTRAL;
        const row = { pct: c.dX, B, T, D: T > 0 ? B / T : 0, seat: p, t };
        cls = 'neutral';
        const fr = fracs(w, p, H, contacts(w, p));
        clsB = tg === NEUTRAL ? bucket(fr.fN) : (tg >= H || w.state[tg] === 2) ? bucket(fr.fB) : bucket(fr.fH);
        if (tg === NEUTRAL) A.neutral.push(row);
        else {
          row.tB = w.bal[tg]; row.tT = w.terr[tg]; row.tD = w.terr[tg] > 0 ? w.bal[tg] / w.terr[tg] : 0;
          row.send = Math.floor(B * (c.dX + 1) / 1024);
          row.back = atkOn(tg, p) ? 1 : 0;
          row.already = w.hasAttack(p, tg) ? 1 : 0;
          row.sq = squad.has(tg) ? 1 : 0;
          const isAi = tg >= H || w.state[tg] === 2;
          // 在同类的邻居里，他挑的是哪一个：接壤最长的 / 地最多的 / 兵最少的 / 密度最低的
          const adj = contacts(w, p);
          let n = 0, maxC = -1, maxT = -1, minB = Infinity, minD = Infinity, anyBot = 0;
          for (const [q2, c2] of adj) {
            if (q2 === NEUTRAL || !w.alive[q2] || !w.isEnemy(p, q2)) continue;
            if (q2 >= H || w.state[q2] === 2) anyBot = 1;
            if ((q2 >= H || w.state[q2] === 2) !== isAi) continue;
            n++;
            if (c2 > maxC) maxC = c2;
            if (w.terr[q2] > maxT) maxT = w.terr[q2];
            if (w.bal[q2] < minB) minB = w.bal[q2];
            const d2 = w.bal[q2] / Math.max(1, w.terr[q2]);
            if (d2 < minD) minD = d2;
          }
          if (adj.has(tg) && n >= 2) {
            row.nAdj = n;
            row.isMaxC = adj.get(tg) === maxC ? 1 : 0;
            row.isMaxT = w.terr[tg] === maxT ? 1 : 0;
            row.isMinB = w.bal[tg] === minB ? 1 : 0;
            row.isMinD = row.tD <= minD + 1e-9 ? 1 : 0;
          }
          row.hasNeutral = adj.has(NEUTRAL) ? 1 : 0;
          cls = isAi ? 'ai' : 'hum';
          // 细分：打 AI 时身边还有没有无主地；打真人时身边还有没有「能白吃的」（无主地或 AI）
          cls2 = isAi ? (row.hasNeutral ? 'aiN' : 'aiNoN') : (row.hasNeutral || anyBot ? 'humFarm' : 'humNoFarm');
          if (isAi) A.ai.push(row); else A.hum.push(row);
        }
      } else if (c.id === 3) { cls = 'boat'; A.boats.push({ pct: c.dX, B, T }); }
      else if (c.id === 2) A.dons.push({ pct: c.dX, B, T, toSq: squad.has(c.dZ) ? 1 : 0 });
    }
    if (p < H && !squad.has(p) && (c.id === 8 || c.id === 9) && w.alive[p] && w.state[p] !== 2 && !w.spawnPhase) leaves.push(w.t);
    const r = execRecorded(w, c);
    if (emptyA && r.ok) emptyA.empty[emptyK]++;
    // 实际出手的兵（陆攻、发船生效的那些），按阶段累计：对照「在场真人的余额·拍」得到每 100 拍花掉余额的几成
    if (tally && r.ok && (c.id === 1 || c.id === 3)) {
      tally.sent += w.attackTroopsTmp; tally.okCmds++;
      tally.sentBy[cls] += w.attackTroopsTmp; tally.okBy[cls]++;
      if (cls2) tally.ok2[cls2]++;
      if (c.id === 1 && clsB >= 0) tally.okB[cls][clsB]++;
      tally.okD[dB]++; tally.sentD[dB] += w.attackTroopsTmp; tally.okDby[cls][dB]++;
      const sa = seatAcc[phOf(w.t)];
      sa.sent[p] += w.attackTroopsTmp; sa.ok[p]++;
    }
    return r;
  };
  for (let p = 0; p < H; p++) if (!squad.has(p) && w.alive[p]) humansTotal++;
  const end = Math.min(TO, M.replayTicks - 1);
  let si = 0;
  while (w.t < end) {
    if (!st.step()) break;
    if (w.t % 7 === 0) {
      let n = 0, bs = 0, ts = 0;
      const sa = seatAcc[phOf(w.t)];
      for (let p = 0; p < H; p++) if (!squad.has(p) && w.alive[p] && w.state[p] !== 2) { n++; bs += w.bal[p]; ts += w.terr[p]; sa.alive[p] += 7; sa.bal[p] += 7 * w.bal[p]; }
      const A = acc[phOf(w.t)];
      A.aliveTicks += 7 * n; A.balTicks += 7 * bs; A.terrTicks += 7 * ts;
      // 每 70 拍看一眼每个在场真人身边有没有这三类对象（无主地 / 内置 AI 与空壳 / 敌方真人）：
      // 「身边有这类对象的人·拍」是各类指令密度的分母 —— 打 AI 的密度随时间下降主要是 AI 被吃光了，不是人变懒了
      if (w.t % 70 === 0) {
        for (let p = 0; p < H; p++) {
          if (squad.has(p) || !w.alive[p] || w.state[p] === 2) continue;
          let hasN = 0, hasB = 0, hasH = 0;
          const adj = contacts(w, p);
          for (const q2 of adj.keys()) {
            if (q2 === NEUTRAL) hasN = 1;
            else if (w.alive[q2] && w.isEnemy(p, q2)) { if (q2 >= H || w.state[q2] === 2) hasB = 1; else hasH = 1; }
          }
          // 自己的兵密度在哪一档（人·拍、余额·拍）：出手密度、花钱速度随自己兵密度怎么变
          if (w.terr[p] > 0) { const db = dBucket(w.bal[p] / w.terr[p]); A.expoD[db] += 70; A.balD[db] += 70 * w.bal[p]; }
          // 分档：这类对象占自己全部接壤的几成（≤10% / 10~30% / 30~60% / >60%）
          const fr = fracs(w, p, H, adj);
          const bn = bucket(fr.fN), bb = bucket(fr.fB), bh = bucket(fr.fH);
          if (bn >= 0) A.expoB.neutral[bn] += 70;
          if (bb >= 0) A.expoB.ai[bb] += 70;
          if (bh >= 0) A.expoB.hum[bh] += 70;
          A.expo.neutral += 70 * hasN; A.expo.ai += 70 * hasB; A.expo.hum += 70 * hasH; A.expo.all += 70;
          if (hasB) A.expo[hasN ? 'aiN' : 'aiNoN'] += 70;
          if (hasH) A.expo[hasN || hasB ? 'humFarm' : 'humNoFarm'] += 70;
        }
      }
    }
    w.tick();
    while (si < SNAP_T.length && w.t === SNAP_T[si]) {
      const S = (snapsAll[SNAP_T[si]] ||= []);
      const r = { mid, humTerr: [], humBal: [], sqTerr: [], sqBal: [], humN: 0, sqN: squad.size, humAlive: 0, sqAlive: 0, aiTerr: 0, aiAlive: 0, land: w.land };
      for (let p = 0; p < H; p++) {
        const al = w.alive[p] && w.state[p] !== 2;
        if (squad.has(p)) { if (al) { r.sqAlive++; r.sqTerr.push(w.terr[p]); r.sqBal.push(w.bal[p]); } }
        else { r.humN++; if (al) { r.humAlive++; r.humTerr.push(w.terr[p]); r.humBal.push(w.bal[p]); } }
      }
      for (let p = H; p < w.players; p++) if (w.alive[p]) { r.aiAlive++; r.aiTerr += w.terr[p]; }
      S.push(r);
      si++;
    }
    if (w.over) break;
  }
  for (let ph = 0; ph < PH.length; ph++) {
    const span = Math.max(0, Math.min(end, PH[ph][1]) - PH[ph][0]);
    if (span <= 0) continue;
    for (let p = 0; p < H; p++) if (!squad.has(p)) acc[ph].perHuman.push(cnt[ph][p] * 100 / span);
    const sa = seatAcc[ph];
    for (let p = 0; p < H; p++) if (!squad.has(p) && sa.alive[p] > 0) acc[ph].seats.push({ seat: p, alive: sa.alive[p], bal: sa.bal[p], sent: sa.sent[p], n: cnt[ph][p], ok: sa.ok[p] });
  }
  return { mid, acc, leaves, humans: humansTotal, snaps: snapsAll };
}

const acc = newAcc();
const leaves = [];      // 其余真人在场时离场的拍
let humansTotal = 0;
const snapsAll = {};   // t → [{ mid, humTerr:[], humBal:[], sqTerr:[], sqBal:[], humAlive, humN, sqAlive, sqN }]
const doneMatches = [];
const cacheDir = path.join(SIMV2, '_cache', 'hp');
const CACHE_V = 10;
const cacheKey = `v${CACHE_V}-${o.phases === 'coarse' ? 'c' : 'f'}${TO}`;
let pending = 0;
for (const mid of mids) {
  const cf = path.join(cacheDir, `${mid}-${cacheKey}.json`);
  let R = null;
  if (fs.existsSync(cf) && !o.fresh) R = JSON.parse(fs.readFileSync(cf, 'utf8'));
  else if (Date.now() - wall0 > budget) { pending++; continue; }
  else {
    R = collect(mid);
    if (R) { fs.mkdirSync(cacheDir, { recursive: true }); fs.writeFileSync(cf, JSON.stringify(R)); }
  }
  if (!R) continue;
  const off = doneMatches.length * 1000;
  for (let i = 0; i < PH.length; i++) {
    const A = acc[i], B = R.acc[i];
    for (const k of ['cmds', 'okCmds', 'sent', 'balTicks', 'terrTicks', 'aliveTicks']) A[k] += B[k];
    for (const k of ['neutral', 'ai', 'hum', 'boat']) { A.sentBy[k] += B.sentBy[k]; A.okBy[k] += B.okBy[k]; }
    for (const k of Object.keys(A.empty)) A.empty[k] += B.empty[k];
    for (let b = 0; b < 8; b++) { A.expoD[b] += B.expoD[b]; A.balD[b] += B.balD[b]; A.okD[b] += B.okD[b]; A.sentD[b] += B.sentD[b]; for (const k of ['neutral', 'ai', 'hum', 'boat']) A.okDby[k][b] += B.okDby[k][b]; }
    for (const k of Object.keys(A.expo)) A.expo[k] += B.expo[k];
    for (const k of Object.keys(A.ok2)) A.ok2[k] += B.ok2[k];
    for (const k of ['neutral', 'ai', 'hum']) for (let b = 0; b < 4; b++) { A.expoB[k][b] += B.expoB[k][b]; A.okB[k][b] += B.okB[k][b]; }
    for (const k of ['neutral', 'ai', 'hum', 'seats']) for (const r of B[k]) { r.seat += off; A[k].push(r); }
    for (const k of ['boats', 'dons', 'gaps', 'perHuman']) for (const r of B[k]) A[k].push(r);
  }
  for (const t of R.leaves) leaves.push(t);
  humansTotal += R.humans;
  for (const [t, a] of Object.entries(R.snaps)) for (const r of a) (snapsAll[t] ||= []).push(r);
  doneMatches.push(mid);
}
if (pending) {
  console.log(`时间预算到了：已算 ${doneMatches.length} 局，还差 ${pending} 局。再跑一次同样的命令接着算（已算过的读缓存）。`);
  process.exit(3);
}

const sumBy = (a, f) => a.reduce((s, x) => s + f(x), 0);
const share = (a, f) => (a.length ? Math.round(100 * a.filter(f).length / a.length) + '%' : '-');
console.log(`其余真人画像：${doneMatches.length} 局（${doneMatches.join(' ')}），重放到 ${TO} 拍`);
console.log('阶段\t指令数\t每人每 100 拍指令（P25/中位/P75/均值）\t对象：无主地 / AI / 真人 / 船 / 捐\t同一人相邻指令间隔（P25/中位/P75）');
const out = { matches: doneMatches, phases: [] };
for (let i = 0; i < PH.length; i++) {
  const A = acc[i];
  const n = A.neutral.length + A.ai.length + A.hum.length + A.boats.length + A.dons.length;
  const pc = (x) => (n ? Math.round(100 * x / n) + '%' : '-');
  const mean = A.perHuman.length ? (sumBy(A.perHuman, (x) => x) / A.perHuman.length).toFixed(2) : '-';
  console.log(`${phName(i)}\t${A.cmds}\t${q3(A.perHuman, 2)}/${mean}（在场的人每 100 拍 ${A.aliveTicks ? (100 * A.cmds / A.aliveTicks).toFixed(2) : '-'} 条）\t${pc(A.neutral.length)} / ${pc(A.ai.length)} / ${pc(A.hum.length)} / ${pc(A.boats.length)} / ${pc(A.dons.length)}\t${q3(A.gaps)}`);
  const P = {
    phase: phName(i), t0: PH[i][0], t1: PH[i][1], cmds: A.cmds, aliveTicks: A.aliveTicks,
    spendPer100: A.balTicks ? +(100 * A.sent / A.balTicks).toFixed(4) : 0, sentPerTile100: A.terrTicks ? +(100 * A.sent / A.terrTicks).toFixed(4) : 0, sentPerCmd: A.okCmds ? Math.round(A.sent / A.okCmds) : 0, ratePerAlive100: A.aliveTicks ? +(100 * A.cmds / A.aliveTicks).toFixed(3) : 0, perHumanPer100: [q(A.perHuman, 0.25), q(A.perHuman, 0.5), q(A.perHuman, 0.75), +mean],
    mix: { neutral: A.neutral.length, ai: A.ai.length, hum: A.hum.length, boat: A.boats.length, don: A.dons.length },
    // 各类对象每 100 拍花掉余额的几成、生效指令每人每 100 拍几条（对手模型的验收口径）
    spendBy: Object.fromEntries(['neutral', 'ai', 'hum', 'boat'].map((k) => [k, A.balTicks ? +(100 * A.sentBy[k] / A.balTicks).toFixed(4) : 0])),
    okRateBy: Object.fromEntries(['neutral', 'ai', 'hum', 'boat'].map((k) => [k, A.aliveTicks ? +(100 * A.okBy[k] / A.aliveTicks).toFixed(3) : 0])),
    // 按自己的兵密度分八档（<2 / 2~5 / 5~10 / 10~20 / 20~40 / 40~70 / 70~100 / ≥100）：这一档的人·拍占比、每 100 拍生效指令数、
    // 每 100 拍花掉余额的几成、指令数；byClass 是各类对象的条数。兵少的时候人是收着打的，顶到软上限（100）才放开花
    byDensity: {
      edges: D_EDGES,
      expo: A.expoD.map((x) => (A.expo.all ? +(x / A.expo.all).toFixed(4) : 0)),
      rate: A.expoD.map((x, b) => (x > 0 && A.expo.all ? +(100 * A.okD[b] / (A.aliveTicks * x / A.expo.all)).toFixed(3) : 0)),
      spend: A.balD.map((x, b) => (x > 0 && A.expo.all ? +(100 * A.sentD[b] / (x * A.aliveTicks / A.expo.all)).toFixed(4) : 0)),
      cmds: A.okD, byClass: A.okDby,
      // 各档里指令的千分比（P25 / 中位 / P75；陆攻三类合并）
      pct: [0, 1, 2, 3, 4, 5, 6, 7].map((b) => { const a = A.neutral.concat(A.ai, A.hum).filter((r) => dBucket(r.D) === b).map((r) => r.pct); return a.length >= 8 ? [q(a, 0.25), q(a, 0.5), q(a, 0.75)] : null; }),
    },
    // 空单（余额 < 2 时点的、引擎照收的指令）：条数，以及占「空单 + 有兵的生效指令」的几成。本文件其余各项都不含空单。
    empty: A.empty,
    emptyShare: Object.fromEntries(['neutral', 'ai', 'hum', 'boat'].map((k) => [k, A.empty[k] + A.okBy[k] ? +(A.empty[k] / (A.empty[k] + A.okBy[k])).toFixed(3) : 0])),
    // 身边有这类对象的人·拍占比，以及「身边有这类对象时」每 100 拍的生效指令数（对手模型各类指令流的强度）
    expoShare: Object.fromEntries(['neutral', 'ai', 'hum'].map((k) => [k, A.expo.all ? +(A.expo[k] / A.expo.all).toFixed(3) : 0])),
    condRateBy: Object.fromEntries(['neutral', 'ai', 'hum'].map((k) => [k, A.expo[k] ? +(100 * A.okBy[k] / (A.aliveTicks * A.expo[k] / Math.max(1, A.expo.all))).toFixed(3) : 0])),
    // 按「这类对象占自己接壤的几成」分四档（≤10% / 10~30% / 30~60% / >60%）的条件密度：expo = 这一档的人·拍占比，cmds = 生效指令数
    condB: Object.fromEntries(['neutral', 'ai', 'hum'].map((k) => [k, [0, 1, 2, 3].map((b) => ({ expo: A.expo.all ? +(A.expoB[k][b] / A.expo.all).toFixed(4) : 0, cmds: A.okB[k][b], rate: A.expoB[k][b] ? +(100 * A.okB[k][b] / (A.aliveTicks * A.expoB[k][b] / Math.max(1, A.expo.all))).toFixed(3) : 0 }))])),
    // 再细一层：打 AI（身边还有 / 已经没有无主地）、打真人（身边还有 / 已经没有能白吃的无主地或 AI）；n = 这类处境的人·拍占比
    cond2: Object.fromEntries(['aiN', 'aiNoN', 'humFarm', 'humNoFarm'].map((k) => [k, { share: A.expo.all ? +(A.expo[k] / A.expo.all).toFixed(3) : 0, cmds: A.ok2[k], rate: A.expo[k] ? +(100 * A.ok2[k] / (A.aliveTicks * A.expo[k] / Math.max(1, A.expo.all))).toFixed(3) : 0 }])),
    gap: [q(A.gaps, 0.25), q(A.gaps, 0.5), q(A.gaps, 0.75)],
    // 连点：同一个人相邻两条指令只隔 1 个回合（7 拍）/ 不超过 2 个回合的占比（占本阶段全部指令）
    burst7: A.cmds ? +(A.gaps.filter((x) => x <= 7).length / A.cmds).toFixed(3) : 0, burst14: A.cmds ? +(A.gaps.filter((x) => x <= 14).length / A.cmds).toFixed(3) : 0,
  };
  const desc = (name, rows, withTarget) => {
    if (!rows.length) return;
    const pct = rows.map((r) => r.pct), D = rows.map((r) => r.D);
    scoreRows(rows);
    const ic = icc(rows);
    let line = `  ${name}（${rows.length}）：千分比 ${q3(pct.map((x) => Math.round((x + 1) * 1000 / 1024)))}，P10 ${Math.round((q(pct, 0.1) + 1) * 1000 / 1024)}，P90 ${Math.round((q(pct, 0.9) + 1) * 1000 / 1024)}，全压（≥950‰）${share(rows, (r) => r.pct >= 972)}；同一个人的千分比组内相关 ${ic ? ic.icc : '-'}；自己的密度（兵÷地）${q3(D, 1)}`;
    const o2 = { n: rows.length, pct: [q(pct, 0.1), q(pct, 0.25), q(pct, 0.5), q(pct, 0.75), q(pct, 0.9)], pctQ: Q21(pct), icc: ic ? ic.icc : null, D: [q(D, 0.25), q(D, 0.5), q(D, 0.75)] };
    if (withTarget) {
      const ratio = rows.filter((r) => r.tB > 0).map((r) => r.send / r.tB);
      const bratio = rows.filter((r) => r.tB > 0).map((r) => r.B / r.tB);
      line += `；出兵÷对象的兵 ${q3(ratio, 2)}；自己的兵÷对象的兵 ${q3(bratio, 2)}；对象密度 ${q3(rows.map((r) => r.tD), 1)}；对象正在打自己 ${share(rows, (r) => r.back)}；已有进攻线 ${share(rows, (r) => r.already)}` + (name === '真人' ? `；对象是我方 ${share(rows, (r) => r.sq)}` : '');
      const ch = rows.filter((r) => r.nAdj >= 2);
      if (ch.length) {
        line += `；同类邻居 ≥2 个时（${ch.length} 条，邻居数中位 ${q(ch.map((r) => r.nAdj), 0.5)}）挑的是：接壤最长 ${share(ch, (r) => r.isMaxC)}、地最多 ${share(ch, (r) => r.isMaxT)}、兵最少 ${share(ch, (r) => r.isMinB)}、密度最低 ${share(ch, (r) => r.isMinD)}`;
        o2.choice = { n: ch.length, nAdj: q(ch.map((r) => r.nAdj), 0.5), maxContact: ch.filter((r) => r.isMaxC).length / ch.length, maxTerr: ch.filter((r) => r.isMaxT).length / ch.length, minBal: ch.filter((r) => r.isMinB).length / ch.length, minDensity: ch.filter((r) => r.isMinD).length / ch.length };
      }
      line += `；对象的地 ${q3(rows.map((r) => r.tT))}`;
      Object.assign(o2, { tT: [q(rows.map((r) => r.tT), 0.25), q(rows.map((r) => r.tT), 0.5), q(rows.map((r) => r.tT), 0.75)], sendRatio: [q(ratio, 0.25), q(ratio, 0.5), q(ratio, 0.75)], balRatio: [q(bratio, 0.25), q(bratio, 0.5), q(bratio, 0.75)], tD: [q(rows.map((r) => r.tD), 0.25), q(rows.map((r) => r.tD), 0.5), q(rows.map((r) => r.tD), 0.75)], back: rows.filter((r) => r.back).length / rows.length, already: rows.filter((r) => r.already).length / rows.length });
    }
    console.log(line);
    P[{ 无主地: 'neutral', AI: 'ai', 真人: 'hum' }[name]] = o2;
  };
  console.log(`  身边有这类对象的人·拍占比：无主地 ${Math.round(100 * P.expoShare.neutral)}% / AI ${Math.round(100 * P.expoShare.ai)}% / 敌方真人 ${Math.round(100 * P.expoShare.hum)}%；身边有时每 100 拍生效指令：无主地 ${P.condRateBy.neutral} / AI ${P.condRateBy.ai} / 真人 ${P.condRateBy.hum}（不分有没有：${P.okRateBy.neutral} / ${P.okRateBy.ai} / ${P.okRateBy.hum}，船 ${P.okRateBy.boat}）`);
  console.log(`  细分（处境占比 → 每 100 拍生效指令）：打 AI，身边还有无主地 ${Math.round(100 * P.cond2.aiN.share)}% → ${P.cond2.aiN.rate}，已经没有无主地 ${Math.round(100 * P.cond2.aiNoN.share)}% → ${P.cond2.aiNoN.rate}；打真人，身边还有无主地或 AI ${Math.round(100 * P.cond2.humFarm.share)}% → ${P.cond2.humFarm.rate}，都没有了 ${Math.round(100 * P.cond2.humNoFarm.share)}% → ${P.cond2.humNoFarm.rate}`);
  console.log(`  出手强度：每 100 拍花掉余额的 ${A.balTicks ? (100 * 100 * A.sent / A.balTicks).toFixed(1) : '-'}%；每格地每 100 拍出兵 ${A.terrTicks ? (100 * A.sent / A.terrTicks).toFixed(2) : '-'}；每条生效指令平均 ${A.okCmds ? Math.round(A.sent / A.okCmds) : '-'} 兵`);
  desc('无主地', A.neutral, false);
  desc('AI', A.ai, true);
  desc('真人', A.hum, true);
  // 滑块档位 × 点击密度 × 花钱速度：把本阶段下过打无主地 / 打 AI 指令的人按个人平均「滑块名次」分五档
  {
    const zs = new Map();
    for (const r of A.neutral.concat(A.ai)) { if (r.z === undefined) continue; let a = zs.get(r.seat); if (!a) zs.set(r.seat, (a = [0, 0, 0])); a[0] += r.z; a[1]++; a[2] += r.pct; }
    const act = A.seats.filter((s) => zs.has(s.seat)).map((s) => { const a = zs.get(s.seat); return { ...s, z: a[0] / a[1], pct: a[2] / a[1] }; }).sort((x, y) => x.z - y.z);
    const idle = A.seats.filter((s) => !zs.has(s.seat));
    // 每人的连点占比：他本阶段打无主地 / 打 AI 的指令里，离自己上一条不超过 1 个回合（7 拍）的占多少
    const b7 = new Map();
    {
      const last = new Map();
      for (const r of A.neutral.concat(A.ai).sort((x, y) => x.t - y.t)) {
        let a = b7.get(r.seat); if (!a) b7.set(r.seat, (a = [0, 0]));
        a[1]++;
        if (last.has(r.seat) && r.t - last.get(r.seat) <= 7) a[0]++;
        last.set(r.seat, r.t);
      }
    }
    const allAlive = sumBy(A.seats, (s) => s.alive), allBal = sumBy(A.seats, (s) => s.bal);
    const groups = [];
    for (let k = 0; k < 5; k++) {
      const g = act.slice(Math.floor(k * act.length / 5), Math.floor((k + 1) * act.length / 5));
      if (!g.length) continue;
      const al = sumBy(g, (s) => s.alive), bl = sumBy(g, (s) => s.bal);
      groups.push({ seats: g.length, burst7: +(sumBy(g, (s) => (b7.get(s.seat) || [0, 0])[0]) / Math.max(1, sumBy(g, (s) => (b7.get(s.seat) || [0, 0])[1]))).toFixed(3), pct: Math.round(sumBy(g, (s) => s.pct) / g.length), rate: +(100 * sumBy(g, (s) => s.n) / al).toFixed(2), spend: bl > 0 ? +(100 * sumBy(g, (s) => s.sent) / bl).toFixed(3) : 0, balShare: allBal > 0 ? +(bl / allBal).toFixed(3) : 0, aliveShare: +(al / allAlive).toFixed(3) });
    }
    // 按人的滑块分布（每人一个值 = 他本阶段在这一类上的平均千分比）：对手模型给席位定滑块用。按指令数的分布会把点得勤的低滑块重复算
    for (const [key, rows] of [['neutral', A.neutral], ['ai', A.ai], ['hum', A.hum]]) {
      if (!P[key]) continue;
      const m = new Map();
      for (const r of rows) { let a = m.get(r.seat); if (!a) m.set(r.seat, (a = [0, 0])); a[0] += r.pct; a[1]++; }
      P[key].seats = m.size;
      P[key].seatQ = Q21([...m.values()].map((a) => Math.round(a[0] / a[1])));
    }
    const idleAl = sumBy(idle, (s) => s.alive), idleBl = sumBy(idle, (s) => s.bal);
    P.byStyle = { groups, idle: { seats: idle.length, aliveShare: allAlive > 0 ? +(idleAl / allAlive).toFixed(3) : 0, balShare: allBal > 0 ? +(idleBl / allBal).toFixed(3) : 0, rate: idleAl > 0 ? +(100 * sumBy(idle, (s) => s.n) / idleAl).toFixed(2) : 0 } };
    console.log(`  按滑块分五档（低→高）：平均千分比 ${groups.map((g) => Math.round((g.pct + 1) * 1000 / 1024)).join(' / ')}；每 100 拍指令 ${groups.map((g) => g.rate).join(' / ')}；每 100 拍花掉余额 ${groups.map((g) => Math.round(100 * g.spend) + '%').join(' / ')}；手里的余额占比 ${groups.map((g) => Math.round(100 * g.balShare) + '%').join(' / ')}；本阶段没打过无主地和 AI 的人：${idle.length} 人，在场人·拍占 ${Math.round(100 * P.byStyle.idle.aliveShare)}%、余额占 ${Math.round(100 * P.byStyle.idle.balShare)}%`);
  }
  if (A.boats.length) { console.log(`  船（${A.boats.length}）：千分比 ${q3(A.boats.map((r) => Math.round((r.pct + 1) * 1000 / 1024)))}`); P.boat = { n: A.boats.length, pct: [q(A.boats.map((r) => r.pct), 0.25), q(A.boats.map((r) => r.pct), 0.5), q(A.boats.map((r) => r.pct), 0.75)], pctQ: Q21(A.boats.map((r) => r.pct)) }; }
  if (A.dons.length) { console.log(`  捐（${A.dons.length}）：千分比 ${q3(A.dons.map((r) => Math.round((r.pct + 1) * 1000 / 1024)))}；给我方席位 ${share(A.dons, (r) => r.toSq)}`); P.don = { n: A.dons.length, pct: [q(A.dons.map((r) => r.pct), 0.25), q(A.dons.map((r) => r.pct), 0.5), q(A.dons.map((r) => r.pct), 0.75)], pctQ: Q21(A.dons.map((r) => r.pct)) }; }
  out.phases.push(P);
}
// 出手风格的个人一致性：把 1530 拍以前打无主地 / 打 AI 的指令（各自在本阶段本类别里打过正态分）按人合起来
{
  const early = [];
  for (let i = 0; i < PH.length; i++) if (PH[i][1] <= 1530) for (const r of acc[i].neutral.concat(acc[i].ai)) early.push(r);
  const ic = icc(early);
  const bySeat = new Map();
  for (const r of early) { let a = bySeat.get(r.seat); if (!a) bySeat.set(r.seat, (a = [])); a.push(r.z); }
  const xs = [], ys = [];
  for (const a of bySeat.values()) if (a.length >= 2) { xs.push(a.reduce((s, x) => s + x, 0) / a.length); ys.push(Math.log(a.length)); }
  // 前半（<630）与后半（630~1530）的个人平均分之间的相关：风格跨阶段是否保持
  const h1 = new Map(), h2 = new Map();
  for (const r of early) { const m = r.t < 630 ? h1 : h2; let a = m.get(r.seat); if (!a) m.set(r.seat, (a = [])); a.push(r.z); }
  const x2 = [], y2 = [];
  for (const [s, a] of h1) { const b = h2.get(s); if (b && a.length >= 2 && b.length >= 2) { x2.push(a.reduce((u, x) => u + x, 0) / a.length); y2.push(b.reduce((u, x) => u + x, 0) / b.length); } }
  out.style = { icc: ic ? ic.icc : null, seats: ic ? ic.seats : 0, cmds: ic ? ic.cmds : 0, corrWithLogCount: corr(xs, ys), corrAcrossHalves: corr(x2, y2), halvesSeats: x2.length };
  console.log(`出手风格的个人一致性（1530 拍以前打无主地和打 AI 的千分比，按阶段类别内名次打分）：组内相关 ${out.style.icc}（${out.style.seats} 人 ${out.style.cmds} 条）；个人平均分与 ln(指令数) 的相关 ${out.style.corrWithLogCount}；630 拍前后两段个人平均分的相关 ${out.style.corrAcrossHalves}（${x2.length} 人）`);
}
// 每人第一条有兵的陆攻指令的时刻（对手模型定「第一条什么时候下」）；到各时刻为止每人下过几条有兵的陆攻指令（验收用）
{
  const times = new Map();
  for (const A of acc) for (const k of ['neutral', 'ai', 'hum']) for (const r of A[k]) { let a = times.get(r.seat); if (!a) times.set(r.seat, (a = [])); a.push(r.t); }
  const first = [...times.values()].map((a) => a.reduce((m, x) => Math.min(m, x), Infinity));
  // 第一条就全压（≥ 977‰）的人下手早得多（中位 35 拍，其余人 70~77 拍），分开给两张表
  const firstRow = new Map();
  for (const A of acc) for (const k of ['neutral', 'ai', 'hum']) for (const r of A[k]) { const a = firstRow.get(r.seat); if (!a || a.t > r.t) firstRow.set(r.seat, r); }
  const fFull = [], fOther = [];
  for (const r of firstRow.values()) (r.pct >= 1000 ? fFull : fOther).push(r.t);
  out.firstCmd = { seats: first.length, humans: humansTotal, q21: Q21(first), full: { seats: fFull.length, q21: Q21(fFull) }, other: { seats: fOther.length, q21: Q21(fOther) } };
  console.log(`每人第一条有兵的陆攻指令的时刻（${first.length} / ${humansTotal} 人下过）：P5 ${q(first, 0.05)}、P10 ${q(first, 0.1)}、P25 ${q(first, 0.25)}、中位 ${q(first, 0.5)}、P75 ${q(first, 0.75)}、P90 ${q(first, 0.9)}、P95 ${q(first, 0.95)}；第一条就全压的 ${fFull.length} 人：P25/中位/P75 ${q3(fFull)}；其余 ${fOther.length} 人：${q3(fOther)}`);
  out.cmdCount = {};
  for (const T of [105, 231, 357, 630, 1071]) {
    const pi = PH.findIndex((p) => p[1] === T);
    if (pi < 0) continue;
    const span = PH[pi][1] - PH[pi][0];
    const a = acc[pi].seats.filter((s) => s.alive >= 0.9 * span).map((s) => (times.get(s.seat) || []).filter((x) => x < T).length).sort((x, y) => x - y);
    if (!a.length) continue;
    out.cmdCount[T] = { seats: a.length, zero: +(a.filter((x) => x === 0).length / a.length).toFixed(3), q: [q(a, 0.1), q(a, 0.25), q(a, 0.5), q(a, 0.75), q(a, 0.9)], mean: +(sumBy(a, (x) => x) / a.length).toFixed(2) };
    console.log(`  到 ${T} 拍每人下过的有兵陆攻指令数（${a.length} 人）：一条没下 ${Math.round(100 * out.cmdCount[T].zero)}%；P10/P25/中位/P75/P90 ${out.cmdCount[T].q.join('/')}；均值 ${out.cmdCount[T].mean}`);
  }
}
console.log('断面\t局数\t其余真人：在场占比 / 人均地（中位，各局中位的 P25/中位/P75）/ 人均兵密度\t我方：在场占比 / 人均地\t我方人均地 ÷ 其余真人人均地（各局 P25/中位/P75）\t内置 AI 占陆地');
out.snaps = {};
for (const t of SNAP_T) {
  const S = snapsAll[t];
  if (!S || !S.length) continue;
  const med = (a) => q(a, 0.5) ?? 0;
  const humMean = S.map((r) => (r.humTerr.length ? sumBy(r.humTerr, (x) => x) / r.humN : 0));
  const sqMean = S.map((r) => (r.sqN ? sumBy(r.sqTerr, (x) => x) / r.sqN : 0));
  const rel = S.map((r, i) => (humMean[i] > 0 ? sqMean[i] / humMean[i] : 0));
  const humAlive = S.map((r) => r.humAlive / Math.max(1, r.humN)), sqAlive = S.map((r) => r.sqAlive / Math.max(1, r.sqN));
  const dens = S.map((r) => { const T = sumBy(r.humTerr, (x) => x), B = sumBy(r.humBal, (x) => x); return T > 0 ? B / T : 0; });
  const humShare = S.map((r) => sumBy(r.humTerr, (x) => x) / r.land), aiShare = S.map((r) => r.aiTerr / r.land);
  console.log(`${t}\t${S.length}\t${Math.round(100 * med(humAlive))}% / ${q3(S.map((r) => med(r.humTerr)))} / ${q3(dens, 1)}\t${Math.round(100 * med(sqAlive))}% / ${q3(S.map((r) => med(r.sqTerr)))}\t${q3(rel, 2)}\t${q3(aiShare.map((x) => 100 * x))}%`);
  out.snaps[t] = { n: S.length, humAlive: med(humAlive), humTerrMed: [q(S.map((r) => med(r.humTerr)), 0.25), med(S.map((r) => med(r.humTerr))), q(S.map((r) => med(r.humTerr)), 0.75)], humMeanTerr: [q(humMean, 0.25), med(humMean), q(humMean, 0.75)], humShare: [q(humShare, 0.25), med(humShare), q(humShare, 0.75)], aiShare: [q(aiShare, 0.25), med(aiShare), q(aiShare, 0.75)], density: [q(dens, 0.25), med(dens), q(dens, 0.75)], sqRel: [q(rel, 0.25), med(rel), q(rel, 0.75)] };
}
{
  const sh = {};
  for (const t of [357, 630, 1071, 1530, 2142, 3210, 4284, 6000, 9000]) sh[t] = +(leaves.filter((x) => x < t).length / Math.max(1, humansTotal)).toFixed(4);
  out.leave = { humans: humansTotal, leftAlive: leaves.length, shareBefore: sh };
  console.log(`在场时离场（变空壳）：${leaves.length} / ${humansTotal} 人；累计占比 ` + Object.entries(sh).map(([t, v]) => `<${t}: ${Math.round(100 * v)}%`).join('  '));
}
const outFile = o.out || path.join(SIMV2, 'calib', o.phases === 'coarse' ? 'human-profile-coarse.json' : 'human-profile.json');
fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(out, null, 1));
console.log(`已写 ${path.relative(process.cwd(), outFile)}；用时 ${Date.now() - wall0} ms`);
