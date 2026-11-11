#!/usr/bin/env node
// eng_replay.cjs — 用线上引擎原文按录像重放一局，导出逐局复盘要用的全场真值。
//
// 引擎宿主用统筹入库的 R04 工具（/agent/repos/c136-data/src/tools/engine_host.cjs：把 live_game_js.js 原样装进 Node，
// 规则一行不改）。本脚本只做「读数」和「记账」：
//   · 在引擎源码上补 4 个只读口子（步进、每圈陆攻前后、利率表、受捐配额计数）；
//   · 把指令入口（bB.qi.*）、经济结算（af.ee）、配额检查（ao.ei）、友军船移交（bB.kw.rE）、统计入口（bg.gz）各包一层，
//     调用前后各读一次状态，差值记进账本，原函数照常执行。
// 输出 out/<id>/sim_state.json，字段与 sim_replay.mjs 相同（simdigest.py / r06lib.py 通用），另加：
//   quota（每个真人的已用受捐点数、全场额度）、quotaLog（每次配额检查）、boatGifts（船靠友军岸的移交）。
//
// 用法（先跑 sim_prep.py <id> 生成 out/<id>/sim_in.json）：
//   bash c136-review/tools/run-heavy.sh node c136-review/agents/R06/scripts/eng_replay.cjs <id> [--to T] [--every N] [--trace p:t0:t1]
//   带 --to 或 --trace 的运行写 out/<id>/sim_state.partial.json，不动整局的 sim_state.json
const fs = require('fs');
const path = require('path');
const { createHost } = require('/agent/repos/c136-data/src/tools/engine_host.cjs');
const { patchSource } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');

const OUT = path.join(__dirname, '..', 'out');
const args = process.argv.slice(2);
const mid = args[0];
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
if (!mid) { console.log('用法：node eng_replay.cjs <id> [--to T] [--every N] [--trace p:t0:t1]'); process.exit(2); }
const inp = JSON.parse(fs.readFileSync(path.join(OUT, mid, 'sim_in.json'), 'utf8'));

function once(src, a, b) {
  if (src.split(a).length !== 2) throw new Error('补口子的锚点不唯一或找不到（引擎版本变了？）：' + a.slice(0, 70));
  return src.replace(a, () => b);
}
function patchAll(src) {
  src = patchSource(src);
  src = once(src, '{gP=aC;gh()}', '{gP=aC;__R06.pre();gh();__R06.post()}');
  src = once(src, 'function cd(){this.aD7=0;var aMg;', 'function cd(){this.aD7=0;var aMg;this.__tab=function(){return aMg};');
  src = once(src, 'function ca(){var aOX=new Uint16Array(aE.fW);var aOY=0;', 'function ca(){var aOX=new Uint16Array(aE.fW);var aOY=0;this.__q=function(){return [aOX,aOY]};this.__chk=function(a,b){return aOZ(a,b)};this.__cost=function(a,b){return aOc(a,b)};');
  src = once(src, 'function acN(player,iI,acL,aae){var k3;', 'function acN(player,iI,acL,aae){__R06.land(player,iI,acL,aae);var k3;');
  src = once(src, 'function acJ(aC,aae,iQ){', 'function acJ(aC,aae,iQ){__R06.slot=aC;');
  return 'var __R06={pre:function(){},post:function(){},land:function(){},slot:-1};' + src;
}

