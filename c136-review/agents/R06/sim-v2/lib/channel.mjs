// channel.mjs — 锁步时变指令通道。
//
// 锁步：页面本机第 W 拍的局面 = 服务器第 W 拍的局面。所以模拟器在世界第 W 拍调用策略（看到的就是页面当时看到的），
// 只把指令的生效拍往后推：
//     S(W) = 页面算到本机第 W 拍时服务器走到的拍（= W + 落后拍数；不降的阶梯：停一段、再连着算一串）
//     到达 = S(W) + d          d = 发包到进服务器回合的拍数。缺省按实测分布（日志带拍号的发令记录 ↔ 录像执行拍，11 局不卡的局 1659 条）：
//                              快页面 5~10 拍（中位 6.9）、约 1/6 的页面再慢 5 拍、4% 的指令再多等 4~14 拍 → 不落后时 生效拍 − 下令拍
//                              P10/中位/P90 ≈ 7/12/17。写 C1:dMin=10,dMax=12 可回到旧口径（整数均匀）
//     E    = 7 × ceil(到达 / 7)  服务器 7 拍一个回合
// 同一席位的指令按发出次序到达：后发的不会比先发的早到。
// 每个回合（世界拍 % 7 == 0）对每个席位：到点的指令里按发出顺序留前 K 条，K = max(0, 9 − 前两个回合已执行条数)，
// 多出来的丢弃（不顺延）；留下的按「后发的先执行」逐条交给引擎，按执行那一刻的余额计价、校验（目标已出局 → 改打无主地；
// 捐款配额在这时才查）。策略看到的墙钟 = 56 ms × S(W)。
//
// 档位：
//   C0  即时：提交那一刻就执行，返回引擎的真实结果（旧门禁的口径，作对照）
//   C1  正常线上：不落后
//   C2  实录：每个席位的 S(W) 取自真局（traces/<局>.json：影子下令拍 ↔ 录像执行拍 的配对）；页面寿命、通道中断也按实录
//   C3  合成卡顿波：w0~w1 拍之间各席位错开起点掉队，落后拍数先爬到峰值 lagMin~lagMax、停一会儿、再线性追平；页面不是匀速慢放，
//       而是一段一段地算（每段 burstMin~burstMax 个本机拍，其中 1 − smooth 的段在同一个服务器时刻算完）
//   C4  发令自激：C3 之上，每条指令再多等 gain × 编队最近 window 拍已发出的指令条数（上限 exciteCap 拍）
import fs from 'node:fs';
import path from 'node:path';
import { hashInt, hashU, ceil7, num } from './util.mjs';

const TICK_MS = 56;

// d（发包到进服务器回合的拍数）的实测分布。来源：tools/opening_delay.mjs —— 策略日志里带本机拍号的两类发令记录
//（[HL-OPENING] 开局陆攻 710 条、[HL-DISPATCH] 捐款 949 条，11 局不卡的局）对录像执行拍，按下令拍的相位分组直接读出
// P(d ≤ k)：k=5 3%，6 16%，7 46%，8 62%，9 72%，10 78%，12 88%，14 95%。按席位看，约 1/6 的页面整体慢 5 拍左右（均值 15 对 10.5）。
// 拆成三部分：快页面的 d 在 5~10 拍之间（下面的分段线性累积分布）；慢页面（占 slowShare）再加 slowExtra 拍；每条指令有 hiccup 的概率再多等 4~14 拍。
const D_KNOTS = [[5.0, 0], [5.2, 0.03], [6, 0.2], [7, 0.55], [8, 0.75], [9, 0.9], [10, 1]];
function dFast(u) {
  for (let i = 1; i < D_KNOTS.length; i++) {
    const [x1, f1] = D_KNOTS[i], [x0, f0] = D_KNOTS[i - 1];
    if (u <= f1) return x0 + (x1 - x0) * (u - f0) / Math.max(1e-9, f1 - f0);
  }
  return D_KNOTS[D_KNOTS.length - 1][0];
}

