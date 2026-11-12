// metrics.mjs — 一条臂在窗口内的账：指令流水（发出 → 到达 → 执行 / 丢弃 / 落空）和席位结果（领土、兵、存活）。
//
// 口径与 R06 scripts/latency.py、landcap.py 对齐，才能和实盘数字并排：
//   · 进录像（rec）  引擎会记进录像的指令：陆攻过了报价 / 目标 / 进攻线检查；发船、捐款则是成交的那些。被 9 条顶丢弃的、
//                    结算时被拒的捐款都不进录像。
//   · 同拍批         同一席位同一个回合进录像 ≥ 3 条；清仓批 = 这一批（出兵 + 手续费）≥ 批前余额的 50%。
//   · 重复单         同一席位对同一目标（发船不分目标）的后一条，下令拍落在前一条「已下令、还没执行」的窗口里（W_前 < W_后 < E_前）。
//                    占比的分母 = 同种类进录像的条数（与 latency.py sec_dups 相同）。另给按「发出」算的占比（分母含被丢弃的）。
//   · 配额拒单率     到达结算的捐款里因接收方配额不够被拒的比例。
//   · 目标已死改道   下令时目标是玩家、执行时它已出局、被引擎改记成打无主地的陆攻（生效的 = 打错，没生效的 = 落空）。
//   · 实抢率         编队领土 ÷ 编队天然份额（开局出生格沿陆地多源扩散，每格归最近的真人）。
//   · 人均相对领土   （编队领土 ÷ 编队席位数）÷（全体真人领土 ÷ 真人数）。
//   · 净产兵         窗口内利息 + 地租入账 − 三种手续费（陆攻 12/1024、发船 32/1024、捐款 64/1024，都按当时余额）。
import { NEUTRAL, P_INNER, T_LAND } from './tgame.mjs';

const BATCH_MIN = 3, BATCH_DRAIN = 0.5;
export const ATK_SEG = [0, 630, 1071, 1530, 2142, 3210, 4284];

// 天然份额：返回 Float64Array(H)，每个真人「走陆路最近」的陆地格数。要在开局第 0 拍（出生阶段刚结束）的世界上调用。
export function naturalShares(w) {
  const N = w.N, H = w.humans, W = w.W;
  const type = w.map.type;
  const owner = new Int16Array(N).fill(-1);
  let q = new Int32Array(N), qn = 0;
  for (let c = 0; c < N; c++) {
    if (w.px[c] >= P_INNER && w.own[c] < H && w.alive[w.own[c]]) { owner[c] = w.own[c]; q[qn++] = c; }
  }
  const d4 = [1, -1, W, -W];
  for (let i = 0; i < qn; i++) {
    const c = q[i], o = owner[c];
    for (let k = 0; k < 4; k++) {
      const n = c + d4[k];
      if (n < 0 || n >= N || owner[n] >= 0 || type[n] !== T_LAND) continue;
      owner[n] = o;
      q[qn++] = n;
    }
  }
  const out = new Float64Array(H);
  for (let c = 0; c < N; c++) if (owner[c] >= 0 && type[c] === T_LAND) out[owner[c]]++;
  return out;
}

export class Metrics {
  constructor(host, squad) {
    this.host = host;          // { world }
    this.squad = squad;        // 席位号数组
    this.cmds = [];
    this.t0 = -1;
    this.snap0 = null;
    this.series = [];
  }

  snapshot() {
    const w = this.host.world;
    const s = { t: w.t, terr: [], bal: [], atk: [], alive: [], husk: [], inc: [] };
    for (const p of this.squad) {
      const al = w.alive[p] ? 1 : 0;
      s.alive.push(al);
      s.husk.push(al && w.state[p] === 2 ? 1 : 0);
      s.terr.push(al ? w.terr[p] : 0);
      s.bal.push(al ? w.bal[p] : 0);
      s.atk.push(al ? w.totalAttackTroops(p) : 0);
      s.inc.push(w.acct ? w.acct.inc[p] : 0);
    }
    let hum = 0, humAlive = 0;
    for (let p = 0; p < w.humans; p++) if (w.alive[p]) { hum += w.terr[p]; humAlive++; }
    s.humTerr = hum; s.humAlive = humAlive;
    if (w.teamGame) {
      const lands = w.teamLands();
      s.teamLand = Array.from(lands);
    }
    return s;
  }

  begin() { this.t0 = this.host.world.t; this.snap0 = this.snapshot(); this.series.push(this.lite(this.snap0)); }

