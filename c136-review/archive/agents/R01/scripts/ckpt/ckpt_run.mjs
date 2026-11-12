// ckpt_run.mjs — 历史断面通道归因（纯离线）。
//
// 一局录像从 0 重放（历史臂 = 当年真实发生的），在断面 t0 把世界分叉成若干条臂。每条臂里我方席位都跑**同一个历史版本**
//（缺省是这一局当年跑的那一版；只接受 va / vb / vc / c110），区别只在指令通道 / 页面状况：
//     C0    即时：下令当拍执行；页面不停摆、不掉线                      → 「这一版规则在这个断面局面上本来能走到哪」
//     C1    基础延迟（不落后，d 按实测分布）；页面不停摆、不掉线          → 再加上锁步通道固有的 1~2 个回合
//     C2w   实录延迟阶梯（R01 自己配出来的 τ↔E），页面不停摆、不掉线     → 再加上这一局实录的落后波
//     C2    实录延迟阶梯 + 实录的页面停摆 / 通道中断 / 掉线离场           → 这一局通道与页面的全部实况
//   历史臂  录像原样                                                    → C2 与它的差 = 模拟器自己的残差
// 臂名后的 @n 是通道随机数的种子（d 的抽样、哪几个页面偏慢）：同一档多个种子之间的散布就是这一档的噪声底。
//
// 物理、策略沙箱、通道、账本全部只读地用 R06 入库的 sim-v2/lib；本文件只做编排（臂怎么配、实录阶梯从哪来、结果怎么落盘）。
// 没有处理臂、没有候选策略：这里不评估任何新策略。
//
// 用法（在 agents/R01 下）：
//   HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/ckpt/ckpt_run.mjs --match A031 --t0 630 --len 870 \
//       [--arms C0,C1,C1@2,C1@3,C2w,C2,C2@2,C2@3] [--strat vb] [--fill auto] [--warmup full|拍数] [--tag x] [--budget-ms 95000]
//       [--trace 阶梯文件] [--floor 地板文件]
// 输出：out/_ckpt/runs/<局>-<t0>[-<tag>].json 与一段摘要
import fs from 'node:fs';
import path from 'node:path';
import { R01, OUT, LM, LC, LA, LX, LU, loadR01, historicalStrategy, loadHistoricalStrategy, cpuMs, writeJson } from './common.mjs';

const o = LU.parseArgs(process.argv.slice(2));
const mid = o.match;
if (!mid) { console.error('用法：ckpt_run.mjs --match <局号> --t0 <拍> --len <拍> [--arms …]'); process.exit(2); }
const wall0 = Date.now(), cpu0 = process.cpuUsage();
const M = loadR01(mid);
const H = M.H;
const t0 = LU.num(o.t0, 1500);
const len = LU.num(o.len, 900);
const budgetMs = LU.num(o['budget-ms'], 95000);
if (t0 >= M.replayTicks - 1) { console.log(`[ckpt] ${mid} 录像只有 ${M.replayTicks} 拍，断面 t0=${t0} 放不到`); process.exit(0); }
let t1 = Math.min(t0 + len, M.replayTicks - 1);
const warm = o.warmup === undefined || o.warmup === 'full' || o.warmup === true ? t0 : LU.num(o.warmup, t0);
const tw = Math.max(0, t0 - warm);
const stratKey = String(o.strat || historicalStrategy(mid)).toLowerCase();
const strat = await loadHistoricalStrategy(stratKey);
const fill = o.fill || 'auto';
const squad = M.squad.slice();
const squadSet = new Set(squad);
const seatDefs = squad.map((p) => ({ p, slot: M.slotOf.get(p) ?? p % 20 }));