export class Profile {
  constructor(name, o = {}) {
    this.name = name;
    this.instant = name === 'C0';
    this.seed = o.seed ?? 1;
    // 给了 dMin / dMax 就用旧口径（整数均匀）；缺省用实测分布
    this.dUniform = o.dMin !== undefined || o.dMax !== undefined;
    this.dMin = o.dMin ?? 10;
    this.dMax = o.dMax ?? 12;
    this.slowShare = o.slowShare ?? (name === 'C2' ? 0 : 0.18);   // C2 的阶梯来自实录，慢页面已经在阶梯里
    this.slowExtra = o.slowExtra ?? 5;
    this.hiccup = o.hiccup ?? 0.04;
    this.stairs = new Map();   // 席位 → Int32Array：S(W)
    this.Wmax = o.Wmax ?? 16000;
    this.o = o;
    this.note = '';
  }

  serverTick(p, W) {
    const s = this.stairs.get(p);
    if (!s) return W;
    return W < s.length ? s[W] : Math.max(W, s[s.length - 1]);
  }

  lag(p, W) { return this.serverTick(p, W) - W; }
  slowSeat(p) { return this.slowShare > 0 && hashU(this.seed, p, 81) < this.slowShare; }
  delay(p, W) {
    if (this.dUniform) return this.dMin === this.dMax ? this.dMin : hashInt(this.dMin, this.dMax, this.seed, p, W, 77);
    let d = dFast(hashU(this.seed, p, W, 77));
    if (this.slowSeat(p)) d += this.slowExtra;
    if (this.hiccup > 0 && hashU(this.seed, p, W, 78) < this.hiccup) d += 4 + 10 * hashU(this.seed, p, W, 79);
    return d;
  }
  // 不落后时 生效拍 − 下令拍 的典型值（d 的均值 + 回合相位的一半）：C2 用它把实录的执行拍换回服务器时刻
  get dMid() { return this.dUniform ? Math.round((this.dMin + this.dMax) / 2) + 3 : 12; }
  dNote() { return this.dUniform ? `d=${this.dMin}~${this.dMax}（生效拍 − 下令拍 = ${this.dMin}~${this.dMax + 6}）` : `d 按实测分布（快页面 5~10 拍、中位 6.9；${Math.round(100 * this.slowShare)}% 的页面再慢 ${this.slowExtra} 拍；${Math.round(100 * this.hiccup)}% 的指令再多等 4~14 拍）`; }
  clockMs(p, W) { return TICK_MS * this.serverTick(p, W); }

  // C3 合成卡顿波。每个席位一条「落后拍数」曲线：w0 起错开 onset 拍内开始掉队 → ramp 个本机拍内爬到峰值 L（lagMin~lagMax 里取）
  // → 峰值上停 plateau 个本机拍 → 线性追回，到 w1 追平。页面不是匀速慢放，而是「停一段、把一串本机拍在同一个服务器时刻算完」：
  // 每串 burstMin~burstMax 个本机拍，这一串里每一拍的 S 都等于串尾那一拍的 本机拍 + 落后拍数。
  // 缺省形状取自 12 局卡顿局的实录（c110：B010 B017 B022 B023 B038 B039；Vb：A021 A027 A049 A057 A058 A070）：每 300 拍一段的
  // 平均落后拍数（12 局的均值）约 600~900:150、900~1200:390、1200~1500:390、1500~1800:300、1800~2100:150、2100~2400:60、之后 ≈ 0；
  // 各局峰值 140~940 拍。同一回合落地的一串指令跨 60~110 个本机拍（中位）、相邻两个落地回合隔 63~196 拍（中位）。
  // 任务卡写的「600~2100 拍、落后 150~400 拍」可以用 C3:w1=2100,lagMin=150,lagMax=400,ramp=250,plateau=150 得到。
  buildC3(seats) {
    const o = this.o;
    const w0 = o.w0 ?? 600, w1 = o.w1 ?? 2400, lagMin = o.lagMin ?? 150, lagMax = o.lagMax ?? 450;
    const bMin = o.burstMin ?? 30, bMax = o.burstMax ?? 150;
    const onset = o.onset ?? 150, ramp = Math.max(1, o.ramp ?? 350), plateau = o.plateau ?? 450, share = o.share ?? 1;
    const smooth = o.smooth ?? 0.12;  // 落后期间「一拍一拍算」的段落占比（其余是成串算）
    const N = this.Wmax + 1;
    let k = 0;
    for (const p of seats) {
      const ord = k++;
      if (hashU(this.seed, p, 5) >= share) continue;
      const s = new Int32Array(N);
      for (let W = 0; W < N; W++) s[W] = W;
      const Wa = w0 + Math.floor(onset * ((ord + hashU(this.seed, p, 6)) / Math.max(1, seats.length)));
      const L = hashInt(lagMin, lagMax, this.seed, p, 7);
      const Wp = Math.min(w1 - 1, Wa + ramp + plateau);
      const lagAt = (W) => (W < Wa ? 0 : W < Wa + ramp ? L * (W - Wa) / ramp : W < Wp ? L : W < w1 ? L * (w1 - W) / Math.max(1, w1 - Wp) : 0);
      let W1 = Wa, j = 0, Tprev = Wa;
      while (W1 < w1 && W1 < N) {
        const b = hashInt(bMin, bMax, this.seed, p, W1, 31 + j);
        const W2 = Math.min(N - 1, w1 - 1, W1 + b - 1);
        if (hashU(this.seed, p, W1, 57 + j) < smooth) {
          // 这一段页面在「落后着一拍一拍地算」：每一拍各有各的服务器时刻
          for (let W = W1; W <= W2; W++) { const T = Math.max(Tprev, W + Math.round(lagAt(W))); s[W] = Math.max(T, W); Tprev = T; }
        } else {
          const T = Math.max(Tprev, W2 + Math.round(lagAt(W2)));
          for (let W = W1; W <= W2; W++) s[W] = Math.max(T, W);
          Tprev = T;
        }
        j++;
        W1 = W2 + 1;
      }
      for (let W = 1; W < N; W++) if (s[W] < s[W - 1]) s[W] = s[W - 1];
      this.stairs.set(p, s);
    }
    this.note = `C3 合成卡顿波：${w0}~${w1} 拍，各席位错开 ${onset} 拍内开始掉队，${ramp} 拍爬到峰值落后 ${lagMin}~${lagMax} 拍、停 ${plateau} 拍、再线性追回到 ${w1} 拍追平；每段 ${bMin}~${bMax} 个本机拍，${Math.round(100 * (1 - smooth))}% 的段在同一时刻算完、其余逐拍算`;
  }

