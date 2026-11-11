#!/usr/bin/env node
// live-rules-check.cjs — 规格书 B 其余规则的「可执行核对」（捐款与配额见 live-donation-check.cjs）。
//
// 做法同 live-donation-check.cjs：按索引从线上客户端文件切出构造函数原文，放进隔离沙箱原样执行；
// 我从代码读出来的规则另写一份（下面的 spec* 函数），同样输入逐项比对。两边不一致 = 我读错了。
// 核对的是「我对代码的转述」，不是服务器行为。界面/统计/消息一律用空桩。
//
//   T  组队分配 dP.ee（颜色票 → 颜色排名 → 战队整块 → 个人按首选/次选 → 兜底）
//   N  船：移动 acU、船对船 acV、航行损耗 acW、靠岸 acN（自己地/队友地/敌地/中立）
//   V  和平投票 cu：发起条件、门槛 aBN、计票 rw、判定 aBI、类型 ce.aBM
//   C  崩溃 cZ.aOV（领土 <= 峰值/4 即出局，峰值缓慢回落）
//
// 用法（先跑 prep.sh）：
//   cd c136-review/agents/R04 && HEAVY_QUEUE=90 timeout 115 bash ../../tools/run-heavy.sh node scripts/live-rules-check.cjs > out/live-rules-check.txt
const fs = require('fs');
const vm = require('vm');
const crypto = require('crypto');
const path = require('path');

const LIVE = process.env.R04_LIVE || '/agent/repos/c136-data/src/engine/live_game_js.js';
const INDEX = process.env.R04_INDEX || path.join(__dirname, '..', 'tmp', 'pretty', 'index.json');
const src = fs.readFileSync(LIVE, 'utf8');
const sha = crypto.createHash('sha256').update(fs.readFileSync(LIVE)).digest('hex');
const index = JSON.parse(fs.readFileSync(INDEX, 'utf8'));

const NEED = ['c1', 'dD', 'dh', 'a5M', 'a5N', 'cd', 'ca', 'qm', 'dP', 'aaJ', 'aaM', 'cu', 'ce', 'cZ'];
const code = NEED.map((c) => {
  const i = index.ctors[c];
  if (!i) throw new Error('索引里没有构造函数 ' + c);
  return src.slice(i.start, i.end);
}).join(';\n');

// ---------- 固定种子随机数 ----------
let seed = 20261111;
function rnd() {
  seed ^= seed << 13; seed >>>= 0;
  seed ^= seed >>> 17;
  seed ^= seed << 5; seed >>>= 0;
  return seed / 4294967296;
}
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));
const g0 = (a, b) => Math.floor((a + 0.5) / b); // c1.g0

