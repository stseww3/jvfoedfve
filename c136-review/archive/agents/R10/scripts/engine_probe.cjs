// engine_probe.cjs — R10 带探针的真引擎重放。
//
// 规则全部来自线上原文 live_game_js.js（经 R04 的 engine_host.cjs 原样装载）；本脚本只加“读数”探针：
//   1) 给受捐配额对象 ca 开一个只读口子 __q(p) -> [aOX[p], aOY]；
//   2) 包一层指令入口 bB.qi.{i6,qv,iB,iE,i2}，记录每条指令执行前后的余额、配额；
//   3) 包一层 ae.ei（所有陆攻的唯一入账口，真人与内置 AI 都走它），按 90 拍窗口汇总我方号的受攻/出兵；
//   4) 每 90 拍取我方号与各队的领土/余额；我方号出局时记录此前 180 拍的主要进攻方；
//   5) 对日志里每一次捐款尝试，在“决策拍 + L”（L = 0/7/14/21/28）按引擎当时的真实状态
//      计算“若此刻到达会不会被配额拒绝”（只读，不改状态）。
//
// 用法（必须经 run-heavy.sh）：
//   node engine_probe.cjs <jobs.json> <outDir> [--budget 秒]
//     jobs.json: [{mid, replay, ours:[玩家号...], attempts:[[idx,t,donor,pct,to],...]}, ...]
//     已有输出文件的局会跳过；到时间预算就停，重复调用直到全部完成。
'use strict';
const fs = require('fs');
const path = require('path');
const TOOLS = '/agent/repos/c136-data/src/tools';
const { createHost } = require(path.join(TOOLS, 'engine_host.cjs'));
const { patchSource } = require(path.join(TOOLS, 'engine_replay.cjs'));

const LAGS = [0, 7, 14, 21, 28];

function patchAll(src) {
  let s = patchSource(src);
  const a = 'function ca(){var aOX=new Uint16Array(aE.fW);var aOY=0;';
  if (s.split(a).length !== 2) throw new Error('配额对象锚点不唯一或找不到');
  s = s.replace(a, a + 'this.__q=function(p){return [aOX[p],aOY]};');
  return s;
}