// 这个函数的源码会在引擎作用域里求值：里面的 ah / ae / ad / aE / bi / bj / bB / af / ao / am / bg / bQ 都是引擎自己的对象。
/* eslint-disable no-undef */
function collector(cfg) {
  var H = aE.ku, NP = aE.fW, land = aE.ke;
  var need = [['ae.gg', ae.gg], ['ae.gl', ae.gl], ['ae.gm', ae.gm], ['ae.hc', ae.hc], ['ae.aLB', ae.aLB], ['ae.aL6', ae.aL6], ['ad.fQ', ad.fQ], ['ad.h9', ad.h9], ['ad.fR', ad.fR],
    ['bB.qi.i6', bB.qi.i6], ['bB.qi.qv', bB.qi.qv], ['bB.qi.iB', bB.qi.iB], ['bB.qi.iE', bB.qi.iE], ['bB.qi.r2', bB.qi.r2], ['bB.qi.rf', bB.qi.rf], ['bB.qi.rA', bB.qi.rA],
    ['bB.kw.rE', bB.kw.rE], ['ad.fU', ad.fU], ['bQ.aLE.ab3', bQ.aLE.ab3], ['bv.fS', bv.fS], ['ae.kY', ae.kY], ['ae.kF', ae.kF], ['af.ee', af.ee], ['af.__tab', af.__tab], ['ao.ei', ao.ei], ['ao.__q', ao.__q], ['bg.gz', bg.gz], ['bQ.lj.aLB', bQ.lj.aLB]];
  for (var z = 0; z < need.length; z++) if (typeof need[z][1] !== 'function') throw new Error('引擎里找不到 ' + need[z][0]);
  var squad = cfg.squad.slice();
  var isSquad = new Uint8Array(NP + 2);
  for (var i0 = 0; i0 < squad.length; i0++) isSquad[squad[i0]] = 1;
  var LW = 100, EVERY = cfg.every, NE = 90, TO = cfg.to;
  var TR = cfg.trace;
  var traceOut = [];

  // ---- 账本
  var ledger = new Map();
  function add(me, kind, other, v) {
    if (!v) return;
    var k = Math.floor(bi.kr() / LW) + '|' + me + '|' + kind + '|' + other;
    ledger.set(k, (ledger.get(k) || 0) + v);
  }

  // ---- 每圈陆攻前后
  var cur = { on: false, p: -1, tg: -1, tr0: 0, b0: 0, t0: 0, vb0: 0, vc0: 0, vt0: 0, fresh: 0 };
  __R06.pre = function () {
    var tg = ae.gl(gQ, gP);
    var rg = TR && (TR[0] === gQ || TR[0] === tg) && bi.kr() >= TR[1] && bi.kr() <= TR[2];
    cur.on = !!(isSquad[gQ] || (tg < NP && isSquad[tg]) || rg);
    if (!cur.on) return;
    cur.rg = rg;
    cur.p = gQ; cur.tg = tg; cur.tr0 = ae.gm(gQ, gP); cur.b0 = ah.hb[gQ]; cur.t0 = ah.hN[gQ]; cur.fresh = ae.gn(gQ, gP);
    cur.vb0 = tg < NP ? ah.hb[tg] : 0; cur.vc0 = tg < NP ? ae.hc(tg, gQ) : 0; cur.vt0 = tg < NP ? ah.hN[tg] : 0;
  };
  __R06.post = function () {
    if (!cur.on) return;
    cur.on = false;
    var p = cur.p, tg = cur.tg;
    var has = ae.kF(p, tg);
    var tr1 = has ? ae.hc(p, tg) : 0;
    var spent = cur.tr0 + cur.b0 - (tr1 + ah.hb[p]);
    var gained = ah.hN[p] - cur.t0;
    if (isSquad[p]) { add(p, 'spent', tg, spent); add(p, 'gain', tg, gained); }
    if (tg < NP && isSquad[tg]) { add(tg, 'lost', p, gained); add(tg, 'dmg', p, cur.vb0 - ah.hb[tg] + (cur.vc0 - ae.hc(tg, p))); }
    if (cur.rg) traceOut.push('RING t=' + bi.kr() + ' ' + p + '→' + tg + ' fresh=' + cur.fresh + ' 兵 ' + cur.tr0 + '→' + tr1 + (has ? '' : '(结束)') + ' 余额 ' + cur.b0 + '→' + ah.hb[p] + ' 得 ' + gained + ' 格（领土 ' + ah.hN[p] + '）｜对方 领土 ' + cur.vt0 + ' 兵 ' + cur.vb0 + '→' + (tg < NP ? ah.hb[tg] : 0) + ' 反击兵 ' + cur.vc0 + '→' + (tg < NP ? ae.hc(tg, p) : 0));
  };

  // ---- 引擎自己的统计入口：12 = 白白损失（回兵撞硬顶、船靠自己岸溢出、友军船被拒、欠债罚金），15 = 船在海上损失
  var o_gz = bg.gz;
  bg.gz = function (player, amt, kind) {
    if (isSquad[player] && amt > 0) {
      if (kind === 12) add(player, cur.on && cur.p === player ? 'capRet' : 'waste', -1, amt);
      else if (kind === 15) add(player, 'seaLoss', -1, amt);
    }
    return o_gz.call(this, player, amt, kind);
  };

  // ---- 指令入口
  var Q = bB.qi;
  var squadCmds = [], donations = [], leaveT = {}, boatGifts = [], quotaLog = [], boatLands = [];
  function cellOwner(c) { var a = c << 2; if (!ad.fU(a)) return -1; if (ad.fQ(a)) return NP; return ad.fR(a); }
  // 发船那一拍，这条船按引擎的靠岸规则（acJ/acN/acO/acP）会登上谁的地：dir<4 = 指定方向的邻格；4 = 先无主地、再别人的地；5 = 先自己的地
  function ownerOf(cell, dir, player) {
    var o = cellOwner(cell), k;
    if (o !== -1) return o;
    if (dir < 4) return cellOwner(cell + bP.ie[dir]);
    var os = [];
    for (k = 0; k < 4; k++) os.push(cellOwner(cell + bP.ie[k]));
    if (dir === 4) {
      for (k = 0; k < 4; k++) if (os[k] === NP) return NP;
      for (k = 0; k < 4; k++) if (os[k] >= 0 && os[k] < NP && os[k] !== player) return os[k];
      for (k = 0; k < 4; k++) if (os[k] >= 0 && os[k] < NP) return os[k];
      return -1;
    }
    for (k = 0; k < 4; k++) if (os[k] === player) return player;
    for (k = 0; k < 4; k++) if (os[k] >= 0 && os[k] < NP) return os[k];
    for (k = 0; k < 4; k++) if (os[k] === NP) return NP;
    return -1;
  }
  // 船靠岸：登陆格当时的主人决定这船兵打谁（无主地 / 敌人 / 自己 / 友军移交）
  __R06.land = function (player, iI, acL, aae) {
    var o = ad.fQ(acL) ? NP : ad.fR(acL);
    if (!isSquad[player] && !(o < NP && isSquad[o])) return;
    var hasSlot = (o === NP || o < NP) ? (ae.kF(player, o) || ae.kY(player)) : true;
    boatLands.push({ t: bi.kr(), p: player, bid: __R06.slot >= 0 ? bQ.z.mn[__R06.slot] : -1, troops: iI, to: o, toTerr: o < NP ? ah.hN[o] : 0, toBal: o < NP ? ah.hb[o] : 0, toLeft: o < NP && ah.a6S[o] === 2 ? 1 : 0,
      friend: o < NP && o !== player && !bv.fS(player, o) ? 1 : 0, self: o === player ? 1 : 0, noSlot: hasSlot ? 0 : 1, myTerr: ah.hN[player], myBal: ah.hb[player] });
  };
  var noEffect = 0;
  function slotMap(p) {
    var m = {};
    for (var k = ae.gg(p) - 1; k >= 0; k--) m[ae.gl(p, k)] = ae.gm(p, k);
    return m;
  }
  var o_i6 = Q.i6;
  Q.i6 = function (player, jC, k3) {
    var tgt = k3 > NP ? NP : k3;
    if (!isSquad[player] && !(tgt < NP && isSquad[tgt])) {
      var b = ah.hb[player];
      o_i6.call(this, player, jC, k3);
      if (ah.hb[player] === b) noEffect++;
      return;
    }
    var B0 = ah.hb[player], before = slotMap(player);
    var toTerr = tgt < NP ? ah.hN[tgt] : 0, toBal = tgt < NP ? ah.hb[tgt] : 0, myTerr = ah.hN[player];
    o_i6.call(this, player, jC, k3);
    var after = slotMap(player), sent = 0, to = tgt;
    for (var key in after) {
      var d = after[key] - (before[key] || 0);
      if (d > 0 || !(key in before)) { sent += d; to = +key; }
    }
    var cost = B0 - ah.hb[player];
    var ok = cost > 0 ? 1 : 0;
    if (!ok) noEffect++;
    squadCmds.push({ t: bi.kr(), k: 'atk', p: player, to: to, raw: tgt, pct: jC, ok: ok, B0: B0, sent: sent, fee: cost - sent, toTerr: toTerr, toBal: toBal, myTerr: myTerr });
    if (isSquad[player] && ok) { add(player, 'atkOut', to, sent); add(player, 'fee', -1, cost - sent); }
  };
  var o_qv = Q.qv;
  Q.qv = function (player, jC, qu) {
    var B0 = ah.hb[player], R0 = ah.hb[qu], toTerr = ah.hN[qu], fromTerr = ah.hN[player], toLeft = ah.a6S[qu] === 2 ? 1 : 0;
    var onRecv = [];
    if (isSquad[player] || isSquad[qu]) {
      var at = ae.aL6(qu);
      for (var k = 0; k < at.length; k++) onRecv.push([at[k], ae.hc(at[k], qu)]);
      onRecv.sort(function (x, y) { return y[1] - x[1]; });
    }
    var q0 = ao.__q();
    var used0 = q0[0][qu], lim0 = q0[1];
    o_qv.call(this, player, jC, qu);
    var delivered = ah.hb[qu] - R0, cost = B0 - ah.hb[player];
    var ok = cost > 0 ? 1 : 0;
    if (!ok) noEffect++;
    donations.push({ t: bi.kr(), from: player, to: qu, pct: jC, ok: ok, B0: B0, fee: cost - delivered, delivered: delivered, toLeft: toLeft, toTerr: toTerr, toBal: R0, fromTerr: fromTerr,
      onRecv: onRecv.slice(0, 4), qUsed0: used0, qUsed1: ao.__q()[0][qu], qLim: lim0 });
    if (ok) {
      if (isSquad[player]) { add(player, 'donOut', qu, delivered); add(player, 'donFee', qu, cost - delivered); }
      if (isSquad[qu]) add(qu, 'donIn', player, delivered);
    }
  };
  var o_iB = Q.iB;
  Q.iB = function (player, jC, qx) {
    if (!isSquad[player]) { var b = ah.hb[player]; o_iB.call(this, player, jC, qx); if (ah.hb[player] === b) noEffect++; return; }
    var B0 = ah.hb[player], S0 = bQ.lj.aLB(player), myTerr = ah.hN[player], tgt0 = ownerOf(qx >> 3, qx & 7, player);
    o_iB.call(this, player, jC, qx);
    var sent = bQ.lj.aLB(player) - S0, cost = B0 - ah.hb[player];
    var ok = cost > 0 ? 1 : 0;
    if (!ok) noEffect++;
    var bid = -1;
    if (ok && bQ.z.mk > 0 && (bQ.z.mo[bQ.z.mk - 1] >> 3) === player) bid = bQ.z.mn[bQ.z.mk - 1];
    squadCmds.push({ t: bi.kr(), k: 'boat', p: player, bid: bid, pct: jC, cell: qx >> 3, dir: qx & 7, tgt: tgt0, tgtTerr: tgt0 >= 0 && tgt0 < NP ? ah.hN[tgt0] : 0, tgtBal: tgt0 >= 0 && tgt0 < NP ? ah.hb[tgt0] : 0,
      ok: ok, B0: B0, sent: sent, fee: cost - sent, myTerr: myTerr });
    if (ok) { add(player, 'boatOut', -1, sent); add(player, 'fee', -1, cost - sent); }
  };
  var o_iE = Q.iE;
  Q.iE = function (player, jC, ns) {
    if (!isSquad[player]) return o_iE.call(this, player, jC, ns);
    var B0 = ah.hb[player], S0 = bQ.lj.aLB(player);
    o_iE.call(this, player, jC, ns);
    var dS = bQ.lj.aLB(player) - S0, cost = B0 - ah.hb[player];
    squadCmds.push({ t: bi.kr(), k: jC === 849 ? 'boatRecall' : 'boatAdd', p: player, pct: jC, ok: (cost !== 0 || dS !== 0) ? 1 : 0, B0: B0, sent: dS, fee: cost - dS, myTerr: ah.hN[player] });
    if (cost > 0) { add(player, 'boatOut', -1, dS); add(player, 'fee', -1, cost - dS); }
  };
  var o_r2 = Q.r2;
  Q.r2 = function (player, k3) {
    if (!isSquad[player]) return o_r2.call(this, player, k3);
    var B0 = ah.hb[player], A0 = ae.aLB(player);
    o_r2.call(this, player, k3);
    var back = ah.hb[player] - B0;
    squadCmds.push({ t: bi.kr(), k: 'retreat', p: player, to: k3, ok: (A0 !== ae.aLB(player)) ? 1 : 0, B0: B0, sent: -back, fee: (A0 - ae.aLB(player)) - back, myTerr: ah.hN[player] });
    if (back > 0) add(player, 'retreatBack', -1, back);
  };
  function wrapLeave(name) {
    var o = Q[name];
    Q[name] = function (player) {
      var alive = ah.nU[player] !== 0, st = ah.a6S[player], terr = ah.hN[player], bal = ah.hb[player];
      o.call(this, player);
      if (!leaveT[player] && alive && st !== 2 && ah.a6S[player] === 2) leaveT[player] = { t: bi.kr(), terr: terr, bal: bal, spawn: aE.hx ? 1 : 0 };
    };
  }
  wrapLeave('rf');
  wrapLeave('rA');

  // ---- 船从海上消失（靠岸后移除 / 兵掉到 0 沉没 / 主人阵亡）：记下消失时船上还剩多少兵
  var boatEnds = [];
  var o_ab3 = bQ.aLE.ab3;
  bQ.aLE.ab3 = function (slot) {
    var owner = bQ.z.mo[slot] >> 3;
    if (isSquad[owner]) boatEnds.push({ t: bi.kr(), p: owner, bid: bQ.z.mn[slot], troops: bQ.z.a9g[slot], mode: bQ.z.ml[slot] });
    return o_ab3.call(this, slot);
  };

  // ---- 受捐配额检查、友军船移交
  var o_ei = ao.ei;
  ao.ei = function (recv, amt) {
    var q = ao.__q();
    var used0 = q[0][recv], lim = q[1];
    var r = o_ei.call(this, recv, amt);
    if (recv < H) quotaLog.push([bi.kr(), recv, amt, r ? 1 : 0, used0, ao.__q()[0][recv], lim]);
    return r;
  };
  var o_rE = bB.kw.rE;
  bB.kw.rE = function (player, qu, iI) {
    var R0 = ah.hb[qu];
    o_rE.call(this, player, qu, iI);
    var d = ah.hb[qu] - R0;
    if (isSquad[player] || isSquad[qu]) {
      boatGifts.push({ t: bi.kr(), from: player, to: qu, troops: iI, delivered: d, toTerr: ah.hN[qu], toBal: R0, toLeft: ah.a6S[qu] === 2 ? 1 : 0 });
      if (isSquad[player]) { add(player, 'boatGiftOut', qu, d); add(player, 'boatGiftLost', qu, iI - d); }
      if (isSquad[qu]) add(qu, 'boatGiftIn', player, d);
    }
  };

  // ---- 经济结算
  var tab = af.__tab();
  var o_ee = af.ee;
  af.ee = function () {
    var t = bi.kr();
    if (t % 10 !== 9) return o_ee.call(this);
    var pre = [];
    for (var i = 0; i < squad.length; i++) {
      var p = squad[i];
      if (ah.nU[p] === 0) continue;
      var b = ah.hb[p];
      var eH = tab[Math.floor((NP - 1) * ah.hN[p] / land)];
      if (t < 1920) eH = Math.max(Math.floor(100 * (13440 - 6 * t) / 1920), eH);
      eH = Math.min(Math.max(eH, 0), 700);
      var pot = Math.max(Math.floor(eH * b / 1e4), 1);
      if (t % 100 === 99) pot += ah.hN[p];
      pre.push([p, b, pot, ah.a6S[p]]);
    }
    o_ee.call(this);
    for (var j = 0; j < pre.length; j++) {
      var e = pre[j];
      var got = ah.hb[e[0]] - e[1];
      add(e[0], 'inc', -1, got);
      if (e[2] > got) add(e[0], e[3] === 2 ? 'huskLoss' : 'capLoss', -1, e[2] - got);
    }
  };

  // ---- 采样
  var fX = bj.fX;
  var nT = 0;
  var ticks = [], teamLand = [], teamBal = [], teamHumans = [], teamHusk = [], quotaY = [];
  var hum = [], quotaX = {};
  for (var h0 = 0; h0 < H; h0++) { hum.push({ terr: [], bal: [] }); quotaX[h0] = []; }
  // 名字撞进编队名字池的内置 AI（策略按名字认编队号，这些 AI 会被当成编队号）：单独留一条领土/兵力序列
  var poolSet = {}, poolAi = {};
  for (var pz = 0; pz < (cfg.pool || []).length; pz++) poolSet[cfg.pool[pz]] = 1;
  for (var pa = H; pa < NP; pa++) {
    var nm0 = String(ah.a3o[pa] == null ? '' : ah.a3o[pa]).trim();
    if (nm0 && poolSet[nm0.toLowerCase()] === 1) poolAi[pa] = { name: nm0, terr: [], bal: [] };
  }
  function sample(t) {
    ticks.push(t);
    for (var pk in poolAi) { var al0 = ah.nU[pk] !== 0; poolAi[pk].terr.push(al0 ? ah.hN[pk] : 0); poolAi[pk].bal.push(al0 ? ah.hb[pk] : 0); }
    var tl = [], tb = [], th = [], tk = [];
    for (var k = 0; k <= nT; k++) { tl.push(0); tb.push(0); th.push(0); tk.push(0); }
    var lV = am.lV;
    for (var i = am.lQ - 1; i >= 0; i--) {
      var p = lV[i], tm = fX[p];
      tl[tm] += ah.hN[p];
      tb[tm] += ah.hb[p];
      if (p < H) { if (ah.a6S[p] === 2) tk[tm] += ah.hN[p]; else th[tm]++; }
    }
    teamLand.push(tl); teamBal.push(tb); teamHumans.push(th); teamHusk.push(tk);
    var q = ao.__q();
    quotaY.push(q[1]);
    for (var p2 = 0; p2 < H; p2++) {
      var al = ah.nU[p2] !== 0;
      hum[p2].terr.push(al ? ah.hN[p2] : 0);
      hum[p2].bal.push(al ? ah.hb[p2] : 0);
      quotaX[p2].push(q[0][p2]);
    }
  }
  var lastAtk = [];
  for (var h1 = 0; h1 < H; h1++) lastAtk.push(new Map());
  function trackAttackers(t) {
    var lV = am.lV;
    for (var i = am.lQ - 1; i >= 0; i--) {
      var a = lV[i];
      for (var k = ae.gg(a) - 1; k >= 0; k--) {
        var tg = ae.gl(a, k);
        if (tg < H) {
          var m = lastAtk[tg], e = m.get(a), tr = ae.gm(a, k);
          if (e) { e.t = t; e.n++; e.sum += tr; } else m.set(a, { t0: t, t: t, n: 1, sum: tr });
        }
      }
    }
  }
  var neigh = [];
  var cntBuf = new Int32Array(NP + 1);
  function sampleNeigh(t) {
    var fb = ad.fb;
    for (var s = 0; s < squad.length; s++) {
      var p = squad[s];
      if (ah.nU[p] === 0) continue;
      var B = ah.hF[p], touched = [], neut = 0, cells = 0;
      for (var i = 0; i < B.length; i++) {
        var b = B[i];
        if (!(ad.h9(b) && ad.fR(b) === p)) continue;
        cells++;
        for (var q = 0; q < 4; q++) {
          var c = b + fb[q];
          if (ad.fQ(c)) neut++;
          else if (ad.h9(c)) {
            var o = ad.fR(c);
            if (o !== p) { if (cntBuf[o] === 0) touched.push(o); cntBuf[o]++; }
          }
        }
      }
      var nb = [];
      for (var k = 0; k < touched.length; k++) { var o2 = touched[k]; nb.push([o2, cntBuf[o2], ah.hN[o2], ah.hb[o2], fX[o2], o2 < H ? (ah.a6S[o2] === 2 ? 2 : 1) : 0]); cntBuf[o2] = 0; }
      nb.sort(function (x, y) { return y[1] - x[1]; });
      var mine = [];
      for (var k2 = 0; k2 < ae.gg(p); k2++) mine.push([ae.gl(p, k2), ae.gm(p, k2)]);
      var at = ae.aL6(p), on = [];
      for (var k3 = 0; k3 < at.length; k3++) on.push([at[k3], ae.hc(at[k3], p), fX[at[k3]]]);
      neigh.push({ t: t, p: p, terr: ah.hN[p], bal: ah.hb[p], st: ah.a6S[p], border: cells, coast: ah.hG[p] ? ah.hG[p].length : 0, neut: neut, nb: nb.slice(0, 8), mine: mine, on: on,
        boats: bQ.z.ky[p], boatTroops: bQ.lj.aLB(p), nbAll: nb.length, q: ao.__q()[0][p] });
    }
  }

  // ---- 日志快照对指纹
  var checksAt = new Map();
  for (var c0 = 0; c0 < cfg.checks.length; c0++) {
    var cc = cfg.checks[c0];
    if (!checksAt.has(cc.t)) checksAt.set(cc.t, []);
    checksAt.get(cc.t).push(cc);
  }
  var checkRows = [], lineId = {}, lineAmb = {};
  function doChecks(t) {
    var cs = checksAt.get(t);
    if (!cs) return;
    for (var i = 0; i < cs.length; i++) {
      var c = cs[i], hits = [], near = -1, nearD = Infinity;
      for (var s = 0; s < squad.length; s++) {
        var p = squad[s];
        if (ah.nU[p] === 0) continue;
        if (ah.hN[p] === c.terr && ah.hb[p] === c.bal) hits.push(p);
        var dd = Math.abs(ah.hN[p] - c.terr) / Math.max(1, c.terr) + Math.abs(ah.hb[p] - c.bal) / Math.max(1, c.bal);
        if (dd < nearD) { nearD = dd; near = p; }
      }
      var hit = -1;
      if (hits.length === 1) { hit = hits[0]; lineId[c.line] = hit; } else if (hits.length > 1) { hit = hits[0]; lineAmb[c.line] = hits; }
      checkRows.push({ line: c.line, name: c.name, t: c.t, terr: c.terr, bal: c.bal, p: hit, near: near, nearTerr: near >= 0 ? ah.hN[near] : 0, nearBal: near >= 0 ? ah.hb[near] : 0, nearD: near >= 0 ? +nearD.toFixed(4) : -1 });
    }
  }

  // ---- 日志里每条捐款在它的日志拍及之后三个服务器回合，用引擎自己的校验函数逐项判一遍（只读，不执行）
  var probesAt = new Map(), probeOut = {};
  for (var pr0 = 0; pr0 < cfg.probes.length; pr0++) {
    var pb = cfg.probes[pr0];
    for (var dk = 0; dk <= 28; dk += 7) {
      if (!probesAt.has(pb.t + dk)) probesAt.set(pb.t + dk, []);
      probesAt.get(pb.t + dk).push(pb);
    }
  }
  function doProbes(t) {
    var ps = probesAt.get(t);
    if (!ps) return;
    for (var i = 0; i < ps.length; i++) {
      var pb = ps[i], to = pb.to, from = pb.me;
      var r = { t: t, recvAlive: ah.nU[to] !== 0 ? 1 : 0, recvLeft: ah.a6S[to] === 2 ? 1 : 0, toTerr: ah.hN[to], toBal: ah.hb[to] };
      if (from !== null && from !== undefined) {
        r.donorOk = bD.gv.hl(from) ? 1 : 0;
        r.sameTeam = (fX[from] !== 0 && fX[from] === fX[to]) ? 1 : 0;
        r.donorBal = ah.hb[from];
      }
      var B = (from !== null && from !== undefined) ? ah.hb[from] : pb.myBal;
      var amt = Math.floor(B * (pb.pct + 1) / 1024);
      amt = Math.min(amt, B - Math.floor(64 * B / 1024));
      r.want = amt;
      var room = Math.max(0, Math.min(ah.hN[to] * aE.a6d - ah.hb[to], aE.a6e - ah.hb[to]));
      r.room = room;
      amt = Math.max(0, Math.min(amt, room));
      r.amount = amt;
      var q = ao.__q();
      r.used = q[0][to]; r.lim = q[1];
      r.cost = amt >= 1 ? ao.__cost(to, amt) : 0;
      r.quotaOk = amt >= 1 ? (ao.__chk(to, amt) ? 1 : 0) : 0;
      r.exempt = (t >= 4284 || bD.gv.kH(to)) ? 1 : 0;
      if (!probeOut[pb.line]) probeOut[pb.line] = [];
      probeOut[pb.line].push(r);
    }
  }

  // ---- 主循环
  var deathT = [], deaths = [], spawnBox = {};
  for (var h2 = 0; h2 < H; h2++) deathT.push(-1);
  var st = bi.a3I, steps = 0, lastT = -1, spawnDone = false, firstT = -1;
  var balTick = {}, terrTick = {};
  for (var s9 = 0; s9 < squad.length; s9++) { balTick[squad[s9]] = []; terrTick[squad[s9]] = []; }
  function onTick(t) {
    for (var s8 = 0; s8 < squad.length; s8++) {
      var q8 = squad[s8], i8 = t - firstT;
      balTick[q8][i8] = ah.nU[q8] !== 0 ? ah.hb[q8] : -1;
      terrTick[q8][i8] = ah.nU[q8] !== 0 ? ah.hN[q8] : 0;
    }
    for (var p = 0; p < H; p++) {
      if (deathT[p] < 0 && ah.nU[p] === 0) {
        deathT[p] = t;
        var at = [];
        lastAtk[p].forEach(function (e, a) {
          if (e.t >= t - 200) at.push({ a: a, team: fX[a], isHuman: a < H ? 1 : 0, left: ah.a6S[a] === 2 ? 1 : 0, from: e.t0, last: e.t, avgTroops: Math.round(e.sum / e.n) });
        });
        at.sort(function (x, y) { return y.avgTroops * (y.last - y.from + 5) - x.avgTroops * (x.last - x.from + 5); });
        deaths.push({ p: p, t: t, attackers: at.slice(0, 5) });
      } else if (!leaveT[p] && ah.a6S[p] === 2 && ah.nU[p] !== 0) {
        leaveT[p] = { t: t, terr: ah.hN[p], bal: ah.hb[p], polled: 1 };
      }
    }
    doChecks(t);
    doProbes(t);
    if (t % NE === 0) sampleNeigh(t);
    if (t % EVERY === 0 && t !== firstT) sample(t);
    if (t % 5 === 0) trackAttackers(t);
    if (TR && t >= TR[1] && t <= TR[2]) {
      var q = TR[0], mine = [], on = [], al = ae.aL6(q);
      for (var k = 0; k < ae.gg(q); k++) mine.push(ae.gl(q, k) + ':' + ae.gm(q, k));
      for (var k2 = 0; k2 < al.length; k2++) on.push(al[k2] + ':' + ae.hc(al[k2], q));
      traceOut.push('TR t=' + t + ' terr=' + ah.hN[q] + ' bal=' + ah.hb[q] + ' myAtk=[' + mine.join(',') + '] onMe=[' + on.join(',') + '] boats=' + bQ.z.ky[q] + ' boatTroops=' + bQ.lj.aLB(q));
    }
  }
  while (true) {
    if (aE.a38 === 2) break;
    st.__step();
    steps++;
    if (steps > 400000) break;
    if (aE.hx) continue;
    var t = bi.kr();
    if (!spawnDone) {
      spawnDone = true;
      firstT = t;
      for (var p3 = 0; p3 < NP; p3++) if (fX[p3] > nT) nT = fX[p3];
      for (var s3 = 0; s3 < squad.length; s3++) { var q3 = squad[s3]; spawnBox[q3] = [ah.jS[q3], ah.jU[q3], ah.jT[q3], ah.jV[q3], ah.hN[q3]]; }
      sample(t);
    }
    if (t === lastT) continue;
    lastT = t;
    onTick(t);
    if (t >= TO) break;
  }
  if (ticks[ticks.length - 1] !== lastT) sample(lastT);

  var led = [];
  ledger.forEach(function (v, k) {
    var a = k.split('|');
    led.push([+a[0] * LW, +a[1], a[2], +a[3], v]);
  });
  var finalBots = {};
  for (var s4 = 0; s4 < squad.length; s4++) { var q4 = squad[s4]; finalBots[q4] = { alive: ah.nU[q4] !== 0 ? 1 : 0, st: ah.a6S[q4], terr: ah.hN[q4], bal: ah.hb[q4], team: fX[q4] }; }
  var teams = [];
  for (var p5 = 0; p5 < NP; p5++) teams.push(fX[p5]);
  var names = [];
  for (var p6 = 0; p6 < H; p6++) names.push(ah.a3o[p6]);
  var allNames = [];
  for (var p7 = 0; p7 < NP; p7++) allNames.push(ah.a3o[p7] == null ? '' : String(ah.a3o[p7]));
  var exact = 0, bad = [];
  for (var r0 = 0; r0 < checkRows.length; r0++) { if (checkRows[r0].p >= 0) exact++; else bad.push(checkRows[r0]); }
  bad.sort(function (x, y) { return x.t - y.t; });
  return {
    W: bV.fk, Hmap: bV.fl, land: land, humans: H, nTeams: nT, endT: lastT, over: aE.a38 === 2 ? 1 : 0, firstT: firstT, steps: steps,
    rejectedCmds: noEffect,
    check: { points: checkRows.length, exact: exact, firstBad: bad.length ? bad[0].t : -1, bad: bad.slice(0, 400) },
    lineId: lineId, lineAmb: lineAmb,
    every: EVERY, ticks: ticks, teamLand: teamLand, teamBal: teamBal, teamHumans: teamHumans, teamHusk: teamHusk, hum: hum,
    teams: teams, engineNames: names, allNames: allNames, poolAi: poolAi,
    deathT: deathT, deaths: deaths, leaveT: leaveT, donations: donations, squadCmds: squadCmds, spawnBox: spawnBox,
    ledgerWindow: LW, ledger: led, neighEvery: NE, neigh: neigh, finalBots: finalBots,
    quota: { Y: quotaY, X: quotaX }, quotaLog: quotaLog, boatGifts: boatGifts, boatLands: boatLands, boatEnds: boatEnds, probes: probeOut, trace: traceOut,
    perTick: { t0: firstT, bal: balTick, terr: terrTick },
  };
}
/* eslint-enable no-undef */