// ---------- 沙箱 ----------
const SETUP = `;
    // 万能空桩：读任何属性、调用任何方法都得到它自己；参与算术时当 0
    var U = new Proxy(function () {}, {
      get: function (t, k) { if (k === Symbol.toPrimitive) return function () { return 0; }; return U; },
      apply: function () { return U; },
      construct: function () { return U; },
      set: function () { return true; },
    });
    var document = U, aO = U, bE = U, ac = U, aS = U, i = U, bf = U, aN = U, aY = U, aX = U, bt = U, ag = U, bg = U, aI = U, bF = U, xm = U, a1 = U, bn = U;
    var a1I = U, a1J = U, a1L = U, L = function () { return ''; };
    var FW = 512;
    var aE = { fW: FW, a6e: 15e8, a7X: 1e9, a6n: 5e4, a6d: 150, iT: true, lE: false, a38: 1, hx: false, ku: 0, ke: 0, lC: 2, a0L: 4, a0M: 0, fJ: 0, hi: false,
               data: { iIncomeType: 0, colorsData: [], passableWater: true } };
    var ah = { hb: new Uint32Array(FW), hN: new Uint32Array(FW), nU: new Uint8Array(FW), a6S: new Uint8Array(FW), a6b: new Uint16Array(FW),
               a0i: new Uint32Array(FW), a3h: new Uint8Array(FW), a3o: new Array(FW).fill(''), a1c: new Array(FW).fill(''), h1: [], hG: [] };
    for (var z = 0; z < FW; z++) { ah.h1.push([]); ah.hG.push([]); }
    var TICK = 0;
    var bi = { kr: function () { return TICK; } };
    var b5 = { a6o: function () {}, a6i: function (p, v) { return v; } };
    var ap = { jh: { kW: new Uint16Array(FW) } };
    var bO = new c1();
    var bR = new dD();
    var bv = new dh();
    var bD = { gv: new a5M(), tK: new a5N(), canvas: U, sM: U, sU: U };
    var af = new cd();
    var ao = new ca();
    var bB = { kw: new qm(), hz: U };
    var bj = null;            // dP 实例，T 组里 new
    // 存活名单、排名（引擎里由别的模块维护，这里直接按当前状态重算）
    var am = new cZ();
    var mV = new Uint16Array(FW), kf = new Uint16Array(FW);
    function RERANK() {
      am.a7n();
      var arr = []; for (var a = 0; a < am.lQ; a++) arr.push(am.lV[a]);
      arr.sort(function (x, y) { return ah.hN[y] - ah.hN[x] || x - y; });
      for (var a = 0; a < arr.length; a++) { mV[a] = arr[a]; kf[arr[a]] = a; }
    }
    // 队伍领土合计（引擎的 dQ 每 32 拍重算一次；这里每次现算）
    var bk = {
      tot: function () { var t = new Array(aE.a0L + 1).fill(0); for (var a = 0; a < am.lQ; a++) t[bj.fX[am.lV[a]]] += ah.hN[am.lV[a]]; return t; },
      lT: function () { var t = this.tot(), s = 0; for (var a = aE.a0L; a > 0; a--) if (t[a] > t[s]) s = a; return s; },
      lR: function () {
        var t = this.tot(), s = this.lT();
        if (bj.lH[s]) return t[s];
        var b = -1; for (var a = aE.a0L; a >= 1; a--) if (b === -1 || t[a] > t[b]) b = a;
        var ea = ah.hN[mV[0]];
        if (b === -1) return ea;
        return t[b] > ea ? t[b] : ea;
      },
    };
    var ai = new ce();
    // 终局记录
    var END = [];
    var bU = { a2l: { a33: function () { END.push('draw'); }, a37: function () { END.push('win'); } } };
    // 崩溃记录
    var DT = [];
    var al = { dt: function (p) { DT.push(p); } };
    // 进攻槽（桩）：SLOT[p] = {targets: [...], max}
    var ATK = [];
    var SLOTFREE = new Uint8Array(FW), HASATK = {};
    var ae = {
      kF: function (p, k) { return !!HASATK[p + ':' + k]; },
      kY: function (p) { return SLOTFREE[p] === 1; },
      ei: function (p, v, k) { ATK.push([p, v, k]); },
    };
    var aG = { k1: function () {} };
    // 地图桩：LANDOWNER[格] = 玩家号；512 = 中立
    var LANDOWNER = {};
    var ad = {
      fQ: function (fD) { return LANDOWNER[fD >> 2] === FW; },
      fR: function (fD) { return LANDOWNER[fD >> 2]; },
      h9: function (fD) { return LANDOWNER[fD >> 2] !== undefined && LANDOWNER[fD >> 2] !== FW; },
      a1B: function (p, fD) { return LANDOWNER[fD >> 2] === p; },
      fU: function () { return true; },
    };
    // 船：坐标直接用 1/16 像素的线性下标；所有船放在同一个邻域桶里
    var bV = { fk: 4096, fl: 4096 };
    var REMOVED = [];
    var bP = { jJ: function (x) { return x; }, jK: function (x) { return x; }, jL: function () { return 0; }, ie: [0, 0, 0, 0], ig: [0, 0, 0, 0], fP: function (x) { return x << 2; } };
    var bQ = { jM: { jM: [[]], act: [0, 1e9, 1e9, 1e9, 1e9, 1e9, 1e9, 1e9, 1e9], n5: function () { return 0; }, ack: function () { return 0; } },
               mt: { aak: function (b) { REMOVED.push(b); } }, aLE: { ab3: function () {} }, lj: { aLB: function () { return 0; } } };
    bQ.z = new aaJ();
    bQ.mp = new aaM();
    var ax = new cu();
    // 每个用例之前把可变状态清回初始（比每次新建沙箱快得多）
    function RESET() {
      ah.hb.fill(0); ah.hN.fill(0); ah.nU.fill(0); ah.a6S.fill(0); ah.a6b.fill(0); ah.a0i.fill(0); ah.a3h.fill(0);
      for (var z = 0; z < FW; z++) { ah.h1[z] = []; ah.hG[z] = []; ah.a3o[z] = ''; }
      aE.ku = 0; aE.ke = 0; aE.lC = 2; aE.a0L = 4; aE.a0M = 0; aE.iT = true; aE.lE = false; aE.a38 = 1; aE.fJ = 0;
      TICK = 0;
      bj = new dP();
      ao = new ca(); ao.dk();
      am = new cZ();
      bQ.z = new aaJ(); bQ.mp = new aaM(); bQ.jM.jM = [[]];
      ax = new cu(); ax.dl(); ax.dk();
      END.length = 0; DT.length = 0; ATK.length = 0; REMOVED.length = 0;
      HASATK = {}; SLOTFREE.fill(0); LANDOWNER = {};
    }
    `;
const SCRIPT = new vm.Script(code + SETUP);
function makeSandbox() {
  const ctx = { Math, Uint8Array, Uint16Array, Uint32Array, Int32Array, Array, console, Proxy, Symbol };
  vm.createContext(ctx);
  SCRIPT.runInContext(ctx);
  return ctx;
}

const SHARED = makeSandbox();
console.log(`# live-rules-check  文件 sha256=${sha}  构造函数原文取自索引：${NEED.join(',')}`);
let failAll = 0;