const traceFile = o.trace || path.join(R01, 'reports', 'ckpt-data', 'traces', `${mid}.json`);
const trace = fs.existsSync(traceFile) ? JSON.parse(fs.readFileSync(traceFile, 'utf8')) : null;
// --floor：日志次序给的地板（scripts/ckpt/logorder_floor.py）。页面算到本机拍 t 时服务器至少已经到了 LB，
// S 对本机拍不降，所以 t 之后的每个本机拍 W 都有 S(W) ≥ LB。只抬高 C2 / C2w 的实录阶梯，不动别的臂。
const floor = o.floor ? JSON.parse(fs.readFileSync(o.floor, 'utf8')) : null;
function applyFloor(profile) {
  let raised = 0, seats = 0;
  for (const p of squad) {
    const pts = floor.seats[String(p)];
    if (!pts || !pts.length) continue;
    let s = profile.stairs.get(p);
    if (!s) { s = new Int32Array(profile.Wmax + 1); for (let W = 0; W < s.length; W++) s[W] = W; profile.stairs.set(p, s); }
    let n = 0;
    for (const [t, lb] of pts) for (let W = t; W < lb && W < s.length; W++) if (s[W] < lb) { s[W] = lb; n++; }
    for (let W = 1; W < s.length; W++) if (s[W] < s[W - 1]) s[W] = s[W - 1];
    if (n) { raised += n; seats++; }
  }
  profile.note += `；再按日志次序的地板抬高（${seats} 个席位、${raised} 个本机拍）`;
}

// ---- 臂的配置
const armNames = LU.list(o.arms || 'C0,C1,C1@2,C1@3,C2w,C2,C2@2,C2@3');
function armCfg(name) {
  const [kind, s] = name.split('@');
  const seed = s ? +s : 1;
  const base = { fallback: 'cheapest', donateSubmit: 'always', keepLogs: false, aoPct: null, react: [], reactSeed: seed, inflightGuard: 'auto', handover: 'carry' };
  if (kind === 'C0') return { seed, spec: 'C0', opts: { ...base, ourLeaves: 'ignore' }, page: false };
  if (kind === 'C1') return { seed, spec: 'C1', opts: { ...base, ourLeaves: 'ignore' }, page: false };
  if (kind === 'C2w') return { seed, spec: `C2:fill=${fill},pagedeath=0`, opts: { ...base, ourLeaves: 'ignore' }, page: false };
  if (kind === 'C2') return { seed, spec: `C2:fill=${fill}`, opts: { ...base, ourLeaves: 'replay' }, page: true };
  // C1p：基础延迟（不落后）+ 实录的页面停摆 / 通道中断 / 掉线离场。只用来检验「落后波」与「页面停摆」两段的先后次序：
  // 主口径是先加落后波（C1→C2w）再加页面（C2w→C2）；有了 C1p 就能反过来算一遍（C1→C1p→C2）。
  if (kind === 'C1p') return { seed, spec: 'C1', opts: { ...base, ourLeaves: 'replay' }, page: false, pageOnC1: true };
  throw new Error(`不认识的臂 ${name}（C0 / C1 / C1p / C2w / C2，可带 @种子）`);
}
// R06 的 makeProfile 只给 C2 档挂页面寿命；C1p 这里照它的做法把同样三样东西挂到 C1 的档上（不改它的代码）
function attachPageLife(profile) {
  profile.pageEnd = new Map(M.pageEnd);
  profile.doomed = M.doomed || null;
  if (M.doomed && M.doomed.size && trace) {
    profile.lostAfter = new Map();
    for (const p of squad) {
      if (!M.doomed.has(p)) continue;
      const rows = trace.seats[String(p)];
      profile.lostAfter.set(p, rows && rows.length ? Math.max(...rows.map((r) => r[0])) : -1);
    }
  }
  profile.note += `；页面寿命按实录（${M.doomed ? M.doomed.size : 0} 个席位的页面在席位还活着时停摆）`;
}
const chanOpts = { multi: false, cap: 9, capRounds: 3, keep: 'first', order: 'lifo' };