const t0 = Date.now();
const h = createHost({ patch: patchAll });
h.run('bx(true)');
h.flushTimers();
h.ctx.__rep = fs.readFileSync(inp.replayPath, 'utf8').trim();
if (!h.run('bC.aMU.zS(window.__rep)')) throw new Error('录像解不开：' + h.log.slice(-3).join(' | '));
h.run('bC.aVq()');
h.flushTimers();
const info = JSON.parse(h.run('JSON.stringify({ku:aE.ku, players:aE.a0E, ke:aE.ke, w:bV.fk, h:bV.fl, map:bV.fF, teams:aE.a0L})'));
const trace = opt('--trace', null);
// 编队名字池：策略源码第一行的 SQUAD_POOL_SET（isOurSquadBot 按它认号）
let pool = [];
try {
  const ssrc = fs.readFileSync('/agent/repos/c136-data/src/strategy/v27-team-c110.js', 'utf8');
  const mm = /const SQUAD_POOL_SET = new Set\(\[(.*?)\]\)/s.exec(ssrc);
  if (mm) pool = JSON.parse('[' + mm[1] + ']').map((s) => String(s).toLowerCase());
} catch (e) { pool = []; }
const cfg = {
  squad: inp.squad, checks: inp.checks, probes: inp.probes || [], every: +opt('--every', 30), to: +opt('--to', 1e9),
  trace: trace ? trace.split(':').map(Number) : null, pool,
};
const fn = h.run('(' + collector.toString() + ')');
const res = fn(cfg);
const out = Object.assign({ matchId: mid, replayPath: inp.replayPath, producer: 'engine-live_game_js(R04 host)', map: String(info.map), wallMs: Date.now() - t0 }, res);
const tr = out.trace;
delete out.trace;
// 只重放到一半（--to）或只为逐拍跟踪（--trace）的运行不覆盖整局的 sim_state.json，另写一个文件
const partial = +opt('--to', 1e9) < 1e9 || !!trace;
fs.writeFileSync(path.join(OUT, mid, partial ? 'sim_state.partial.json' : 'sim_state.json'), JSON.stringify(out));
for (const l of tr) console.log(l);
const c = out.check;
console.log(`${mid}: 真引擎重放到 t=${out.endT}（over=${out.over}，出生阶段后首拍 ${out.firstT}），耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s；真人 ${out.humans}，队 ${out.nTeams}，陆地 ${out.land}；没生效的指令 ${out.rejectedCmds} 条`);
console.log(`日志快照 ${c.points} 条，在重放同一拍找到 (领土, 兵力) 完全相同的我方号 ${c.exact} 条（${c.points ? (100 * c.exact / c.points).toFixed(1) : 0}%），第一条对不上的拍 ${c.firstBad}`);
for (const r of c.bad.slice(0, 8)) console.log(`  对不上：t=${r.t} [${r.name}] 日志 领土 ${r.terr} 兵 ${r.bal} ｜ 最接近的我方号 me=${r.near} 重放 领土 ${r.nearTerr} 兵 ${r.nearBal}`);
const errs = h.log.filter((l) => /ERR|error|Error/.test(l));
if (errs.length) console.log('引擎自己报的错：' + errs.slice(0, 5).join(' | '));
