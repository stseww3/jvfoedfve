// live.mjs — 模式 live：真局签名扫描。只放录像、不跑策略：对每一局、每个窗口，用和模拟臂同一套口径（metrics.mjs）算出
// 当年真实发生的指令签名（同拍批、清仓批、同回合连发、陆攻落空、记成无主地的陆攻、捐款发出 ↔ 成交）和席位结果（人均相对领土、
// 实抢率、存活），外加两项核对：日志快照（[HL-TICK] 的 领土、兵力）对重放、我方席位名单。G0 的「实盘四分位区间」由它给出。
//
// 一局一个结果文件（--out-dir，缺省 sim-v2/calib/live/<局>.json），已有的跳过（--force 重算）；墙钟预算（--budget-ms，缺省 90000）
// 用完就停，打印还剩几局——再调一次接着跑。
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, buildWorld, ReplayStepper, execRecorded, SIMV2, NEUTRAL, BUNDLES } from './match.mjs';
import { Metrics, naturalShares, traceStats } from './metrics.mjs';
import { loadTrace } from './channel.mjs';
import { num, list, cohortOf } from './util.mjs';
export { cohortOf };

export function parseWindows(s) {
  const out = [];
  for (const w of list(s || '630:1530,1530:3210')) {
    const [a, b] = w.split(':').map(Number);
    if (Number.isFinite(a) && Number.isFinite(b) && b > a) out.push([a, b]);
  }
  if (!out.length) throw new Error('--windows 的写法：630:1530,1530:3210');
  return out;
}

const KEEP = ['recorded', 'batches', 'batchCmds', 'dumpBatches', 'dumpTicks', 'fullBatches', 'batchShare', 'batchShareAtk', 'gapShare', 'gapN', 'atkVoid', 'atkVoidRate',
  'atkNeutralShare', 'atkOnAi', 'atkOnHuman', 'atkOnNeutral', 'relTerr0', 'relTerr1', 'capture0', 'capture1', 'alive0', 'alive1', 'husk1', 'dead1', 'terr0', 'terr1',
  'feeLoss', 'feeAtk', 'netProd', 'income', 'wealth0', 'wealth1', 'landShare1'];

export function liveOne(mid, windows, deadline = Infinity) {
  const cpu0 = process.cpuUsage();
  const M = loadMatch(mid);
  const H = M.H;
  const squad = M.squad.slice();
  const squadSet = new Set(squad);
  const res = {
    match: mid, cohort: cohortOf(mid), replay: M.replayMid, map: M.mapKey, humans: H, nTeams: M.ta ? M.ta.nTeams : 0, botsTeamed: M.ta ? M.ta.botsTeamed : false,
    squad: squad.length, squadTeams: [...new Set(squad.map((p) => (M.ta ? M.ta.fX[p] : 0)))], replayTicks: M.replayTicks, windows: [],
  };
  if (!squad.length) { res.error = '没有认出我方席位'; return res; }
  const g = buildWorld(M);
  const st = new ReplayStepper(M, g);
  st.runSpawnPhase();
  const natural = naturalShares(g);
  g.enableAccounting();
  const wins = windows.map(([a, b]) => ({ t0: a, t1: Math.min(b, M.replayTicks - 1), asked: [a, b], m: null, out: null })).filter((w) => w.t0 < w.t1);
  const tmax = wins.length ? Math.max(...wins.map((w) => w.t1)) : 0;
  // 日志快照
  const snapAt = new Map();
  for (const s of M.log.snaps) {
    const p = M.log.seatOf.get(s.label);
    if (p === undefined || s.t > tmax) continue;
    let a = snapAt.get(s.t);
    if (!a) snapAt.set(s.t, (a = []));
    a.push({ p, terr: s.terr, bal: s.bal });
  }
  let snapN = 0, snapOk = 0, snapFirstBad = -1;
  st.exec = (c) => {
    const p = c.player;
    if (squadSet.has(p) && (c.id === 1 || c.id === 2 || c.id === 3)) {
      const live = wins.filter((w) => w.m && !w.out);
      if (live.length) {
        const B0 = g.bal[p], g0 = g.donGiven[p], f0 = g.donFee[p];
        const r = execRecorded(g, c);
        const kind = c.id === 1 ? 'atk' : c.id === 2 ? 'don' : 'boat';
        const to = c.id === 1 ? Math.min(c.dZ, NEUTRAL) : c.id === 2 ? c.dZ : -1;
        const sent = !r.ok ? 0 : c.id === 2 ? g.donGiven[p] - g0 : g.attackTroopsTmp;
        const fee = !r.ok ? 0 : c.id === 2 ? g.donFee[p] - f0 : g.attackFeeTmp;
        for (const w of live) w.m.onRecorded(p, kind, g.t, to, { ok: r.ok, rec: true, sent, fee, B0, pct: c.dX });
        return r;
      }
    }
    return execRecorded(g, c);
  };
  const trace = loadTrace(SIMV2, mid);
  const close = (w) => {
    const f = w.m.finalize(natural, {});
    const o = { t0: w.t0, t1: g.t, asked: w.asked };
    for (const k of KEEP) o[k] = f[k];
    o.byKind = { atk: f.byKind.atk.recorded, boat: f.byKind.boat.recorded, don: f.byKind.don.recorded };
    o.donOk = f.don.ok; o.donGiven = f.don.given; o.donToSquad = f.don.toSquad;
    // 捐款发出（策略日志 [HL-DISPATCH]，本机拍落在窗口里的）↔ 成交（录像里的捐款指令，执行拍落在窗口里的）
    const disp = M.log.dispatch.filter((d) => d.t >= w.t0 && d.t < w.t1 && squadSet.has(M.log.seatOf.get(d.label)));
    o.dispatchLogged = disp.length;
    o.donNotLanded = disp.length ? +Math.max(0, 1 - f.don.ok / disp.length).toFixed(4) : null;
    const ts = traceStats(trace, squad, w.t0, w.t1);
    if (ts) { o.dupShare = ts.dupShare; o.rerouteRate = ts.rerouteRate; o.trace = ts; }
    w.out = o;
  };
  let truncated = false;
  while (g.t < tmax && !g.over) {
    const t = g.t;
    if ((t & 63) === 0 && Date.now() > deadline) { truncated = true; break; }
    for (const w of wins) {
      if (t === w.t0 && !w.m) { w.m = new Metrics({ world: g }, squad); w.m.begin(); }
      if (t === w.t1 && w.m && !w.out) close(w);
    }
    const sn = snapAt.get(t);
    if (sn) for (const s of sn) { snapN++; if (g.alive[s.p] && g.terr[s.p] === s.terr && g.bal[s.p] === s.bal) snapOk++; else if (snapFirstBad < 0) snapFirstBad = t; }
    if (!st.step()) break;
    g.tick();
  }
  for (const w of wins) if (w.m && !w.out && !truncated) close(w);
  res.windows = wins.filter((w) => w.out).map((w) => w.out);
  res.endT = g.t; res.over = !!g.over; res.truncated = truncated;
  res.logSnaps = { n: snapN, ok: snapOk, firstBadT: snapFirstBad };
  res.dispatchTotal = M.log.dispatch.length;
  res.hasTrace = !!trace; res.hasPack = !!M.deathT;
  const c = process.cpuUsage(cpu0);
  res.cpuMs = Math.round((c.user + c.system) / 1000);
  return res;
}