// =====================================================================================
// T. 组队分配
// =====================================================================================
const TC = [[128, 128, 128], [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255], [0, 255, 255], [255, 255, 255], [0, 0, 0]];
function specTag(name) {
  const a = name.indexOf('[');
  if (a < 0) return null;
  const b = name.indexOf(']');
  if (b - a > 1 && b - a <= 8) return name.substring(a + 1, b).toUpperCase().trim();
  return null;
}
// 返回 {teams（分配阶段用的队数）, teamsFinal（aem 之后）, fX[0..ku-1], rankColour}
function specTeams(ku, nominal, colors, names) {
  let T = nominal;
  const first = new Array(ku).fill(0), second = new Array(ku).fill(0), votes = new Array(8).fill(0);
  for (let p = ku - 1; p >= 0; p--) {
    const c = colors[p];
    const rgb = [4 * (c >> 12), 4 * ((c >> 6) & 63), 4 * (c & 63)];
    const d = [];
    for (let k = 0; k < 8; k++) d[k] = Math.abs(rgb[0] - TC[k + 1][0]) + Math.abs(rgb[1] - TC[k + 1][1]) + Math.abs(rgb[2] - TC[k + 1][2]);
    let best = 768;
    for (let ft = 7; ft >= 0; ft--) { const e = (ft + p) % 8; if (d[e] < best) { best = d[e]; first[p] = e; } }
    votes[first[p]] += 4;
    best = 768;
    for (let ft = 7; ft >= 0; ft--) { const e = (ft + p) % 8; if (d[e] < best && e !== first[p]) { best = d[e]; second[p] = e; } }
    votes[second[p]]++;
  }
  // 颜色按票数排名：rank[1..8] = 颜色号 1..8（并列时号小的在前）
  const rank = [0];
  const v = votes.map((x) => x + 1);
  for (let r = 1; r <= 8; r++) {
    let lr = 0;
    for (let ft = 1; ft < 8; ft++) if (v[ft] > v[lr]) lr = ft;
    v[lr] = 0;
    rank[r] = lr + 1;
  }
  // 战队
  const tags = [], members = [];
  let biggest = 0;
  for (let p = 0; p < ku; p++) {
    const t = specTag(names[p]);
    if (t === null) continue;
    let k = -1;
    for (let j = tags.length - 1; j >= 0; j--) if (tags[j] === t) { k = j; break; }
    if (k < 0) { tags.push(t); members.push([p]); biggest = Math.max(biggest, 1); } else { members[k].push(p); biggest = Math.max(biggest, members[k].length); }
  }
  while (T > 2 && biggest > g0(ku, T)) T--;
  const fX = new Array(ku).fill(0);
  const size = new Array(9).fill(0);
  const done = tags.map(() => false);
  for (let it = tags.length - 1; it >= 0; it--) {
    let fc = -1;
    for (let j = tags.length - 1; j >= 0; j--) if (!done[j] && (fc === -1 || members[j].length > members[fc].length)) fc = j;
    const sp = new Array(8).fill(1);
    for (const p of members[fc]) { sp[first[p]] += 3; sp[second[p]]++; }
    for (let attempt = 0; attempt < 8; attempt++) {
      let e = fc % 8;
      for (let j = 7; j >= 0; j--) if (sp[j] > sp[e]) e = j;
      let team = -1;
      for (let j = T; j > 0; j--) if (rank[j] === e + 1) { team = j; break; }
      sp[e] = 0;
      if (team === -1) continue;
      let bigger = 0;
      for (let j = T; j > 0; j--) if (size[team] > size[j]) bigger++;
      if (bigger === T - 1) continue; // 这个队已经比其它所有队都大，换下一个颜色
      for (const p of members[fc]) { size[team]++; fX[p] = team; }
      break;
    }
    done[fc] = true;
  }
  // 个人
  const cap = g0(ku, T) + (ku % T > 0 ? 1 : 0);
  const rankOf = new Array(10).fill(0);
  for (let r = 8; r >= 1; r--) rankOf[rank[r]] = r;
  for (let p = 0; p < ku; p++) { const tv = rankOf[first[p] + 1]; if (fX[p] === 0 && tv <= T && size[tv] < cap) { size[tv]++; fX[p] = tv; } }
  for (let p = 0; p < ku; p++) { const tv = rankOf[second[p] + 1]; if (fX[p] === 0 && tv <= T && size[tv] < cap) { size[tv]++; fX[p] = tv; } }
  for (let t = T; t >= 1; t--) for (let p = ku - 1; p >= 0; p--) { if (size[t] >= cap) break; if (fX[p] === 0) { size[t]++; fX[p] = t; } }
  return { teams: T, teamsFinal: T < 8 ? T + 1 : T, fX, rank, cap };
}
function liveTeams(ctx, ku, nominal, colors, names) {
  ctx.aE.ku = ku; ctx.aE.a0L = nominal; ctx.aE.lC = nominal - 2; ctx.aE.a0M = 0; ctx.aE.iT = true; ctx.aE.lE = false;
  ctx.aE.data.colorsData = colors.slice();
  for (let p = 0; p < 512; p++) ctx.ah.a3o[p] = p < ku ? names[p] : '';
  vm.runInContext('bj = new dP(); bj.dk();', ctx);
  return { teamsFinal: ctx.aE.a0L, fX: Array.from(ctx.bj.fX.slice(0, ku)), botTeams: Array.from(ctx.bj.fX.slice(ku, ku + 8)) };
}
const colorOf = (r, g, b) => ((r >> 2) << 12) + ((g >> 2) << 6) + (b >> 2);
function randomLobby(ku) {
  const colors = [], names = [];
  const tagPool = ['APEX', 'ABC', 'x', 'Longtag', 'TOOLONGTAG', 'A B', ' zz '];
  for (let p = 0; p < ku; p++) {
    colors.push(ri(0, 262143));
    const r = rnd();
    if (r < 0.25) names.push(`[${tagPool[ri(0, tagPool.length - 1)]}] p${p}`);
    else if (r < 0.3) names.push(`p${p} [${tagPool[ri(0, 2)]}]`);
    else if (r < 0.33) names.push(`]p${p}[`);
    else names.push(`p${p}`);
  }
  return { colors, names };
}
{
  const ctx = makeSandbox();
  let n = 0, bad = 0;
  for (let trial = 0; trial < 3000; trial++) {
    const ku = ri(4, 90), nominal = ri(2, 8);
    const { colors, names } = randomLobby(ku);
    const s = specTeams(ku, nominal, colors, names);
    const l = liveTeams(ctx, ku, nominal, colors, names);
    n++;
    if (s.teamsFinal !== l.teamsFinal || s.fX.join(',') !== l.fX.join(',')) {
      bad++;
      if (bad <= 3) console.log(`T MISMATCH trial=${trial} ku=${ku} nominal=${nominal}\n  spec ${s.teamsFinal} ${s.fX.join('')}\n  live ${l.teamsFinal} ${l.fX.join('')}`);
    }
  }
  failAll += bad;
  console.log(`\nT. 组队分配：随机大厅 ${n} 个（真人 4~90、名义队数 2~8、随机颜色、约三成带战队标签），线上原文与我的转述不一致 ${bad} 个 → ${bad === 0 ? 'PASS' : 'FAIL'}`);

  // T1 场景统计：同一个大厅里放进我方 N 个号，看它们被分到几个队
  function scenario(label, kuList, nominalList, squadN, mkSquad, trials) {
    const rows = [];
    for (const nominal of nominalList) for (const ku of kuList) {
      if (ku <= squadN) continue;
      const dist = {};
      let sumBiggest = 0, sumTeams = 0;
      for (let k = 0; k < trials; k++) {
        const colors = [], names = [];
        // 我方号的座位随机散布
        const seats = new Set();
        while (seats.size < squadN) seats.add(ri(0, ku - 1));
        let j = 0;
        for (let p = 0; p < ku; p++) {
          if (seats.has(p)) { const s = mkSquad(j++); colors.push(s.color); names.push(s.name); } else { colors.push(ri(0, 262143)); names.push(`p${p}`); }
        }
        const s = specTeams(ku, nominal, colors, names);
        const cnt = {};
        for (const p of seats) cnt[s.fX[p]] = (cnt[s.fX[p]] || 0) + 1;
        const groups = Object.values(cnt).sort((a, b) => b - a);
        dist[groups.length] = (dist[groups.length] || 0) + 1;
        sumBiggest += groups[0];
        sumTeams += s.teams;
      }
      rows.push(`  名义${nominal}队 真人${ku}：实际队数均值 ${(sumTeams / trials).toFixed(2)}；我方落在几个队 → ${Object.keys(dist).sort((a, b) => a - b).map((k) => `${k}队:${(100 * dist[k] / trials).toFixed(0)}%`).join(' ')}；最大一组平均 ${(sumBiggest / trials).toFixed(1)} 人`);
    }
    console.log(`T1 ${label}（每格 ${trials} 次，其余真人随机颜色、无标签）`);
    console.log(rows.join('\n'));
  }
  scenario('10 个号同一战队标签 [APEX]、颜色各自随机', [25, 40, 60], [3, 5, 8], 10, (j) => ({ color: ri(0, 262143), name: `[APEX] s${j}` }), 400);
  scenario('20 个号无标签、颜色各自随机', [40, 60, 80], [3, 5, 8], 20, (j) => ({ color: ri(0, 262143), name: `s${j}` }), 400);
  scenario('20 个号无标签、全部选同一种颜色（纯红 255,0,0）', [40, 60, 80], [3, 5, 8], 20, (j) => ({ color: colorOf(255, 0, 0), name: `s${j}` }), 400);
  scenario('20 个号同一战队标签、颜色各自随机', [40, 60, 80], [3, 5, 8], 20, (j) => ({ color: ri(0, 262143), name: `[APEX] s${j}` }), 400);
}