function probe(job) {
  const h = createHost({ patch: patchAll });
  h.run('bx(true)');
  h.flushTimers();
  h.ctx.__rep = fs.readFileSync(job.replay, 'utf8').trim();
  if (!h.run('bC.aMU.zS(window.__rep)')) throw new Error('录像解不开');
  h.run('bC.aVq()');
  h.flushTimers();
  h.ctx.__ours = job.ours;
  h.ctx.__attempts = job.attempts || [];
  h.ctx.__lags = LAGS;
  const api = h.run(`(function () {
    var ours = window.__ours, attempts = window.__attempts, LAGS = window.__lags;
    var NP = aE.fW;
    var isOur = new Uint8Array(NP + 1);
    for (var i = 0; i < ours.length; i++) isOur[ours[i]] = 1;
    var R = { cmds: [], dons: [], evals: [], snapT: [], bots: {}, teamTerr: [], teamBal: [], teamN: [], inc: [], out: [], deaths: [], spawn: [] };
    for (var i = 0; i < ours.length; i++) R.bots[ours[i]] = [];
    var qi = bB.qi;
    var o_i0 = qi.i0, o_i6 = qi.i6, o_qv = qi.qv, o_iB = qi.iB, o_iE = qi.iE, o_i2 = qi.i2;
    qi.i0 = function (player, fL) {
      if (isOur[player]) R.spawn.push([player, fL]);
      return o_i0.call(this, player, fL);
    };
    qi.i6 = function (player, jC, k3) {
      var b0 = ah.hb[player];
      o_i6.call(this, player, jC, k3);
      if (isOur[player]) R.cmds.push([bi.kr(), 1, player, jC, k3, b0, ah.hb[player]]);
    };
    qi.iB = function (player, jC, qx) {
      var b0 = ah.hb[player];
      o_iB.call(this, player, jC, qx);
      if (isOur[player]) R.cmds.push([bi.kr(), 3, player, jC, qx, b0, ah.hb[player]]);
    };
    qi.iE = function (player, jC, ns) {
      var b0 = ah.hb[player];
      o_iE.call(this, player, jC, ns);
      if (isOur[player]) R.cmds.push([bi.kr(), 4, player, jC, ns, b0, ah.hb[player]]);
    };
    qi.i2 = function (player, jC, px, k3) {
      var b0 = ah.hb[player];
      o_i2.call(this, player, jC, px, k3);
      if (isOur[player]) R.cmds.push([bi.kr(), 10, player, jC, k3, b0, ah.hb[player]]);
    };
    qi.qv = function (player, jC, qu) {
      var b0 = ah.hb[player], r0 = ah.hb[qu], q0 = ao.__q(qu), t = bi.kr(), rt = ah.hN[qu], dt = ah.hN[player];
      o_qv.call(this, player, jC, qu);
      var q1 = ao.__q(qu);
      R.dons.push([t, player, jC, qu, b0, ah.hb[player], r0, ah.hb[qu], q0[0], q1[0], q0[1], rt, dt, isOur[player], isOur[qu]]);
      if (isOur[player]) R.cmds.push([t, 2, player, jC, qu, b0, ah.hb[player]]);
    };
    // 陆攻入账口：按 (目标号, 窗口) 汇总
    var incMap = new Map(), outMap = new Map();
    var recent = {};            // 我方号 -> Map(attacker -> [lastTick, troops])
    for (var i = 0; i < ours.length; i++) recent[ours[i]] = new Map();
    function isHuman(p) { return p < aE.ku && ah.a6S[p] !== 2; }
    var o_ei = ae.ei;
    ae.ei = function (player, troops, target) {
      var t = bi.kr(), w = Math.floor(t / 90) + 1;
      if (target < NP && isOur[target] && player !== target) {
        var key = target * 4096 + w, e = incMap.get(key);
        if (!e) { e = { hum: 0, humSet: new Map(), ai: 0, aiSet: new Set(), sq: 0, sqSet: new Set() }; incMap.set(key, e); }
        if (isOur[player]) { e.sq += troops; e.sqSet.add(player); }
        else if (isHuman(player)) { e.hum += troops; e.humSet.set(player, (e.humSet.get(player) || 0) + troops); }
        else { e.ai += troops; e.aiSet.add(player); }
        var rm = recent[target], x = rm.get(player);
        if (!x) rm.set(player, [t, troops]); else { if (t - x[0] > 180) x[1] = 0; x[0] = t; x[1] += troops; }
      }
      if (isOur[player]) {
        var key2 = player * 4096 + w, o = outMap.get(key2);
        if (!o) { o = [0, 0, 0, 0, 0]; outMap.set(key2, o); }
        if (target >= NP) o[0] += troops; else if (isOur[target]) o[3] += troops; else if (isHuman(target)) o[1] += troops; else o[2] += troops;
        o[4]++;
      }
      return o_ei.call(this, player, troops, target);
    };
    // 捐款尝试的假设性评估
    var sched = new Map();
    for (var i = 0; i < attempts.length; i++) {
      for (var j = 0; j < LAGS.length; j++) {
        var tt = attempts[i][1] + LAGS[j];
        if (!sched.has(tt)) sched.set(tt, []);
        sched.get(tt).push([i, j]);
      }
    }
    function costOf(to, v, t) {
      if (t >= 3213) return 4 + bO.g0(100 * v, af.ka(to));
      var uv = 1 + bO.g0(aE.ke, 300);
      var k = t < 357 ? 1 : t < 714 ? 4 : t < 1071 ? 10 : t < 2142 ? 30 : 100;
      return 2 + bO.g0(100 * v, k * uv);
    }
    function evalDon(a, j) {
      var player = a[2], pct = a[3], to = a[4], t = bi.kr();
      var B = ah.hb[player];
      var aliveD = bD.gv.hl(player) ? 1 : 0;
      var okRec = (ah.nU[to] !== 0 && !bv.fS(player, to)) ? 1 : 0;
      var fee = bO.g0(64 * B, 1024);
      var v = Math.min(bO.g0(B * (pct + 1), 1024), B - fee);
      var rb = ah.hb[to];
      v = Math.min(v, ah.hN[to] * aE.a6d - rb); v = Math.min(v, aE.a6e - rb); v = Math.max(v, 0);
      var free = (aE.lE || t >= 4284 || bD.gv.kH(to)) ? 1 : 0;
      var q = ao.__q(to);
      R.evals.push([a[0], LAGS[j], B, v, fee, costOf(to, v, t), q[0], q[1], free, aliveD, okRec, ah.hN[to], rb, ah.hN[player]]);
    }
    var alivePrev = {};
    for (var i = 0; i < ours.length; i++) alivePrev[ours[i]] = 1;
    var prevState = {};
    function snapshot(t) {
      R.snapT.push(t);
      var inN = {}, inTr = {};
      for (var p = 0; p < aE.a0E; p++) {
        if (ah.nU[p] === 0) continue;
        var n = ae.gg(p);
        for (var k = 0; k < n; k++) {
          var tg = ae.gl(p, k);
          if (tg < NP && isOur[tg]) { inN[tg] = (inN[tg] || 0) + 1; inTr[tg] = (inTr[tg] || 0) + ae.gm(p, k); }
        }
      }
      for (var i = 0; i < ours.length; i++) {
        var p = ours[i];
        R.bots[p].push([ah.hN[p], ah.hb[p], ah.nU[p], ah.a6S[p], inN[p] || 0, inTr[p] || 0, ae.gg(p), ae.aLB(p)]);
      }
      var nt = aE.a0L + 1, tt = new Array(nt).fill(0), tb = new Array(nt).fill(0), tn = new Array(nt).fill(0);
      for (var p = 0; p < aE.a0E; p++) {
        if (ah.nU[p] === 0) continue;
        var k = bj.fX[p]; if (k >= nt) continue;
        tt[k] += ah.hN[p]; tb[k] += ah.hb[p]; if (p < aE.ku && ah.a6S[p] !== 2) tn[k]++;
      }
      R.teamTerr.push(tt); R.teamBal.push(tb); R.teamN.push(tn);
    }
    function afterTick(t) {
      for (var i = 0; i < ours.length; i++) {
        var p = ours[i];
        if (alivePrev[p] && ah.nU[p] === 0) {
          alivePrev[p] = 0;
          var rm = recent[p], arr = [];
          rm.forEach(function (x, a) { if (t - x[0] <= 180) arr.push([a, a < aE.ku ? (ah.a6S[a] !== 2 ? 1 : 2) : 0, bj.fX[a], x[1], isOur[a]]); });
          arr.sort(function (x, y) { return y[3] - x[3]; });
          var ps = prevState[p] || [0, 0];
          R.deaths.push([t, p, ps[0], ps[1], arr.slice(0, 4)]);
        }
        if (alivePrev[p]) prevState[p] = [ah.hN[p], ah.hb[p]];
      }
      var s = sched.get(t);
      if (s) for (var k = 0; k < s.length; k++) evalDon(attempts[s[k][0]], s[k][1]);
      if (t % 90 === 0) snapshot(t);
    }
    return {
      run: function (deadline) {
        var st = bi.a3I, lastT = -1, steps = 0, ended = 0;
        while (true) {
          if (aE.a38 === 2) { ended = 1; break; }
          st.__step(); steps++;
          if (aE.hx) continue;
          var t = bi.kr();
          if (t === lastT) { if (aE.a38 === 2) { ended = 1; break; } continue; }
          lastT = t;
          afterTick(t);
          if ((steps & 255) === 0 && Date.now() > deadline) break;
        }
        incMap.forEach(function (e, key) {
          var top = -1, topTr = 0;
          e.humSet.forEach(function (tr, a) { if (tr > topTr) { topTr = tr; top = a; } });
          R.inc.push([Math.floor(key / 4096), key % 4096, e.hum, e.humSet.size, e.ai, e.aiSet.size, e.sq, e.sqSet.size, top, topTr]);
        });
        outMap.forEach(function (o, key) { R.out.push([Math.floor(key / 4096), key % 4096, o[0], o[1], o[2], o[3], o[4]]); });
        var names = [], team = [];
        for (var p = 0; p < aE.ku; p++) { names.push(ah.a3o[p]); team.push(bj.fX[p]); }
        R.lastTick = lastT; R.ended = ended; R.names = names; R.team = team;
        R.info = { ku: aE.ku, players: aE.a0E, land: aE.ke, teams: aE.a0L, lC: aE.lC, softCapMax: aE.a7X, hardMul: aE.a6d, hardMax: aE.a6e, fW: aE.fW };
        return JSON.stringify(R);
      }
    };
  })()`);
  const t0 = Date.now();
  // Date 在引擎里被替换成假时钟，这里用宿主时钟做预算：分段跑
  const out = JSON.parse(api.run(Number.MAX_SAFE_INTEGER));
  out.mid = job.mid;
  out.ours = job.ours;
  out.lags = LAGS;
  out.ms = Date.now() - t0;
  return out;
}

