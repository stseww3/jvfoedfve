// channel.mjs — 锁步时变指令通道。
//
// 锁步：页面本机第 W 拍的局面 = 服务器第 W 拍的局面。所以模拟器在世界第 W 拍调用策略（看到的就是页面当时看到的），
// 只把指令的生效拍往后推：
//     S(W) = 页面算到本机第 W 拍时服务器走到的拍（= W + 落后拍数；不降的阶梯：停一段、再连着算一串）
//     到达 = S(W) + d          d = 发包到进服务器回合的拍数（缺省 10~12 → 不落后时 生效拍 − 下令拍 = 10~18）
//     E    = 7 × ceil(到达 / 7)  服务器 7 拍一个回合
// 每个回合（世界拍 % 7 == 0）对每个席位：到点的指令里按发出顺序留前 K 条，K = max(0, 9 − 前两个回合已执行条数)，
// 多出来的丢弃（不顺延）；留下的按「后发的先执行」逐条交给引擎，按执行那一刻的余额计价、校验（目标已出局 → 改打无主地；
// 捐款配额在这时才查）。策略看到的墙钟 = 56 ms × S(W)。
//
// 档位：
//   C0  即时：提交那一刻就执行，返回引擎的真实结果（旧门禁的口径，作对照）
//   C1  正常线上：不落后，d = 10~12
//   C2  实录：每个席位的 S(W) 取自真局（traces/<局>.json：影子下令拍 ↔ 录像执行拍 的配对）
//   C3  合成卡顿波：w0~w1 拍之间各席位错开起点，一次落后 lagMin~lagMax 拍，然后一串一串地追（每串 burstMin~burstMax 个本机拍
//       在同一个服务器时刻算完，追帧平均速度 speed 倍），追平或到 w1 为止
//   C4  发令自激：同 C3，但每次落后的拍数 = lagMin + gain × 编队最近 100 拍已发出的指令条数（上限 lagMax）
import fs from 'node:fs';
import path from 'node:path';
import { hashInt, hashU, ceil7, num } from './util.mjs';

const TICK_MS = 56;