// ---- 历史臂
const base = LM.buildWorld(M);
const st = new LM.ReplayStepper(M, base);
st.runSpawnPhase();
const natural = LX.naturalShares(base);
base.enableAccounting();
const hist = new LX.Metrics({ world: base }, squad);
let histLive = false;
st.exec = (c) => {
  const p = c.player;
  if (histLive && squadSet.has(p) && (c.id === 1 || c.id === 2 || c.id === 3)) {
    const B0 = base.bal[p], g0 = base.donGiven[p], f0 = base.donFee[p];
    const r = LM.execRecorded(base, c);
    const kind = c.id === 1 ? 'atk' : c.id === 2 ? 'don' : 'boat';
    const to = c.id === 1 ? Math.min(c.dZ, LM.NEUTRAL) : c.id === 2 ? c.dZ : -1;
    const sent = !r.ok ? 0 : c.id === 2 ? base.donGiven[p] - g0 : base.attackTroopsTmp;
    const fee = !r.ok ? 0 : c.id === 2 ? base.donFee[p] - f0 : base.attackFeeTmp;
    hist.onRecorded(p, kind, base.t, to, { ok: r.ok, rec: true, sent, fee, B0, pct: c.dX });
    return r;
  }
  return LM.execRecorded(base, c);
};
while (base.t < tw) { if (!st.step()) break; base.tick(); }
const cpuReplay = cpuMs(cpu0);

// ---- 分叉
const arms = [];
for (const name of armNames) {
  const cfg = armCfg(name);
  if (/^C2/.test(cfg.spec) && !trace) { console.log(`[ckpt] ${mid} 没有实录阶梯文件 ${traceFile}，跳过臂 ${name}`); continue; }
  const profile = LC.makeProfile(cfg.spec, { seed: cfg.seed, seats: squad, trace, seatMap: null, Wmax: t1 + 2000, pageEnd: cfg.page ? M.pageEnd : null, doomed: cfg.page ? M.doomed : null, ownTrace: true });
  if (cfg.pageOnC1) attachPageLife(profile);
  if (floor && /^C2/.test(cfg.spec)) applyFloor(profile);
  const w = base.clone();
  const arm = new LA.Arm({ name, world: w, strat, params: {}, seats: seatDefs, profile, chanOpts, opts: cfg.opts, history: base, takeoverT: t0 });
  arm.attachReplay(st.fork(w));
  arm.cfg = cfg;
  arms.push(arm);
}
if (!arms.length) { console.log(`[ckpt] ${mid} 没有可跑的臂`); process.exit(0); }

// 发散度：臂的世界与历史臂在同一拍的差（我方席位 / 其余真人的领土）
function divergence(w) {
  let sq = 0, sqBase = 0, ot = 0, otBase = 0;
  for (let p = 0; p < H; p++) {
    const a = w.alive[p] ? w.terr[p] : 0, b = base.alive[p] ? base.terr[p] : 0;
    if (squadSet.has(p)) { sq += Math.abs(a - b); sqBase += b; } else { ot += Math.abs(a - b); otBase += b; }
  }
  return { squadL1: sq, squadHist: sqBase, othersL1: ot, othersHist: otBase };
}

let truncated = false, ended = '', cpuWarm = 0;
while (base.t < t1) {
  const t = base.t;
  if (t === t0) {
    cpuWarm = cpuMs(cpu0) - cpuReplay;
    for (const a of arms) a.takeover();
    hist.begin();
    histLive = true;
  }
  for (const a of arms) a.tickOnce();
  if (!st.step()) { ended = '录像放完'; break; }
  base.tick();
  if (histLive && base.t % 30 === 0) hist.sample();
  if (base.over || arms.some((a) => a.world.over)) { ended = '分出胜负'; break; }
  if ((t & 7) === 0 && Date.now() - wall0 > budgetMs) { truncated = true; break; }
}
if (!histLive) { console.log(`[ckpt] ${mid} t0=${t0}：时间预算在热身阶段就用完了（走到 t=${base.t}）`); process.exit(3); }
t1 = base.t;