function main() {
  const args = process.argv.slice(2);
  const jobs = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  const outDir = args[1];
  const bi = args.indexOf('--budget');
  const budget = (bi >= 0 ? +args[bi + 1] : 80) * 1000;
  fs.mkdirSync(outDir, { recursive: true });
  const t0 = Date.now();
  let done = 0, skipped = 0, left = 0;
  for (const job of jobs) {
    const f = path.join(outDir, job.mid + '.json');
    if (fs.existsSync(f)) { skipped++; continue; }
    if (Date.now() - t0 > budget) { left++; continue; }
    try {
      const out = probe(job);
      fs.writeFileSync(f, JSON.stringify(out));
      done++;
      console.log(`${job.mid} ok lastTick=${out.lastTick} ended=${out.ended} cmds=${out.cmds.length} dons=${out.dons.length} evals=${out.evals.length} ${out.ms}ms`);
    } catch (e) {
      fs.writeFileSync(f, JSON.stringify({ mid: job.mid, error: String(e && e.message ? e.message : e) }));
      console.log(`${job.mid} ERROR ${e && e.message ? e.message : e}`);
      done++;
    }
  }
  console.log(`PROBE done=${done} skipped=${skipped} left=${left}`);
}

if (require.main === module) main();
module.exports = { probe, LAGS };