  lite(s) {
    const sum = (a) => a.reduce((x, y) => x + y, 0);
    return { t: s.t, terr: sum(s.terr), bal: sum(s.bal), atk: sum(s.atk), alive: sum(s.alive) - sum(s.husk), husk: sum(s.husk), humTerr: s.humTerr };
  }

  sample() { this.series.push(this.lite(this.snapshot())); }

  onIssue(cmd) { cmd.st = 'fly'; this.cmds.push(cmd); }
  onDrop(cmd, why) { cmd.st = 'drop'; cmd.dropWhy = why; }
  onExec(cmd, res, t) {
    cmd.st = 'exec'; cmd.Ex = t;
    cmd.ok = !!res.ok; cmd.rec = !!res.rec; cmd.sent = res.sent || 0; cmd.fee = res.fee || 0; cmd.why = res.why || '';
    cmd.toExec = res.to === undefined ? cmd.to : res.to; cmd.Bx = res.B0;
  }

  // 没有下令拍的流水（历史臂：录像里我方席位实际执行的指令）
  onRecorded(p, k, t, to, res) {
    this.cmds.push({ p, k, W: null, E: t, Ex: t, to, toExec: res.to === undefined ? to : res.to, st: 'exec', ok: !!res.ok, rec: !!res.rec, sent: res.sent || 0, fee: res.fee || 0, why: res.why || '', Bx: res.B0, pct: res.pct });
  }

