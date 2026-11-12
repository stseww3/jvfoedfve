#!/usr/bin/env node
// cloneprobe.mjs — 断面克隆续跑的保真度（会审稿验收条款 S2、S3 的现状）。
//
// 断面反事实有两种做法：从头按录像重演到断面再分叉（前缀重放），或者在断面把对局对象克隆一份再分叉（克隆续跑）。
// src/sim/sim/clone.js 给了克隆：Game.prototype.clone()。读代码有两件事要量：
//   · 拷贝出来的对象原型固定是基类 Game.prototype（clone.js L18）。重放器比基类多出来的三处（各队总地的 32 拍缓存、
//     组队版猎杀、组队版终局提速）都在子类 TGame 的方法里，拷贝以后这三处退回基类的写法。
//   · 拷贝是逐字段的（clone.js L20-29），漏一个会变的字段，续跑就会和原对局分开。
// 这里不分叉、不改任何指令：在断面 T 克隆，然后原对象和拷贝吃同一份录像指令，逐拍并排比。两条臂：
//   原样   clone() 返回什么就用什么（原型是基类）
//   恢复类 把拷贝的原型改回原对象的类（TGame），其余不动——这一条只考「状态拷全了没有」
// 每个断面（630 / 1500 / 4284）各克隆一次，续跑到下一个断面（最后一个续跑到局末），段末把两边的全部字段逐个比一遍。
// 顺手记一件事（huskprobe 查到的那一处走偏的暴露面），两个量：
//   gap      组队局里「还有地的队只剩一个、而第二名个人还有地」第一次出现在哪一拍（各队总地读 32 拍缓存，和线上引擎 bk.a6U() 同一份）。
//   scanGap  模拟器的 scanTick 走到「要不要重扫」那一步（bots.js L723）、按模拟器的规则不重扫（第二名个人还有地）、
//            而按线上引擎组队局的规则（bD.gv.mf()：还有地的队多于一个才不重扫）该重扫——第一次出现在哪一拍。
//            从这一拍起两边的无主地扫描表分开。这是照着模拟器自己的状态推的，没有跑线上引擎；A001 上 huskprobe 直接读到的是 4676 拍这一步、4678 拍表里有了格子。
// 每一局用它自己那份录像（不换同房另一份包的录像）：同一个物理房间出了两份包的（roompairs.txt），两份录像是同一条指令流，
// 这里各跑各的，输出里带一个房间记号 roomKey（真人数、地图号、地图种子、整张名单的摘要），汇总时按房间去重。
// 顺手把参照重演对本包日志快照的逐行核对结果（行数、地和兵都一致的行数）记下来，汇总时和 fidabl 已入库的数对一遍。
// 只读 /agent/repos/c136-data（发现集的对局包 + src/sim）；不跑策略。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/cloneprobe.mjs [--budget 秒] [--at 630,1500,4284] <局> [<局> ...]
//   → out/_run/cloneprobe/<局>.json（已有的跳过）；汇总见 cloneprobe.py
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUN = path.join(HERE, '..', 'out', '_run');
const OUT = path.join(RUN, 'cloneprobe');
const argv = process.argv.slice(2);
let budget = 80, AT = [630, 1500, 4284];
const mids = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--budget') budget = +argv[++i];
  else if (argv[i] === '--at') AT = argv[++i].split(',').map(Number);
  else mids.push(argv[i]);
}
const T0 = Date.now();

// 重放器喂给对局对象的入口（resim_r08.mjs execCmd 用到的全部会改状态的方法）+ 推进一拍
const ENTRY = ['attack', 'donate', 'boat', 'recall', 'chase', 'retreat', 'leave', 'tick'];
// 子类自己的两个字段：基类的方法不读也不写，原样那条臂里它们停在克隆那一拍的值，单列，不算进「字段不等」
const SUB_ONLY = new Set(['teamCache', 'teamW0']);

function sameSeq(u, v) {
  if (u === v) return true;
  if (!u || !v || u.length !== v.length) return false;
  for (let j = 0; j < u.length; j++) if (u[j] !== v[j]) return false;
  return true;
}