// =====================================================================================
// N. 船
// =====================================================================================
{
  // N1 航行损耗 + 船对船 + 移动：随机摆几条船，逐拍比对兵力/位置/减速标记
  let bad = 0, steps = 0, fights = 0;
  for (let trial = 0; trial < 300; trial++) {
    const ctx = SHARED;
    ctx.RESET();
    const z = ctx.bQ.z;
    const n = ri(2, 7);
    const W16 = ctx.bV.fk << 4;
    const spec = [];
    const bucket = [];
    for (let b = 0; b < n; b++) {
      const owner = ri(0, 5);
      ctx.bj.fX[owner] = [0, 1, 1, 2, 2, 0][owner];
      const x0 = 2000 + ri(0, 400), y0 = 2000 + ri(0, 400);
      const x1 = x0 + ri(-3000, 3000), y1 = y0 + ri(-3000, 3000);
      const troops = [60, ri(60, 500), ri(500, 20000), ri(20000, 600000)][ri(0, 3)];
      z.mo[b] = (owner << 3) + 0;
      z.mz[b] = x0 + W16 * y0;
      z.ab0[b] = 0;
      z.a9g[b] = troops;
      z.ml[b] = 4;
      z.abA[b] = 0;
      z.mm[b] = [x0 + W16 * y0, Math.max(0, x1) + W16 * Math.max(0, y1)];
      z.my[b] = 0;
      bucket.push(b);
      spec.push({ owner, x0, y0, x1: Math.max(0, x1), y1: Math.max(0, y1), prog: 0, x: x0, y: y0, troops, slow: 0 });
    }
    z.mk = n;
    ctx.bQ.jM.jM = [bucket];
    const team = (o) => ctx.bj.fX[o];
    let t = ri(0, 50);
    for (let step = 0; step < 40; step++, t++) {
      ctx.TICK = t;
      // --- 线上
      z.ee();
      // --- 转述
      // 移动
      for (let b = n - 1; b >= 0; b--) {
        const s = spec[b];
        if (s.prog === 65535) continue; // 已到终点（线上由 bQ.mp.ee 处理靠岸；本组不测靠岸，见下方跳出）
        const dx = s.x1 - s.x0, dy = s.y1 - s.y0;
        const len = Math.max(~~Math.sqrt(dx * dx + dy * dy + 0.5), 1);
        const speed = s.slow ? 4e4 : 25e4 + Math.min(20 * s.troops, 3e5) + Math.min(s.troops >> 3, 5e4);
        const p = s.prog + Math.max(~~((speed + 0.5) / len), 1);
        if (p >= 65535) { s.prog = 65535; s.x = s.x1; s.y = s.y1; } else { s.prog = p; s.x = s.x0 + g0(p * dx, 65535); s.y = s.y0 + g0(p * dy, 65535); }
      }
      // 船对船（奇数拍）
      if (t % 2 === 1) {
        const h8 = (n - 1) * (g0(t, 2) % 2);
        for (let a = 0; a < n; a++) {
          const me = spec[Math.abs(a - h8)];
          const mine = me.troops;
          for (let o = 0; o < n; o++) {
            const ot = spec[o];
            if (me.owner === ot.owner || (team(me.owner) === team(ot.owner) && team(me.owner))) continue;
            const ddx = me.x - ot.x, ddy = me.y - ot.y;
            if (ddx * ddx + ddy * ddy < 120 * 120) {
              const dmg = ot.troops <= mine ? Math.max(1, g0(ot.troops + g0(mine - ot.troops, 10), 10)) : Math.max(1, g0(mine, 10));
              ot.troops = Math.max(ot.troops - dmg, 0);
              ot.slow = 4;
              fights++;
            }
          }
        }
      }
      // 航行损耗（t%5==3）
      if (t % 5 === 3) for (const s of spec) s.troops = Math.max(s.troops - Math.max(1, s.troops >> 7), 0);
      // 减速标记每拍折半
      for (const s of spec) s.slow >>= 1;
      steps++;
      let same = true;
      for (let b = 0; b < n; b++) {
        const s = spec[b];
        if (z.a9g[b] !== s.troops || z.abA[b] !== s.slow || z.ab0[b] !== s.prog || z.mz[b] !== s.x + W16 * s.y) { same = false; break; }
      }
      if (!same) {
        bad++;
        if (bad <= 3) console.log(`N1 MISMATCH trial=${trial} t=${t} live=${Array.from(z.a9g.slice(0, n))}/${Array.from(z.ab0.slice(0, n))} spec=${spec.map((s) => s.troops)}/${spec.map((s) => s.prog)}`);
        break;
      }
      if (spec.some((s) => s.troops === 0 || s.prog === 65535)) break; // 有船沉了或到了终点就结束这一轮
    }
  }
  failAll += bad;
  console.log(`\nN1. 船的移动/交战/损耗：300 轮、逐拍比对 ${steps} 拍（其中船对船结算 ${fights} 次），不一致 ${bad} 轮 → ${bad === 0 ? 'PASS' : 'FAIL'}`);

  // N2 靠岸
  let n2 = 0, bad2 = 0;
  const kinds = { own: 0, mate: 0, mateQuotaLost: 0, mateNoRoomLost: 0, enemy: 0, neutral: 0, noSlotLost: 0 };
  for (let trial = 0; trial < 4000; trial++) {
    const ctx = SHARED;
    ctx.RESET();
    const z = ctx.bQ.z;
    const ku = 6;
    ctx.aE.ku = ku; ctx.aE.ke = [292727, 546152, 762763][trial % 3];
    const land = [], bal = [], teamArr = [];
    for (let p = 0; p < 8; p++) {
      land[p] = ri(20, 30000); bal[p] = ri(0, 7) === 0 ? land[p] * 150 - ri(0, 1) : Math.floor(land[p] * ri(1, 150) * rnd()); teamArr[p] = [1, 1, 1, 2, 2, 0, 0, 0][p];
      ctx.ah.hN[p] = land[p]; ctx.ah.hb[p] = bal[p]; ctx.bj.fX[p] = teamArr[p]; ctx.ah.nU[p] = 1;
    }
    const player = ri(0, 4);
    const where = ri(0, 7) === 0 ? 512 : ri(0, 7); // 落点归属
    const troops = ri(1, 400000);
    const t = [100, 500, 900, 1500, 2500, 3500, 4300][ri(0, 6)];
    // 预先用掉一些配额，让“配额不够”的情况出现
    ctx.TICK = t;
    for (let tt = 0; tt <= t; tt++) { ctx.TICK = tt; ctx.ao.ee(); }
    ctx.TICK = t;
    let cap = 15;
    for (let tt = 0; tt <= t; tt++) if (tt % 100 === 99) cap += tt < 1071 ? 4 : tt < 2142 ? 6 : tt < 3213 ? 8 : 10;
    const hasSlot = ri(0, 3) !== 0, hasAtk = ri(0, 3) === 0;
    ctx.SLOTFREE[player] = hasSlot ? 1 : 0;
    if (hasAtk) ctx.HASATK[player + ':' + where] = 1;
    ctx.LANDOWNER[777] = where;
    z.mk = 1; z.mo[0] = (player << 3); z.mz[0] = 777; z.ab0[0] = 65535; z.a9g[0] = troops; z.ml[0] = 0; z.mm[0] = [0, 777]; z.my[0] = 0;
    ctx.bQ.mp.ee();
    // --- 转述
    const exp = { bal: bal.slice(), atk: null };
    const room = (q, v) => Math.max(Math.min(v, land[q] * 150 - bal[q], 15e8 - bal[q]), 0);
    let kind;
    if (where === 512) {
      if (hasAtk || hasSlot) { exp.atk = [player, troops, 512]; kind = 'neutral'; } else kind = 'noSlotLost';
    } else if (where === player) {
      exp.bal[player] += room(player, troops); kind = 'own';
    } else if (teamArr[player] !== 0 && teamArr[player] === teamArr[where]) {
      const v = room(where, troops);
      if (v < 1) kind = 'mateNoRoomLost';
      else {
        const free = t >= 4284 || where >= ku;
        let cost;
        if (t >= 3213) cost = 4 + g0(100 * v, Math.min(100 * land[where], 1e9));
        else { const uv = 1 + g0(ctx.aE.ke, 300); cost = 2 + g0(100 * v, (t < 357 ? 1 : t < 714 ? 4 : t < 1071 ? 10 : t < 2142 ? 30 : 100) * uv); }
        if (!free && cost > cap) kind = 'mateQuotaLost';
        else { exp.bal[where] += v; kind = 'mate'; }
      }
    } else {
      if (hasAtk || hasSlot) { exp.atk = [player, troops, where]; kind = 'enemy'; } else kind = 'noSlotLost';
    }
    kinds[kind]++;
    n2++;
    let same = true;
    for (let p = 0; p < 8; p++) if (ctx.ah.hb[p] !== exp.bal[p]) same = false;
    const la = ctx.ATK.length ? ctx.ATK[0].join(',') : 'none';
    if (la !== (exp.atk ? exp.atk.join(',') : 'none')) same = false;
    if (!same) {
      bad2++;
      if (bad2 <= 3) console.log(`N2 MISMATCH trial=${trial} kind=${kind} player=${player} where=${where} troops=${troops} t=${t} liveAtk=${la} bal=${Array.from(ctx.ah.hb.slice(0, 8))} exp=${exp.bal}`);
    }
  }
  failAll += bad2;
  console.log(`N2. 船靠岸：${n2} 例（${Object.entries(kinds).map(([k, v]) => `${k}=${v}`).join(' ')}），不一致 ${bad2} 例 → ${bad2 === 0 ? 'PASS' : 'FAIL'}`);
  console.log('    own=落在自己地上（兵回到余额，受 150 倍领土上限）；mate=落在队友地上（整船兵记到队友余额，不收税，但要过防喂养配额）；');
  console.log('    mateQuotaLost=队友配额不够，整船兵消失；mateNoRoomLost=队友余额已到上限，整船兵消失；enemy/neutral=开始或并入一次进攻；noSlotLost=没有空闲进攻槽且没有对该目标的现有进攻，整船兵消失');

  // N3 表：船速、损耗
  console.log('\nN3. 船速（像素/拍）= (25e4 + min(20*兵,3e5) + min(兵>>3,5e4)) / 65535 / 16；被敌船打到后 3 拍内固定 4e4（约 0.038 像素/拍）');
  console.log('兵\t速度(像素/拍)\t走 100 像素要多少拍\t这段路上的损耗（每 5 拍减 max(1, 兵>>7)）');
  for (const troops of [60, 1000, 5000, 15000, 50000, 100000, 400000]) {
    const sp = (25e4 + Math.min(20 * troops, 3e5) + Math.min(troops >> 3, 5e4)) / 65535 / 16;
    // 逐拍模拟：兵力下降会让船变慢
    let x = 0, tr = troops, tk = 0;
    while (x < 100 && tr > 0 && tk < 5000) {
      x += (25e4 + Math.min(20 * tr, 3e5) + Math.min(tr >> 3, 5e4)) / 65535 / 16;
      if (tk % 5 === 3) tr = Math.max(tr - Math.max(1, tr >> 7), 0);
      tk++;
    }
    console.log(`${troops}\t${sp.toFixed(3)}\t${tk}\t${troops - tr}（${(100 * (troops - tr) / troops).toFixed(1)}%）`);
  }
  console.log('N4. 船对船（每逢奇数拍，距离 < 7.5 像素，双方不同队）：对方兵 <= 我方时，对方损失 max(1, floor((对方 + floor((我方-对方)/10))/10))；对方兵 > 我方时，对方损失 max(1, floor(我方/10))');
  console.log('我方\t对方\t对方一次损失\t我方一次损失');
  for (const [a, b] of [[10000, 10000], [10000, 1000], [10000, 100], [100000, 10000], [1000, 10000], [60, 10000]]) {
    const dmg = (mine, other) => (other <= mine ? Math.max(1, g0(other + g0(mine - other, 10), 10)) : Math.max(1, g0(mine, 10)));
    console.log(`${a}\t${b}\t${dmg(a, b)}\t${dmg(b, a)}`);
  }
}