  // C2：traces/<局>.json 里每个席位的 (下令拍 τ, 执行拍 E) 配对 → S(τ) = max(τ, E − dMid)。已知点之间怎么补：
  //   auto（缺省）相邻两个已知点都只落后一点（≤ thr 拍，缺省 28）→ 页面在连续地算、只是慢半步：线性；有一头落后得多 → 页面在成串地追：取近的那个已知点。
  //   nearest     一律取近的那个已知点：S 是纯阶梯——页面停一段、再把一串本机拍在同一个服务器时刻算完。
  //   burst,m=16  已知点前后各 m 个本机拍与它同一串、两串之间线性；linear 全线性（页面匀速慢放）；upper / lower 取后 / 前一个点。
  //   各种补法对着真局的对照见 SIM-V2-CALIBRATION-G0.md：linear 的同拍批占比明显偏低；nearest 在轻微落后的局里同拍批偏多；auto 两头都贴近。
  // 最后一个已知点之后保持不降直到追平（缺省）；after=hold 改成一直保持那个已知点上的落后，after=cut 改成之后发出的
  // 指令一律没落地（在 makeProfile 里）——都只作对照用，看「已知点之后其实还在卡」的局对这条假定有多敏感
  // （SIM-V2-CALIBRATION-G0.md 断面一节）。
  buildC2(seats, trace, fill = 'linear', seatMap = null) {
    const N = this.Wmax + 1;
    // fill=burst：已知点前后各 m 个本机拍算同一串（S 与那个已知点相同），两串之间线性。m=0 就是 linear，m 很大就是 nearest。
    const m = fill === 'burst' ? Math.max(0, this.o.m ?? 16) : 0;
    // fill=auto：两头的已知点都只落后一点（≤ thr 拍）→ 页面是在连续地算、只是慢半步（线性）；有一头落后得多 → 页面在成串地追（nearest）。
    const thr = this.o.thr ?? 28;
    const between = (W, ta, sa, tb, sb) => {
      if (fill === 'upper') return sb;
      if (fill === 'lower') return sa;
      if (fill === 'auto') {
        if (Math.max(sa - ta, sb - tb) <= thr) return Math.round(sa + (sb - sa) * (W - ta) / (tb - ta));
        return W - ta <= tb - W ? sa : sb;
      }
      if (fill === 'nearest') return W - ta <= tb - W ? sa : sb;
      if (fill === 'burst') {
        if (tb - ta <= 2 * m) return W - ta <= tb - W ? sa : sb;
        if (W - ta <= m) return sa;
        if (tb - W <= m) return sb;
        return Math.round(sa + (sb - sa) * (W - ta - m) / (tb - ta - 2 * m));
      }
      return Math.round(sa + (sb - sa) * (W - ta) / (tb - ta));
    };
    const dMid = this.dMid; // 不落后时 E − τ 的中位（实测 12）
    let used = 0;
    for (const p of seats) {
      const src = seatMap ? seatMap.get(p) : p;
      const rows = trace.seats[String(src)];
      if (!rows || !rows.length) continue;
      // 后缀最小：阶梯不降
      const pts = rows.map(([tau, E]) => [tau, Math.max(tau, E - dMid)]).sort((a, b) => a[0] - b[0]);
      for (let i = pts.length - 2; i >= 0; i--) if (pts[i][1] > pts[i + 1][1]) pts[i][1] = pts[i + 1][1];
      const s = new Int32Array(N);
      let j = 0;
      for (let W = 0; W < N; W++) {
        while (j < pts.length && pts[j][0] < W) j++;
        let v;
        if (j >= pts.length) v = this.o.after === 'hold' ? W + Math.max(0, pts[pts.length - 1][1] - pts[pts.length - 1][0]) : Math.max(W, pts[pts.length - 1][1]);
        else if (pts[j][0] === W) v = pts[j][1];
        else if (j === 0) v = fill === 'upper' ? pts[0][1] : W;
        else {
          const [ta, sa] = pts[j - 1], [tb, sb] = pts[j];
          v = between(W, ta, sa, tb, sb);
        }
        s[W] = Math.max(W, v);
      }
      for (let W = 1; W < N; W++) if (s[W] < s[W - 1]) s[W] = s[W - 1];
      this.stairs.set(p, s);
      used++;
    }
    this.note = `C2 实录阶梯：${used}/${seats.length} 个席位有实录（${trace.matchId}，配对 ${trace.rows} 条），已知点之间 ${fill}${fill === 'burst' ? `（m=${m}）` : fill === 'auto' ? `（两头落后都 ≤ ${thr} 拍时线性，否则取近的已知点）` : ''}${this.o.after === 'hold' ? '；最后一个已知点之后保持那时的落后（对照用）' : ''}`;
    return used;
  }