export class Profile {
  constructor(name, o = {}) {
    this.name = name;
    this.instant = name === 'C0';
    this.seed = o.seed ?? 1;
    this.dMin = o.dMin ?? 10;
    this.dMax = o.dMax ?? 12;
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
  delay(p, W) { return this.dMin === this.dMax ? this.dMin : hashInt(this.dMin, this.dMax, this.seed, p, W, 77); }
  clockMs(p, W) { return TICK_MS * this.serverTick(p, W); }

  // C3 / C4 的一段卡顿：从本机拍 Wa 起落后 J 拍，然后成串追帧。返回追平的本机拍。
  stall(s, p, Wa, J, w1) {
    const o = this.o;
    const bMin = o.burstMin ?? 20, bMax = o.burstMax ?? 60, speed = o.speed ?? 1.45;
    let T = Wa + J, Wc = Wa, k = 0;
    const N = s.length;
    while (Wc < N && T > Wc) {
      let b = hashInt(bMin, bMax, this.seed, p, Wc, 31 + k++);
      if (Wc + b >= w1) b = Math.max(1, T - Wc + 1);              // 到 w1：剩下的积压一口气算完
      if (Wc + b > T) b = Math.max(1, T - Wc + 1);                 // 最后一串：正好追到当前
      const end = Math.min(N, Wc + b);
      for (let W = Wc; W < end; W++) s[W] = Math.max(T, W, s[W]);
      Wc = end;
      T += Math.ceil(b / speed);
    }
    return Wc;
  }

  buildC3(seats) {
    const o = this.o;
    const w0 = o.w0 ?? 600, w1 = o.w1 ?? 2100, lagMin = o.lagMin ?? 150, lagMax = o.lagMax ?? 400;
    const share = o.share ?? 1, onsetSpan = o.onsetSpan ?? 0.4;
    const N = this.Wmax + 1;
    let k = 0;
    for (const p of seats) {
      const ord = k++;
      if (hashU(this.seed, p, 5) >= share) continue;
      const s = new Int32Array(N);
      for (let W = 0; W < N; W++) s[W] = W;
      // 起点按席位次序错开，铺满 w0 起的前 onsetSpan 段
      const span = Math.max(1, Math.floor((w1 - w0) * onsetSpan));
      let Wa = w0 + Math.floor(span * ((ord + hashU(this.seed, p, 6)) / Math.max(1, seats.length)));
      let ep = 0;
      while (Wa < w1 - 50 && ep < 6) {
        const J = hashInt(lagMin, lagMax, this.seed, p, 7 + ep);
        const end = this.stall(s, p, Wa, J, w1);
        Wa = end + hashInt(o.gapMin ?? 150, o.gapMax ?? 450, this.seed, p, 8 + ep);
        ep++;
      }
      this.stairs.set(p, s);
    }
    this.note = `C3 合成卡顿波：${w0}~${w1} 拍，每次落后 ${lagMin}~${lagMax} 拍，追帧每串 ${o.burstMin ?? 20}~${o.burstMax ?? 60} 个本机拍、平均 ${o.speed ?? 1.45} 倍速`;
  }

  // C2：traces/<局>.json 里每个席位的 (下令拍 τ, 执行拍 E) 配对 → S(τ) = max(τ, E − dMid)。已知点之间怎么补：
  //   burst（缺省，m=16）已知点前后各 m 个本机拍与它同一串、两串之间线性；linear 全线性；nearest 取近的那个点；upper / lower 取后 / 前一个点。
  //   缺省值是拿 B039 / B023 / B017 的 630~1500 拍对着真局的「同拍批占比、同回合连发占比、同拍批数」调出来的（见 SIM-V2-CALIBRATION-G0.md）。
  // 最后一个已知点之后保持不降直到追平。
  buildC2(seats, trace, fill = 'linear', seatMap = null) {
    const N = this.Wmax + 1;
    // fill=burst：已知点前后各 m 个本机拍算同一串（S 与那个已知点相同），两串之间线性。m=0 就是 linear，m 很大就是 nearest。
    const m = fill === 'burst' ? Math.max(0, this.o.m ?? 16) : 0;
    const between = (W, ta, sa, tb, sb) => {
      if (fill === 'upper') return sb;
      if (fill === 'lower') return sa;
      if (fill === 'nearest') return W - ta <= tb - W ? sa : sb;
      if (fill === 'burst') {
        if (tb - ta <= 2 * m) return W - ta <= tb - W ? sa : sb;
        if (W - ta <= m) return sa;
        if (tb - W <= m) return sb;
        return Math.round(sa + (sb - sa) * (W - ta - m) / (tb - ta - 2 * m));
      }
      return Math.round(sa + (sb - sa) * (W - ta) / (tb - ta));
    };
    const dMid = Math.round((this.dMin + this.dMax) / 2) + 3; // 不落后时 E − τ 的中位约 14
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
        if (j >= pts.length) v = Math.max(W, pts[pts.length - 1][1]);
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
    this.note = `C2 实录阶梯：${used}/${seats.length} 个席位有实录（${trace.matchId}，配对 ${trace.rows} 条），已知点之间 ${fill}${fill === 'burst' ? `（m=${m}）` : ''}`;
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
  else if (name === 'C1') prof.note = `C1 正常线上：不落后，d=${prof.dMin}~${prof.dMax}（生效拍 − 下令拍 = ${prof.dMin}~${prof.dMax + 6}）`;
  else if (name === 'C2') {
    const trace = ctx.trace;
    if (!trace) throw new Error('C2 要实录阶梯：这一局没有 sim-v2/traces/<局>.json（先跑 tools/export_traces.py），或用 --trace-from 指定别的局');
    prof.buildC2(ctx.seats, trace, o.fill || 'burst', ctx.seatMap || null);
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
  } else if (name === 'C3' || name === 'C4') {
    prof.buildC3(ctx.seats);
    if (name === 'C4') { prof.selfExcite = { gain: o.gain ?? 4, window: o.window ?? 100 }; prof.note = prof.note.replace('C3 合成卡顿波', 'C4 发令自激卡顿波') + `；每次落后 = lagMin + ${prof.selfExcite.gain} × 编队最近 ${prof.selfExcite.window} 拍发令条数`; }
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
    if (prof.selfExcite) this.excite(seat, W);
    cmd.arrive = prof.serverTick(p, W) + prof.delay(p, W);
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
    const arrive = prof.serverTick(p, W) + prof.delay(p, W);
    const E = ceil7(arrive);
    if (E < T0) return;
    cmd.p = p; cmd.W = W; cmd.seq = this.seq++; cmd.arrive = arrive; cmd.E = E; cmd.pre = true; cmd.seat = seat;
    this.q.push(cmd);
    this.host.onIssue(seat, cmd);
  }

  // C4：发令越密，下一次卡得越久。编队最近 window 拍每发 1 条，当前席位「下一段卡顿」的落后拍数加 gain。
  excite(seat, W) {
    const se = this.profile.selfExcite;
    this.recent.push(W);
    while (this.recent.length && this.recent[0] < W - se.window) this.recent.shift();
    const s = this.profile.stairs.get(seat.p);
    if (!s || W + 1 >= s.length) return;
    const extra = Math.min(this.profile.o.lagMax ?? 400, se.gain * this.recent.length);
    // 只在席位当前不落后时触发新的卡顿（已经在追帧的不叠加）
    if (s[W] - W > 20 || hashU(this.profile.seed, seat.p, W, 91) > 0.02) return;
    this.profile.stall(s, seat.p, W + 1, (this.profile.o.lagMin ?? 150) + extra, s.length);
    for (let k = W + 2; k < s.length; k++) if (s[k] < s[k - 1]) s[k] = s[k - 1];
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
