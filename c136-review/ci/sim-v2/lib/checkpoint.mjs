// checkpoint.mjs — 模式 1：真局断面重演（只用历史旧策略）。
//
// 流程：录像从 0 重放到热身起点 tw（没有策略）→ 在 tw 把世界分叉出一条「复现臂」，继续照录像重放，
// 我方席位挂这一局当年线上那一版历史策略作「影子」跟着决策（指令不生效，只为把策略内部状态带到断面）→ 到 t0 接管：
// 我方席位的录像指令作废，改由策略经指令通道下令；其余真人照放录像（目标已出局或已不接壤的陆攻改打身边最便宜的内置 AI / 无主地）→
// 跑到 t1。原始世界一路照录像放到 t1，作「历史臂」（当年真实发生的），用来看复现臂离历史有多远（模拟器保真度）。
// 换一档通道（C0 / C1 / C2 / C3）再跑同一个断面，两次结果之差 = 这一段里通道延迟这一个环节的归因量。
// 两个世界逐拍交替推进，所以半路被时间预算截断时，二者停在同一拍。
import fs from 'node:fs';
import path from 'node:path';
import { loadMatch, buildWorld, ReplayStepper, execRecorded, SIMV2, NEUTRAL } from './match.mjs';
import { compileStrategy, strategyPath, parseParams, refuseOutOfScope } from './sandbox.mjs';
import { makeProfile, loadTrace } from './channel.mjs';
import { Arm } from './arm.mjs';
import { Metrics, naturalShares, PAIR_KEYS, traceStats } from './metrics.mjs';
import { num, list, fmtN, cohortOf } from './util.mjs';

export function chanOptsOf(o) {
  return { multi: !!o.multi, cap: num(o.cap, 9), capRounds: num(o['cap-rounds'], 3), keep: o.keep || 'first', order: o.order || 'lifo' };
}
export function armOptsOf(o) {
  return {
    fallback: o.fallback || 'cheapest',
    ourLeaves: o['our-leaves'] || 'replay',
    donateSubmit: o['donate-submit'] || 'always',
    keepLogs: !!o['keep-logs'],
    aoPct: o['ao-id'] === undefined || o['ao-id'] === 'off' ? null : num(o['ao-id'], 511),
    react: o.react === undefined || o.react === 'off' ? [] : (o.react === true || o.react === 'on' ? ['first', 'thin'] : list(o.react)),
    reactSeed: num(o.seed, 1),
    handover: o.handover === 'clean' ? 'clean' : 'carry',
  };
}