  finalize(natural, extra = {}) {
    const w = this.host.world;
    const end = this.snapshot();
    const s0 = this.snap0 || end;
    const sum = (a) => a.reduce((x, y) => x + y, 0);
    const cmds = this.cmds;
    const ex = cmds.filter((c) => c.st === 'exec');
    const rec = ex.filter((c) => c.rec);
    const kinds = ['atk', 'boat', 'don'];
    const cnt = (arr, k) => arr.filter((c) => c.k === k).length;
    const out = { t0: s0.t, t1: end.t, seats: this.squad.length };

    // ---- 指令漏斗（pre = 接管前影子发出、接管时还在路上的；「发出」只数接管之后的，「到达 / 进录像」数窗口里落地的全部）
    const own = cmds.filter((c) => !c.pre);
    out.issued = own.length;
    out.preIssued = cmds.length - own.length;
    out.arrived = ex.length;
    out.dropped = cmds.filter((c) => c.st === 'drop' && c.dropWhy !== 'deadchan').length;
    out.lostChan = cmds.filter((c) => c.st === 'drop' && c.dropWhy === 'deadchan').length;
    out.pending = cmds.filter((c) => c.st === 'fly').length;
    out.recorded = rec.length;
    out.effective = ex.filter((c) => c.ok).length;
    out.landedShare = ratio(rec.filter((c) => !c.pre).length, own.length);
    out.byKind = {};
    for (const k of kinds) {
      out.byKind[k] = {
        issued: cnt(own, k), arrived: cnt(ex, k), recorded: cnt(rec, k), effective: ex.filter((c) => c.k === k && c.ok).length,
        dropped: cmds.filter((c) => c.k === k && c.st === 'drop').length,
        sent: sum(ex.filter((c) => c.k === k && c.ok).map((c) => c.sent)), fee: sum(ex.filter((c) => c.k === k && c.ok).map((c) => c.fee)),
      };
    }

    // ---- 陆攻：落空 / 目标已死改道
    const atkRec = rec.filter((c) => c.k === 'atk');
    const atkVoid = atkRec.filter((c) => !c.ok);
    const atkOnPlayer = atkRec.filter((c) => c.to < NEUTRAL);
    const rer = atkOnPlayer.filter((c) => c.toExec === NEUTRAL);
    out.atkVoid = atkVoid.length;
    out.atkVoidRate = ratio(atkVoid.length, atkRec.length);
    out.rerouted = rer.length;
    out.reroutedOk = rer.filter((c) => c.ok).length;
    out.reroutedSent = sum(rer.filter((c) => c.ok).map((c) => c.sent));
    // 目标已死改道率：分母 = 窗口里发出（不含接管时已在路上的）、下令时目标是活人 / AI 的陆攻；窗口里落地的全部陆攻另给一个口径
    const atkOnPlayerOwn = atkOnPlayer.filter((c) => !c.pre);
    out.rerouteRate = ratio(atkOnPlayerOwn.filter((c) => c.toExec === NEUTRAL).length, atkOnPlayerOwn.length);
    out.rerouteRateExec = ratio(rer.length, atkOnPlayer.length);
    // 落地时记成「无主地」的陆攻占比（下令就是无主地的 + 目标已死改道的；录像里两者分不开，所以真局也能算）
    out.atkNeutralShare = ratio(atkRec.filter((c) => c.toExec === NEUTRAL).length, atkRec.length);
    const atkAi = atkOnPlayer.filter((c) => c.to >= w.humans);
    out.rerouteRateAi = ratio(atkAi.filter((c) => c.toExec === NEUTRAL).length, atkAi.length);
    out.atkOnAi = atkAi.length;
    out.atkOnHuman = atkOnPlayer.length - atkAi.length;
    out.atkOnNeutral = atkRec.length - atkOnPlayer.length;
    // 生效的陆攻按时段、按落地时的对象（无主地 / 内置 AI / 真人席位，含已成空壳的）：条数与出兵。arena 拿它对照同一局录像里我方的打法
    out.atkSeg = ATK_SEG.map((a, i) => {
      const b = ATK_SEG[i + 1] ?? Infinity;
      const o2 = { t0: a, neutral: 0, ai: 0, hum: 0, neutralSent: 0, aiSent: 0, humSent: 0 };
      for (const c of atkRec) {
        if (!c.ok || c.Ex < a || c.Ex >= b) continue;
        const k = c.toExec === NEUTRAL || c.toExec === undefined ? 'neutral' : c.toExec >= w.humans ? 'ai' : 'hum';
        o2[k]++; o2[k + 'Sent'] += c.sent || 0;
      }
      return o2;
    });

    // ---- 同拍批 / 清仓批
    const groups = new Map();
    for (const c of rec) {
      const key = c.p * 100000 + c.Ex;
      let g = groups.get(key);
      if (!g) groups.set(key, (g = []));
      g.push(c);
    }
    let batches = 0, batchCmds = 0, dumpBatches = 0, fullBatches = 0, dumpTicks = 0, dumpCost = 0, extra2 = 0, batchAtk = 0;
    const worst = [];
    for (const g of groups.values()) {
      const B0 = Math.max(...g.map((c) => c.Bx || 0));
      const cost = sum(g.filter((c) => c.ok).map((c) => c.sent + c.fee));
      const frac = B0 > 0 ? cost / B0 : 0;
      if (frac >= BATCH_DRAIN) dumpTicks++;
      if (g.length < BATCH_MIN) continue;
      batches++; batchCmds += g.length;
      batchAtk += g.filter((c) => c.k === 'atk').length;
      if (g.length >= 9) fullBatches++;
      if (frac >= BATCH_DRAIN) { dumpBatches++; dumpCost += cost; }
      // 一批里第 2 条起多发的兵（按执行次序）
      let first = true;
      for (const c of g) { if (!c.ok) continue; if (first) { first = false; continue; } extra2 += c.sent + c.fee; }
      worst.push({ p: g[0].p, t: g[0].Ex, n: g.length, ok: g.filter((c) => c.ok).length, B0, cost, frac: +frac.toFixed(3), W0: minOf(g.map((c) => c.W)), W1: maxOf(g.map((c) => c.W)) });
    }
    worst.sort((a, b) => b.frac - a.frac);
    out.batches = batches; out.batchCmds = batchCmds; out.batchShare = ratio(batchCmds, rec.length);
    out.batchShareAtk = ratio(batchAtk, atkRec.length);
    out.fullBatches = fullBatches; out.dumpBatches = dumpBatches; out.dumpTicks = dumpTicks; out.dumpCost = dumpCost; out.batchExtra = extra2;
    out.worstBatches = worst.slice(0, 6);

    // ---- 同一席位相邻两条进录像指令的执行拍间隔（0 = 同一回合）：各档占比
    {
      const last = new Map();
      const h = { 0: 0, 7: 0, 14: 0, 21: 0, 28: 0, more: 0 };
      let n = 0;
      for (const c of rec.slice().sort((a, b) => a.Ex - b.Ex)) {
        const pv = last.get(c.p);
        if (pv !== undefined) { const g = c.Ex - pv; if (g <= 28 && h[g] !== undefined) h[g]++; else h.more++; n++; }
        last.set(c.p, c.Ex);
      }
      out.gapShare = Object.fromEntries(Object.entries(h).map(([k, v]) => [k, ratio(v, n)]));
      out.gapN = n;
    }

    // ---- 重复单
    const dupOf = (arr) => {
      const by = new Map();
      for (const c of arr) {
        if (c.W === null || c.W === undefined) continue;
        const key = `${c.p}|${c.k}|${c.k === 'boat' ? -1 : c.to}`;
        let g = by.get(key);
        if (!g) by.set(key, (g = []));
        g.push(c);
      }
      const dup = new Set();
      for (const g of by.values()) {
        g.sort((a, b) => a.W - b.W || a.seq - b.seq);
        for (let j = 1; j < g.length; j++) {
          const r = g[j];
          for (let i = 0; i < j; i++) {
            const pv = g[i];
            const eP = pv.st === 'exec' ? pv.Ex : pv.E;
            if (pv.W < r.W && r.W < eP) { dup.add(r); break; }
          }
        }
      }
      return dup;
    };
    // 接管前发出的（pre）只当「前一条」用，不进分母
    const live = cmds.filter((c) => c.dropWhy !== 'deadchan');
    const dRec = dupOf(rec), dAll = dupOf(live);
    const inWin = (c) => !c.pre && c.W !== null && c.W !== undefined;
    out.dup = {};
    for (const k of kinds) {
      const b = rec.filter((c) => c.k === k && inWin(c)), bi = live.filter((c) => c.k === k && inWin(c));
      const d = b.filter((c) => dRec.has(c)), di = bi.filter((c) => dAll.has(c));
      out.dup[k] = { base: b.length, dups: d.length, share: ratio(d.length, b.length), okSent: sum(d.filter((c) => c.ok).map((c) => c.sent)), fee: sum(d.filter((c) => c.ok).map((c) => c.fee)),
        issuedBase: bi.length, issuedDups: di.length, issuedShare: ratio(di.length, bi.length) };
    }
    out.dupShare = ratio(rec.filter((c) => inWin(c) && dRec.has(c)).length, rec.filter(inWin).length);
    out.dupShareIssued = ratio(live.filter((c) => inWin(c) && dAll.has(c)).length, live.filter(inWin).length);

    // ---- 捐款
    const don = ex.filter((c) => c.k === 'don');
    const rej = (why) => don.filter((c) => !c.ok && c.why === why).length;
    out.don = {
      arrived: don.length, ok: don.filter((c) => c.ok).length, quota: rej('quota'), room: rej('room'), target: rej('target'), other: don.filter((c) => !c.ok && !['quota', 'room', 'target'].includes(c.why)).length,
      given: sum(don.filter((c) => c.ok).map((c) => c.sent)), fee: sum(don.filter((c) => c.ok).map((c) => c.fee)),
    };
    out.quotaRejectRate = ratio(out.don.quota, don.length);
    // 捐款发出后没成交的占比：分母 = 窗口里发出的捐款（策略得到 true 的），分子 = 分母 − 窗口里成交的。
    // 真局的同一项 = 1 − 录像里的捐款条数 ÷ 策略日志 [HL-DISPATCH] 的条数（checkpoint / live 模式在外面填）。
    out.donIssued = out.byKind.don.issued;
    out.donNotLanded = out.donIssued > 0 ? +Math.max(0, 1 - out.don.ok / out.donIssued).toFixed(4) : null;
    const donEarly = don.filter((c) => c.Ex < 3213);
    out.quotaRejectRateEarly = ratio(donEarly.filter((c) => !c.ok && c.why === 'quota').length, donEarly.length);
    const sq = new Set(this.squad);
    out.don.toSquad = sum(don.filter((c) => c.ok && sq.has(c.to)).map((c) => c.sent));
    out.don.toOthers = out.don.given - out.don.toSquad;

    // ---- 手续费 / 净产兵
    out.feeAtk = out.byKind.atk.fee; out.feeBoat = out.byKind.boat.fee; out.feeDon = out.byKind.don.fee;
    out.feeLoss = out.feeBoat + out.feeDon;
    out.income = sum(end.inc) - sum(s0.inc);
    out.netProd = out.income - out.feeAtk - out.feeBoat - out.feeDon;
    out.wealth0 = sum(s0.bal) + sum(s0.atk);
    out.wealth1 = sum(end.bal) + sum(end.atk);

    // ---- 席位结果
    out.alive0 = sum(s0.alive) - sum(s0.husk);
    out.alive1 = sum(end.alive) - sum(end.husk);
    out.husk1 = sum(end.husk);
    out.dead1 = this.squad.length - sum(end.alive);
    out.terr0 = sum(s0.terr); out.terr1 = sum(end.terr);
    out.bal1 = sum(end.bal);
    out.landShare1 = ratio(out.terr1, w.land);
    out.relTerr0 = rel(s0, this.squad.length, w.humans);
    out.relTerr1 = rel(end, this.squad.length, w.humans);
    if (natural) {
      const nat = sum(this.squad.map((p) => natural[p] || 0));
      out.natural = nat;
      out.capture0 = ratio(out.terr0, nat);
      out.capture1 = ratio(out.terr1, nat);
    }
    out.terrGrowth = out.terr0 > 0 ? out.terr1 / out.terr0 : null;
    if (end.teamLand) out.teamLand1 = end.teamLand;
    out.perSeat = this.squad.map((p, i) => ({ p, terr0: s0.terr[i], terr1: end.terr[i], bal1: end.bal[i], alive: end.alive[i], husk: end.husk[i] }));
    out.series = this.series;
    Object.assign(out, extra);
    return out;
  }
}

