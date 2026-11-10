#!/usr/bin/env node
// live-donation-check.cjs — 捐款规则的「可执行核对」。
//
// 做两件事：
//  A. 从当前线上客户端文件里按索引切出与捐款有关的构造函数原文（qj=指令入口、a5M=规则助手、cd=入账、ca=防喂养配额、
//     qm=内置 AI 捐款/船靠岸转给队友、dh=是否同队、c1=整数除法、dD=暂存区），放进一个隔离的沙箱里原样执行；
//     另外用我从代码里读出来、自己重写的一份公式（下面的 spec* 函数）算同样的输入，逐项比对。
//     两边不一致就说明我读错了。这一步核对的是「我对代码的转述」，不是服务器行为。
//  B. 用核对过的公式打印几张表（手续费比例、配额上限随时间、不同阶段一次捐款耗多少配额点）。
//
// 用法（先跑 prep.sh）：
//   HEAVY_QUEUE=90 timeout 115 bash c136-review/tools/run-heavy.sh node c136-review/agents/R04/scripts/live-donation-check.cjs \
//     > c136-review/agents/R04/out/live-donation-check.txt
// 不依赖 acorn/prettier；只读 /agent/repos/c136-data/src/engine/live_game_js.js 和 ../tmp/pretty/index.json（prep.sh 生成）。
const fs = require('fs');
const vm = require('vm');
const crypto = require('crypto');

const path = require('path');
const LIVE = process.env.R04_LIVE || '/agent/repos/c136-data/src/engine/live_game_js.js';
const INDEX = process.env.R04_INDEX || path.join(__dirname, '..', 'tmp', 'pretty', 'index.json');
const src = fs.readFileSync(LIVE, 'utf8');
const sha = crypto.createHash('sha256').update(fs.readFileSync(LIVE)).digest('hex');
const index = JSON.parse(fs.readFileSync(INDEX, 'utf8'));

const NEED = ['qj', 'a5M', 'cd', 'ca', 'qm', 'dh', 'c1', 'dD'];
const code = NEED.map((c) => {
  const i = index.ctors[c];
  if (!i) throw new Error('索引里没有构造函数 ' + c);
  return src.slice(i.start, i.end);
}).join(';\n');

// ---------- 沙箱：只放规则需要的状态，其余（界面、统计、消息）一律空函数 ----------
function makeSandbox() {
  const ctx = { Math, Uint8Array, Uint16Array, Uint32Array, Int32Array, Array, console };
  vm.createContext(ctx);
  vm.runInContext(
    code +
      `;
    var FW = 512;
    var aE = { fW: FW, a6e: 15e8, a7X: 1e9, a6n: 5e4, a6d: 150, iT: true, lE: false, a38: 1, hx: false, ku: 0, ke: 0, lC: 2, fJ: 0, data: { iIncomeType: 0 } };
    var ah = { hb: new Uint32Array(FW), hN: new Uint32Array(FW), nU: new Uint8Array(FW), a6S: new Uint8Array(FW), a6b: new Uint16Array(FW) };
    var bj = { fX: new Uint8Array(FW) };
    var TICK = 0;
    var bi = { kr: function () { return TICK; } };
    var REC = [];
    var bC = { rg: { rh: function (id, a, b, c) { REC.push([id, a, b, c]); } } };
    var nop = function () {};
    var bt = { rG: nop };
    var bg = { rH: nop, gz: nop };
    var ag = { aMk: nop, rI: nop };
    var b5 = { a6o: nop, a6i: function (p, v) { return v; } };
    var ap = { jh: { kW: new Uint16Array(FW) } };
    var aS = { i3: function () { return 0; } };
    var bO = new c1();
    var bR = new dD();
    var bv = new dh();
    var bD = { gv: new a5M() };
    var af = new cd();
    var ao = new ca();
    var bB = { qi: new qj(), kw: new qm() };
    `,
    ctx,
  );
  return ctx;
}