  // 落后拍数的时间剖面（全体席位平均，每 step 拍一个点）——写进结果里，方便和实录对照
  lagCourse(seats, a, b, step = 150) {
    const out = [];
    for (let t = a; t < b; t += step) {
      let s = 0, n = 0;
      for (const p of seats) { s += this.lag(p, t); n++; }
      out.push([t, n ? Math.round(s / n) : 0]);
    }
    return out;
  }
}

// 命令行的通道写法：C1 | C2 | C3 | C3:w0=600,w1=2100,lagMin=150,lagMax=400 | C1:dMin=10,dMax=12 …
export function parseChannel(spec) {
  const s = String(spec || 'C1');
  const [name, rest] = s.split(':');
  const o = {};
  if (rest) for (const kv of rest.split(',')) { const [k, v] = kv.split('='); o[k.trim()] = Number.isNaN(+v) ? v : +v; }
  return { name: name.toUpperCase(), o };
}

export function loadTrace(simv2Dir, mid) {
  const f = path.join(simv2Dir, 'traces', `${mid}.json`);
  if (!fs.existsSync(f)) return null;
  return JSON.parse(fs.readFileSync(f, 'utf8'));
}

export function makeProfile(spec, ctx) {
  const { name, o } = parseChannel(spec);
  const prof = new Profile(name, { seed: ctx.seed ?? 1, Wmax: ctx.Wmax ?? 16000, ...o });
  if (name === 'C0') prof.note = 'C0 即时：提交即执行';
  else if (name === 'C1') prof.note = `C1 正常线上：不落后，${prof.dNote()}`;
  else if (name === 'C2') {
    const trace = ctx.trace;
    if (!trace) throw new Error('C2 要实录阶梯：这一局没有 sim-v2/traces/<局>.json（先跑 tools/export_traces.py），或用 --trace-from 指定别的局');
    prof.buildC2(ctx.seats, trace, o.fill || 'auto', ctx.seatMap || null);
    // 页面寿命：实录里这个席位的页面最后有动静的本机拍；之后不再调策略（在途的指令照常落地）。pagedeath=0 关掉。
    if (ctx.pageEnd && o.pagedeath !== 0) {
      prof.pageEnd = new Map(ctx.pageEnd);
      prof.doomed = ctx.doomed || null;
      // 席位还活着页面就停摆的：它最后一条落地的指令之后发出的，实录里一条也没落地 → 通道在那之后算断了（指令发出即丢）
      if (ctx.doomed && ctx.doomed.size && ctx.ownTrace !== false) {
        prof.lostAfter = new Map();
        for (const p of ctx.seats) {
          if (!ctx.doomed.has(p)) continue;
          const rows = trace.seats[String(ctx.seatMap ? ctx.seatMap.get(p) : p)];
          prof.lostAfter.set(p, rows && rows.length ? Math.max(...rows.map((r) => r[0])) : -1);
        }
      }
      prof.note += `；页面寿命按实录（${ctx.doomed ? ctx.doomed.size + ' 个席位的页面在席位还活着时停摆' : '停摆与否到时按历史臂里席位是否还活着判断'}${prof.lostAfter ? '，其最后一条落地指令之后发出的算丢失' : ''}）`;
    }
    // after=cut（只作对照用）：每个席位最后一个已知点之后发出的指令一律算没落地。影子在那之后发的指令本来就一条也没进录像
    // （进了就会配成已知点）；缺省假定是页面追平、指令照常落地，这一档是另一头。SIM-V2-CALIBRATION-G0.md 断面一节拿它查
    // 录像在卡顿当中截断的局。
    if (o.after === 'cut' && ctx.ownTrace !== false) {
      prof.lostAfter = prof.lostAfter || new Map();
      let nCut = 0;
      for (const p of ctx.seats) {
        const rows = trace.seats[String(ctx.seatMap ? ctx.seatMap.get(p) : p)];
        if (!rows || !rows.length) continue;
        prof.lostAfter.set(p, Math.max(...rows.map((r) => r[0])));
        nCut++;
      }
      prof.note += `；${nCut} 个席位最后一个已知点之后发出的指令算没落地（对照用）`;
    }
  } else if (name === 'C3' || name === 'C4') {
    prof.buildC3(ctx.seats);
    if (name === 'C4') { prof.selfExcite = { gain: o.gain ?? 2, window: o.window ?? 100, cap: o.exciteCap ?? 300 }; prof.note = prof.note.replace('C3 合成卡顿波', 'C4 发令自激卡顿波') + `；每条指令再多等 ${prof.selfExcite.gain} × 编队最近 ${prof.selfExcite.window} 拍的发令条数（上限 ${prof.selfExcite.cap} 拍）`; }
  } else throw new Error(`不认识的通道档 ${name}（C0 / C1 / C2 / C3 / C4）`);
  return prof;
}