export async function runCheckpoint(o) {
  const wall0 = Date.now(), cpu0 = process.cpuUsage();
  const mid = o.match;
  if (!mid) throw new Error('checkpoint 模式要 --match <局号>');
  const M = loadMatch(mid);
  const H = M.H;
  const t0 = num(o.t0, 1500);
  const len = num(o.len, 900);
  const budgetMs = num(o['budget-ms'], 95000);
  let t1 = Math.min(t0 + len, M.replayTicks - 1);
  if (t0 >= M.replayTicks - 1) throw new Error(`${mid} 的录像只有 ${M.replayTicks} 拍，断面 t0=${t0} 放不到`);
  const warm = o.warmup === undefined || o.warmup === 'full' || o.warmup === true ? t0 : num(o.warmup, t0);
  const tw = Math.max(0, t0 - warm);

  let squad = M.squad.slice();
  if (o.seats) { const pick = new Set(list(o.seats).map(Number)); squad = squad.filter((p) => pick.has(p)); }
  if (!squad.length) throw new Error(`${mid} 没有认出我方席位`);
  const seatDefs = squad.map((p) => ({ p, slot: M.slotOf.get(p) ?? p % 20 }));
  const squadSet = new Set(squad);

  refuseOutOfScope(o, cohortOf(mid));
  const specs = [{ name: 'baseline', file: strategyPath(o.baseline || cohortOf(mid)), params: parseParams(o['base-params']) }];
  if (o.candidate) {
    specs.push({ name: 'candidate', file: strategyPath(o.candidate), params: parseParams(o['cand-params']) });
  }
  for (const s of specs) s.strat = await compileStrategy(s.file);

  const chanSpec = o.channel || 'C1';
  const seed = num(o.seed, 1);
  const traceMid = o['trace-from'] || mid;
  const trace = /^c2/i.test(chanSpec) ? loadTrace(SIMV2, traceMid) : null;
  let seatMap = null;
  if (trace && traceMid !== mid) seatMap = borrowSeats(trace, traceMid, squad, t0, t1);
  // 页面寿命是这一局自己的页面的事（借别的局的阶梯也照用）；「最后一条落地指令之后发出的算丢失」要本局自己的配对才知道
  const mkProfile = () => makeProfile(chanSpec, { seed, seats: squad, trace, seatMap, Wmax: t1 + 2000, pageEnd: M.pageEnd, doomed: M.deathT ? M.doomed : null, ownTrace: traceMid === mid });

  // ---- 历史臂：录像原样放
  const base = buildWorld(M);
  const st = new ReplayStepper(M, base);
  st.runSpawnPhase();
  const natural = naturalShares(base);
  base.enableAccounting();
  const hist = new Metrics({ world: base }, squad);
  let histLive = false;
  st.exec = (c) => {
    const p = c.player;
    if (histLive && squadSet.has(p) && (c.id === 1 || c.id === 2 || c.id === 3)) {
      const B0 = base.bal[p], g0 = base.donGiven[p], f0 = base.donFee[p];
      const r = execRecorded(base, c);
      const kind = c.id === 1 ? 'atk' : c.id === 2 ? 'don' : 'boat';
      const to = c.id === 1 ? Math.min(c.dZ, NEUTRAL) : c.id === 2 ? c.dZ : -1;
      const sent = !r.ok ? 0 : c.id === 2 ? base.donGiven[p] - g0 : base.attackTroopsTmp;
      const fee = !r.ok ? 0 : c.id === 2 ? base.donFee[p] - f0 : base.attackFeeTmp;
      hist.onRecorded(p, kind, base.t, to, { ok: r.ok, rec: true, sent, fee, B0, pct: c.dX });
      return r;
    }
    return execRecorded(base, c);
  };
  while (base.t < tw) { if (!st.step()) break; base.tick(); }
  const cpuReplay = cpuMs(cpu0);

  // ---- 分叉
  const arms = specs.map((s) => {
    const w = base.clone();
    const arm = new Arm({ name: s.name, world: w, strat: s.strat, params: s.params, seats: seatDefs, profile: mkProfile(), chanOpts: chanOptsOf(o), opts: armOptsOf(o), history: base, takeoverT: t0 });
    arm.attachReplay(st.fork(w));
    return arm;
  });
  const profile = arms[0].profile;

  let truncated = false, ended = '';
  let cpuWarm = 0;
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
  if (!histLive) throw new Error(`时间预算在热身阶段就用完了（走到 t=${base.t}，断面 t0=${t0}）。缩短热身：--warmup 600，或放宽 --budget-ms`);
  t1 = base.t;

  const res = {
    mode: 'checkpoint', match: mid, replay: M.replayMid, map: M.mapKey, humans: H, nTeams: M.ta ? M.ta.nTeams : 0, botsTeamed: M.ta ? M.ta.botsTeamed : false,
    squad, squadTeams: [...new Set(squad.map((p) => (M.ta ? M.ta.fX[p] : 0)))],
    t0, t1, tw, lenAsked: len, truncated, ended,
    channel: profile.name, channelNote: profile.note + (seatMap ? `；阶梯借自 ${traceMid} 的席位 ${[...new Set(seatMap.values())].join(',')}` : ''), channelSpec: chanSpec + (seatMap ? `←${traceMid}` : ''), seed,
    lagCourse: profile.instant ? [] : profile.lagCourse(squad, t0, t1, 150),
    opts: { ...armOptsOf(o), ...chanOptsOf(o) },
    history: hist.finalize(natural, { arm: 'history' }),
    arms: {},
  };
  // 真局的重复单占比 / 改道率：要下令拍，只有实录配对里有（traces/<本局>.json）
  const ownTrace = traceMid === mid && trace ? trace : loadTrace(SIMV2, mid);
  const ts = traceStats(ownTrace, squad, t0, t1);
  // 历史臂的指令流水来自录像：没有下令拍、目标是落地时记的 → 这两项只能从配对算，没有配对就是空
  res.history.dupShare = ts ? ts.dupShare : null;
  res.history.rerouteRate = ts ? ts.rerouteRate : null;
  res.history.rerouteRateExec = null;
  res.history.dupShareIssued = null;
  // 真局的捐款：发出 = 策略日志 [HL-DISPATCH]（c116 系才打这条日志；本机拍落在窗口里的），成交 = 录像里的捐款指令
  {
    const disp = M.log.dispatch.filter((d) => d.t >= t0 && d.t < t1 && squadSet.has(M.log.seatOf.get(d.label)));
    res.history.donIssued = disp.length ? disp.length : null;
    res.history.donNotLanded = disp.length ? +Math.max(0, 1 - res.history.don.ok / disp.length).toFixed(4) : null;
  }
  if (ts) res.history.trace = ts;
  for (const a of arms) res.arms[a.name] = a.finish(natural, { file: a.strat.file, sha256: a.strat.sha256 });
  res.cpuMs = cpuMs(cpu0); res.wallMs = Date.now() - wall0; res.cpuReplayMs = cpuReplay; res.cpuWarmMs = cpuWarm;
  res.heapMB = Math.round(process.memoryUsage().heapUsed / 1048576);

  if (o.quiet) console.log(`[checkpoint] ${mid} t0=${t0}→${t1} ${chanSpec} ${specs.map((s) => s.strat.name).join(' ↔ ')}：CPU ${res.cpuMs} ms${truncated ? '（时间预算截断）' : ''}`);
  else printCheckpoint(res);
  if (o['dump-cmds']) {
    const rows = [];
    for (const a of arms) for (const c of a.metrics.cmds) rows.push({ arm: a.name, p: c.p, k: c.k, W: c.W, E: c.E, Ex: c.Ex ?? null, st: c.st, to: c.to, toExec: c.toExec ?? null, pct: c.pct ?? null, amt: c.amt ?? null, ok: c.ok ?? null, rec: c.rec ?? null, sent: c.sent ?? null, fee: c.fee ?? null, why: c.why || c.dropWhy || '', Bx: c.Bx ?? null });
    fs.mkdirSync(path.dirname(path.resolve(o['dump-cmds'])), { recursive: true });
    fs.writeFileSync(o['dump-cmds'], JSON.stringify(rows));
  }
  if (o['keep-logs'] && o['dump-logs']) {
    const logs = {};
    for (const a of arms) logs[a.name] = Object.fromEntries(a.seatList.map((s) => [s.p, s.logLines]));
    fs.writeFileSync(o['dump-logs'], JSON.stringify(logs));
  }
  if (o.out) {
    fs.mkdirSync(path.dirname(path.resolve(o.out)), { recursive: true });
    fs.writeFileSync(o.out, JSON.stringify(res));
  }
  return res;
}