// ---------- 我从代码读出来的规则（独立重写） ----------
const g0 = (a, b) => Math.floor((a + 0.5) / b); // c1.g0
function specNew(n, ku, ke) {
  return { n, ku, ke, bal: new Float64Array(n), land: new Float64Array(n), alive: new Uint8Array(n), left: new Uint8Array(n), team: new Uint8Array(n), debt: new Float64Array(n), used: new Float64Array(n), cap: 15, single: false, running: true };
}
function specRoom(s, q, v) {
  v = Math.min(v, s.land[q] * 150 - s.bal[q]);
  v = Math.min(v, 15e8 - s.bal[q]);
  return Math.max(v, 0);
}
function specCost(s, t, q, v) {
  if (t >= 3213) return 4 + g0(100 * v, Math.min(100 * s.land[q], 1e9));
  const uv = 1 + g0(s.ke, 300);
  if (t < 357) return 2 + g0(100 * v, uv);
  if (t < 714) return 2 + g0(100 * v, 4 * uv);
  if (t < 1071) return 2 + g0(100 * v, 10 * uv);
  if (t < 2142) return 2 + g0(100 * v, 30 * uv);
  return 2 + g0(100 * v, 100 * uv);
}
const specIsBotLike = (s, p) => p >= s.ku || s.left[p] === 2;
const specQuotaFree = (s, t, q) => s.single || t >= 4284 || specIsBotLike(s, q);
function specCapTick(s, t) {
  if (t % 100 !== 99) return;
  s.cap += t < 1071 ? 4 : t < 2142 ? 6 : t < 3213 ? 8 : 10;
}
function specCredit(s, q, v) {
  v = specRoom(s, q, v);
  s.bal[q] += v;
  if (s.debt[q]) {
    const m = Math.min(s.debt[q], s.bal[q]);
    s.debt[q] -= m;
    s.bal[q] -= m;
  }
  return v;
}
// 玩家捐款指令（指令号 2）。返回 null=被拒；否则 {amount, fee}
function specDonate(s, t, p, pct, q) {
  if (!s.running) return null;
  if (!(s.alive[p] !== 0 && s.left[p] !== 2)) return null;
  if (p === q) return null;
  if (s.alive[q] === 0) return null;
  if (s.team[p] === 0 || s.team[p] !== s.team[q]) return null;
  const B = s.bal[p];
  const fee = g0(64 * B, 1024);
  let v = g0(B * (pct + 1), 1024);
  v = Math.min(v, B - fee);
  v = specRoom(s, q, v);
  if (v < 1) return null;
  if (!specQuotaFree(s, t, q)) {
    const c = specCost(s, t, q, v);
    if (s.used[q] + c > s.cap) return null;
    s.used[q] += c;
  }
  specCredit(s, q, v);
  s.bal[p] -= v + fee;
  return { amount: v, fee };
}

// ---------- A. 随机比对 ----------
let seed = 20261110;
function rnd() {
  // xorshift32，固定种子，结果可重算
  seed ^= seed << 13; seed >>>= 0;
  seed ^= seed >>> 17;
  seed ^= seed << 5; seed >>>= 0;
  return seed / 4294967296;
}
const ri = (a, b) => a + Math.floor(rnd() * (b - a + 1));