// 两个对局对象的全部自有字段逐个比；返回不等的字段名
function deepDiff(a, b) {
  const diffs = [];
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const x = a[k], y = b[k];
    if (typeof x === 'function' || typeof y === 'function' || x === y) continue;
    if (x === null || y === null || x === undefined || y === undefined || typeof x !== 'object' || typeof y !== 'object') { diffs.push(k); continue; }
    if (ArrayBuffer.isView(x)) { if (!ArrayBuffer.isView(y) || !sameSeq(x, y)) diffs.push(k); continue; }
    if (Array.isArray(x)) {
      let same = Array.isArray(y) && x.length === y.length;
      for (let i = 0; same && i < x.length; i++) same = sameSeq(x[i], y[i]);
      if (!same) diffs.push(k);
      continue;
    }
    if (x instanceof Map) {
      let same = y instanceof Map && x.size === y.size;
      if (same) for (const [kk, vv] of x) if (y.get(kk) !== vv) { same = false; break; }
      if (!same) diffs.push(k);
      continue;
    }
    if ('s' in x && 's' in y) { if (x.s !== y.s) diffs.push(k); continue; }
    diffs.push(`${k}（没法比）`);
  }
  return diffs;
}

function probe(mid) {
  const segs = [];
  let live = [];
  let G = null;
  let gap = null;
  let scanGap = null;
  const teamsLeft = (g) => {
    let left = 0;
    for (const v of g.teamCacheGet().subarray(0, g.nTeams + 1)) left += v > 0 ? 1 : 0;
    return left;
  };
  const mk = (g, T, arm) => {
    const s = { T, arm, origClass: g.constructor.name, cloneProto: null, cloneErr: null, g: null, live: false,
      firstVis: null, vis: null, firstHid: null, hid: null, err: null, errT: null, endT: null, endWhy: null, diffAtEnd: null, subOnlyStale: null };
    segs.push(s);
    try {
      const c = g.clone();
      s.cloneProto = Object.getPrototypeOf(c).constructor.name;
      if (arm === 'class') Object.setPrototypeOf(c, Object.getPrototypeOf(g));
      // 原对象身上挂着的函数（重放器记账用的钩子、本脚本的分发壳）不属于模拟器，拷贝上去掉
      for (const k of Object.keys(c)) if (typeof c[k] === 'function') delete c[k];
      s.g = c;
      s.live = true;
      s.diffAtClone = deepDiff(g, c);
    } catch (e) {
      s.cloneErr = String(e && e.message || e);
    }
    return s;
  };
  const close = (g, s, why) => {
    if (!s.live) return;
    s.live = false;
    s.endT = g.t;
    s.endWhy = why;
    const d = deepDiff(g, s.g);
    s.diffAtEnd = d.filter((k) => !SUB_ONLY.has(k));
    s.subOnlyStale = d.filter((k) => SUB_ONLY.has(k));
    s.g = null;
  };
  const cheap = (g, s) => {
    const c = s.g, n = g.players;
    const A = g.terr, B = g.bal, L = g.alive, a = c.terr, b = c.bal, l = c.alive;
    for (let p = 0; p < n; p++) {
      if (A[p] !== a[p] || B[p] !== b[p] || L[p] !== l[p]) {
        s.firstVis = g.t;
        s.vis = { p, land: [A[p], a[p]], bal: [B[p], b[p]], alive: [L[p], l[p]] };
        let nBad = 0;
        for (let q = 0; q < n; q++) if (A[q] !== a[q] || B[q] !== b[q] || L[q] !== l[q]) nBad++;
        s.vis.nBad = nBad;
        return false;
      }
    }
    if (s.firstHid === null) {
      const h = [];
      if (g.rng.s !== c.rng.s) h.push('随机数状态');
      if (g.scanLen !== c.scanLen) h.push('扫描表条数');
      if (g.boatN !== c.boatN) h.push('全场船数');
      if (g.routes.length !== c.routes.length) h.push('航线表条数');
      if (g.endgameFast !== c.endgameFast) h.push('终局提速');
      if (g.over !== c.over) h.push('对局结束标志');
      if (!sameSeq(g.debt, c.debt)) h.push('欠账');
      if (!sameSeq(g.boatMemo, c.boatMemo)) h.push('猎杀 / 发船目标');
      if (h.length) { s.firstHid = g.t; s.hid = h; }
    }
    return true;
  };
  const X = resim(mid, {
    onStart: (g) => {
      G = g;
      // scanTick 外面包一层只读的壳：原样调用，调用完按 bots.js L696-727 的分支条件判断这一拍有没有走到「要不要重扫」那一步
      // （走到了而没有重扫 = 模拟器的规则认为第二名个人还有地）。
      const scan0 = g.scanTick;
      g.scanTick = function () {
        const pass0 = this.scanPass, seen0 = this.scanSeen;
        scan0.call(this);
        if (scanGap !== null || !this.teamGame || pass0 < 300 || this.scanPass < 300) return;
        const n = this.scanLen, t = this.t;
        if (n >= 512) return;
        const reached = n ? (t % 350 === 1 && seen0 === n && this.isBot(this.rank[0])) : t % 12 === 8;
        if (reached && teamsLeft(this) <= 1) scanGap = { t, scanLen: n, alive: this.aliveCount, second: this.terr[this.rank[1]] };
      };
      let depth = 0;
      for (const name of ENTRY) {
        const f = g[name];
        g[name] = function (...a) {
          depth++;
          let r;
          try { r = f.apply(this, a); } finally { depth--; }
          if (depth === 0) {
            for (const s of live) {
              if (!s.live) continue;
              try { s.g[name](...a); } catch (e) { s.err = `${name}：${String(e && e.message || e)}`; s.errT = g.t; close(g, s, '抛错'); }
            }
          }
          return r;
        };
      }
    },
    onTick: (g) => {
      if (gap === null && g.teamGame) {
        const second = g.aliveCount < 2 ? 0 : g.terr[g.rank[1]];
        if (teamsLeft(g) <= 1 && second > 0) gap = { t: g.t, second, alive: g.aliveCount, scanLen: g.scanLen, scanPass: g.scanPass };
      }
      for (const s of live) if (s.live && !cheap(g, s)) close(g, s, '地或兵不等');
      if (AT.includes(g.t)) {
        for (const s of live) close(g, s, '到下一个断面');
        live = [mk(g, g.t, 'asis'), mk(g, g.t, 'class')];
      }
    },
  });
  for (const s of live) close(G, s, G.over ? '局末' : '录像到头');
  for (const s of segs) delete s.g;
  const ev = (X.engineEvents || []).map((e) => [e[0], e[1]]);
  const roomKey = crypto.createHash('sha1').update([X.H, X.mapIdx, X.mapSeed, ...X.names].join('\u0001')).digest('hex').slice(0, 12);
  const val = X.validate ? { rows: X.validate.rows, both: X.validate.bothExact } : null;
  return { matchId: mid, roomKey, H: X.H, nTeams: X.nTeams, teamGame: !!G.teamGame, endTick: G.t, over: G.over ? 1 : 0, at: AT, events: ev, val, gap, scanGap, segs };
}