// 借别的局的实录阶梯（--trace-from）：只借「页面活到窗口结束」的席位（页面中途停摆的席位，阶梯在停摆后没有意义），
// 按窗口内已知点多的排前，我方席位按次序轮着用。
export function borrowSeats(trace, traceMid, squad, t0, t1) {
  let doomed = new Set();
  let pageEnd = new Map();
  try { const S = loadMatch(traceMid); doomed = S.deathT ? S.doomed : new Set(); pageEnd = S.pageEnd; } catch (e) { /* 来源局的对局包不在本机：只按已知点筛 */ }
  const all = Object.keys(trace.seats).map(Number);
  const inWin = (p) => trace.seats[String(p)].filter((r) => r[0] >= t0 - 300 && r[0] < t1).length;
  const lastTau = (p) => Math.max(...trace.seats[String(p)].map((r) => r[0]));
  let src = all.filter((p) => !doomed.has(p) && (pageEnd.get(p) ?? Infinity) >= t1 && lastTau(p) >= t1 - 400 && inWin(p) >= 3);
  if (src.length < 3) src = all.filter((p) => lastTau(p) >= t1 - 400 && inWin(p) >= 3);
  if (!src.length) src = all;
  src.sort((a, b) => inWin(b) - inWin(a) || a - b);
  return new Map(squad.map((p, i) => [p, src[i % src.length]]));
}

function cpuMs(c0) { const c = process.cpuUsage(c0); return Math.round((c.user + c.system) / 1000); }

const show = (v) => (v === null || v === undefined ? '-' : typeof v === 'number' ? (Number.isInteger(v) ? fmtN(v) : Math.abs(v) < 10 ? v.toFixed(3) : fmtN(v)) : String(v));

