#!/usr/bin/env node
// openloop.mjs — 开环可信期（会审稿验收条款 S5）在四个断面上的现状：t=0 / 630 / 1500 / 4284。
//
// 断面反事实里，本编队换一种走法，别人照录像走（开环）。别人那些录像指令是在历史局面下发的，局面一变，它们有的就不再成立——
// 这里量「不成立」得有多快：别的真人的录像陆攻，逐条和历史比，「生效 / 没生效」翻了面的占比，按断面后 270 / 630 / 870 拍分窗。
// 只用两条不带任何规则的臂（都是量尺，不是打法）：
//   wj    本编队还是录像里的指令，断面以后的每条推迟 7~19 拍再执行（执行拍取 7 的倍数）——「把历史指令挪一下」本身翻多少面，当地板
//   idle  断面以后本编队的指令（陆攻 / 捐款 / 船 / 追船或召回 / 撤军）一条都不执行
// 另有一条对照：
//   ctl   拷贝原样照录像走。它必须和参照重演逐条相同、段末全部字段相等——用来验收这个量法自己（几份拷贝并排跑，互相不串）。
// 做法：参照重演（不克隆、照录像一路走）走到断面那一拍，把对局对象 clone() 三份、原型改回重放器的子类
// （cloneprobe 量过：这样的拷贝照录像续跑，326 次全部逐拍相等、段末全部字段相等 [CP-B]），然后参照和三份拷贝并排走 870 拍。
// 和 cfprobe（t=630 一个断面，每条臂从头重演一遍）是同一个量、同一套窗；idle 臂在 t=630 断面上应该和 cfprobe 逐局对得上（openloop.py 里对）。
// 只读 /agent/repos/c136-data（发现集的对局包 + src/sim）；不跑策略，不改 src/sim。
//
// 参照重演有没有被并排的拷贝带偏（拷贝和它共用模拟器的几块临时缓冲区），另有两道检查：
//   · 每 10 拍把全场 512 个玩家的地和兵折进一个校验和（refHash）；加 --plain 不放任何拷贝再跑一遍，两个校验和必须相同；
//   · 参照重演对本包日志快照的逐位核对行数（val）、猎杀 / 终局提速事件表（events）、结束拍，必须和 cloneprobe 那一遍的相同。
//
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/openloop.mjs [--budget 秒] [--plain] <局> [<局> ...]
//   → out/_run/openloop/<局>.json（--plain：<局>.plain.json）；已有的跳过；汇总见 openloop.py
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { resim } from './resim_r08.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'out', '_run', 'openloop');
const argv = process.argv.slice(2);
let budget = 80, plain = false;
const mids = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--budget') budget = +argv[++i];
  else if (argv[i] === '--plain') plain = true;
  else mids.push(argv[i]);
}
const T0 = Date.now();
const SECTIONS = [0, 630, 1500, 4284];
const WIN = [270, 630, 870];        // 断面后的三个窗：(0, 270]、(270, 630]、(630, 870]
const SPAN = WIN[WIN.length - 1];
const ARMS = ['ctl', 'wj', 'idle'];
// 重放器喂给对局对象的入口（resim_r08.mjs execCmd 用到的全部会改状态的方法）+ 推进一拍
const ENTRY = ['attack', 'donate', 'boat', 'recall', 'chase', 'retreat', 'leave', 'tick'];
// 算「本编队的指令」的那几种，和玩家号是第几个参数（leave 不算：离开照录像）
const OWNCMD = { attack: 2, donate: 2, boat: 3, recall: 1, chase: 2, retreat: 1 };
const ceil7 = (t) => 7 * Math.ceil(t / 7);
const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
const mulberry = (a) => () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

function sameSeq(u, v) {
  if (u === v) return true;
  if (!u || !v || u.length !== v.length) return false;
  for (let j = 0; j < u.length; j++) if (u[j] !== v[j]) return false;
  return true;
}