export class Channel {
  // host：{ world, execOur(seat, cmd) → {ok, rec, …}, onIssue(seat, cmd), onDrop(seat, cmd), onRound(t) }
  constructor(host, profile, o = {}) {
    this.host = host;
    this.profile = profile;
    this.instant = profile.instant;
    this.multi = !!o.multi;            // true = 一个决策拍可以受理多条（线下口径；缺省关）
    this.cap = o.cap ?? 9;             // 连续 3 个回合最多执行的条数
    this.capRounds = o.capRounds ?? 3;
    this.keep = o.keep || 'first';     // 超顶时留 first（最早发出的）| last（最晚发出的）
    this.order = o.order || 'lifo';    // 同一回合内的执行次序：lifo（后发先执行）| fifo
    this.q = [];
    this.seq = 0;
    this.hist = new Map();             // 席位 → 最近 capRounds−1 个回合各执行了几条
    this.recent = [];                  // C4：最近发令的拍号
    this.lastArrive = new Map();       // 席位 → 上一条指令的到达拍
  }

  submit(seat, cmd) {
    const w = this.host.world, W = w.t, p = seat.p;
    cmd.p = p; cmd.W = W; cmd.seq = this.seq++;
    if (this.instant) {
      cmd.arrive = W; cmd.E = W;
      this.host.onIssue(seat, cmd);
      const res = this.host.execOur(seat, cmd);
      return cmd.k === 'atk' ? res.ok : res.ok;
    }
    const prof = this.profile;
    if (prof.lostAfter && prof.lostAfter.has(p) && W > prof.lostAfter.get(p)) {
      cmd.arrive = Infinity; cmd.E = Infinity;
      this.host.onIssue(seat, cmd);
      this.host.onDrop(seat, cmd, 'deadchan');
      return true;
    }
    cmd.arrive = prof.serverTick(p, W) + prof.delay(p, W) + (prof.selfExcite ? this.excite(seat, W) : 0);
    // 同一席位的指令按发出次序到达（一条连接）：后发的不会比先发的早到
    const la = this.lastArrive.get(p);
    if (la !== undefined && cmd.arrive < la) cmd.arrive = la;
    this.lastArrive.set(p, cmd.arrive);
    cmd.E = ceil7(cmd.arrive);
    this.q.push(cmd);
    cmd.seat = seat;
    this.host.onIssue(seat, cmd);
    return true;
  }