function ratio(a, b) { return b > 0 ? +(a / b).toFixed(4) : null; }
function rel(s, nSquad, H) {
  const mine = s.terr.reduce((x, y) => x + y, 0) / Math.max(1, nSquad);
  const all = s.humTerr / Math.max(1, H);
  return all > 0 ? +(mine / all).toFixed(4) : null;
}
function minOf(a) { let m = null; for (const x of a) if (x !== null && x !== undefined && (m === null || x < m)) m = x; return m; }
function maxOf(a) { let m = null; for (const x of a) if (x !== null && x !== undefined && (m === null || x > m)) m = x; return m; }

// 真局的重复单占比 / 目标已死改道率：从实录配对（traces/<局>.json，每行 [下令拍 τ, 执行拍 E, 种类, 下令时目标, 生效, 录像目标]）算，
// 口径与模拟臂相同：同一席位、同一种类、同一目标（发船不分目标）的后一条，下令拍落在前一条「已下令、还没执行」之间。
export function traceStats(trace, squad, t0, t1) {
  if (!trace) return null;
  let n = 0, dups = 0, atkP = 0, rer = 0, voidN = 0, atkN = 0;
  const byKind = { 0: [0, 0], 1: [0, 0], 2: [0, 0] };
  for (const p of squad) {
    const rows = trace.seats[String(p)];
    if (!rows) continue;
    const by = new Map();
    for (const r of rows) {
      const key = `${r[2]}|${r[2] === 1 ? -1 : r[3]}`;
      let g = by.get(key);
      if (!g) by.set(key, (g = []));
      g.push(r);
    }
    for (const g of by.values()) {
      g.sort((a, b) => a[0] - b[0]);
      for (let j = 0; j < g.length; j++) {
        const r = g[j];
        if (r[0] < t0 || r[0] >= t1) continue;
        n++; byKind[r[2]][0]++;
        let d = false;
        for (let i = 0; i < j; i++) if (g[i][0] < r[0] && r[0] < g[i][1]) { d = true; break; }
        if (d) { dups++; byKind[r[2]][1]++; }
        if (r[2] === 0) {
          atkN++;
          if (!r[4]) voidN++;
          if (r[3] < NEUTRAL && r.length > 5) { atkP++; if (r[5] === NEUTRAL) rer++; }
        }
      }
    }
  }
  return { n, dups, dupShare: ratio(dups, n), dupAtk: ratio(byKind[0][1], byKind[0][0]), dupBoat: ratio(byKind[1][1], byKind[1][0]), dupDon: ratio(byKind[2][1], byKind[2][0]),
    atkOnPlayer: atkP, rerouted: rer, rerouteRate: ratio(rer, atkP), atkVoidRate: ratio(voidN, atkN) };
}

