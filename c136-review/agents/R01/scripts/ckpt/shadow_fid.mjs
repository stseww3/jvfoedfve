// shadow_fid.mjs — 决策层保真度（纯离线）。
//
// R06 的策略沙箱（lib/sandbox.mjs 的 Seat）在「影子」模式下跟着录像走：世界照录像，策略逐拍决策但指令不生效。
// 策略自己每 90 拍打一行 [HL-TICK]（cmds= boats= nb= neut=），真局日志里同一席位同一拍也有这一行。
// 逐点比这两行：如果沙箱里的页面替身（受理口径、墙钟、每拍 1 条）与线上外壳一致，cmds（策略自认为发出的条数）应当逐点相同；
// nb / neut 只取决于局面，是视图有没有接对的对照项。
// 两种墙钟各跑一遍：C1（墙钟 = 56 ms × 本机拍）与 C2（墙钟 = 56 ms × 实录阶梯 S(本机拍)，页面寿命按实录）。
// 参照：R01 自己的影子（scripts/shadow.mjs，逐局调过受理口径）在同一批点上的 cmds（shadow_check.csv 的 shCmds）。
//
// 用法：HEAVY_TIMEOUT=110 timeout 120 bash ../../tools/run-heavy.sh node scripts/ckpt/shadow_fid.mjs <局号> [--to 5400]
// 输出：out/<局>/ckpt_shadow_fid.json 与一段摘要
import fs from 'node:fs';
import path from 'node:path';
import { R01, OUT, LM, LC, LA, LU, loadR01, historicalStrategy, loadHistoricalStrategy, readCsv, cpuMs, writeJson } from './common.mjs';

const o = LU.parseArgs(process.argv.slice(2));
const mid = o._[0];
if (!mid) { console.error('用法：shadow_fid.mjs <局号> [--to T]'); process.exit(2); }
const cpu0 = process.cpuUsage(), wall0 = Date.now();
const M = loadR01(mid);
const squad = M.squad.slice();
const squadSet = new Set(squad);
const seatDefs = squad.map((p) => ({ p, slot: M.slotOf.get(p) ?? p % 20 }));
const strat = await loadHistoricalStrategy(historicalStrategy(mid));
const to = Math.min(LU.num(o.to, 5400), M.replayTicks - 1);
const trace = JSON.parse(fs.readFileSync(path.join(R01, 'reports', 'ckpt-data', 'traces', `${mid}.json`), 'utf8'));

// 真局日志的同一批点（R01 的 shadow_check.csv：日志值与 R01 影子值并排）
const seatOfBot = M.r01.meta.squad || {};
const ref = new Map();
for (const r of readCsv(path.join(OUT, mid, 'shadow_check.csv'))) {
  const p = seatOfBot[r.bot];
  if (p === undefined || !squadSet.has(p)) continue;
  ref.set(`${r.t}|${p}`, { t: +r.t, p, logCmds: +r.logCmds, logBoats: +r.logBoats, logNb: +r.logNb, logNeut: +r.logNeut, shCmds: +r.shCmds, shBoats: +r.shBoats });
}

const opts = { fallback: 'cheapest', ourLeaves: 'replay', donateSubmit: 'always', keepLogs: false, aoPct: null, react: [], reactSeed: 1, inflightGuard: 'auto', handover: 'clean' };
const mkArm = (name, spec, page) => {
  const g = LM.buildWorld(M);
  const st = new LM.ReplayStepper(M, g);
  st.runSpawnPhase();
  const profile = LC.makeProfile(spec, { seed: 1, seats: squad, trace, seatMap: null, Wmax: to + 2000, pageEnd: page ? M.pageEnd : null, doomed: page ? M.doomed : null, ownTrace: true });
  const arm = new LA.Arm({ name, world: g, strat, params: {}, seats: seatDefs, profile, chanOpts: { multi: false, cap: 9, capRounds: 3, keep: 'first', order: 'lifo' }, opts, history: null, takeoverT: null });
  arm.attachReplay(st);
  arm.pts = new Map();
  arm.onLog = (seat, tag, line) => {
    if (tag !== 'HL-TICK') return;
    const m = /t=(\d+) .*\bnb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)/.exec(line);
    if (m) arm.pts.set(`${m[1]}|${seat.p}`, { cmds: +m[4], boats: +m[5], nb: +m[2], neut: +m[3] });
  };
  return arm;
};
const arms = [mkArm('C1', 'C1', false), mkArm('C2', 'C2:fill=auto', true)];
let truncated = false;
for (let t = 0; t < to; t++) {
  for (const a of arms) a.tickOnce();
  if ((t & 63) === 0 && Date.now() - wall0 > 95000) { truncated = true; break; }
}
const endT = arms[0].world.t;

