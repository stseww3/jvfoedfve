// base_xcheck.mjs — 物理底座交叉核对（纯离线）。
//
// 把一局录像用 R06 的 TGame 整局重放一遍，逐采样拍与三套互相独立的参照比：
//   ① R01 自己的重演（out/<局>/resim_players.csv：每 90 拍全部真人的 存活 / 状态 / 领土 / 兵力；scripts/resim_lib.mjs，另一套补丁写法）
//   ② 真引擎导出（out/<局>/engine_dump.tsv：c136-data/src/tools/engine_replay.cjs --dump，线上客户端原文逐拍重放），有就比
//   ③ 策略日志快照（out/<局>/resim_check.csv 里的 logTerr / logBal：[HL-TICK] 当拍页面上看到的自己）
// 用法（在 agents/R01 下）：
//   HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/ckpt/base_xcheck.mjs <局号> [--to T]
// 输出：一行摘要 + out/<局>/ckpt_base.json
import fs from 'node:fs';
import path from 'node:path';
import { OUT, LM, LX, LU, loadR01, readCsv, cpuMs, writeJson } from './common.mjs';

const o = LU.parseArgs(process.argv.slice(2));
const mid = o._[0];
if (!mid) { console.error('用法：base_xcheck.mjs <局号> [--to T]'); process.exit(2); }
const cpu0 = process.cpuUsage();
const M = loadR01(mid);
const H = M.H;
const dir = path.join(OUT, mid);

const byT = (rows, f) => { const m = new Map(); for (const r of rows) { const t = +r.t; let a = m.get(t); if (!a) m.set(t, (a = [])); a.push(f(r)); } return m; };
const resim = byT(readCsv(path.join(dir, 'resim_players.csv')), (r) => ({ p: +r.p, alive: +r.alive, state: +r.state, terr: +r.terr, bal: +r.bal }));
let engine = null;
const engF = path.join(dir, 'engine_dump.tsv');
if (fs.existsSync(engF)) {
  const lines = fs.readFileSync(engF, 'utf8').split('\n').filter(Boolean);
  const head = lines[0].split('\t');
  const ix = Object.fromEntries(head.map((k, i) => [k, i]));
  engine = new Map();
  for (const l of lines.slice(1)) {
    const c = l.split('\t');
    const t = +c[ix.t];
    let a = engine.get(t);
    if (!a) engine.set(t, (a = []));
    a.push({ p: +c[ix.p], terr: +c[ix.terr], bal: +c[ix.bal], alive: +c[ix.alive], state: +c[ix.state] });
  }
}
const logSnaps = byT(readCsv(path.join(dir, 'resim_check.csv')), (r) => ({ p: +r.p, terr: +r.logTerr, bal: +r.logBal }));

const g = LM.buildWorld(M);
const st = new LM.ReplayStepper(M, g);
st.runSpawnPhase();
const natural = LX.naturalShares(g);
const to = LU.num(o.to, Infinity);

const mk = () => ({ samples: 0, cells: 0, same: 0, firstBadT: -1, firstBad: null, lastT: -1 });
const vsResim = mk(), vsEngine = engine ? mk() : null, vsLog = mk();
const squadSet = new Set(M.squad);
const deathSeen = {};
while (!g.over && g.t < to) {
  const t = g.t;
  // R01 的 died 事件记的是出局发生的那一拍；这里在下一拍开头才看到，所以减 1 再比
  for (const p of M.squad) if (deathSeen[p] === undefined && !g.alive[p]) deathSeen[p] = t - 1;
  const a = resim.get(t);
  if (a) {
    vsResim.samples++; vsResim.lastT = t;
    for (const r of a) {
      if (r.p >= H) continue;
      vsResim.cells++;
      const al = g.alive[r.p] ? 1 : 0;
      const ok = al === r.alive && g.state[r.p] === r.state && (al ? g.terr[r.p] === r.terr && g.bal[r.p] === r.bal : true);
      if (ok) vsResim.same++;
      else if (vsResim.firstBadT < 0) { vsResim.firstBadT = t; vsResim.firstBad = { p: r.p, ref: r, got: { alive: al, state: g.state[r.p], terr: g.terr[r.p], bal: g.bal[r.p] } }; }
    }
  }
  const e = engine && engine.get(t);
  if (e) {
    vsEngine.samples++; vsEngine.lastT = t;
    for (const r of e) {
      if (r.p >= H) continue;
      vsEngine.cells++;
      const tt = g.alive[r.p] ? g.terr[r.p] : 0;
      // 真引擎对已出局的号仍留着旧的兵力数：只在还有地时比兵力（与 R06 的指纹口径相同）
      const ok = tt === r.terr && (tt > 0 ? g.bal[r.p] === r.bal : true);
      if (ok) vsEngine.same++;
      else if (vsEngine.firstBadT < 0) { vsEngine.firstBadT = t; vsEngine.firstBad = { p: r.p, ref: r, got: { alive: g.alive[r.p] ? 1 : 0, state: g.state[r.p], terr: g.terr[r.p], bal: g.bal[r.p] } }; }
    }
  }
  const s = logSnaps.get(t);
  if (s) {
    vsLog.samples++; vsLog.lastT = t;
    for (const r of s) {
      if (!squadSet.has(r.p)) continue;
      vsLog.cells++;
      const ok = g.alive[r.p] && g.terr[r.p] === r.terr && g.bal[r.p] === r.bal;
      if (ok) vsLog.same++;
      else if (vsLog.firstBadT < 0) { vsLog.firstBadT = t; vsLog.firstBad = { p: r.p, ref: r, got: { alive: g.alive[r.p] ? 1 : 0, terr: g.terr[r.p], bal: g.bal[r.p] } }; }
    }
  }
  if (!st.step()) break;
  g.tick();
}
const cpu = cpuMs(cpu0);
const deathDiff = M.squad.filter((p) => (M.deathT[p] ?? -1) !== (deathSeen[p] ?? -1)).map((p) => ({ p, r01: M.deathT[p], tgame: deathSeen[p] ?? -1 }));
const res = {
  match: mid, replay: M.replayMid, map: M.mapKey, humans: H, nTeams: M.ta ? M.ta.nTeams : 0, squad: M.squad, endT: g.t, over: !!g.over, replayTicks: M.replayTicks,
  natural: M.squad.map((p) => natural[p]), vsResim, vsEngine, vsLog,
  deathT: M.deathT, deathDiff, doomed: [...M.doomed], pageEnd: Object.fromEntries(M.pageEnd), pageEndR06: Object.fromEntries(M.r01.pageEndR06),
  oddLandings: g.oddLandings, cpuMs: cpu, cpuMsPer1000: Math.round(1000 * cpu / Math.max(1, g.t)),
};
writeJson(path.join(dir, 'ckpt_base.json'), res, true);
const f = (v) => (v ? `${v.same}/${v.cells}（${v.samples} 个采样拍，到 t=${v.lastT}${v.firstBadT >= 0 ? `，第一处不同 t=${v.firstBadT}` : ''}）` : '无');
console.log(`[base] ${mid}（录像 ${M.replayMid}，图 ${M.mapKey}，真人 ${H}，我方 ${M.squad.length} 席）走到 t=${g.t}${g.over ? '（分出胜负）' : ''}：对 R01 重演 ${f(vsResim)}；对真引擎 ${f(vsEngine)}；对日志快照 ${f(vsLog)}；出局拍与 R01 不同的席位 ${deathDiff.length}；页面中途停摆 ${M.doomed.size} 席；CPU ${cpu} ms`);