// 两个对局对象的全部自有字段逐个比；返回不等的字段名（和 cloneprobe.mjs 里的是同一个函数）
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
  let G = null, H = 0, own = new Set();
  let refHash = 2166136261, refHashN = 0;
  const census = (g) => {
    let nP = 0, land = 0, ownOn = 0, ownLand = 0;
    for (let p = 0; p < H; p++) {
      const on = g.alive[p] && g.state[p] !== 2 && g.terr[p] > 0;
      if (own.has(p)) { if (on) { ownOn++; ownLand += g.terr[p]; } } else if (on) { nP++; land += g.terr[p]; }
    }
    return { nP, land, ownOn, ownLand };
  };
  const mk = (g, T, arm) => {
    // wj 的抖动：和 cfprobe 的 wj 臂同一个种子、同一种抽法（本编队每条 1~5 号录像指令抽一次），t=630 断面上两边应该逐条相同
    const s = { T, arm, g: null, live: false, cloneErr: null, err: null, errT: null, endT: null, why: null,
      at: census(g),
      n: [0, 0, 0], flip: [0, 0, 0], down: [0, 0, 0], up: [0, 0, 0],   // 别的真人的录像陆攻：条数｜翻面｜历史生效→现在没生效｜历史没生效→现在生效
      ownCmd: 0, ownDrop: 0, ownLate: 0, ownLateSkip: 0,                // 断面后本编队的录像指令：条数｜没执行（idle）｜推迟执行了（wj）｜推迟到点时人已经不在（wj）
      drift: [null, null, null], ctlDiff: null,
      q: [], due: 0, rnd: arm === 'wj' ? mulberry(hash(`${mid}|wj`)) : null };
    segs.push(s);
    try {
      const c = g.clone();
      Object.setPrototypeOf(c, Object.getPrototypeOf(g));
      // 原对象身上挂着的函数（重放器记账用的钩子、本脚本的分发壳）不属于模拟器，拷贝上去掉
      for (const k of Object.keys(c)) if (typeof c[k] === 'function') delete c[k];
      s.g = c;
      s.live = true;
    } catch (e) {
      s.cloneErr = String(e && e.message || e);
    }
    return s;
  };
  // 窗末记一笔漂移：别的真人（参照重演里还在、不是空壳、有地）的地，拷贝和参照差了多少；本编队的地两边各多少
  const noteDrift = (g, s, k) => {
    const c = s.g;
    let land = 0, dLand = 0, nP = 0, nDiff = 0, ownRef = 0, ownArm = 0;
    for (let p = 0; p < H; p++) {
      if (own.has(p)) { ownRef += g.terr[p]; ownArm += c.terr[p]; continue; }
      if (!g.alive[p] || g.state[p] === 2 || g.terr[p] <= 0) continue;
      nP++;
      land += g.terr[p];
      const d = Math.abs(g.terr[p] - c.terr[p]);
      dLand += d;
      if (d) nDiff++;
    }
    s.drift[k] = { nP, nDiff, land, dLand, ownRef, ownArm };
  };
  const close = (g, s, why) => {
    if (!s.live) return;
    s.live = false;
    s.endT = g.t;
    s.why = why;
    if (s.arm === 'ctl') s.ctlDiff = deepDiff(g, s.g);
    s.g = null;
    s.q = null;
    s.rnd = null;
  };
  const X = resim(mid, {
    // 只当「每条录像指令执行前」的通知用（总是返回 true，不改重演）：给 wj 臂抽这条指令的执行拍
    cmdFilter: (c, g) => {
      if (!g.spawnPhase && c.id >= 1 && c.id <= 5 && own.has(c.player)) {
        for (const s of live) if (s.live && s.arm === 'wj') s.due = ceil7(g.t + 7 + Math.floor(13 * s.rnd()));
      }
      return true;
    },
    onStart: (g, ctx) => {
      G = g;
      H = ctx.H;
      own = new Set(ctx.squadIds);
      let depth = 0;
      for (const name of ENTRY) {
        const f = g[name];
        const pi = OWNCMD[name];
        g[name] = function (...a) {
          depth++;
          let r;
          try { r = f.apply(this, a); } finally { depth--; }
          if (depth !== 0) return r;
          for (const s of live) {
            if (!s.live) continue;
            try {
              const c = s.g;
              if (name === 'tick') {
                c.tick();
                if (s.arm === 'wj' && s.q.length) {
                  // 推迟的录像指令到点（执行拍 ≤ 当拍）后直接调引擎接口执行；人已经出局或离开的不执行（和 cfprobe 的 wj 臂同一写法）
                  for (let i = 0; i < s.q.length;) {
                    const [due, nm, args, pl] = s.q[i];
                    if (due > c.t) { i++; continue; }
                    if (c.alive[pl] && c.state[pl] !== 2) { c[nm](...args); s.ownLate++; } else s.ownLateSkip++;
                    s.q.splice(i, 1);
                  }
                }
                continue;
              }
              const player = pi === undefined ? -1 : a[pi];
              if (pi !== undefined && own.has(player)) {
                s.ownCmd++;
                if (s.arm === 'idle') { s.ownDrop++; continue; }
                if (s.arm === 'wj') { s.q.push([s.due, name, a, player]); continue; }
              }
              const rc = c[name](...a);
              if (name === 'attack' && player >= 0 && player < H && !own.has(player)) {
                const off = this.t - s.T;
                const k = off <= WIN[0] ? 0 : off <= WIN[1] ? 1 : 2;
                s.n[k]++;
                if (!!r !== !!rc) { s.flip[k]++; if (r) s.down[k]++; else s.up[k]++; }
              }
            } catch (e) {
              s.err = `${name}：${String(e && e.message || e)}`;
              s.errT = this.t;
              close(this, s, '抛错');
            }
          }
          return r;
        };
      }
      if (SECTIONS.includes(0) && own.size && !plain) live = ARMS.map((arm) => mk(g, 0, arm));
    },
    onTick: (g) => {
      const t = g.t;
      if (t % 10 === 0) {
        const A = g.terr, B = g.bal;
        let h = refHash;
        for (let p = 0; p < 512; p++) { h = Math.imul(h ^ A[p], 16777619); h = Math.imul(h ^ B[p], 16777619); }
        refHash = h >>> 0;
        refHashN++;
      }
      if (!own.size || plain) return;
      for (const s of live) {
        if (!s.live) continue;
        const off = t - s.T;
        for (let k = 0; k < WIN.length; k++) if (off === WIN[k] && s.arm !== 'ctl') noteDrift(g, s, k);
        if (off >= SPAN) close(g, s, '走满');
      }
      if (live.length && live.every((s) => !s.live)) live = [];
      else if (live.some((s) => !s.live)) live = live.filter((s) => s.live);
      if (SECTIONS.includes(t)) live = live.concat(ARMS.map((arm) => mk(g, t, arm)));
    },
  });
  for (const s of live) close(G, s, G.over ? '局末' : '录像到头');
  for (const s of segs) { delete s.g; delete s.q; delete s.rnd; delete s.live; }
  const roomKey = crypto.createHash('sha1').update([X.H, X.mapIdx, X.mapSeed, ...X.names].join('\u0001')).digest('hex').slice(0, 12);
  const val = X.validate ? { rows: X.validate.rows, both: X.validate.bothExact } : null;
  return { matchId: mid, plain: plain ? 1 : 0, roomKey, H: X.H, nTeams: X.nTeams, endTick: G.t, over: G.over ? 1 : 0, own: own.size, ownIds: [...own],
    val, events: X.engineEvents || [], refHash, refHashN, sections: SECTIONS, win: WIN, segs };
}