// =====================================================================================
// V. 和平投票
// =====================================================================================
function specVoteThreshold(isDraw, teamGame, leadShareLand /* 领先队领土 */, ke, humanLand) {
  let yes;
  if (isDraw) yes = Math.max(g0(3 * humanLand, 4), 1);
  else if (teamGame) {
    let g1 = g0(100 * leadShareLand, ke);
    g1 = g0(Math.min(Math.max(1600 - 12 * g1, 400), 1000), 10);
    yes = Math.max(g0(g1 * humanLand, 100), 1);
  } else yes = Math.max(g0(3 * humanLand, 5), 1);
  return { yes, no: Math.max(humanLand - yes, 1) };
}
{
  let n = 0, bad = 0;
  const outcomes = {};
  for (let trial = 0; trial < 3000; trial++) {
    const ctx = SHARED;
    ctx.RESET();
    const ku = ri(6, 14), nBots = ri(0, 6), N = ku + nBots;
    const teams = ri(2, 4);
    ctx.aE.ku = ku; ctx.aE.a0L = teams; ctx.aE.lC = teams - 2; ctx.aE.iT = true;
    const ke = 500000;
    ctx.aE.ke = ke;
    const land = [], bal = [], team = [], left = [];
    let remaining = ke;
    for (let p = 0; p < N; p++) {
      const l = p === N - 1 ? Math.max(1, Math.floor(remaining * rnd())) : Math.max(1, Math.floor(remaining * rnd() * (rnd() < 0.3 ? 0.9 : 0.3)));
      remaining -= l;
      land[p] = l; bal[p] = Math.floor(l * ri(1, 120) * rnd());
      team[p] = p < ku ? ri(1, teams) : 0; left[p] = p < ku && ri(0, 9) === 0 ? 2 : 0;
      ctx.ah.hN[p] = l; ctx.ah.hb[p] = bal[p]; ctx.bj.fX[p] = team[p]; ctx.ah.nU[p] = 1; ctx.ah.a6S[p] = left[p];
    }
    ctx.RERANK();
    const isHuman = (p) => p < ku && left[p] !== 2;
    // 转述：投票类型
    const order = [...Array(N).keys()].sort((a, b) => land[b] - land[a] || a - b);
    const teamLand = new Array(teams + 1).fill(0), teamBal = new Array(teams + 1).fill(0);
    for (let p = 0; p < N; p++) { teamLand[team[p]] += land[p]; teamBal[team[p]] += bal[p]; }
    let lead = 0;
    for (let a = teams; a > 0; a--) if (teamLand[a] > teamLand[lead]) lead = a;
    const totalBal = bal.reduce((a, b) => a + b, 0);
    let isDraw;
    if (N < 3) isDraw = false;
    else if (land[order[0]] >= ke >> 1) isDraw = false;
    else isDraw = !(2 * teamBal[lead] >= totalBal);
    // 领先队领土（bk.lR）：领先队是 0 号（内置 AI 那一“队”）时，取“最大的真人队”和“头名个人”里大的
    let leadLand;
    if (lead !== 0) leadLand = teamLand[lead];
    else { let b = -1; for (let a = teams; a >= 1; a--) if (b === -1 || teamLand[a] > teamLand[b]) b = a; leadLand = Math.max(teamLand[b], land[order[0]]); }
    const humanLand = [...Array(N).keys()].filter(isHuman).reduce((a, p) => a + land[p], 0);
    const th = specVoteThreshold(isDraw, true, leadLand, ke, humanLand);
    // 发起：t=2000，由某个真人发起（必须排名前 10，或是排名里前 10 个真人之一）
    const caller = ri(0, ku - 1);
    ctx.TICK = 2000;
    const rankOfCaller = order.indexOf(caller);
    let humansBefore = 0, okRank = rankOfCaller < 10;
    if (!okRank) {
      // a6p(player, 9)：沿排名数真人，轮到自己之前真人数不超过 9 个
      let cnt = 0; okRank = false;
      for (const p of order) { if (isHuman(p)) { if (p === caller) { okRank = true; break; } if (++cnt > 9) break; } }
    }
    const specCan = isHuman(caller) && okRank;
    const liveCan = ctx.ax.iO(caller);
    n++;
    if (specCan !== liveCan) { bad++; if (bad <= 3) console.log(`V MISMATCH(iO) trial=${trial} caller=${caller} spec=${specCan} live=${liveCan}`); continue; }
    if (!liveCan) { outcomes.cannotCall = (outcomes.cannotCall || 0) + 1; continue; }
    ctx.ax.iK(caller);
    ctx.ax.ee(); // 这一拍开票
    if (!ctx.ax.iL) { bad++; continue; }
    // 随机投票时刻与内容，逐拍推进。三种节奏：很快投完 / 分散在整个 360 拍里 / 大半人不投
    const pace = ri(0, 2);
    const voteAt = {};
    for (const p of [...Array(N).keys()].filter(isHuman)) {
      if (pace === 2 && rnd() < 0.7) continue;
      const when = pace === 0 ? ri(0, 20) : ri(0, 380);
      (voteAt[when] = voteAt[when] || []).push(p);
    }
    const yesBias = rnd();
    let yes = 0, no = 0, left360 = 360, specOutcome = null, pendingFail = 0;
    for (let step = 0; step < 400 && specOutcome === null; step++) {
      ctx.TICK++;
      // 指令先于本拍结算
      for (const p of voteAt[step] || []) {
        const v = rnd() < yesBias;
        const can = ctx.ax.iM(p);
        if (!can) continue;
        ctx.ax.rw(p, v ? 1 : 0);
        if (pendingFail === 0) { if (v) yes += Math.max(land[p], 1); else no += Math.max(land[p], 1); }
      }
      ctx.ax.ee();
      // 转述：判定
      if (pendingFail > 0) { pendingFail--; if (pendingFail === 0) specOutcome = 'fail-no'; }
      else {
        left360--;
        if (left360 === 180 && 3 * yes < th.yes) specOutcome = 'fail-half';
        else if (yes >= th.yes) specOutcome = isDraw ? 'draw' : 'win';
        else if (no >= th.no) pendingFail = 4;
        else if (left360 <= 0) specOutcome = 'fail-timeout';
      }
      const liveEnded = ctx.END.length > 0 ? ctx.END[0] : !ctx.ax.iL && pendingFail === 0 ? 'fail' : null;
      const specNorm = specOutcome === null ? null : specOutcome.startsWith('fail') ? 'fail' : specOutcome;
      if (liveEnded !== specNorm && !(pendingFail > 0)) {
        bad++;
        if (bad <= 3) console.log(`V MISMATCH trial=${trial} step=${step} live=${liveEnded} spec=${specOutcome} yes=${yes}/${th.yes} no=${no}/${th.no} draw=${isDraw}`);
        specOutcome = 'mismatch';
      }
    }
    outcomes[specOutcome] = (outcomes[specOutcome] || 0) + 1;
  }
  failAll += bad;
  console.log(`\nV. 和平投票：${n} 个随机局面（发起资格 + 类型 + 门槛 + 逐拍计票判定），不一致 ${bad} 个 → ${bad === 0 ? 'PASS' : 'FAIL'}`);
  console.log('   结果分布：' + Object.entries(outcomes).map(([k, v]) => `${k}=${v}`).join(' '));
  console.log('\nV1. 团队局“胜负型”投票的赞成门槛（占“在场真人领土合计”的百分比）= clamp(1600 - 12*领先队领土%, 400, 1000) / 10');
  console.log('领先队领土%\t赞成门槛%（按领土加权）');
  const row = [];
  for (const sh of [30, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 96, 100]) row.push(`${sh}\t${g0(Math.min(Math.max(1600 - 12 * sh, 400), 1000), 10)}`);
  console.log(row.join('\n'));
  console.log('“平局型”投票（领先队兵力不到全场一半、头名个人领土不到一半、在场不少于 3 人）：赞成门槛固定 75%。');
}