// 成对差要比的数值项（键、显示名、越大越好 +1 / 越小越好 −1 / 中性 0）
export const PAIR_KEYS = [
  ['capture1', '实抢率（领土÷天然份额）', 1],
  ['relTerr1', '人均相对领土', 1],
  ['terr1', '编队领土（格）', 1],
  ['alive1', '存活席位', 1],
  ['batches', '同拍批（≥3 条）', -1],
  ['dumpBatches', '同拍清仓批', -1],
  ['dumpTicks', '单回合抽走 ≥50% 余额的次数', -1],
  ['batchShare', '同拍批占进录像条数', -1],
  ['dupShare', '重复单占比（进录像）', -1],
  ['dupShareIssued', '重复单占比（发出）', -1],
  ['quotaRejectRate', '配额拒单率（到达结算的捐款里）', -1],
  ['donNotLanded', '捐款发出后没成交的占比', -1],
  ['atkVoidRate', '陆攻落空率', -1],
  ['rerouteRate', '目标已死改道率', -1],
  ['atkNeutralShare', '陆攻落地记成无主地的占比', 0],
  ['landedShare', '进录像 ÷ 发出', 1],
  ['dropped', '被 9 条顶丢弃（条）', -1],
  ['feeLoss', '捐款 + 船手续费（兵）', -1],
  ['feeAtk', '陆攻手续费（兵）', 0],
  ['netProd', '净产兵（收入 − 手续费）', 1],
  ['income', '利息 + 地租入账（兵）', 1],
  ['wealth1', '期末 余额 + 在攻兵', 0],
  ['issued', '发出指令（条）', 0],
];