const res = {
  mode: 'r01-ckpt', match: mid, replay: M.replayMid, map: M.mapKey, humans: H, nTeams: M.ta ? M.ta.nTeams : 0,
  strategy: strat.name, stratKey, historical: stratKey === historicalStrategy(mid),
  squad, t0, t1, tw, lenAsked: len, truncated, ended, fill,
  traceRows: trace ? trace.rows : 0, traceVariant: trace ? trace.variant || 'located' : null, floor: o.floor ? path.basename(path.dirname(o.floor)) + '/' + path.basename(o.floor) : null, doomed: [...M.doomed], deathT: M.deathT,
  history: hist.finalize(natural, { arm: 'history' }),
  arms: {},
};
{
  const ts = LX.traceStats(trace, squad, t0, t1);
  res.history.dupShare = ts ? ts.dupShare : null;
  res.history.rerouteRate = ts ? ts.rerouteRate : null;
  res.history.rerouteRateExec = null;
  res.history.dupShareIssued = null;
  if (ts) res.history.trace = ts;
}
for (const a of arms) {
  const m = a.finish(natural, { file: path.basename(a.strat.file) });
  m.cfg = { spec: a.cfg.spec, seed: a.cfg.seed, ourLeaves: a.cfg.opts.ourLeaves, page: a.cfg.page };
  m.note = a.profile.note;
  m.lagCourse = a.profile.instant ? [] : a.profile.lagCourse(squad, t0, t1, 150);
  m.div = divergence(a.world);
  res.arms[a.name] = m;
}
res.cpuMs = cpuMs(cpu0); res.wallMs = Date.now() - wall0; res.cpuReplayMs = cpuReplay; res.cpuWarmMs = cpuWarm;
res.heapMB = Math.round(process.memoryUsage().heapUsed / 1048576);

const tag = o.tag ? `-${o.tag}` : '';
const outFile = o.out || path.join(OUT, '_ckpt', 'runs', `${mid}-${t0}${tag}.json`);
writeJson(outFile, res);

// ---- 摘要
const f3 = (v) => (v === null || v === undefined ? '-' : typeof v === 'number' ? (Number.isInteger(v) ? LU.fmtN(v) : Math.abs(v) < 10 ? v.toFixed(3) : LU.fmtN(v)) : String(v));
const cols = [['历史', res.history], ...Object.entries(res.arms)];
console.log(`[ckpt] ${mid}（录像 ${M.replayMid}，真人 ${H}，${res.nTeams} 队，我方 ${squad.length} 席，${strat.name}${res.historical ? '' : '【不是这一局当年的版本】'}）断面 t0=${t0} → t1=${t1}${truncated ? '（时间预算截断）' : ''}${ended ? `（${ended}）` : ''}，热身从 t=${tw}`);
console.log('  ' + ['指标'.padEnd(14), ...cols.map(([n]) => n.padStart(9))].join(' '));
const rows = [['relTerr0', '起点人均相对领土'], ['relTerr1', '终点人均相对领土'], ['capture1', '终点实抢率'], ['terr1', '终点领土'], ['alive1', '终点存活(非壳)'], ['husk1', '终点空壳'], ['wealth1', '终点兵(含在攻)'],
  ['issued', '发出'], ['recorded', '进录像'], ['dropped', '被9条顶丢'], ['lostChan', '通道断丢'], ['batches', '同拍批≥3'], ['fullBatches', '满9批'], ['batchShare', '同拍批占比'], ['dupShare', '重复单占比'], ['atkVoidRate', '陆攻落空率'], ['netProd', '净产兵'], ['feeAtk', '陆攻手续费']];
for (const [k, label] of rows) console.log('  ' + [label.padEnd(14 - Math.min(8, [...label].filter((ch) => ch.charCodeAt(0) > 0x2e80).length)), ...cols.map(([, m]) => f3(m[k]).padStart(9))].join(' '));
for (const [n, m] of Object.entries(res.arms)) {
  console.log(`  ${n}：${m.note}；页面停摆 ${m.pageDead} 席；策略报错 ${m.stratErrors.length} 席${m.stratErrors.length ? `（${m.stratErrors[0].first}）` : ''}；其余真人陆攻 ${m.others.atk}：照录像 ${m.others.asRecorded}、改打 ${m.others.rerouted}、作废 ${m.others.dropped}；与历史臂的领土差（L1）我方 ${m.div.squadL1}/${m.div.squadHist}、其余真人 ${m.div.othersL1}/${m.div.othersHist}`);
}
console.log(`  计时：CPU ${res.cpuMs} ms（重放到热身起点 ${res.cpuReplayMs}、热身 ${res.cpuWarmMs}、窗口 ${res.cpuMs - res.cpuReplayMs - res.cpuWarmMs}），墙钟 ${res.wallMs} ms，堆 ${res.heapMB} MB → ${path.relative(R01, outFile)}`);