fs.mkdirSync(OUT, { recursive: true });
let done = 0;
for (const mid of mids) {
  const fp = path.join(OUT, `${mid}.json`);
  if (fs.existsSync(fp)) continue;
  if (done && (Date.now() - T0) / 1000 > budget) break;
  // 开跑前留一个记号：跑到一半被时间上限杀掉的局，批处理下一轮跳过（汇总里单列），免得卡在同一局上
  const mark = path.join(OUT, `${mid}.started`);
  fs.writeFileSync(mark, String(Date.now()));
  const t1 = Date.now();
  const R = probe(mid);
  R.sec = Math.round((Date.now() - t1) / 100) / 10;
  fs.writeFileSync(fp, JSON.stringify(R));
  fs.unlinkSync(mark);
  done++;
  console.log(`${mid} 真人 ${R.H} 队 ${R.nTeams} 到 ${R.endTick} 拍 ${R.sec}s | ` + R.segs.map((s) => `${s.T}/${s.arm}:${s.cloneErr ? '克隆抛错' : s.firstVis !== null ? `走偏@${s.firstVis}` : s.err ? `抛错@${s.errT}` : `一致到${s.endT}${s.diffAtEnd && s.diffAtEnd.length ? `（字段不等 ${s.diffAtEnd.length}）` : ''}`}`).join(' '));
}
console.log(`CLONEPROBE ${done} 局，用时 ${Math.round((Date.now() - T0) / 1000)}s`);