fs.mkdirSync(OUT, { recursive: true });
let done = 0;
for (const mid of mids) {
  const fp = path.join(OUT, plain ? `${mid}.plain.json` : `${mid}.json`);
  if (fs.existsSync(fp)) continue;
  if (done && (Date.now() - T0) / 1000 > budget) break;
  // 开跑前留一个记号：跑到一半被时间上限杀掉的局，批处理下一轮跳过（汇总里单列）
  const mark = path.join(OUT, plain ? `${mid}.plain.started` : `${mid}.started`);
  fs.writeFileSync(mark, String(Date.now()));
  const t1 = Date.now();
  const R = probe(mid);
  R.sec = Math.round((Date.now() - t1) / 100) / 10;
  R.maxRssMb = Math.round(process.resourceUsage().maxRSS / 1024);
  fs.writeFileSync(fp, JSON.stringify(R));
  fs.unlinkSync(mark);
  done++;
  const cell = (s) => `${s.T}/${s.arm}:${s.cloneErr ? '克隆抛错' : s.err ? `抛错@${s.errT}` : s.arm === 'ctl' ? (s.flip.reduce((x, y) => x + y, 0) || (s.ctlDiff && s.ctlDiff.length) ? '对照不等!' : '对照相等') : s.flip.map((f, k) => `${f}/${s.n[k]}`).join(',')}`;
  console.log(`${mid}${plain ? '（不放拷贝）' : ''} 真人 ${R.H} 本编队 ${R.own} 到 ${R.endTick} 拍 ${R.sec}s 内存峰值 ${R.maxRssMb}MB 校验和 ${R.refHash} | ` + R.segs.map(cell).join(' '));
}
console.log(`OPENLOOP ${done} 局，用时 ${Math.round((Date.now() - T0) / 1000)}s`);