  // 接管之前影子发的指令：按同一条通道算生效拍，生效拍落在接管拍 T0 之后的算「接管时还在路上」，照常排队落地（标 pre）；
  // 生效拍在 T0 之前的不进世界（那段时间世界照录像走）。
  submitPre(seat, cmd, T0) {
    if (this.instant) return;
    const W = this.host.world.t, p = seat.p, prof = this.profile;
    if (prof.lostAfter && prof.lostAfter.has(p) && W > prof.lostAfter.get(p)) return;
    let arrive = prof.serverTick(p, W) + prof.delay(p, W);
    const la = this.lastArrive.get(p);
    if (la !== undefined && arrive < la) arrive = la;
    this.lastArrive.set(p, arrive);
    const E = ceil7(arrive);
    if (E < T0) return;
    cmd.p = p; cmd.W = W; cmd.seq = this.seq++; cmd.arrive = arrive; cmd.E = E; cmd.pre = true; cmd.seat = seat;
    this.q.push(cmd);
    this.host.onIssue(seat, cmd);
  }

  // C4：发令越密，指令到得越晚。编队最近 window 个本机拍每发过 1 条，这一条就多等 gain 拍（上限 cap）。返回多等的拍数。
  excite(seat, W) {
    const se = this.profile.selfExcite;
    this.recent.push(W);
    while (this.recent.length && this.recent[0] < W - se.window) this.recent.shift();
    return Math.min(se.cap, se.gain * (this.recent.length - 1));
  }

  pending() { return this.q.length; }

  // 世界第 t 拍的回合结算（t % 7 == 0 时调）
  settle(t) {
    const hist = this.hist, R = this.capRounds - 1;
    const due = [];
    if (this.q.length) {
      const rest = [];
      for (const c of this.q) (c.E <= t ? due : rest).push(c);
      this.q = rest;
    }
    const execN = new Map();
    if (due.length) {
      // 每个席位：按发出顺序排，过 9 条顶
      const by = new Map();
      for (const c of due) { let a = by.get(c.p); if (!a) by.set(c.p, (a = [])); a.push(c); }
      const run = [];
      for (const [p, a] of by) {
        a.sort((x, y) => x.seq - y.seq);
        const h = hist.get(p);
        let used = 0;
        if (h) for (let i = 0; i < R; i++) used += h[i] || 0;
        const K = Math.max(0, this.cap - used);
        let keep = a, drop = [];
        if (a.length > K) {
          if (this.keep === 'last') { keep = a.slice(a.length - K); drop = a.slice(0, a.length - K); }
          else { keep = a.slice(0, K); drop = a.slice(K); }
        }
        for (const c of drop) this.host.onDrop(c.seat, c, 'cap');
        for (const c of keep) { c.batchN = keep.length; run.push(c); }
        execN.set(p, keep.length);
      }
      // 回合内的执行次序：后到的先执行（同一席位内就是后发先执行）
      if (this.order === 'fifo') run.sort((x, y) => x.arrive - y.arrive || x.seq - y.seq);
      else run.sort((x, y) => y.arrive - x.arrive || y.seq - x.seq);
      for (const c of run) this.host.execOur(c.seat, c);
    }
    // 滚动每个席位的回合计数
    for (const [p, h] of hist) {
      for (let i = R - 1; i > 0; i--) h[i] = h[i - 1];
      h[0] = execN.get(p) || 0;
      execN.delete(p);
    }
    for (const [p, n] of execN) { const h = new Array(R).fill(0); h[0] = n; hist.set(p, h); }
  }

  // 窗口结束时还在路上的指令
  flushPending() {
    const rest = this.q;
    this.q = [];
    return rest;
  }
}

export { TICK_MS, num };