// =====================================================================================
// C. 崩溃
// =====================================================================================
{
  let n = 0, bad = 0, deaths = 0;
  for (let trial = 0; trial < 400; trial++) {
    const ctx = SHARED;
    ctx.RESET();
    const N = 6;
    const land = [], peak = [];
    for (let p = 0; p < N; p++) { land[p] = ri(50, 40000); peak[p] = 0; ctx.ah.hN[p] = land[p]; ctx.ah.nU[p] = 1; }
    ctx.am.a7n();
    for (let step = 0; step < 300; step++) {
      for (let p = 0; p < N; p++) {
        const r = rnd();
        if (r < 0.5) land[p] = Math.max(0, Math.floor(land[p] * (1 - rnd() * 0.08)));
        else if (r < 0.8) land[p] = Math.floor(land[p] * (1 + rnd() * 0.05)) + ri(0, 3);
        ctx.ah.hN[p] = land[p];
      }
      ctx.DT.length = 0;
      ctx.am.n9();
      const specDead = [];
      for (let p = N - 1; p >= 0; p--) {
        const ea = land[p], lp = peak[p];
        if (ea <= g0(lp, 4)) specDead.push(p);
        else if (ea >= lp) peak[p] = ea;
        else peak[p] = lp - Math.max(1, g0(lp - ea, 1000));
      }
      n++;
      let same = specDead.join(',') === Array.from(ctx.DT).join(',');
      for (let p = 0; p < N; p++) if (ctx.ah.a0i[p] !== peak[p]) same = false;
      if (!same) { bad++; if (bad <= 3) console.log(`C MISMATCH trial=${trial} step=${step} live=${Array.from(ctx.DT)} spec=${specDead}`); break; }
      deaths += specDead.length;
      if (specDead.length) break;
    }
  }
  failAll += bad;
  console.log(`\nC. 崩溃判定：${n} 拍比对（触发出局 ${deaths} 次），不一致 ${bad} → ${bad === 0 ? 'PASS' : 'FAIL'}`);
  console.log('C1. 峰值回落速度：每拍减 max(1, floor((峰值-领土)/1000))。例：峰值 20000、领土瞬间掉到 6000 后保持不变，多少拍之后“领土 <= 峰值/4”不再可能触发');
  for (const [pk, cur] of [[20000, 6000], [20000, 5100], [8000, 2100], [3000, 800]]) {
    let p = pk, k = 0;
    while (cur <= g0(p, 4) === false && p > cur && k < 100000) { p -= Math.max(1, g0(p - cur, 1000)); k++; }
    console.log(`  峰值 ${pk} 领土 ${cur}：出局线 = floor(峰值/4) = ${g0(pk, 4)}；峰值回落到与领土相等需要 ${k} 拍`);
  }
}

console.log(`\n# 总结：不一致合计 ${failAll} → ${failAll === 0 ? 'ALL PASS' : 'HAS FAIL'}`);