export function printCheckpoint(res) {
  const b = res.arms.baseline, h = res.history;
  console.log(`[checkpoint] ${res.match}（录像 ${res.replay}，真人 ${res.humans}，${res.nTeams} 队）断面 t0=${res.t0} → t1=${res.t1}${res.truncated ? '（时间预算截断）' : ''}${res.ended ? `（${res.ended}）` : ''}，热身从 t=${res.tw}`);
  console.log(`  我方 ${res.squad.length} 席（队 ${res.squadTeams.join('/')}）；通道 ${res.channelNote}`);
  if (res.lagCourse.length) console.log(`  我方平均落后拍数（每 150 拍）：${res.lagCourse.map(([t, v]) => `${t}:${v}`).join(' ')}`);
  const cols = [['历史(录像)', h], [`基线 ${b.strategy}`, b]];
  const cArm = res.arms.candidate;
  if (cArm) cols.push([`候选 ${cArm.strategy}`, cArm]);
  const diff = (k) => (typeof h[k] === 'number' && typeof b[k] === 'number' ? +(b[k] - h[k]).toFixed(4) : null);
  const candDiff = (k) => (cArm && typeof b[k] === 'number' && typeof cArm[k] === 'number' ? +(cArm[k] - b[k]).toFixed(4) : null);
  const head = ['指标'.padEnd(26), ...cols.map(([n]) => n.padStart(22)), (cArm ? '候选−基线' : '复现−历史').padStart(14)];
  console.log('  ' + head.join(' '));
  for (const [k, label] of PAIR_KEYS) {
    const row = [label.padEnd(26 - Math.max(0, cjk(label))), ...cols.map(([, m]) => show(m[k]).padStart(22)), show(cArm ? candDiff(k) : diff(k)).padStart(14)];
    console.log('  ' + row.join(' '));
  }
  for (const [n, m] of cols.slice(1)) {
    const bk = m.byKind;
    console.log(`  ${n}：接管时还在路上 ${m.preIssued}；发出 ${m.issued}（陆攻 ${bk.atk.issued} / 船 ${bk.boat.issued} / 捐 ${bk.don.issued}）→ 到达 ${m.arrived}、被 9 条顶丢弃 ${m.dropped}、通道已断丢失 ${m.lostChan}、窗口结束还在路上 ${m.pending} → 进录像 ${m.recorded}、生效 ${m.effective}；` +
      `陆攻目标：AI ${m.atkOnAi} / 真人 ${m.atkOnHuman} / 无主地 ${m.atkOnNeutral}，目标已死改道 ${m.rerouted}（生效 ${m.reroutedOk}，${fmtN(m.reroutedSent)} 兵）；` +
      `捐款到达 ${m.don.arrived}：成交 ${m.don.ok}、配额拒 ${m.don.quota}、接收方满 ${m.don.room}、目标失效 ${m.don.target}；满 9 条的批 ${m.fullBatches}；` +
      `其余真人陆攻 ${m.others.atk} 条：照录像 ${m.others.asRecorded}、改打 ${m.others.rerouted}、作废 ${m.others.dropped}；策略报错的席位 ${m.stratErrors.length}` +
      (m.stratErrors.length ? `（${m.stratErrors[0].first}）` : '') + (m.react.fired ? `；对手反击脉冲 ${m.react.fired}（生效 ${m.react.ok}）` : '') +
      `；桥接在途保护 ${m.guard}（跳过 ${m.guarded} 次决策）；页面停摆的席位 ${m.pageDead}`);
  }
  const gs = (m) => (m.gapN ? Object.entries(m.gapShare).map(([k, v]) => `${k}:${v === null ? '-' : Math.round(100 * v) + '%'}`).join(' ') : '-');
  console.log(`  同一席位相邻两条指令的执行拍间隔占比：` + cols.map(([n, m]) => `${n}（${m.gapN}）${gs(m)}`).join('｜'));
  console.log(`  计时：CPU ${res.cpuMs} ms（重放到热身起点 ${res.cpuReplayMs}、热身 ${res.cpuWarmMs}、窗口 ${res.cpuMs - res.cpuReplayMs - res.cpuWarmMs}），墙钟 ${res.wallMs} ms，堆 ${res.heapMB} MB`);
}

// 终端对齐：一个汉字占两格
function cjk(s) { let n = 0; for (const ch of s) if (ch.charCodeAt(0) > 0x2e80) n++; return n; }