function runTrial(trial) {
  const ctx = makeSandbox();
  const n = 12;
  const ku = ri(4, 10);
  const ke = [546152, 664497, 292727, 762763, 430654, 423950][trial % 6];
  const s = specNew(n, ku, ke);
  ctx.aE.ku = ku;
  ctx.aE.ke = ke;
  ctx.ao.dk();
  for (let p = 0; p < n; p++) {
    const land = ri(0, 3) === 0 ? ri(1, 60) : ri(50, 60000);
    const bal = ri(0, 5) === 0 ? ri(0, 200) : Math.floor(land * (rnd() < 0.2 ? ri(100, 160) : ri(1, 90)) * rnd());
    const team = ri(0, 6) === 0 ? 0 : ri(1, 3);
    const alive = ri(0, 12) === 0 ? 0 : 1;
    const left = ri(0, 12) === 0 ? 2 : 0;
    const debt = ri(0, 9) === 0 ? ri(1, 50000) : 0;
    s.land[p] = land; s.bal[p] = bal; s.team[p] = team; s.alive[p] = alive; s.left[p] = left; s.debt[p] = debt;
    ctx.ah.hN[p] = land; ctx.ah.hb[p] = bal; ctx.bj.fX[p] = team; ctx.ah.nU[p] = alive; ctx.ah.a6S[p] = left; ctx.ah.a6b[p] = debt;
  }
  const stat = { cmds: 0, accepted: 0, mismatch: 0, rejQuota: 0 };
  let t = ri(0, 300);
  const tEnd = t + ri(500, 5000);
  for (; t < tEnd; t++) {
    // 指令在本 tick 的 n8() 之前执行（多人对局循环 af2：先 bB.qk.ee 再 n8），配额上限在 n8() 里的 ao.ee() 增长
    const k = rnd() < 0.3 ? ri(1, 3) : 0;
    for (let j = 0; j < k; j++) {
      const p = ri(0, n - 1), q = ri(0, n - 1), pct = [0, 51, 102, 255, 511, 767, 1023][ri(0, 6)];
      ctx.TICK = t;
      const before = ctx.REC.length;
      ctx.bB.qi.qv(p, pct, q);
      const liveOk = ctx.REC.length > before;
      const usedBefore = s.used[q];
      const r = specDonate(s, t, p, pct, q);
      stat.cmds++;
      if (r) stat.accepted++;
      if (!r && usedBefore === s.used[q]) {
        // 统计一下「只因为配额被拒」的次数（其余条件都满足）
        const B = s.bal[p];
        const fee = g0(64 * B, 1024);
        const v = specRoom(s, q, Math.min(g0(B * (pct + 1), 1024), B - fee));
        if (s.alive[p] && s.left[p] !== 2 && p !== q && s.alive[q] && s.team[p] && s.team[p] === s.team[q] && v >= 1) stat.rejQuota++;
      }
      let same = liveOk === !!r;
      for (let x = 0; x < n && same; x++) if (ctx.ah.hb[x] !== s.bal[x] || ctx.ah.a6b[x] !== s.debt[x]) same = false;
      if (!same) {
        stat.mismatch++;
        if (stat.mismatch <= 3) console.log(`MISMATCH trial=${trial} t=${t} p=${p} q=${q} pct=${pct} live=${liveOk} spec=${JSON.stringify(r)}`);
        for (let x = 0; x < n; x++) { s.bal[x] = ctx.ah.hb[x]; s.debt[x] = ctx.ah.a6b[x]; }
      }
    }
    ctx.TICK = t;
    ctx.ao.ee();
    specCapTick(s, t);
    // 余额随机涨一点，模拟收入（两边同步加）
    if (t % 10 === 9) for (let x = 0; x < n; x++) { const inc = ri(0, 400); s.bal[x] += inc; ctx.ah.hb[x] += inc; }
  }
  return stat;
}

console.log(`# live-donation-check  文件 sha256=${sha}  构造函数原文取自索引：${NEED.join(',')}`);
const total = { cmds: 0, accepted: 0, mismatch: 0, rejQuota: 0 };
const TRIALS = 60;
for (let i = 0; i < TRIALS; i++) {
  const st = runTrial(i);
  for (const k of Object.keys(total)) total[k] += st[k];
}
console.log(`A. 随机比对：${TRIALS} 轮，捐款指令 ${total.cmds} 条，其中通过 ${total.accepted} 条，仅因配额被拒 ${total.rejQuota} 条；线上原文与我的公式结果不一致 ${total.mismatch} 条`);
console.log(total.mismatch === 0 ? 'A. 结论：一致（PASS）' : 'A. 结论：不一致（FAIL）');