export function runLive(o) {
  const wall0 = Date.now();
  const budget = num(o['budget-ms'], 90000);
  const windows = parseWindows(o.windows);
  const outDir = path.resolve(o['out-dir'] || path.join(SIMV2, 'calib', 'live'));
  fs.mkdirSync(outDir, { recursive: true });
  let mids = list(o.matches || o.match);
  if (!mids.length) {
    const want = new Set(list(o.cohort || 'vb,c110'));
    mids = fs.readdirSync(BUNDLES).filter((d) => /^[ABG]\d+$/.test(d) && (want.has('all') || want.has(cohortOf(d)))).sort();
  }
  let done = 0, skipped = 0, left = 0;
  for (const mid of mids) {
    const file = path.join(outDir, `${mid}.json`);
    if (fs.existsSync(file) && !o.force) { skipped++; continue; }
    if (Date.now() - wall0 > budget) { left++; continue; }
    let res;
    try { res = liveOne(mid, windows, wall0 + budget + 15000); } catch (err) { res = { match: mid, cohort: cohortOf(mid), error: String(err && err.message ? err.message : err).slice(0, 200), windows: [] }; }
    if (res.truncated) { left++; console.log(`[live] ${mid}：墙钟预算用完，没跑完（不写文件）`); continue; }
    fs.writeFileSync(file, JSON.stringify(res));
    done++;
    if (res.error) { console.log(`[live] ${mid}：${res.error}`); continue; }
    const w = res.windows[0];
    console.log(`[live] ${mid} ${res.cohort} 真人 ${res.humans} / ${res.nTeams} 队，我方 ${res.squad} 席；日志快照 ${res.logSnaps.ok}/${res.logSnaps.n}` +
      (w ? `；${w.t0}~${w.t1}：进录像 ${w.recorded}，同拍批占比 ${pc(w.batchShare)}，同回合连发 ${pc(w.gapShare ? w.gapShare[0] : null)}，清仓批 ${w.dumpBatches}，人均相对领土 ${w.relTerr1}` : '；录像不够长') +
      `；CPU ${res.cpuMs} ms`);
  }
  console.log(`[live] 本次算了 ${done} 局，跳过已有 ${skipped} 局，还剩 ${left} 局${left ? '（再调一次接着跑）' : ''}`);
  return { done, skipped, left };
}

const pc = (v) => (v === null || v === undefined ? '-' : Math.round(100 * v) + '%');