const CK = [630, 1530, 3240, 4320];
function summarize(get) {
  const perSeat = new Map();
  let n = 0, eqCmds = 0, eqBoats = 0, eqNb = 0, eqNeut = 0, miss = 0;
  const diffs = [];
  for (const r of ref.values()) {
    if (r.t > endT) continue;
    const v = get(r);
    if (!v) { miss++; continue; }
    n++;
    if (v.cmds === r.logCmds) eqCmds++;
    if (v.boats === r.logBoats) eqBoats++;
    if (v.nb === undefined || v.nb === r.logNb) eqNb++;
    if (v.neut === undefined || v.neut === r.logNeut) eqNeut++;
    diffs.push(v.cmds - r.logCmds);
    let s = perSeat.get(r.p);
    if (!s) perSeat.set(r.p, (s = { first: -1, lastT: -1, lastDiff: 0, lastLog: 0 }));
    if (v.cmds !== r.logCmds && (s.first < 0 || r.t < s.first)) s.first = r.t;
    if (r.t > s.lastT) { s.lastT = r.t; s.lastDiff = v.cmds - r.logCmds; s.lastLog = r.logCmds; }
  }
  const at = CK.map((ck) => {
    let m = 0, eq = 0, sumAbs = 0, sumLog = 0;
    for (const p of squad) {
      const r = ref.get(`${ck}|${p}`);
      if (!r) continue;
      const v = get(r);
      if (!v) continue;
      m++; if (v.cmds === r.logCmds) eq++;
      sumAbs += Math.abs(v.cmds - r.logCmds); sumLog += r.logCmds;
    }
    return { t: ck, seats: m, eq, sumAbs, sumLog };
  });
  const firsts = [...perSeat.values()].map((s) => s.first);
  const abs = diffs.map(Math.abs).sort((a, b) => a - b);
  return {
    n, miss, eqCmds, eqBoats, eqNb, eqNeut,
    seats: perSeat.size, seatsNeverDiverge: firsts.filter((f) => f < 0).length, firstDivergeMin: firsts.filter((f) => f >= 0).length ? Math.min(...firsts.filter((f) => f >= 0)) : -1,
    firstDivergeMedian: (() => { const f = firsts.filter((x) => x >= 0).sort((a, b) => a - b); return f.length ? f[Math.floor(f.length / 2)] : -1; })(),
    absDiffMedian: abs.length ? abs[Math.floor(abs.length / 2)] : null, absDiffP90: abs.length ? abs[Math.min(abs.length - 1, Math.floor(0.9 * abs.length))] : null,
    endRel: (() => { let d = 0, l = 0; for (const s of perSeat.values()) { d += s.lastDiff; l += s.lastLog; } return l ? +(d / l).toFixed(4) : null; })(),
    at,
  };
}
const res = { match: mid, strategy: strat.name, endT, truncated, points: ref.size, arms: {}, r01Shadow: summarize((r) => ({ cmds: r.shCmds, boats: r.shBoats })) };
for (const a of arms) {
  res.arms[a.name] = summarize((r) => a.pts.get(`${r.t}|${r.p}`));
  res.arms[a.name].stratErrors = a.seatList.filter((s) => s.errors).length;
}
res.cpuMs = cpuMs(cpu0);
writeJson(path.join(OUT, mid, 'ckpt_shadow_fid.json'), res, true);
const f = (s) => `${s.eqCmds}/${s.n} 点 cmds 相同（boats ${s.eqBoats}、nb ${s.eqNb}、neut ${s.eqNeut}；缺 ${s.miss} 点）；${s.seatsNeverDiverge}/${s.seats} 个席位全程相同，最早分岔 t=${s.firstDivergeMin}（中位 ${s.firstDivergeMedian}）；|差| 中位 ${s.absDiffMedian} / P90 ${s.absDiffP90} 条；各席位最后一点合计 (影子−日志)/日志 = ${s.endRel}；断面处相同席位 ${s.at.map((x) => `${x.t}:${x.eq}/${x.seats}`).join(' ')}`;
console.log(`[shadow-fid] ${mid}（${strat.name}，走到 t=${endT}${truncated ? '，时间预算截断' : ''}）日志快照点 ${ref.size}`);
console.log(`  R06 沙箱 · C1 墙钟：${f(res.arms.C1)}`);
console.log(`  R06 沙箱 · C2 墙钟：${f(res.arms.C2)}`);
console.log(`  R01 影子（参照）  ：${f(res.r01Shadow)}`);
console.log(`  CPU ${res.cpuMs} ms`);