// ---------- B. 表 ----------
console.log('\nB1. 手续费与到账（发起方余额 B，滑杆值 pct，对方有足够空间时）：到账 = floor((B*(pct+1)+0.5)/1024)，手续费 = floor((64*B+0.5)/1024)，与 pct 无关');
console.log('pct\t到账占B\t手续费占B\t手续费/到账\t发起方共减少占B');
for (const pct of [0, 9, 51, 102, 255, 511, 767, 959, 1023]) {
  const B = 1024000;
  const fee = g0(64 * B, 1024);
  const v = Math.min(g0(B * (pct + 1), 1024), B - fee);
  console.log(`${pct}\t${(100 * v / B).toFixed(2)}%\t${(100 * fee / B).toFixed(2)}%\t${(fee / v).toFixed(3)}\t${(100 * (v + fee) / B).toFixed(2)}%`);
}
console.log('（pct 最大 1023：想捐 100%，实际到账封顶 B - 手续费 = 93.75% B）');

console.log('\nB2. 配额上限（全场共用一个数，开局 15；每逢 tick%100==99 增加：t<1071 加 4，<2142 加 6，<3213 加 8，其后加 10）');
{
  const s = { cap: 15 };
  const rows = [];
  for (let t = 0; t <= 4300; t++) {
    specCapTick(s, t);
    if ([0, 98, 99, 199, 299, 356, 399, 499, 599, 699, 713, 799, 899, 999, 1070, 1099, 1499, 1999, 2099, 2141, 2199, 2599, 2999, 3199, 3212, 3299, 3599, 3999, 4199, 4283].includes(t)) rows.push(`t=${t}: ${s.cap}`);
  }
  console.log(rows.join('  |  '));
  console.log('t>=4284 之后不再检查配额（任何人都不限）。单机对局、收款方是内置 AI 或已离开的真人时也不检查。');
}

console.log('\nB3. 一次捐款消耗的配额点 = 底数 + floor((100*到账+0.5)/分母)。到账量 v 需要的点数（按已公布对局的地图陆地格数 ke）');
console.log('分母：t<357 → uv；<714 → 4uv；<1071 → 10uv；<2142 → 30uv；<3213 → 100uv（uv = 1 + floor((ke+0.5)/300)，底数 2）；t>=3213 → min(100*收款方领土, 1e9)，底数 4');
for (const ke of [292727, 423950, 430654, 546152, 664497, 762763]) {
  const uv = 1 + g0(ke, 300);
  const s = { cap: 15 };
  const marks = { 356: 1, 713: 4, 1070: 10, 2141: 30, 3212: 100 };
  const out = [];
  for (let t = 0; t <= 3212; t++) {
    specCapTick(s, t);
    if (marks[t]) {
      // 该阶段结束时，一个此前从未收过款的玩家，单笔最多能收多少：2 + floor((100v+0.5)/(m*uv)) <= cap
      const d = marks[t] * uv;
      const vmax = Math.floor(((s.cap - 2 + 1) * d - 0.5) / 100);
      // 回代确认
      const ok = 2 + g0(100 * vmax, d) <= s.cap && 2 + g0(100 * (vmax + 1), d) > s.cap;
      out.push(`t=${t}（上限 ${s.cap}，分母 ${d}）单笔最多 ${vmax}${ok ? '' : ' ?!'}`);
    }
  }
  console.log(`ke=${ke} uv=${uv}: ` + out.join('；'));
}
console.log('t>=3213：消耗 = 4 + floor((100*v+0.5)/min(100*领土,1e9))，即每收到「1 倍自己领土格数」的兵约耗 1 点，另加每笔 4 点。');
{
  const s = { cap: 15 };
  const out = [];
  for (let t = 0; t <= 4283; t++) {
    specCapTick(s, t);
    if ([3299, 3599, 3999, 4199].includes(t)) out.push(`t=${t} 上限 ${s.cap}`);
  }
  console.log('     ' + out.join('；') + '。例：t=3600 时上限 249，一个从未收过款的玩家单笔最多收 (249-4+1) 倍领土 -1 左右的兵；但同时受「余额不超过 150 倍领土」限制，所以此阶段真正卡人的是 150 倍领土上限和累计点数。');
}
